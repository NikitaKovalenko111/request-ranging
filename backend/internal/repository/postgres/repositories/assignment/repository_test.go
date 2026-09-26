package assignmentrepo

import (
	"context"
	"errors"
	"testing"

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
