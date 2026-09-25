package config

import "time"

type ReservationConfig struct {
	TTL time.Duration
}

func loadReservationConfig() (ReservationConfig, error) {
	ttl, err := durationEnv("RESERVATION_TTL", 30*time.Second)
	if err != nil {
		return ReservationConfig{}, err
	}
	return ReservationConfig{TTL: ttl}, nil
}
