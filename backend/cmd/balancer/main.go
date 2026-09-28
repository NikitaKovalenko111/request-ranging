package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"request-ranging/executor-balancer/internal/config"
	"request-ranging/executor-balancer/internal/integration/ais"
	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	"request-ranging/executor-balancer/internal/package/logger"
	"request-ranging/executor-balancer/internal/repository/postgres"
	postgresrepositories "request-ranging/executor-balancer/internal/repository/postgres/repositories"
	redisstorage "request-ranging/executor-balancer/internal/repository/redis"
	redisexecutors "request-ranging/executor-balancer/internal/repository/redis/executors"
	redisreservations "request-ranging/executor-balancer/internal/repository/redis/reservations"
	assignmentservice "request-ranging/executor-balancer/internal/services/assignment"
	decisionservice "request-ranging/executor-balancer/internal/services/decision"
	executorservice "request-ranging/executor-balancer/internal/services/executor"
	orderservice "request-ranging/executor-balancer/internal/services/order"
	systemservice "request-ranging/executor-balancer/internal/services/system"
	httptransport "request-ranging/executor-balancer/internal/transport/http"
	apihandler "request-ranging/executor-balancer/internal/transport/http/handlers/api"
	systemhandler "request-ranging/executor-balancer/internal/transport/http/handlers/system"
	kafkatransport "request-ranging/executor-balancer/internal/transport/kafka"
	decisionhandler "request-ranging/executor-balancer/internal/transport/kafka/handlers/decision"
	executorhandler "request-ranging/executor-balancer/internal/transport/kafka/handlers/executor"
	orderhandler "request-ranging/executor-balancer/internal/transport/kafka/handlers/order"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	cfg, err := config.Load()
	if err != nil {
		return fmt.Errorf("load config: %w", err)
	}

	appLogger := logger.New(cfg.App.LogLevel)
	slog.SetDefault(appLogger)

	postgresClient, err := postgres.New(cfg.Postgres.DSN)
	if err != nil {
		return fmt.Errorf("initialize postgres client: %w", err)
	}
	defer postgresClient.Close()

	redisClient := redisstorage.New(cfg.Redis.Address)
	defer redisClient.Close()

	kafkaClient, err := kafkatransport.New(cfg.Kafka.Brokers, cfg.Kafka.ConsumerGroup)
	if err != nil {
		return fmt.Errorf("initialize kafka client: %w", err)
	}
	defer kafkaClient.Close()

	repositories := postgresrepositories.New(postgresClient.DB())
	bootstrapContext, cancelBootstrap := context.WithTimeout(context.Background(), cfg.App.DependencyCheckTimeout)
	defer cancelBootstrap()
	activeExecutors, err := repositories.Executors.ListActive(bootstrapContext)
	if err != nil {
		return fmt.Errorf("load active executors: %w", err)
	}
	redisExecutorRepository := redisexecutors.New(redisClient.Raw())
	if err := redisExecutorRepository.ReplaceActive(bootstrapContext, activeExecutors); err != nil {
		return fmt.Errorf("restore active executors in redis: %w", err)
	}
	reservationRepository := redisreservations.New(redisClient.Raw(), cfg.Reservation.TTL)
	executorEventService := executorservice.NewService(
		repositories.Executors, redisExecutorRepository, repositories.Events,
	)
	orderEventService := orderservice.NewService(
		repositories.Orders, repositories.Assignments, repositories.Events, reservationRepository,
	)
	executorEventHandler := executorhandler.New(executorEventService)
	orderEventHandler := orderhandler.New(orderEventService)
	decisionService := decisionservice.NewService(
		repositories.Orders,
		repositories.Executors,
		repositories.Assignments,
		repositories.Decisions,
		repositories.DecisionTraces,
		reservationRepository,
	)
	aisClient, err := ais.New(cfg.AIS.BaseURL, cfg.AIS.RequestTimeout)
	if err != nil {
		return fmt.Errorf("initialize AIS client: %w", err)
	}
	assignmentService := assignmentservice.NewService(
		decisionService, repositories.Assignments, reservationRepository, aisClient,
	)
	decisionHandler := decisionhandler.New(func(ctx context.Context, result decisionmodel.Result) error {
		processErr := assignmentService.ProcessDecision(ctx, result)
		if errors.Is(processErr, decisionservice.ErrOrderAlreadyAssigned) {
			appLogger.Info("decision already processed", "order_id", result.OrderID)
			return nil
		}
		if errors.Is(processErr, decisionservice.ErrNoCandidateReserved) {
			appLogger.Warn("no decision candidate reserved", "order_id", result.OrderID)
			return nil
		}
		if processErr != nil {
			return processErr
		}
		appLogger.Info("assignment confirmed", "order_id", result.OrderID)
		return nil
	})
	kafkaHandlers := map[string]kafkatransport.MessageHandler{
		cfg.Kafka.OrderTopic:          orderEventHandler,
		cfg.Kafka.ExecutorTopic:       executorEventHandler,
		cfg.Kafka.DecisionResultTopic: decisionHandler,
	}

	checkers := []systemservice.DependencyChecker{
		postgresClient,
		redisClient,
		kafkaClient,
	}

	healthService := systemservice.NewHealthService(cfg.App.DependencyCheckTimeout, checkers...)
	systemHandler := systemhandler.New(healthService)
	apiHandler := apihandler.New(postgresClient.DB(), redisClient.Raw(), aisClient)
	transportServer := httptransport.NewServer(appLogger, systemHandler, apiHandler)
	server := &http.Server{
		Addr:              cfg.HTTP.Address,
		Handler:           transportServer.Handler(),
		ReadHeaderTimeout: cfg.HTTP.ReadHeaderTimeout,
		ReadTimeout:       cfg.HTTP.ReadTimeout,
		WriteTimeout:      cfg.HTTP.WriteTimeout,
		IdleTimeout:       cfg.HTTP.IdleTimeout,
	}

	signalContext, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go runReservationCleanup(signalContext, appLogger, reservationRepository, cfg.Reservation.TTL)
	go runDailyCounterReset(signalContext, appLogger, redisExecutorRepository, time.Now)

	serverErrors := make(chan error, 1)
	go func() {
		appLogger.Info("http server started", "address", cfg.HTTP.Address)
		serverErrors <- server.ListenAndServe()
	}()
	kafkaErrors := make(chan error, 1)
	go func() {
		appLogger.Info("kafka consumer started",
			"order_topic", cfg.Kafka.OrderTopic,
			"executor_topic", cfg.Kafka.ExecutorTopic,
			"decision_topic", cfg.Kafka.DecisionResultTopic,
		)
		kafkaErrors <- kafkaClient.Consume(signalContext, kafkaHandlers, cfg.Kafka.DeadLetterTopic)
	}()

	select {
	case <-signalContext.Done():
		appLogger.Info("shutdown signal received")
	case serverErr := <-serverErrors:
		if !errors.Is(serverErr, http.ErrServerClosed) {
			return fmt.Errorf("http server: %w", serverErr)
		}
		return nil
	case consumerErr := <-kafkaErrors:
		if consumerErr != nil {
			return fmt.Errorf("decision consumer: %w", consumerErr)
		}
		return nil
	}
	stop()

	shutdownContext, cancel := context.WithTimeout(context.Background(), cfg.App.ShutdownTimeout)
	defer cancel()

	if err := server.Shutdown(shutdownContext); err != nil {
		return fmt.Errorf("graceful shutdown: %w", err)
	}

	appLogger.Info("service stopped")
	return nil
}

