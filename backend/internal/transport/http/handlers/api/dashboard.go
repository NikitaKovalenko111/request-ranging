package api

import (
	"encoding/json"
	"math"
	"net/http"
	"time"
)

type executorLoadDTO struct {
	ExecutorID      string  `json:"executorId"`
	ExecutorName    string  `json:"executorName"`
	CapacityWeight  float64 `json:"capacityWeight"`
	ConfirmedWeight float64 `json:"confirmedWeight"`
	PendingWeight   float64 `json:"pendingWeight"`
	EffectiveLoad   float64 `json:"effectiveLoad"`
	DailyCount      int     `json:"dailyCount"`
	MaxDailyLimit   any     `json:"maxDailyLimit"`
}

func (h *Handler) dashboard(response http.ResponseWriter, request *http.Request) {
	to := time.Now().UTC()
	from := to.Add(-time.Hour)
	if value, err := time.Parse(time.RFC3339, request.URL.Query().Get("from")); err == nil {
		from = value
	}
	if value, err := time.Parse(time.RFC3339, request.URL.Query().Get("to")); err == nil {
		to = value
	}
	var total, assigned, failed, active, pending int
	var average, p95 float64
	err := h.db.QueryRowContext(request.Context(), `
		SELECT
			COUNT(DISTINCT o.id),
			COUNT(DISTINCT o.id) FILTER (WHERE o.assigned_executor_id IS NOT NULL),
			COUNT(DISTINCT o.id) FILTER (WHERE a.status IN ('failed', 'cancelled')),
			(SELECT COUNT(*) FROM executors WHERE active),
			COUNT(DISTINCT a.id) FILTER (WHERE a.status = 'pending'),
			COALESCE(AVG(d.processing_time_ms), 0),
			COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY d.processing_time_ms), 0)
		FROM orders o
		LEFT JOIN assignments a ON a.order_id = o.id
		LEFT JOIN decision_traces d ON d.order_id = o.id
		WHERE o.created_at BETWEEN $1 AND $2
	`, from, to).Scan(&total, &assigned, &failed, &active, &pending, &average, &p95)
	if err != nil {
		writeError(response, 500, "DASHBOARD_QUERY_FAILED", err.Error())
		return
	}
	loads, err := h.dashboardLoads(request)
	if err != nil {
		writeError(response, 500, "DASHBOARD_LOAD_FAILED", err.Error())
		return
	}
	timeline, err := h.dashboardTimeline(request, from, to)
	if err != nil {
		writeError(response, 500, "DASHBOARD_TIMELINE_FAILED", err.Error())
		return
	}
	latest, err := h.latestAssignments(request)
	if err != nil {
		writeError(response, 500, "DASHBOARD_ASSIGNMENTS_FAILED", err.Error())
		return
	}
	hours := math.Max(to.Sub(from).Hours(), 1.0/3600)
	writeJSON(response, 200, map[string]any{
		"summary": map[string]any{
			"periodFrom": from, "periodTo": to, "generatedAt": time.Now().UTC(),
			"totalOrders": total, "assignedOrders": assigned, "unassignedOrders": total - assigned,
			"failedOrders": failed, "activeExecutors": active, "pendingAssignments": pending,
			"ordersPerSecond": float64(total) / (hours * 3600), "averageAssignmentTimeMs": average,
			"p95AssignmentTimeMs": p95, "ruleRejections": 0,
			"reservationConflicts": 0, "errors": failed,
		},
		"timeline":          timeline,
		"executorLoads":     loads,
		"fairness":          fairness(loads),
		"latestAssignments": latest,
	})
}

func (h *Handler) dashboardLoads(request *http.Request) ([]executorLoadDTO, error) {
	rows, err := h.db.QueryContext(request.Context(), executorSelect+" WHERE e.active ORDER BY e.id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	values := make([]executorLoadDTO, 0)
	for rows.Next() {
		value, scanErr := scanExecutor(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		values = append(values, executorLoadDTO{
			ExecutorID: value.ID, ExecutorName: value.DisplayName,
			CapacityWeight: value.CapacityWeight, ConfirmedWeight: value.ConfirmedWeight,
			PendingWeight: value.PendingWeight, EffectiveLoad: value.EffectiveLoad,
			DailyCount: value.DailyCount, MaxDailyLimit: value.MaxDailyLimit,
		})
	}
	return values, rows.Err()
}

func fairness(values []executorLoadDTO) map[string]any {
	if len(values) == 0 {
		return map[string]any{"kind": "JAIN_INDEX", "value": 1, "target": 0.98, "description": "No active executors"}
	}
	sum, squares := 0.0, 0.0
	for _, value := range values {
		sum += value.EffectiveLoad
		squares += value.EffectiveLoad * value.EffectiveLoad
	}
	index := 1.0
	if squares > 0 {
		index = sum * sum / (float64(len(values)) * squares)
	}
	return map[string]any{"kind": "JAIN_INDEX", "value": index, "target": 0.98, "description": "Jain fairness index for effective load"}
}

func (h *Handler) dashboardTimeline(request *http.Request, from, to time.Time) ([]map[string]any, error) {
	bucket := request.URL.Query().Get("bucket")
	if bucket != "hour" && bucket != "day" {
		bucket = "minute"
	}
	rows, err := h.db.QueryContext(request.Context(), `
		SELECT date_trunc($3, created_at) point, COUNT(*),
			COUNT(*) FILTER (WHERE assigned_executor_id IS NOT NULL),
			COUNT(*) FILTER (WHERE status = 'reject')
		FROM orders WHERE created_at BETWEEN $1 AND $2
		GROUP BY point ORDER BY point
	`, from, to, bucket)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	values := make([]map[string]any, 0)
	for rows.Next() {
		var point time.Time
		var orders, assignments, failures int
		if err := rows.Scan(&point, &orders, &assignments, &failures); err != nil {
			return nil, err
		}
		values = append(values, map[string]any{
			"timestamp": point, "orders": orders, "assignments": assignments, "failures": failures,
		})
	}
	return values, rows.Err()
}

func (h *Handler) latestAssignments(request *http.Request) ([]map[string]any, error) {
	rows, err := h.db.QueryContext(request.Context(), `
		SELECT a.order_id, a.executor_id, a.status, a.created_at, a.confirmed_at,
			d.processing_time_ms, e.attributes
		FROM assignments a
		LEFT JOIN LATERAL (
			SELECT processing_time_ms FROM decision_traces WHERE order_id = a.order_id
			ORDER BY created_at DESC, id DESC LIMIT 1
		) d ON TRUE
		LEFT JOIN executors e ON e.id = a.executor_id
		ORDER BY a.created_at DESC LIMIT 20
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	values := make([]map[string]any, 0)
	for rows.Next() {
		var orderID, executorID, status string
		var created time.Time
		var confirmed any
		var duration any
		var attributes []byte
		if err := rows.Scan(&orderID, &executorID, &status, &created, &confirmed, &duration, &attributes); err != nil {
			return nil, err
		}
		var executorValues map[string]any
		_ = json.Unmarshal(attributes, &executorValues)
		values = append(values, map[string]any{
			"orderId": orderID, "executorId": executorID,
			"executorName": stringValue(executorValues, "display_name", executorID),
			"status":       displayAssignmentStatus(status, status == "confirmed"),
			"createdAt":    created, "reservedAt": created, "confirmedAt": confirmed,
			"processingTimeMs": duration, "explanation": nil,
		})
	}
	return values, rows.Err()
}
