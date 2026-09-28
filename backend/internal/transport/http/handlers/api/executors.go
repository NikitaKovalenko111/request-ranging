package api

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strings"
	"time"
)

type executorDTO struct {
	ID               string         `json:"id"`
	FirstName        string         `json:"firstName"`
	LastName         string         `json:"lastName"`
	MiddleName       any            `json:"middleName"`
	DisplayName      string         `json:"displayName"`
	Status           string         `json:"status"`
	Qualification    any            `json:"qualification"`
	CapacityWeight   float64        `json:"capacityWeight"`
	ConfirmedWeight  float64        `json:"confirmedWeight"`
	PendingWeight    float64        `json:"pendingWeight"`
	EffectiveLoad    float64        `json:"effectiveLoad"`
	DailyCount       int            `json:"dailyCount"`
	MaxDailyLimit    any            `json:"maxDailyLimit"`
	LastAssignmentAt *time.Time     `json:"lastAssignmentAt"`
	Parameters       map[string]any `json:"parameters,omitempty"`
}

const executorSelect = `
SELECT e.id, e.active, e.capacity, e.attributes,
	COALESCE(runtime.confirmed_weight, 0), COALESCE(runtime.pending_weight, 0),
	COALESCE(runtime.daily_count, 0), runtime.last_assignment_at
FROM executors e
LEFT JOIN LATERAL (
	SELECT
		COALESCE(SUM(a.order_weight) FILTER (WHERE a.status = 'confirmed' AND o.status = 'processed'), 0) confirmed_weight,
		COALESCE(SUM(a.order_weight) FILTER (WHERE a.status = 'pending'), 0) pending_weight,
		COUNT(*) FILTER (WHERE a.status = 'confirmed' AND a.confirmed_at >= date_trunc('day', NOW())) daily_count,
		MAX(a.confirmed_at) last_assignment_at
	FROM assignments a LEFT JOIN orders o ON o.id = a.order_id WHERE a.executor_id = e.id
) runtime ON TRUE`

func scanExecutor(row rowScanner) (executorDTO, error) {
	var value executorDTO
	var active bool
	var attributes []byte
	var last sql.NullTime
	err := row.Scan(&value.ID, &active, &value.CapacityWeight, &attributes,
		&value.ConfirmedWeight, &value.PendingWeight, &value.DailyCount, &last)
	if err != nil {
		return value, err
	}
	_ = json.Unmarshal(attributes, &value.Parameters)
	value.FirstName = stringValue(value.Parameters, "first_name", "")
	value.LastName = stringValue(value.Parameters, "last_name", "")
	value.MiddleName = value.Parameters["middle_name"]
	value.DisplayName = stringValue(value.Parameters, "display_name", value.ID)
	value.Qualification = value.Parameters["qualification"]
	value.MaxDailyLimit = value.Parameters["max_daily_limit"]
	value.Status = "INACTIVE"
	if active {
		value.Status = "ACTIVE"
	}
	if value.CapacityWeight > 0 {
		value.EffectiveLoad = (value.ConfirmedWeight + value.PendingWeight) / value.CapacityWeight
	}
	if last.Valid {
		value.LastAssignmentAt = &last.Time
	}
	return value, nil
}

func (h *Handler) executors(response http.ResponseWriter, request *http.Request) {
	rows, err := h.db.QueryContext(request.Context(), executorSelect+" ORDER BY e.id")
	if err != nil {
		writeError(response, 500, "EXECUTORS_QUERY_FAILED", err.Error())
		return
	}
	defer rows.Close()
	values := make([]executorDTO, 0)
	search := strings.ToLower(request.URL.Query().Get("search"))
	status := request.URL.Query().Get("status")
	for rows.Next() {
		value, scanErr := scanExecutor(rows)
		if scanErr != nil {
			writeError(response, 500, "EXECUTORS_SCAN_FAILED", scanErr.Error())
			return
		}
		if status != "" && value.Status != status {
			continue
		}
		if search != "" && !strings.Contains(strings.ToLower(value.DisplayName+" "+value.ID), search) {
			continue
		}
		values = append(values, value)
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
	writeJSON(response, 200, page[executorDTO]{
		Items:      values[offset:end],
		Pagination: pagination{Limit: limit, Offset: offset, Total: total},
	})
}

func (h *Handler) executor(response http.ResponseWriter, request *http.Request) {
	value, err := scanExecutor(h.db.QueryRowContext(
		request.Context(), executorSelect+" WHERE e.id = $1", request.PathValue("id"),
	))
	if err == sql.ErrNoRows {
		writeError(response, 404, "EXECUTOR_NOT_FOUND", "Executor not found")
		return
	}
	if err != nil {
		writeError(response, 500, "EXECUTOR_QUERY_FAILED", err.Error())
		return
	}
	writeJSON(response, 200, value)
}

func (h *Handler) patchExecutor(response http.ResponseWriter, request *http.Request) {
	var body struct {
		Status string `json:"status"`
	}
	if err := decode(request, &body); err != nil {
		writeError(response, 400, "INVALID_REQUEST", err.Error())
		return
	}
	if body.Status != "ACTIVE" && body.Status != "INACTIVE" {
		writeError(response, 400, "INVALID_STATUS", "Status must be ACTIVE or INACTIVE")
		return
	}
	id := request.PathValue("id")
	if err := h.ais.SetExecutorActive(request.Context(), id, body.Status == "ACTIVE"); err != nil {
		writeError(response, 502, "AIS_UPDATE_FAILED", err.Error())
		return
	}
	value, err := scanExecutor(h.db.QueryRowContext(request.Context(), executorSelect+" WHERE e.id = $1", id))
	if err != nil {
		writeError(response, 500, "EXECUTOR_QUERY_FAILED", err.Error())
		return
	}
	value.Status = body.Status
	writeJSON(response, 200, value)
}
