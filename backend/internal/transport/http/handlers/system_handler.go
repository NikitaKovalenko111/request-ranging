package handlers

import (
	"context"
	"encoding/json"
	stdhttp "net/http"

	"request-ranging/executor-balancer/internal/application"
)

type ReadinessProvider interface {
	Readiness(ctx context.Context) application.Readiness
}

type SystemHandler struct {
	readiness ReadinessProvider
}

func NewSystemHandler(readiness ReadinessProvider) *SystemHandler {
	return &SystemHandler{readiness: readiness}
}

func StartSystemHandler(mux *stdhttp.ServeMux, handler *SystemHandler) {
	mux.HandleFunc("GET /health", handler.Health)
	mux.HandleFunc("GET /ready", handler.Ready)
}

func (h *SystemHandler) Health(response stdhttp.ResponseWriter, _ *stdhttp.Request) {
	writeJSON(response, stdhttp.StatusOK, map[string]string{
		"status":  "up",
		"service": "executor-balancer",
	})
}

func (h *SystemHandler) Ready(response stdhttp.ResponseWriter, request *stdhttp.Request) {
	result := h.readiness.Readiness(request.Context())
	statusCode := stdhttp.StatusOK
	if result.Status != "ready" {
		statusCode = stdhttp.StatusServiceUnavailable
	}
	writeJSON(response, statusCode, result)
}

func writeJSON(response stdhttp.ResponseWriter, statusCode int, value any) {
	response.Header().Set("Content-Type", "application/json; charset=utf-8")
	response.WriteHeader(statusCode)
	_ = json.NewEncoder(response).Encode(value)
}
