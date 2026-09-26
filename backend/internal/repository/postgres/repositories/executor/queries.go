package executorrepo

const (
	upsertQuery = `
		INSERT INTO executors (id, version, active, capacity, daily_limit, attributes, last_assigned_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (id) DO UPDATE SET
			version = EXCLUDED.version,
			active = EXCLUDED.active,
			capacity = EXCLUDED.capacity,
			daily_limit = EXCLUDED.daily_limit,
			attributes = EXCLUDED.attributes,
			updated_at = NOW()
		WHERE EXCLUDED.version > executors.version`

	selectQuery = `
		SELECT id, version, active, capacity, daily_limit, daily_count, daily_count_date,
			confirmed_weight, pending_weight, open_orders, attributes,
			last_assigned_at, created_at, updated_at
		FROM executors`
)
