package order

import (
	"context"
	"testing"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	ordermodel "request-ranging/executor-balancer/internal/models/order"
)

type fakeProcessor struct {
	snapshot *ordermodel.SnapshotPayload
	status   *ordermodel.StatusChangedPayload
}

func (f *fakeProcessor) ApplySnapshot(_ context.Context, _ eventmodel.Envelope, payload ordermodel.SnapshotPayload) error {
	f.snapshot = &payload
	return nil
}

func (f *fakeProcessor) ApplyStatus(_ context.Context, _ eventmodel.Envelope, payload ordermodel.StatusChangedPayload) error {
	f.status = &payload
	return nil
}

func TestHandleOrderCreated(t *testing.T) {
	processor := &fakeProcessor{}
	handler := New(processor)
	payload := []byte(`{
		"event_id":"event-1","event_type":"OrderCreated","event_version":1,
		"occurred_at":"2026-09-27T10:00:00Z","source":"ais-simulator",
		"payload":{"order_id":"order-1","parent_id":null,"status":"processed",
		"weight":1.5,"version":1,"attributes":{"sum":100,"order_type":"LEGAL_REVIEW","subject":"contract","vip":false}}
	}`)
	if err := handler.Handle(context.Background(), payload); err != nil {
		t.Fatalf("Handle() error = %v", err)
	}
	if processor.snapshot == nil || processor.snapshot.ID != "order-1" {
		t.Fatalf("snapshot = %+v", processor.snapshot)
	}
}
