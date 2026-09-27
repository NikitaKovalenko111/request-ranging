package orderrepo

const (
	upsertQuery = `
		INSERT INTO orders (id, parent_id, status, weight, version, attributes, assigned_executor_id)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (id) DO UPDATE SET
			parent_id = EXCLUDED.parent_id,
			status = EXCLUDED.status,
			weight = EXCLUDED.weight,
			version = EXCLUDED.version,
			attributes = EXCLUDED.attributes,
			assigned_executor_id = COALESCE(EXCLUDED.assigned_executor_id, orders.assigned_executor_id),
			updated_at = NOW()
		WHERE EXCLUDED.version > orders.version`

	selectQuery = `
		SELECT id, parent_id, status, weight, version, attributes, assigned_executor_id, created_at, updated_at
		FROM orders`
)
