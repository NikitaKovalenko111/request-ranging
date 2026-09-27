package system

import (
	"context"
	"errors"
	"testing"
	"time"
)

type fakeChecker struct {
	name string
	err  error
}

func (f fakeChecker) Name() string { return f.name }

func (f fakeChecker) Check(context.Context) error { return f.err }

func TestHealthServiceReady(t *testing.T) {
	service := NewHealthService(time.Second, fakeChecker{name: "postgres"})
	result := service.Readiness(context.Background())
	if result.Status != "ready" {
		t.Fatalf("status = %q, want ready", result.Status)
	}
	if result.Checks["postgres"].Status != "up" {
		t.Fatalf("postgres status = %q, want up", result.Checks["postgres"].Status)
	}
}

func TestHealthServiceNotReady(t *testing.T) {
	service := NewHealthService(time.Second, fakeChecker{name: "redis", err: errors.New("connection refused")})
	result := service.Readiness(context.Background())
	if result.Status != "not_ready" {
		t.Fatalf("status = %q, want not_ready", result.Status)
	}
	if result.Checks["redis"].Status != "down" {
		t.Fatalf("redis status = %q, want down", result.Checks["redis"].Status)
	}
}
