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
	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	"request-ranging/executor-balancer/internal/package/logger"
	"request-ranging/executor-balancer/internal/repository/postgres"
	postgresrepositories "request-ranging/executor-balancer/internal/repository/postgres/repositories"
	redisstorage "request-ranging/executor-balancer/internal/repository/redis"
	redisexecutors "request-ranging/executor-balancer/internal/repository/redis/executors"
	redisreservations "request-ranging/executor-balancer/internal/repository/redis/reservations"
	decisionservice "request-ranging/executor-balancer/internal/services/decision"
	systemservice "request-ranging/executor-balancer/internal/services/system"
	httptransport "request-ranging/executor-balancer/internal/transport/http"
	systemhandler "request-ranging/executor-balancer/internal/transport/http/handlers/system"
	kafkatransport "request-ranging/executor-balancer/internal/transport/kafka"
	decisionhandler "request-ranging/executor-balancer/internal/transport/kafka/handlers/decision"
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
	decisionService := decisionservice.NewService(
		repositories.Orders,
		repositories.Executors,
		repositories.Assignments,
		repositories.Decisions,
		repositories.DecisionTraces,
		reservationRepository,
	)
	decisionHandler := decisionhandler.New(func(ctx context.Context, result decisionmodel.Result) error {
		outcome, processErr := decisionService.Process(ctx, result)
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
		appLogger.Info("executor reserved",
			"order_id", result.OrderID,
			"executor_id", outcome.Candidate.ExecutorID,
			"assignment_id", outcome.Assignment.ID,
		)
		return nil
	})

	checkers := []systemservice.DependencyChecker{
		postgresClient,
		redisClient,
		kafkaClient,
	}

	healthService := systemservice.NewHealthService(cfg.App.DependencyCheckTimeout, checkers...)
	systemHandler := systemhandler.New(healthService)
	transportServer := httptransport.NewServer(appLogger, systemHandler)
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

	serverErrors := make(chan error, 1)
	go func() {
		appLogger.Info("http server started", "address", cfg.HTTP.Address)
		serverErrors <- server.ListenAndServe()
	}()
	kafkaErrors := make(chan error, 1)
	go func() {
		appLogger.Info("decision consumer started", "topic", cfg.Kafka.DecisionResultTopic)
		kafkaErrors <- kafkaClient.Consume(signalContext, cfg.Kafka.DecisionResultTopic, decisionHandler)
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
