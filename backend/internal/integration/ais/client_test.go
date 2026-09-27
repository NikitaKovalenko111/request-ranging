package ais

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestAssign(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.Header.Get("Idempotency-Key") != "assignment-1" {
			t.Fatalf("Idempotency-Key = %q", request.Header.Get("Idempotency-Key"))
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{
			"assignment_id":"assignment-1","order_id":"order-1","executor_id":"executor-1",
			"status":"confirmed","confirmed_at":"2026-09-27T10:00:01Z"
		}`))
	}))
	defer server.Close()
	client, err := New(server.URL, time.Second)
	if err != nil {
		t.Fatalf("New() error = %v", err)
	}
	result, err := client.Assign(context.Background(), AssignmentRequest{
		AssignmentID: "assignment-1", OrderID: "order-1", ExecutorID: "executor-1",
		DecidedAt: time.Date(2026, 9, 27, 10, 0, 0, 0, time.UTC),
	})
	if err != nil || result.Status != "confirmed" {
		t.Fatalf("Assign() = (%+v, %v)", result, err)
	}
}

func TestAssignReturnsTypedAPIError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusServiceUnavailable)
		_, _ = writer.Write([]byte(`{"code":"UNAVAILABLE","message":"later","retryable":true}`))
	}))
	defer server.Close()
	client, _ := New(server.URL, time.Second)
	_, err := client.Assign(context.Background(), AssignmentRequest{
		AssignmentID: "assignment-1", OrderID: "order-1", ExecutorID: "executor-1", DecidedAt: time.Now(),
	})
	apiError, ok := err.(*APIError)
	if !ok || !apiError.Retryable {
		t.Fatalf("Assign() error = %#v, want retryable APIError", err)
	}
}

func TestGetAssignedExecutor(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.Method != http.MethodGet || request.URL.Path != "/api/v1/orders/order-1" {
			t.Fatalf("unexpected request: %s %s", request.Method, request.URL.Path)
		}
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{
			"order_id":"order-1","status":"processed","assigned_executor_id":"executor-2"
		}`))
	}))
	defer server.Close()
	client, _ := New(server.URL, time.Second)
	executorID, err := client.GetAssignedExecutor(context.Background(), "order-1")
	if err != nil || executorID != "executor-2" {
		t.Fatalf("GetAssignedExecutor() = (%q, %v)", executorID, err)
	}
}
