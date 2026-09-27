package executorrepo

const (
	upsertQuery = `
		INSERT INTO executors (
			id, version, active, capacity, current_load, active_count,
			pending_count, processed_today, skills, attributes, last_assignment_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
		ON CONFLICT (id) DO UPDATE SET
			version = EXCLUDED.version,
			active = EXCLUDED.active,
			capacity = EXCLUDED.capacity,
			current_load = EXCLUDED.current_load,
			active_count = EXCLUDED.active_count,
			pending_count = EXCLUDED.pending_count,
			processed_today = EXCLUDED.processed_today,
			skills = EXCLUDED.skills,
			attributes = EXCLUDED.attributes,
			last_assignment_at = EXCLUDED.last_assignment_at,
			updated_at = NOW()
		WHERE EXCLUDED.version > executors.version`

	selectQuery = `
		SELECT id, version, active, capacity, current_load, active_count,
			pending_count, processed_today, skills, attributes, last_assignment_at,
			created_at, updated_at
		FROM executors`

	selectActiveRuntimeQuery = `
		SELECT e.id, e.version, e.active, e.capacity,
			COALESCE(runtime.current_load, 0),
			COALESCE(runtime.active_count, 0),
			0 AS pending_count,
			COALESCE(runtime.processed_today, 0),
			e.skills, e.attributes, runtime.last_assignment_at,
			e.created_at, e.updated_at
		FROM executors e
		LEFT JOIN LATERAL (
			SELECT
				COALESCE(SUM(a.order_weight) FILTER (WHERE o.status = 'processed'), 0) AS current_load,
				COUNT(*) FILTER (WHERE o.status = 'processed') AS active_count,
				COUNT(*) FILTER (
					WHERE o.status IN ('await', 'accept', 'reject')
					AND o.updated_at >= date_trunc('day', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
				) AS processed_today,
				MAX(a.confirmed_at) AS last_assignment_at
			FROM assignments a
			JOIN orders o ON o.id = a.order_id
			WHERE a.executor_id = e.id AND a.status = 'confirmed'
		) runtime ON TRUE
		WHERE e.active = TRUE
		ORDER BY e.id`
)
