package api

import (
	"context"
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"

	redisclient "github.com/redis/go-redis/v9"
)

const rulesKey = "rules:active"

type executorControl interface {
	SetExecutorActive(context.Context, string, bool) error
}

type Handler struct {
	db    *sql.DB
	redis *redisclient.Client
	ais   executorControl
}

func New(db *sql.DB, redis *redisclient.Client, ais executorControl) *Handler {
	return &Handler{db: db, redis: redis, ais: ais}
}

func Register(mux *http.ServeMux, h *Handler) {
	mux.HandleFunc("GET /api/v1/dashboard", h.dashboard)
	mux.HandleFunc("GET /api/v1/metrics", h.dashboard)
	mux.HandleFunc("GET /api/v1/orders", h.orders)
	mux.HandleFunc("GET /api/v1/orders/options", h.orderOptions)
	mux.HandleFunc("GET /api/v1/orders/{id}", h.order)
	mux.HandleFunc("GET /api/v1/executors", h.executors)
	mux.HandleFunc("GET /api/v1/executors/{id}", h.executor)
	mux.HandleFunc("PATCH /api/v1/executors/{id}", h.patchExecutor)
	mux.HandleFunc("GET /api/v1/assignments/{orderID}", h.assignment)
	registerRuleRoutes(mux, h)
}

func registerRuleRoutes(mux *http.ServeMux, h *Handler) {
	mux.HandleFunc("GET /api/v1/rule-schema", h.ruleSchema)
	mux.HandleFunc("GET /api/v1/rules", h.rules)
	mux.HandleFunc("POST /api/v1/rules", h.createRule)
	mux.HandleFunc("PUT /api/v1/rules/{id}", h.updateRule)
	mux.HandleFunc("PATCH /api/v1/rules/{id}", h.patchRule)
	mux.HandleFunc("DELETE /api/v1/rules/{id}", h.deleteRule)
	mux.HandleFunc("POST /api/v1/rules/test", h.testRule)
}

type pagination struct {
	Limit  int `json:"limit"`
	Offset int `json:"offset"`
	Total  int `json:"total"`
}

type page[T any] struct {
	Items      []T        `json:"items"`
	Pagination pagination `json:"pagination"`
}

func pageValues(request *http.Request, fallback int) (int, int) {
	limit, _ := strconv.Atoi(request.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(request.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = fallback
	}
	if limit > 1000 {
		limit = 1000
	}
	if offset < 0 {
		offset = 0
	}
	return limit, offset
}

func decode(request *http.Request, target any) error {
	decoder := json.NewDecoder(request.Body)
	decoder.DisallowUnknownFields()
	return decoder.Decode(target)
}

func writeJSON(response http.ResponseWriter, status int, value any) {
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(status)
	_ = json.NewEncoder(response).Encode(value)
}

func writeError(response http.ResponseWriter, status int, code, message string) {
	writeJSON(response, status, map[string]any{
		"error": map[string]any{"code": code, "message": message},
	})
}

func stringValue(values map[string]any, key, fallback string) string {
	value, ok := values[key].(string)
	if !ok || value == "" {
		return fallback
	}
	return value
}

func floatValue(values map[string]any, key string) *float64 {
	value, ok := values[key].(float64)
	if !ok {
		return nil
	}
	return &value
}

func boolValue(values map[string]any, key string) bool {
	value, _ := values[key].(bool)
	return value
}
