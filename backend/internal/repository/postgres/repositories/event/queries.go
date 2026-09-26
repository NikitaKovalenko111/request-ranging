package eventrepo

const (
	tryStartQuery = `
		INSERT INTO processed_events (event_id, event_type, received_at)
		VALUES ($1, $2, COALESCE($3, NOW()))
		ON CONFLICT (event_id) DO NOTHING`

	markProcessedQuery = `
		UPDATE processed_events
		SET processed_at = NOW()
		WHERE event_id = $1`

	getByIDQuery = `
		SELECT event_id, event_type, received_at, processed_at
		FROM processed_events
		WHERE event_id = $1`
)
