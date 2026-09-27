package executorrepo

import (
	"context"
	"database/sql"
	"fmt"

	executormodel "request-ranging/executor-balancer/internal/models/executor"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct{ database *sql.DB }

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) Upsert(ctx context.Context, value *executormodel.Executor) error {
	attributes, err := shared.EncodeMap(value.Attributes)
	if err != nil {
		return err
	}
	if _, err := r.database.ExecContext(
		ctx, upsertQuery, value.ID, value.Version, value.Active, value.Capacity,
		value.CurrentLoad, value.ActiveCount, value.PendingCount, value.ProcessedToday,
		attributes, value.LastAssignmentAt,
	); err != nil {
		return fmt.Errorf("upsert executor: %w", err)
	}
	return nil
}

func (r *Repository) GetByID(ctx context.Context, id string) (*executormodel.Executor, error) {
	value, err := scan(r.database.QueryRowContext(ctx, selectQuery+" WHERE id = $1", id))
	if err != nil {
		return nil, fmt.Errorf("get executor %q: %w", id, shared.MapNotFound(err))
	}
	return value, nil
}

func (r *Repository) ListActive(ctx context.Context) ([]executormodel.Executor, error) {
	rows, err := r.database.QueryContext(ctx, selectQuery+" WHERE active = TRUE ORDER BY id")
	if err != nil {
		return nil, fmt.Errorf("list active executors: %w", err)
	}
	defer rows.Close()

	values := make([]executormodel.Executor, 0)
	for rows.Next() {
		value, scanErr := scan(rows)
		if scanErr != nil {
			return nil, fmt.Errorf("scan executor: %w", scanErr)
		}
		values = append(values, *value)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate executors: %w", err)
	}
	return values, nil
}

type scanner interface {
	Scan(destinations ...any) error
}

func scan(source scanner) (*executormodel.Executor, error) {
	var value executormodel.Executor
	var attributes []byte
	err := source.Scan(
		&value.ID, &value.Version, &value.Active, &value.Capacity, &value.CurrentLoad,
		&value.ActiveCount, &value.PendingCount, &value.ProcessedToday, &attributes,
		&value.LastAssignmentAt, &value.CreatedAt, &value.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	if err := shared.DecodeJSON(attributes, &value.Attributes); err != nil {
		return nil, err
	}
	return &value, nil
}
