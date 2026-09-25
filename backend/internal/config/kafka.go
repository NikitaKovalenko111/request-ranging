package config

import (
	"fmt"
	"strings"
)

type KafkaConfig struct {
	Brokers       []string
	ConsumerGroup string
}

func loadKafkaConfig() (KafkaConfig, error) {
	config := KafkaConfig{
		Brokers:       splitAndTrim(envOrDefault("KAFKA_BROKERS", "localhost:9092")),
		ConsumerGroup: envOrDefault("KAFKA_CONSUMER_GROUP", "executor-balancer-v1"),
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
	return config, nil
}
