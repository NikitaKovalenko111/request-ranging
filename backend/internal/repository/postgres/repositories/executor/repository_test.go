package executorrepo

import (
	"context"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"

	executormodel "request-ranging/executor-balancer/internal/models/executor"
)

func TestUpsertUsesVersionGuard(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	mock.ExpectExec(`(?s)INSERT INTO executors.*WHERE EXCLUDED.version > executors.version`).
		WithArgs("executor-1", int64(3), true, 1.5, 0.0, 0, 0, 0, sqlmock.AnyArg(), sqlmock.AnyArg(), nil).
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = New(database).Upsert(context.Background(), &executormodel.Executor{
		ID: "executor-1", Version: 3, Active: true, Capacity: 1.5, Skills: []string{"Go"},
	})
	if err != nil {
		t.Fatalf("Upsert() error = %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("unmet SQL expectations: %v", err)
	}
}

func TestListActiveUsesPersistedAssignmentsForRuntimeRecovery(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	now := time.Date(2026, 9, 27, 10, 0, 0, 0, time.UTC)
	mock.ExpectQuery(`(?s)FROM executors e.*LEFT JOIN LATERAL.*assignments.*orders.*a.status = 'confirmed'`).
		WillReturnRows(sqlmock.NewRows([]string{
			"id", "version", "active", "capacity", "current_load", "active_count",
			"pending_count", "processed_today", "skills", "attributes", "last_assignment_at",
			"created_at", "updated_at",
		}).AddRow(
			"executor-1", int64(2), true, 3.0, 1.5, 2, 0, 4,
			[]byte(`["Go"]`), []byte(`{"region":"ural"}`), now, now, now,
		))
	values, err := New(database).ListActive(context.Background())
	if err != nil {
		t.Fatalf("ListActive() error = %v", err)
	}
	if len(values) != 1 || values[0].CurrentLoad != 1.5 || values[0].ActiveCount != 2 || values[0].ProcessedToday != 4 || len(values[0].Skills) != 1 {
		t.Fatalf("ListActive() = %+v", values)
	}
}
