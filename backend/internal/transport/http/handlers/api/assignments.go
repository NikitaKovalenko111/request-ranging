package api

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"time"
)

func (h *Handler) assignment(response http.ResponseWriter, request *http.Request) {
	orderID := request.PathValue("orderID")
	var id, executorID, status string
	var createdAt time.Time
	var confirmedAt sql.NullTime
	var errorMessage sql.NullString
	err := h.db.QueryRowContext(request.Context(), `
		SELECT id, executor_id, status, created_at, confirmed_at, error_message
		FROM assignments WHERE order_id = $1 ORDER BY created_at DESC, id DESC LIMIT 1
	`, orderID).Scan(&id, &executorID, &status, &createdAt, &confirmedAt, &errorMessage)
	if err != nil && err != sql.ErrNoRows {
		writeError(response, 500, "ASSIGNMENT_QUERY_FAILED", err.Error())
		return
	}
	var assignment any
	if err == nil {
		var confirmed any
		if confirmedAt.Valid {
			confirmed = confirmedAt.Time
		}
		var explanation any
		if errorMessage.Valid {
			explanation = errorMessage.String
		}
		assignment = map[string]any{
			"orderId":          orderID,
			"executorId":       executorID,
			"executorName":     h.executorName(request, executorID),
			"status":           displayAssignmentStatus(status, status == "confirmed"),
			"createdAt":        createdAt,
			"reservedAt":       createdAt,
			"confirmedAt":      confirmed,
			"processingTimeMs": nil,
			"explanation":      explanation,
		}
	}
	trace, traceErr := h.decisionTrace(request, orderID)
	if traceErr != nil {
		writeError(response, 500, "TRACE_QUERY_FAILED", traceErr.Error())
		return
	}
	writeJSON(response, 200, map[string]any{"assignment": assignment, "decisionTrace": trace})
}

func (h *Handler) executorName(request *http.Request, id string) string {
	var attributes []byte
	if err := h.db.QueryRowContext(request.Context(), "SELECT attributes FROM executors WHERE id = $1", id).Scan(&attributes); err != nil {
		return id
	}
	var values map[string]any
	_ = json.Unmarshal(attributes, &values)
	return stringValue(values, "display_name", id)
}

func (h *Handler) decisionTrace(request *http.Request, orderID string) (any, error) {
	var raw []byte
	var duration int64
	var createdAt time.Time
	err := h.db.QueryRowContext(request.Context(), `
		SELECT trace, processing_time_ms, created_at FROM decision_traces
		WHERE order_id = $1 ORDER BY created_at DESC, id DESC LIMIT 1
	`, orderID).Scan(&raw, &duration, &createdAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var data map[string]any
	if err := json.Unmarshal(raw, &data); err != nil {
		return nil, err
	}
	return h.tracePayload(request, orderID, duration, createdAt, data), nil
}

func (h *Handler) tracePayload(request *http.Request, orderID string, duration int64, created time.Time, data map[string]any) map[string]any {
	rawCandidates, _ := data["balanced_candidates"].([]any)
	attempts, _ := data["reservation_attempts"].([]any)
	attemptStatus := make(map[string]string)
	for _, item := range attempts {
		value, _ := item.(map[string]any)
		attemptStatus[stringValue(value, "executor_id", "")] = stringValue(value, "status", "")
	}
	selected, _ := data["selected_executor_id"].(string)
	candidates := make([]map[string]any, 0, len(rawCandidates))
	for _, item := range rawCandidates {
		value, _ := item.(map[string]any)
		executorID := stringValue(value, "executor_id", "")
		result := "SKIPPED"
		switch attemptStatus[executorID] {
		case "reserved":
			result = "SUCCESS"
		case "busy", "inactive":
			result = "CONFLICT"
		}
		candidates = append(candidates, map[string]any{
			"executorId":        executorID,
			"executorName":      h.executorName(request, executorID),
			"active":            attemptStatus[executorID] != "inactive",
			"passedRules":       true,
			"failedRules":       []any{},
			"dailyLimitReached": false,
			"rankScore":         value["ml_score"],
			"confirmedWeight":   value["active_count"],
			"pendingWeight":     value["pending_count"],
			"effectiveLoad":     value["effective_load"],
			"reservationResult": result,
			"selected":          executorID == selected,
		})
	}
	explanation := "No executor could be reserved"
	if selected != "" {
		explanation = "Executor selected after rules, ranking and atomic load reservation"
	}
	count := len(candidates)
	output := 0
	if selected != "" {
		output = 1
	}
	return map[string]any{
		"orderId":            orderID,
		"timestamp":          created,
		"processingTimeMs":   duration,
		"modelVersion":       "ranker-v2",
		"rulesVersion":       "redis:rules:active",
		"totalExecutors":     count,
		"activeExecutors":    count,
		"eligibleExecutors":  count,
		"topKExecutors":      count,
		"selectedExecutorId": nullableString(selected),
		"explanation":        explanation,
		"stages": []map[string]any{
			{"code": "RANKING", "label": "Ranking and balancing", "inputCount": count, "outputCount": count, "durationMs": nil},
			{"code": "RESERVATION", "label": "Atomic reservation", "inputCount": count, "outputCount": output, "durationMs": duration},
		},
		"parentReuse": map[string]any{
			"attempted": false, "parentOrderId": nil, "previousExecutorId": nil,
			"previousExecutorName": nil, "previousExecutorActive": nil,
			"parametersMatched": nil, "dailyLimitIgnored": false, "reused": false, "reason": nil,
		},
		"candidates": candidates,
	}
}

func nullableString(value string) any {
	if value == "" {
		return nil
	}
	return value
}
