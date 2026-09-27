package executor

import (
	"context"
	"testing"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	executormodel "request-ranging/executor-balancer/internal/models/executor"
)

type fakeProcessor struct {
	payload *executormodel.SnapshotPayload
}

func (f *fakeProcessor) Apply(_ context.Context, _ eventmodel.Envelope, payload executormodel.SnapshotPayload) error {
	f.payload = &payload
	return nil
}

func TestHandleExecutorUpdatedAllowsIgnoredDailyLimit(t *testing.T) {
	processor := &fakeProcessor{}
	handler := New(processor)
	payload := []byte(`{
		"event_id":"event-1","event_type":"ExecutorUpdated","event_version":1,
		"occurred_at":"2026-09-27T10:00:00Z","source":"ais-simulator",
		"payload":{"executor_id":"executor-1","active":true,"capacity":1.5,
		"daily_limit":100,"version":2,"attributes":{"order_types":["LEGAL_REVIEW"]}}
	}`)
	if err := handler.Handle(context.Background(), payload); err != nil {
		t.Fatalf("Handle() error = %v", err)
	}
	if processor.payload == nil || processor.payload.ID != "executor-1" || processor.payload.DailyLimit == nil {
		t.Fatalf("payload = %+v", processor.payload)
	}
}
