package decisiontracerepo

const (
	createQuery = `
		INSERT INTO decision_traces (order_id, assignment_id, trace, processing_time_ms)
		VALUES ($1, $2, $3, $4)
		RETURNING id, created_at`

	getLatestByOrderIDQuery = `
		SELECT id, order_id, assignment_id, trace, processing_time_ms, created_at
		FROM decision_traces
		WHERE order_id = $1
		ORDER BY created_at DESC, id DESC
		LIMIT 1`
)
