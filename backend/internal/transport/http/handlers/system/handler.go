package system

import (
	"context"
	"encoding/json"
	stdhttp "net/http"

	systemservice "request-ranging/executor-balancer/internal/services/system"
)

type ReadinessProvider interface {
	Readiness(ctx context.Context) systemservice.Readiness
}

type Handler struct {
	readiness ReadinessProvider
}

func New(readiness ReadinessProvider) *Handler {
	return &Handler{readiness: readiness}
}

func (h *Handler) Health(response stdhttp.ResponseWriter, _ *stdhttp.Request) {
	writeJSON(response, stdhttp.StatusOK, map[string]string{
		"status":  "up",
		"service": "executor-balancer",
	})
}

func (h *Handler) Ready(response stdhttp.ResponseWriter, request *stdhttp.Request) {
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
