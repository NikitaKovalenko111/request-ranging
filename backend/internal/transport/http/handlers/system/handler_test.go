package system

import (
	"context"
	stdhttp "net/http"
	"net/http/httptest"
	"strings"
	"testing"

	systemservice "request-ranging/executor-balancer/internal/services/system"
)

type fakeReadiness struct{ result systemservice.Readiness }

func (f fakeReadiness) Readiness(context.Context) systemservice.Readiness { return f.result }

func TestHealth(t *testing.T) {
	handler := New(fakeReadiness{})
	request := httptest.NewRequest(stdhttp.MethodGet, "/health", nil)
	response := httptest.NewRecorder()
	handler.Health(response, request)
	if response.Code != stdhttp.StatusOK {
		t.Fatalf("status = %d, want 200", response.Code)
	}
	if !strings.Contains(response.Body.String(), `"status":"up"`) {
		t.Fatalf("body = %q, want status up", response.Body.String())
	}
}

func TestReadyReturnsServiceUnavailable(t *testing.T) {
	handler := New(fakeReadiness{result: systemservice.Readiness{Status: "not_ready"}})
	request := httptest.NewRequest(stdhttp.MethodGet, "/ready", nil)
	response := httptest.NewRecorder()
	handler.Ready(response, request)
	if response.Code != stdhttp.StatusServiceUnavailable {
		t.Fatalf("status = %d, want 503", response.Code)
	}
}
