package decisionresultrepo

import (
	"context"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	tracemodel "request-ranging/executor-balancer/internal/models/decisiontrace"
)

func TestCreateAssignmentWithTrace(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	now := time.Now().UTC()
	mock.ExpectBegin()
	mock.ExpectQuery(`(?s)INSERT INTO assignments.*RETURNING created_at, confirmed_at, updated_at`).
		WithArgs("assignment-1", "42", "7", assignmentmodel.StatusPending, 0.7, "reservation-1", nil).
		WillReturnRows(sqlmock.NewRows([]string{"created_at", "confirmed_at", "updated_at"}).AddRow(now, nil, now))
	mock.ExpectQuery(`(?s)INSERT INTO decision_traces.*RETURNING id, created_at`).
		WithArgs("42", sqlmock.AnyArg(), sqlmock.AnyArg(), int64(15)).
		WillReturnRows(sqlmock.NewRows([]string{"id", "created_at"}).AddRow(1, now))
	mock.ExpectCommit()

	assignment := &assignmentmodel.Assignment{
		ID: "assignment-1", OrderID: "42", ExecutorID: "7", Status: assignmentmodel.StatusPending,
		OrderWeight: 0.7, ReservationID: "reservation-1",
	}
	assignmentID := assignment.ID
	trace := &tracemodel.DecisionTrace{
		OrderID: "42", AssignmentID: &assignmentID, Data: map[string]any{"rank": 1}, ProcessingTimeMS: 15,
	}
	if err := New(database).CreateAssignmentWithTrace(context.Background(), assignment, trace); err != nil {
		t.Fatalf("CreateAssignmentWithTrace() error = %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("unmet expectations: %v", err)
	}
}
