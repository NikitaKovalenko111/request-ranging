package http

import (
	"context"
	"io"
	"log/slog"
	stdhttp "net/http"
	"net/http/httptest"
	"testing"

	systemservice "request-ranging/executor-balancer/internal/services/system"
	systemhandler "request-ranging/executor-balancer/internal/transport/http/handlers/system"
)

type fakeReadiness struct {
	result systemservice.Readiness
}

func (f fakeReadiness) Readiness(context.Context) systemservice.Readiness { return f.result }

func TestServerRegistersSystemRoutes(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	systemHandler := systemhandler.New(fakeReadiness{
		result: systemservice.Readiness{Status: "ready", Checks: map[string]systemservice.DependencyStatus{}},
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
