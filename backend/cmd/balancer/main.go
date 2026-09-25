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

	"request-ranging/executor-balancer/internal/application"
	"request-ranging/executor-balancer/internal/config"
	"request-ranging/executor-balancer/internal/package/logger"
	"request-ranging/executor-balancer/internal/repository/postgres"
	redisstorage "request-ranging/executor-balancer/internal/repository/redis"
	httptransport "request-ranging/executor-balancer/internal/transport/http"
	"request-ranging/executor-balancer/internal/transport/http/handlers"
	kafkatransport "request-ranging/executor-balancer/internal/transport/kafka"
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

	checkers := []application.DependencyChecker{
		postgresClient,
		redisClient,
		kafkaClient,
	}

	healthService := application.NewHealthService(cfg.App.DependencyCheckTimeout, checkers...)
	systemHandler := handlers.NewSystemHandler(healthService)
	transportServer := httptransport.NewServer(appLogger, systemHandler)
	server := &http.Server{
		Addr:              cfg.HTTP.Address,
		Handler:           transportServer.Handler(),
		ReadHeaderTimeout: cfg.HTTP.ReadHeaderTimeout,
		ReadTimeout:       cfg.HTTP.ReadTimeout,
		WriteTimeout:      cfg.HTTP.WriteTimeout,
		IdleTimeout:       cfg.HTTP.IdleTimeout,
	}

	serverErrors := make(chan error, 1)
	go func() {
		appLogger.Info("http server started", "address", cfg.HTTP.Address)
		serverErrors <- server.ListenAndServe()
	}()

	signalContext, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	select {
	case <-signalContext.Done():
		appLogger.Info("shutdown signal received")
	case serverErr := <-serverErrors:
		if !errors.Is(serverErr, http.ErrServerClosed) {
			return fmt.Errorf("http server: %w", serverErr)
		}
		return nil
	}

	shutdownContext, cancel := context.WithTimeout(context.Background(), cfg.App.ShutdownTimeout)
	defer cancel()

	if err := server.Shutdown(shutdownContext); err != nil {
		return fmt.Errorf("graceful shutdown: %w", err)
	}

	appLogger.Info("service stopped")
	return nil
}
