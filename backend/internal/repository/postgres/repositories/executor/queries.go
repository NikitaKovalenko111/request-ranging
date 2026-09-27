package executorrepo

const (
	upsertQuery = `
		INSERT INTO executors (
			id, version, active, capacity, current_load, active_count,
			pending_count, processed_today, attributes, last_assignment_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		ON CONFLICT (id) DO UPDATE SET
			version = EXCLUDED.version,
			active = EXCLUDED.active,
			capacity = EXCLUDED.capacity,
			current_load = EXCLUDED.current_load,
			active_count = EXCLUDED.active_count,
			pending_count = EXCLUDED.pending_count,
			processed_today = EXCLUDED.processed_today,
			attributes = EXCLUDED.attributes,
			last_assignment_at = EXCLUDED.last_assignment_at,
			updated_at = NOW()
		WHERE EXCLUDED.version > executors.version`

	selectQuery = `
		SELECT id, version, active, capacity, current_load, active_count,
			pending_count, processed_today, attributes, last_assignment_at,
			created_at, updated_at
		FROM executors`
)
