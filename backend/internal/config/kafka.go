package config

import (
	"fmt"
	"strconv"
	"strings"
)

type KafkaConfig struct {
	Brokers             []string
	ConsumerGroup       string
	OrderTopic          string
	ExecutorTopic       string
	DecisionResultTopic string
	DeadLetterTopic     string
	DecisionWorkers     int
}

func loadKafkaConfig() (KafkaConfig, error) {
	config := KafkaConfig{
		Brokers:             splitAndTrim(envOrDefault("KAFKA_BROKERS", "localhost:9092")),
		ConsumerGroup:       envOrDefault("KAFKA_CONSUMER_GROUP", "executor-balancer-v1"),
		OrderTopic:          envOrDefault("KAFKA_ORDER_TOPIC", "ais.orders.v1"),
		ExecutorTopic:       envOrDefault("KAFKA_EXECUTOR_TOPIC", "ais.executors.v1"),
		DecisionResultTopic: envOrDefault("KAFKA_DECISION_RESULT_TOPIC", "decision.result.v1"),
		DeadLetterTopic:     envOrDefault("KAFKA_DEAD_LETTER_TOPIC", "executor-balancer.dead-letter.v1"),
		DecisionWorkers:     12,
	}
	if raw := strings.TrimSpace(envOrDefault("KAFKA_DECISION_WORKERS", "12")); raw != "" {
		workers, err := strconv.Atoi(raw)
		if err != nil || workers < 1 || workers > 100 {
			return KafkaConfig{}, fmt.Errorf("KAFKA_DECISION_WORKERS must be an integer between 1 and 100")
		}
		config.DecisionWorkers = workers
	}
	if len(config.Brokers) == 0 {
		return KafkaConfig{}, fmt.Errorf("KAFKA_BROKERS must contain at least one broker")
	}
	for _, broker := range config.Brokers {
		if err := validateHostPort("KAFKA_BROKERS", broker); err != nil {
			return KafkaConfig{}, err
		}
	}
	if strings.TrimSpace(config.ConsumerGroup) == "" {
		return KafkaConfig{}, fmt.Errorf("KAFKA_CONSUMER_GROUP must not be empty")
	}
	for name, topic := range map[string]string{
		"KAFKA_ORDER_TOPIC":           config.OrderTopic,
		"KAFKA_EXECUTOR_TOPIC":        config.ExecutorTopic,
		"KAFKA_DECISION_RESULT_TOPIC": config.DecisionResultTopic,
		"KAFKA_DEAD_LETTER_TOPIC":     config.DeadLetterTopic,
	} {
		if strings.TrimSpace(topic) == "" {
			return KafkaConfig{}, fmt.Errorf("%s must not be empty", name)
		}
	}
	return config, nil
}
