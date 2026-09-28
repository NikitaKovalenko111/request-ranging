package kafka

import (
	"context"
	"errors"
	"sync/atomic"
	"testing"
	"time"

	"github.com/twmb/franz-go/pkg/kgo"
)

type retryHandler struct{ calls atomic.Int32 }

func (h *retryHandler) Handle(context.Context, []byte) error {
	if h.calls.Add(1) == 1 {
		return errors.New("temporary failure")
	}
	return nil
}

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

func TestProcessRecordRetriesTransientFailure(t *testing.T) {
	handler := new(retryHandler)
	client := new(Client)
	if err := client.processRecord(
		context.Background(), handler, "unused", &kgo.Record{Value: []byte("payload")},
	); err != nil {
		t.Fatalf("processRecord() error = %v", err)
	}
	if calls := handler.calls.Load(); calls != 2 {
		t.Fatalf("handler calls = %d, want 2", calls)
	}
}
