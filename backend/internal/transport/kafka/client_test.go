package kafka

import (
	"context"
	"testing"
	"time"
)

func TestWaitForRetryStopsWithContext(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	started := time.Now()
	if err := waitForRetry(ctx, time.Minute); err == nil {
		t.Fatal("waitForRetry() error = nil")
	}
	if time.Since(started) > time.Second {
		t.Fatal("waitForRetry() did not stop promptly")
	}
}