type dailyCounterRepository interface {
	ResetProcessedToday(ctx context.Context) (int64, error)
}

func runDailyCounterReset(
	ctx context.Context,
	appLogger *slog.Logger,
	repository dailyCounterRepository,
	now func() time.Time,
) {
	for {
		timer := time.NewTimer(untilNextUTCMidnight(now()))
		select {
		case <-ctx.Done():
			if !timer.Stop() {
				<-timer.C
			}
			return
		case <-timer.C:
			count, err := repository.ResetProcessedToday(ctx)
			if err != nil {
				appLogger.Error("reset daily executor counters", "error", err)
				continue
			}
			appLogger.Info("daily executor counters reset", "executors", count)
		}
	}
}

func untilNextUTCMidnight(value time.Time) time.Duration {
	utc := value.UTC()
	next := time.Date(utc.Year(), utc.Month(), utc.Day()+1, 0, 0, 0, 0, time.UTC)
	return next.Sub(utc)
}

func runReservationCleanup(
	ctx context.Context,
	appLogger *slog.Logger,
	repository *redisreservations.Repository,
	ttl time.Duration,
) {
	interval := ttl / 2
	if interval < time.Second {
		interval = time.Second
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case now := <-ticker.C:
			count, err := repository.CancelExpired(ctx, now, 100)
			if err != nil {
				appLogger.Error("cancel expired reservations", "error", err)
				continue
			}
			if count > 0 {
				appLogger.Info("expired reservations cancelled", "count", count)
			}
		}
	}
}
