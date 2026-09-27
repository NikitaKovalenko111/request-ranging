package executorrepo

import (
	"context"
	"testing"

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
		WithArgs("executor-1", int64(3), true, 1.5, 0.0, 0, 0, 0, sqlmock.AnyArg(), nil).
		WillReturnResult(sqlmock.NewResult(0, 1))

	err = New(database).Upsert(context.Background(), &executormodel.Executor{
		ID: "executor-1", Version: 3, Active: true, Capacity: 1.5,
	})
	if err != nil {
		t.Fatalf("Upsert() error = %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("unmet SQL expectations: %v", err)
	}
}
