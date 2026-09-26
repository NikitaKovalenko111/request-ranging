package assignmentrepo

import (
	"context"
	"database/sql"
	"fmt"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	"request-ranging/executor-balancer/internal/repository"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct{ database *sql.DB }

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) Create(ctx context.Context, value *assignmentmodel.Assignment) error {
	row := r.database.QueryRowContext(ctx, createQuery,
		value.ID, value.OrderID, value.ExecutorID, value.Status, value.OrderWeight,
		value.ReservationID, value.ErrorMessage,
	)
	if err := row.Scan(&value.CreatedAt, &value.ConfirmedAt, &value.UpdatedAt); err != nil {
		return fmt.Errorf("create assignment: %w", err)
	}
	return nil
}

func (r *Repository) GetByID(ctx context.Context, id string) (*assignmentmodel.Assignment, error) {
	value, err := scan(r.database.QueryRowContext(ctx, selectQuery+" WHERE id = $1", id))
	if err != nil {
		return nil, fmt.Errorf("get assignment %q: %w", id, shared.MapNotFound(err))
	}
	return value, nil
}

func (r *Repository) GetLatestByOrderID(ctx context.Context, orderID string) (*assignmentmodel.Assignment, error) {
	value, err := scan(r.database.QueryRowContext(
		ctx, selectQuery+" WHERE order_id = $1 ORDER BY created_at DESC, id DESC LIMIT 1", orderID,
	))
	if err != nil {
		return nil, fmt.Errorf("get assignment for order %q: %w", orderID, shared.MapNotFound(err))
	}
	return value, nil
}

func (r *Repository) SetStatus(ctx context.Context, id string, status assignmentmodel.Status, errorMessage *string) error {
	result, err := r.database.ExecContext(ctx, setStatusQuery, id, status, errorMessage)
	if err != nil {
		return fmt.Errorf("set assignment %q status: %w", id, err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read set assignment status result: %w", err)
	}
	if affected == 0 {
		return fmt.Errorf("set assignment %q status: %w", id, repository.ErrNotFound)
	}
	return nil
}

type scanner interface {
	Scan(destinations ...any) error
}

func scan(source scanner) (*assignmentmodel.Assignment, error) {
	var value assignmentmodel.Assignment
	var status string
	if err := source.Scan(
		&value.ID, &value.OrderID, &value.ExecutorID, &status, &value.OrderWeight,
		&value.ReservationID, &value.ErrorMessage, &value.CreatedAt, &value.ConfirmedAt, &value.UpdatedAt,
	); err != nil {
		return nil, err
	}
	value.Status = assignmentmodel.Status(status)
	return &value, nil
}
