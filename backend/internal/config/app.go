package config

import (
	"fmt"
	"strings"
	"time"
)

type AppConfig struct {
	LogLevel               string
	ShutdownTimeout        time.Duration
	DependencyCheckTimeout time.Duration
}

func loadAppConfig() (AppConfig, error) {
	shutdownTimeout, err := durationEnv("SHUTDOWN_TIMEOUT", 10*time.Second)
	if err != nil {
		return AppConfig{}, err
	}
	dependencyCheckTimeout, err := durationEnv("DEPENDENCY_CHECK_TIMEOUT", 2*time.Second)
	if err != nil {
		return AppConfig{}, err
	}

	config := AppConfig{
		LogLevel:               strings.ToLower(envOrDefault("LOG_LEVEL", "info")),
		ShutdownTimeout:        shutdownTimeout,
		DependencyCheckTimeout: dependencyCheckTimeout,
	}
	if config.LogLevel != "debug" && config.LogLevel != "info" && config.LogLevel != "warn" && config.LogLevel != "error" {
		return AppConfig{}, fmt.Errorf("LOG_LEVEL must be debug, info, warn or error")
	}
	return config, nil
}
