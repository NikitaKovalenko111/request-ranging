package api

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type orderDTO struct {
	ID                   string     `json:"id"`
	ParentID             *string    `json:"parentId"`
	AssignedExecutorID   *string    `json:"assignedExecutorId"`
	AssignedExecutorName *string    `json:"assignedExecutorName"`
	Sum                  *float64   `json:"sum"`
	ClientMSP            any        `json:"clientMsp"`
	ExecutorMSP          any        `json:"executorMsp"`
	OrderType            string     `json:"orderType"`
	Subject              string     `json:"subject"`
	VIP                  bool       `json:"vip"`
	Weight               float64    `json:"weight"`
	Text                 string     `json:"text"`
	Status               string     `json:"status"`
	AssignmentStatus     string     `json:"assignmentStatus"`
	CreatedAt            time.Time  `json:"createdAt"`
	AssignedAt           *time.Time `json:"assignedAt"`
	ProcessingTimeMS     *int64     `json:"processingTimeMs"`
	Explanation          *string    `json:"explanation"`
}

const orderSelect = `
SELECT o.id, o.parent_id, o.status, o.weight, o.attributes, o.assigned_executor_id,
	o.created_at, a.status, a.executor_id, a.confirmed_at, a.error_message,
	d.processing_time_ms, e.attributes
FROM orders o
LEFT JOIN LATERAL (
	SELECT * FROM assignments WHERE order_id = o.id ORDER BY created_at DESC, id DESC LIMIT 1
) a ON TRUE
LEFT JOIN LATERAL (
	SELECT processing_time_ms FROM decision_traces WHERE order_id = o.id
	ORDER BY created_at DESC, id DESC LIMIT 1
) d ON TRUE
LEFT JOIN executors e ON e.id = COALESCE(o.assigned_executor_id, a.executor_id)`

type rowScanner interface{ Scan(...any) error }

func scanOrder(row rowScanner) (orderDTO, error) {
	var result orderDTO
	var attributes, executorAttributes []byte
	var assignmentStatus, assignmentExecutor sql.NullString
	var assignedAt sql.NullTime
	var errorMessage sql.NullString
	var processingTime sql.NullInt64
	err := row.Scan(&result.ID, &result.ParentID, &result.Status, &result.Weight, &attributes,
		&result.AssignedExecutorID, &result.CreatedAt, &assignmentStatus, &assignmentExecutor,
		&assignedAt, &errorMessage, &processingTime, &executorAttributes)
	if err != nil {
		return result, err
	}
	var values, executorValues map[string]any
	_ = json.Unmarshal(attributes, &values)
	_ = json.Unmarshal(executorAttributes, &executorValues)
	result.Sum = floatValue(values, "sum")
	result.ClientMSP = values["client_msp"]
	result.ExecutorMSP = values["executor_msp"]
	result.OrderType = stringValue(values, "order_type", "UNKNOWN")
	result.Subject = stringValue(values, "subject", "")
	result.VIP = boolValue(values, "vip")
	result.Text = stringValue(values, "text", "")
	if result.AssignedExecutorID == nil && assignmentExecutor.Valid {
		result.AssignedExecutorID = &assignmentExecutor.String
	}
	if result.AssignedExecutorID != nil {
		name := stringValue(executorValues, "display_name", *result.AssignedExecutorID)
		result.AssignedExecutorName = &name
	}
	if assignedAt.Valid {
		result.AssignedAt = &assignedAt.Time
	}
	if processingTime.Valid {
		result.ProcessingTimeMS = &processingTime.Int64
	}
	if errorMessage.Valid {
		result.Explanation = &errorMessage.String
	}
	result.AssignmentStatus = displayAssignmentStatus(assignmentStatus.String, result.AssignedExecutorID != nil)
	return result, nil
}

func displayAssignmentStatus(status string, assigned bool) string {
	switch status {
	case "pending":
		return "pending"
	case "confirmed":
		return "assigned"
	case "failed", "cancelled":
		return "failed"
	default:
		if assigned {
			return "assigned"
		}
		return "unassigned"
	}
}

