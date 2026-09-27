package config

import (
	"fmt"
	"net/url"
)

type PostgresConfig struct {
	DSN string
}

func loadPostgresConfig() (PostgresConfig, error) {
	config := PostgresConfig{
		DSN: envOrDefault("POSTGRES_DSN", "postgres://executor_balancer:executor_balancer@localhost:5442/executor_balancer?sslmode=disable"),
	}
	parsed, err := url.Parse(config.DSN)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" || parsed.Path == "" {
		return PostgresConfig{}, fmt.Errorf("POSTGRES_DSN must be a valid PostgreSQL URL")
	}
	return config, nil
}
