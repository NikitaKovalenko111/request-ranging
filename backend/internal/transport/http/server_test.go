package http

import (
	"context"
	"io"
	"log/slog"
	stdhttp "net/http"
	"net/http/httptest"
	"testing"

	"request-ranging/executor-balancer/internal/application"
	"request-ranging/executor-balancer/internal/transport/http/handlers"
)

type fakeReadiness struct {
	result application.Readiness
}

func (f fakeReadiness) Readiness(context.Context) application.Readiness { return f.result }

func TestServerRegistersSystemRoutes(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	systemHandler := handlers.NewSystemHandler(fakeReadiness{
		result: application.Readiness{Status: "ready", Checks: map[string]application.DependencyStatus{}},
	})
	server := NewServer(logger, systemHandler)

	for _, path := range []string{"/health", "/ready"} {
		request := httptest.NewRequest(stdhttp.MethodGet, path, nil)
		response := httptest.NewRecorder()
		server.Handler().ServeHTTP(response, request)
		if response.Code != stdhttp.StatusOK {
			t.Fatalf("GET %s status = %d, want 200", path, response.Code)
		}
	}
}
