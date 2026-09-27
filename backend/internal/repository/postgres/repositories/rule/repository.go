package rulerepo

import (
	"context"
	"database/sql"
	"fmt"

	rulemodel "request-ranging/executor-balancer/internal/models/rule"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct {
	database *sql.DB
}

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) Create(ctx context.Context, value *rulemodel.Rule) error {
	leftOperand, rightOperand, err := encodeOperands(value)
	if err != nil {
		return err
	}
	row := r.database.QueryRowContext(ctx, createQuery,
		value.ID, value.Name, value.Active, value.Priority, leftOperand,
		value.Operator, rightOperand, value.FailureReason,
	)
	if err := row.Scan(&value.CreatedAt, &value.UpdatedAt); err != nil {
		return fmt.Errorf("create rule: %w", err)
	}
	return nil
}

func (r *Repository) Update(ctx context.Context, value *rulemodel.Rule) error {
	leftOperand, rightOperand, err := encodeOperands(value)
	if err != nil {
		return err
	}
	row := r.database.QueryRowContext(ctx, updateQuery,
		value.ID, value.Name, value.Active, value.Priority, leftOperand,
		value.Operator, rightOperand, value.FailureReason,
	)
	if err := row.Scan(&value.CreatedAt, &value.UpdatedAt); err != nil {
		return fmt.Errorf("update rule %q: %w", value.ID, shared.MapNotFound(err))
	}
	return nil
}

func (r *Repository) Delete(ctx context.Context, id string) error {
	result, err := r.database.ExecContext(ctx, "DELETE FROM rules WHERE id = $1", id)
	if err != nil {
		return fmt.Errorf("delete rule %q: %w", id, err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read delete rule result: %w", err)
	}
	if affected == 0 {
		return fmt.Errorf("delete rule %q: %w", id, shared.MapNotFound(sql.ErrNoRows))
	}
	return nil
}

func (r *Repository) GetByID(ctx context.Context, id string) (*rulemodel.Rule, error) {
	value, err := scan(r.database.QueryRowContext(ctx, selectQuery+" WHERE id = $1", id))
	if err != nil {
		return nil, fmt.Errorf("get rule %q: %w", id, shared.MapNotFound(err))
	}
	return value, nil
}

func (r *Repository) List(ctx context.Context, activeOnly bool) ([]rulemodel.Rule, error) {
	query := selectQuery
	if activeOnly {
		query += " WHERE active = TRUE"
	}
	query += " ORDER BY priority, id"
	rows, err := r.database.QueryContext(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("list rules: %w", err)
	}
	defer rows.Close()

	values := make([]rulemodel.Rule, 0)
	for rows.Next() {
		value, scanErr := scan(rows)
		if scanErr != nil {
			return nil, fmt.Errorf("scan rule: %w", scanErr)
		}
		values = append(values, *value)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate rules: %w", err)
	}
	return values, nil
}

func encodeOperands(value *rulemodel.Rule) ([]byte, []byte, error) {
	leftOperand, err := shared.EncodeJSON(value.LeftOperand)
	if err != nil {
		return nil, nil, fmt.Errorf("encode left operand: %w", err)
	}
	rightOperand, err := shared.EncodeJSON(value.RightOperand)
	if err != nil {
		return nil, nil, fmt.Errorf("encode right operand: %w", err)
	}
	return leftOperand, rightOperand, nil
}

type scanner interface {
	Scan(destinations ...any) error
}

func scan(source scanner) (*rulemodel.Rule, error) {
	var value rulemodel.Rule
	var leftOperand, rightOperand []byte
	var operator string
	if err := source.Scan(
		&value.ID, &value.Name, &value.Active, &value.Priority, &leftOperand,
		&operator, &rightOperand, &value.FailureReason, &value.CreatedAt, &value.UpdatedAt,
	); err != nil {
		return nil, err
	}
	value.Operator = rulemodel.Operator(operator)
	if err := shared.DecodeJSON(leftOperand, &value.LeftOperand); err != nil {
		return nil, fmt.Errorf("decode left operand: %w", err)
	}
	if err := shared.DecodeJSON(rightOperand, &value.RightOperand); err != nil {
		return nil, fmt.Errorf("decode right operand: %w", err)
	}
	return &value, nil
}
