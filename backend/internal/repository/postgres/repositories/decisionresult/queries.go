package decisionresultrepo

const (
	createAssignmentQuery = `
		INSERT INTO assignments (
			id, order_id, executor_id, status, order_weight, reservation_id, error_message
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING created_at, confirmed_at, updated_at`

	createTraceQuery = `
		INSERT INTO decision_traces (order_id, assignment_id, trace, processing_time_ms)
		VALUES ($1, $2, $3, $4)
		RETURNING id, created_at`
)
