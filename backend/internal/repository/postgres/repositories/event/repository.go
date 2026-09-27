package eventrepo

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	"request-ranging/executor-balancer/internal/repository"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct{ database *sql.DB }

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) TryStart(ctx context.Context, value *eventmodel.ProcessedEvent) (bool, error) {
	result, err := r.database.ExecContext(ctx, tryStartQuery, value.ID, value.Type, nullableTime(value.ReceivedAt))
	if err != nil {
		return false, fmt.Errorf("start event: %w", err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("read start event result: %w", err)
	}
	return affected == 1, nil
}

func (r *Repository) MarkProcessed(ctx context.Context, eventID string) error {
	result, err := r.database.ExecContext(ctx, markProcessedQuery, eventID)
	if err != nil {
		return fmt.Errorf("mark event %q processed: %w", eventID, err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read mark event processed result: %w", err)
	}
	if affected == 0 {
		return fmt.Errorf("mark event %q processed: %w", eventID, repository.ErrNotFound)
	}
	return nil
}

func (r *Repository) GetByID(ctx context.Context, eventID string) (*eventmodel.ProcessedEvent, error) {
	row := r.database.QueryRowContext(ctx, getByIDQuery, eventID)
	var value eventmodel.ProcessedEvent
	if err := row.Scan(&value.ID, &value.Type, &value.ReceivedAt, &value.ProcessedAt); err != nil {
		return nil, fmt.Errorf("get event %q: %w", eventID, shared.MapNotFound(err))
	}
	return &value, nil
}

func nullableTime(value time.Time) any {
	if value.IsZero() {
		return nil
	}
	return value
}
