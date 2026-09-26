package decisiontracerepo

import (
	"context"
	"database/sql"
	"fmt"

	tracemodel "request-ranging/executor-balancer/internal/models/decisiontrace"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct{ database *sql.DB }

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) Create(ctx context.Context, value *tracemodel.DecisionTrace) error {
	data, err := shared.EncodeMap(value.Data)
	if err != nil {
		return err
	}
	row := r.database.QueryRowContext(ctx, createQuery,
		value.OrderID, value.AssignmentID, data, value.ProcessingTimeMS,
	)
	if err := row.Scan(&value.ID, &value.CreatedAt); err != nil {
		return fmt.Errorf("create decision trace: %w", err)
	}
	return nil
}

func (r *Repository) GetLatestByOrderID(ctx context.Context, orderID string) (*tracemodel.DecisionTrace, error) {
	row := r.database.QueryRowContext(ctx, getLatestByOrderIDQuery, orderID)
	var value tracemodel.DecisionTrace
	var data []byte
	if err := row.Scan(
		&value.ID, &value.OrderID, &value.AssignmentID, &data,
		&value.ProcessingTimeMS, &value.CreatedAt,
	); err != nil {
		return nil, fmt.Errorf("get decision trace for order %q: %w", orderID, shared.MapNotFound(err))
	}
	if err := shared.DecodeJSON(data, &value.Data); err != nil {
		return nil, err
	}
	return &value, nil
}
