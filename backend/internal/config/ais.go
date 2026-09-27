package config

import (
	"fmt"
	"net/url"
	"time"
)

type AISConfig struct {
	BaseURL        string
	RequestTimeout time.Duration
}

func loadAISConfig() (AISConfig, error) {
	requestTimeout, err := durationEnv("AIS_REQUEST_TIMEOUT", 12*time.Second)
	if err != nil {
		return AISConfig{}, err
	}
	config := AISConfig{
		BaseURL:        envOrDefault("AIS_BASE_URL", "http://localhost:8091"),
		RequestTimeout: requestTimeout,
	}
	parsed, err := url.ParseRequestURI(config.BaseURL)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return AISConfig{}, fmt.Errorf("AIS_BASE_URL must be an absolute URL")
	}
	return config, nil
}
