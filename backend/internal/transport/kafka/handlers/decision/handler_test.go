package decision

import (
	"context"
	"testing"

	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
)

func TestHandle(t *testing.T) {
	called := false
	handler := New(func(_ context.Context, result decisionmodel.Result) error {
		called = true
		if result.OrderID != 42 {
			t.Fatalf("order_id = %d, want 42", result.OrderID)
		}
		return nil
	})
	payload := []byte(`{
		"event_type":"ExecutorDecisionCompleted","event_version":1,
		"occurred_at":"2026-09-27T10:00:00Z","order_id":42,
		"balanced_candidates":[{
			"executor_id":"7","rank":1,"ml_score":0.82,"effective_load":0.2,
			"capacity":1,"active_count":1,"pending_count":0,"processed_today":5,
			"last_assignment_at":"2026-09-27T09:59:00Z"
		}]
	}`)
	if err := handler.Handle(context.Background(), payload); err != nil {
		t.Fatalf("Handle() error = %v", err)
	}
	if !called {
		t.Fatal("processor was not called")
	}
}

func TestHandleRejectsUnknownField(t *testing.T) {
	handler := New(func(context.Context, decisionmodel.Result) error { return nil })
	payload := []byte(`{
		"event_type":"ExecutorDecisionCompleted","event_version":1,
		"occurred_at":"2026-09-27T10:00:00Z","order_id":42,
		"unexpected":true,"balanced_candidates":[]
	}`)
	if err := handler.Handle(context.Background(), payload); err == nil {
		t.Fatal("Handle() error = nil, want unknown field error")
	}
}
