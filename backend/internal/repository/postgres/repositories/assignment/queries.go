package assignmentrepo

const (
	createQuery = `
		INSERT INTO assignments (
			id, order_id, executor_id, status, order_weight, reservation_id, error_message
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING created_at, confirmed_at, updated_at`

	setStatusQuery = `
		WITH changed AS (
			UPDATE assignments SET
				status = $2,
				error_message = $3,
				confirmed_at = CASE
					WHEN $2 = 'confirmed' THEN COALESCE(confirmed_at, NOW())
					ELSE confirmed_at
				END,
				updated_at = NOW()
			WHERE id = $1
			RETURNING order_id, executor_id, status
		)
		UPDATE orders o SET
			assigned_executor_id = CASE
				WHEN changed.status = 'confirmed' THEN changed.executor_id
				ELSE o.assigned_executor_id
			END
		FROM changed
		WHERE o.id = changed.order_id`

	reconcileConfirmedQuery = `
		WITH reconciled AS (
			UPDATE assignments SET
				executor_id = $2,
				status = 'confirmed',
				error_message = NULL,
				confirmed_at = COALESCE(confirmed_at, $3),
				updated_at = NOW()
			WHERE id = $1
			RETURNING order_id, executor_id
		)
		UPDATE orders o SET assigned_executor_id = reconciled.executor_id
		FROM reconciled
		WHERE o.id = reconciled.order_id`

	selectQuery = `
		SELECT id, order_id, executor_id, status, order_weight, reservation_id,
			error_message, created_at, confirmed_at, updated_at
		FROM assignments`
)
