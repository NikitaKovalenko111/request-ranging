package orderrepo

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	ordermodel "request-ranging/executor-balancer/internal/models/order"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct {
	database *sql.DB
}

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) Upsert(ctx context.Context, value *ordermodel.Order) error {
	attributes, err := shared.EncodeMap(value.Attributes)
	if err != nil {
		return err
	}
	if _, err := r.database.ExecContext(
		ctx, upsertQuery, value.ID, value.ParentID, value.Status, value.Weight,
		value.Version, attributes, value.AssignedExecutorID,
	); err != nil {
		return fmt.Errorf("upsert order: %w", err)
	}
	return nil
}

func (r *Repository) GetByID(ctx context.Context, id string) (*ordermodel.Order, error) {
	value, err := scan(r.database.QueryRowContext(ctx, selectQuery+" WHERE id = $1", id))
	if err != nil {
		return nil, fmt.Errorf("get order %q: %w", id, shared.MapNotFound(err))
	}
	return value, nil
}

func (r *Repository) List(ctx context.Context, status *ordermodel.Status, limit, offset int) ([]ordermodel.Order, error) {
	limit, offset = shared.NormalizePage(limit, offset)
	query := selectQuery
	arguments := []any{}
	if status != nil {
		query += " WHERE status = $1"
		arguments = append(arguments, *status)
	}
	query += fmt.Sprintf(" ORDER BY created_at DESC, id LIMIT $%d OFFSET $%d", len(arguments)+1, len(arguments)+2)
	arguments = append(arguments, limit, offset)

	rows, err := r.database.QueryContext(ctx, query, arguments...)
	if err != nil {
		return nil, fmt.Errorf("list orders: %w", err)
	}
	defer rows.Close()

	values := make([]ordermodel.Order, 0)
	for rows.Next() {
		value, scanErr := scan(rows)
		if scanErr != nil {
			return nil, fmt.Errorf("scan order: %w", scanErr)
		}
		values = append(values, *value)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate orders: %w", err)
	}
	return values, nil
}

type scanner interface {
	Scan(destinations ...any) error
}

func scan(source scanner) (*ordermodel.Order, error) {
	var value ordermodel.Order
	var status string
	var attributes []byte
	err := source.Scan(
		&value.ID, &value.ParentID, &status, &value.Weight, &value.Version,
		&attributes, &value.AssignedExecutorID, &value.CreatedAt, &value.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	value.Status = ordermodel.Status(strings.ToLower(status))
	if err := shared.DecodeJSON(attributes, &value.Attributes); err != nil {
		return nil, err
	}
	return &value, nil
}
