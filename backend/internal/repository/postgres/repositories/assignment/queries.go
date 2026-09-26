package assignmentrepo

const (
	createQuery = `
		INSERT INTO assignments (
			id, order_id, executor_id, status, order_weight, reservation_id, error_message
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING created_at, confirmed_at, updated_at`

	setStatusQuery = `
		UPDATE assignments SET
			status = $2,
			error_message = $3,
			confirmed_at = CASE
				WHEN $2 = 'confirmed' THEN COALESCE(confirmed_at, NOW())
				ELSE confirmed_at
			END,
			updated_at = NOW()
		WHERE id = $1`

	selectQuery = `
		SELECT id, order_id, executor_id, status, order_weight, reservation_id,
			error_message, created_at, confirmed_at, updated_at
		FROM assignments`
)