func (h *Handler) orders(response http.ResponseWriter, request *http.Request) {
	rows, err := h.db.QueryContext(request.Context(), orderSelect+" ORDER BY o.created_at DESC, o.id")
	if err != nil {
		writeError(response, 500, "ORDERS_QUERY_FAILED", err.Error())
		return
	}
	defer rows.Close()
	values := make([]orderDTO, 0)
	for rows.Next() {
		value, scanErr := scanOrder(rows)
		if scanErr != nil {
			writeError(response, 500, "ORDERS_SCAN_FAILED", scanErr.Error())
			return
		}
		if matchesOrder(value, request) {
			values = append(values, value)
		}
	}
	limit, offset := pageValues(request, 20)
	total := len(values)
	if offset > total {
		offset = total
	}
	end := offset + limit
	if end > total {
		end = total
	}
	writeJSON(response, 200, page[orderDTO]{
		Items:      values[offset:end],
		Pagination: pagination{Limit: limit, Offset: offset, Total: total},
	})
}

func (h *Handler) order(response http.ResponseWriter, request *http.Request) {
	value, err := scanOrder(h.db.QueryRowContext(
		request.Context(), orderSelect+" WHERE o.id = $1", request.PathValue("id"),
	))
	if err == sql.ErrNoRows {
		writeError(response, 404, "ORDER_NOT_FOUND", "Order not found")
		return
	}
	if err != nil {
		writeError(response, 500, "ORDER_QUERY_FAILED", err.Error())
		return
	}
	writeJSON(response, 200, value)
}

func (h *Handler) orderOptions(response http.ResponseWriter, request *http.Request) {
	rows, err := h.db.QueryContext(request.Context(), orderSelect+" ORDER BY o.created_at DESC LIMIT 1000")
	if err != nil {
		writeError(response, 500, "ORDERS_QUERY_FAILED", err.Error())
		return
	}
	defer rows.Close()
	items := make([]map[string]any, 0)
	for rows.Next() {
		value, scanErr := scanOrder(rows)
		if scanErr != nil {
			writeError(response, 500, "ORDERS_SCAN_FAILED", scanErr.Error())
			return
		}
		items = append(items, map[string]any{
			"id":     value.ID,
			"label":  fmt.Sprintf("#%s - %s", value.ID, value.OrderType),
			"status": value.Status,
			"vip":    value.VIP,
		})
	}
	writeJSON(response, 200, map[string]any{"items": items})
}

func matchesOrder(value orderDTO, request *http.Request) bool {
	query := request.URL.Query()
	search := strings.ToLower(strings.TrimSpace(query.Get("search")))
	if search != "" && !strings.Contains(strings.ToLower(value.ID+" "+value.Text+" "+value.Subject), search) {
		return false
	}
	if expected := query.Get("status"); expected != "" && value.Status != expected {
		return false
	}
	if expected := query.Get("assignmentStatus"); expected != "" && value.AssignmentStatus != expected {
		return false
	}
	if expected := query.Get("orderType"); expected != "" && value.OrderType != expected {
		return false
	}
	if expected := query.Get("executorId"); expected != "" &&
		(value.AssignedExecutorID == nil || *value.AssignedExecutorID != expected) {
		return false
	}
	if query.Get("hasParent") == "true" && value.ParentID == nil {
		return false
	}
	if expected := query.Get("vip"); expected != "" && fmt.Sprint(value.VIP) != expected {
		return false
	}
	if raw := query.Get("from"); raw != "" {
		if from, err := time.Parse(time.RFC3339, raw); err == nil && value.CreatedAt.Before(from) {
			return false
		}
	}
	if raw := query.Get("to"); raw != "" {
		if to, err := time.Parse(time.RFC3339, raw); err == nil && value.CreatedAt.After(to) {
			return false
		}
	}
	return true
}
