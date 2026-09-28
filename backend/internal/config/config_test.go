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
	if cfg.Kafka.DecisionResultTopic != "decision.result.v1" {
		t.Fatalf("Kafka.DecisionResultTopic = %q, want decision.result.v1", cfg.Kafka.DecisionResultTopic)
	}
	if cfg.Kafka.OrderTopic != "ais.orders.v1" || cfg.Kafka.ExecutorTopic != "ais.executors.v1" {
		t.Fatalf("unexpected AIS topics: order=%q executor=%q", cfg.Kafka.OrderTopic, cfg.Kafka.ExecutorTopic)
	}
	if cfg.Kafka.DeadLetterTopic != "executor-balancer.dead-letter.v1" {
		t.Fatalf("Kafka.DeadLetterTopic = %q", cfg.Kafka.DeadLetterTopic)
	}
	if cfg.Kafka.DecisionWorkers != 12 {
		t.Fatalf("Kafka.DecisionWorkers = %d, want 12", cfg.Kafka.DecisionWorkers)
	}
}

func TestLoadRejectsInvalidDecisionWorkers(t *testing.T) {
	clearEnvironment(t)
	t.Setenv("KAFKA_DECISION_WORKERS", "0")
	if _, err := Load(); err == nil {
		t.Fatal("Load() error = nil, want invalid decision worker count")
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
		"KAFKA_BROKERS", "KAFKA_CONSUMER_GROUP", "KAFKA_ORDER_TOPIC", "KAFKA_EXECUTOR_TOPIC",
		"KAFKA_DECISION_RESULT_TOPIC", "KAFKA_DEAD_LETTER_TOPIC", "AIS_BASE_URL", "AIS_REQUEST_TIMEOUT",
		"KAFKA_DECISION_WORKERS",
		"RESERVATION_TTL", "SHUTDOWN_TIMEOUT", "DEPENDENCY_CHECK_TIMEOUT",
		"HTTP_READ_HEADER_TIMEOUT", "HTTP_READ_TIMEOUT", "HTTP_WRITE_TIMEOUT", "HTTP_IDLE_TIMEOUT",
	}
	for _, key := range keys {
		t.Setenv(key, "")
	}
}
