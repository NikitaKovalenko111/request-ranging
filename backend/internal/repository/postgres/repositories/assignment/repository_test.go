package assignmentrepo

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	"request-ranging/executor-balancer/internal/repository"
)

func TestSetStatusNotFound(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	mock.ExpectExec(`(?s)UPDATE assignments SET.*WHERE id = \$1`).
		WithArgs("assignment-1", assignmentmodel.StatusConfirmed, nil).
		WillReturnResult(sqlmock.NewResult(0, 0))

	err = New(database).SetStatus(context.Background(), "assignment-1", assignmentmodel.StatusConfirmed, nil)
	if !errors.Is(err, repository.ErrNotFound) {
		t.Fatalf("SetStatus() error = %v, want ErrNotFound", err)
	}
}

func TestReconcileConfirmed(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	confirmedAt := time.Date(2026, 9, 27, 10, 0, 0, 0, time.UTC)
	mock.ExpectExec(`(?s)UPDATE assignments SET.*executor_id = \$2.*status = 'confirmed'.*WHERE id = \$1`).
		WithArgs("assignment-1", "executor-2", confirmedAt).
		WillReturnResult(sqlmock.NewResult(0, 1))
	if err := New(database).ReconcileConfirmed(context.Background(), "assignment-1", "executor-2", confirmedAt); err != nil {
		t.Fatalf("ReconcileConfirmed() error = %v", err)
	}
}
