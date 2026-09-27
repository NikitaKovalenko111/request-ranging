package config

import (
	"fmt"
	"net"
	"strings"
	"time"
)

type HTTPConfig struct {
	Address           string
	ReadHeaderTimeout time.Duration
	ReadTimeout       time.Duration
	WriteTimeout      time.Duration
	IdleTimeout       time.Duration
}

func loadHTTPConfig() (HTTPConfig, error) {
	readHeaderTimeout, err := durationEnv("HTTP_READ_HEADER_TIMEOUT", 5*time.Second)
	if err != nil {
		return HTTPConfig{}, err
	}
	readTimeout, err := durationEnv("HTTP_READ_TIMEOUT", 10*time.Second)
	if err != nil {
		return HTTPConfig{}, err
	}
	writeTimeout, err := durationEnv("HTTP_WRITE_TIMEOUT", 15*time.Second)
	if err != nil {
		return HTTPConfig{}, err
	}
	idleTimeout, err := durationEnv("HTTP_IDLE_TIMEOUT", 60*time.Second)
	if err != nil {
		return HTTPConfig{}, err
	}

	config := HTTPConfig{
		Address:           envOrDefault("APP_HTTP_ADDR", ":8090"),
		ReadHeaderTimeout: readHeaderTimeout,
		ReadTimeout:       readTimeout,
		WriteTimeout:      writeTimeout,
		IdleTimeout:       idleTimeout,
	}
	if err := validateListenAddress(config.Address); err != nil {
		return HTTPConfig{}, fmt.Errorf("APP_HTTP_ADDR: %w", err)
	}
	return config, nil
}

func validateListenAddress(address string) error {
	if strings.HasPrefix(address, ":") {
		address = "0.0.0.0" + address
	}
	_, port, err := net.SplitHostPort(address)
	if err != nil || port == "" {
		return fmt.Errorf("must use :port or host:port format")
	}
	return nil
}
