package orderrepo

import (
	"context"
	"database/sql"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"

	ordermodel "request-ranging/executor-balancer/internal/models/order"
	"request-ranging/executor-balancer/internal/repository"
)

func TestGetByID(t *testing.T) {
	database, mock := newMock(t)
	now := time.Now().UTC()
	mock.ExpectQuery(`(?s)SELECT .* FROM orders.*WHERE id = \$1`).WithArgs("order-1").WillReturnRows(
		sqlmock.NewRows([]string{"id", "parent_id", "status", "weight", "version", "attributes", "assigned_executor_id", "created_at", "updated_at"}).
			AddRow("order-1", nil, "processed", 2.0, 1, []byte(`{"vip":true}`), nil, now, now),
	)

	value, err := New(database).GetByID(context.Background(), "order-1")
	if err != nil {
		t.Fatalf("GetByID() error = %v", err)
	}
	if value.Status != ordermodel.StatusProcessed || value.Attributes["vip"] != true {
		t.Fatalf("unexpected order: %+v", value)
	}
}

func TestGetByIDNotFound(t *testing.T) {
	database, mock := newMock(t)
	mock.ExpectQuery(`(?s)SELECT .* FROM orders.*WHERE id = \$1`).WithArgs("missing").WillReturnError(sql.ErrNoRows)
	_, err := New(database).GetByID(context.Background(), "missing")
	if !errors.Is(err, repository.ErrNotFound) {
		t.Fatalf("GetByID() error = %v, want ErrNotFound", err)
	}
}

func newMock(t *testing.T) (*sql.DB, sqlmock.Sqlmock) {
	t.Helper()
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	t.Cleanup(func() {
		if err := mock.ExpectationsWereMet(); err != nil {
			t.Errorf("unmet SQL expectations: %v", err)
		}
		_ = database.Close()
	})
	return database, mock
}
