package rulerepo

const (
	createQuery = `
		INSERT INTO rules (id, name, active, priority, left_operand, operator, right_operand, failure_reason)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING created_at, updated_at`

	updateQuery = `
		UPDATE rules SET
			name = $2,
			active = $3,
			priority = $4,
			left_operand = $5,
			operator = $6,
			right_operand = $7,
			failure_reason = $8,
			updated_at = NOW()
		WHERE id = $1
		RETURNING created_at, updated_at`

	selectQuery = `
		SELECT id, name, active, priority, left_operand, operator, right_operand,
			failure_reason, created_at, updated_at
		FROM rules`
)
