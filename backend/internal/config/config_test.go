package config

import (
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	clearEnvironment(t)
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.HTTP.Address != ":8090" {
		t.Fatalf("HTTP.Address = %q, want :8090", cfg.HTTP.Address)
	}
	if cfg.Postgres.DSN != "postgres://executor_balancer:executor_balancer@localhost:5442/executor_balancer?sslmode=disable" {
		t.Fatalf("unexpected Postgres.DSN = %q", cfg.Postgres.DSN)
	}
	if cfg.AIS.RequestTimeout != 12*time.Second {
		t.Fatalf("AIS.RequestTimeout = %s, want 12s", cfg.AIS.RequestTimeout)
	}
	if cfg.Reservation.TTL != 30*time.Second {
		t.Fatalf("Reservation.TTL = %s, want 30s", cfg.Reservation.TTL)
	}
}

func TestLoadRejectsInvalidDuration(t *testing.T) {
	clearEnvironment(t)
	t.Setenv("RESERVATION_TTL", "later")
	if _, err := Load(); err == nil {
		t.Fatal("Load() error = nil, want invalid duration error")
	}
}

func TestLoadSplitsKafkaBrokers(t *testing.T) {
	clearEnvironment(t)
	t.Setenv("KAFKA_BROKERS", "kafka-1:9092, kafka-2:9092")
	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if len(cfg.Kafka.Brokers) != 2 {
		t.Fatalf("len(Kafka.Brokers) = %d, want 2", len(cfg.Kafka.Brokers))
	}
}

func clearEnvironment(t *testing.T) {
	t.Helper()
	keys := []string{
		"APP_HTTP_ADDR", "LOG_LEVEL", "POSTGRES_DSN", "REDIS_ADDR",
		"KAFKA_BROKERS", "KAFKA_CONSUMER_GROUP", "AIS_BASE_URL", "AIS_REQUEST_TIMEOUT",
		"RESERVATION_TTL", "SHUTDOWN_TIMEOUT", "DEPENDENCY_CHECK_TIMEOUT",
		"HTTP_READ_HEADER_TIMEOUT", "HTTP_READ_TIMEOUT", "HTTP_WRITE_TIMEOUT", "HTTP_IDLE_TIMEOUT",
	}
	for _, key := range keys {
		t.Setenv(key, "")
	}
}
