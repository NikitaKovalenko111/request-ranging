package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestRuleSchemaRoute(t *testing.T) {
	mux := http.NewServeMux()
	Register(mux, &Handler{})
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/api/v1/rule-schema", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusOK)
	}
	var payload struct {
		Version        string           `json:"version"`
		OrderFields    []map[string]any `json:"orderFields"`
		ExecutorFields []map[string]any `json:"executorFields"`
	}
	if err := json.NewDecoder(response.Body).Decode(&payload); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if payload.Version != "1" || len(payload.OrderFields) == 0 || len(payload.ExecutorFields) == 0 {
		t.Fatalf("unexpected schema: %+v", payload)
	}
}

func TestUnknownAPIRoute(t *testing.T) {
	mux := http.NewServeMux()
	Register(mux, &Handler{})
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/api/v1/unknown", nil))
	if response.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusNotFound)
	}
}
