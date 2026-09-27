package decisionresultrepo

import (
	"context"
	"database/sql"
	"fmt"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	tracemodel "request-ranging/executor-balancer/internal/models/decisiontrace"
	"request-ranging/executor-balancer/internal/repository/postgres/repositories/shared"
)

type Repository struct{ database *sql.DB }

func New(database *sql.DB) *Repository { return &Repository{database: database} }

func (r *Repository) CreateAssignmentWithTrace(
	ctx context.Context,
	assignment *assignmentmodel.Assignment,
	trace *tracemodel.DecisionTrace,
) error {
	transaction, err := r.database.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin decision transaction: %w", err)
	}
	defer transaction.Rollback()

	row := transaction.QueryRowContext(ctx, createAssignmentQuery,
		assignment.ID, assignment.OrderID, assignment.ExecutorID, assignment.Status,
		assignment.OrderWeight, assignment.ReservationID, assignment.ErrorMessage,
	)
	if err := row.Scan(&assignment.CreatedAt, &assignment.ConfirmedAt, &assignment.UpdatedAt); err != nil {
		return fmt.Errorf("create assignment: %w", err)
	}

	data, err := shared.EncodeMap(trace.Data)
	if err != nil {
		return err
	}
	row = transaction.QueryRowContext(ctx, createTraceQuery,
		trace.OrderID, trace.AssignmentID, data, trace.ProcessingTimeMS,
	)
	if err := row.Scan(&trace.ID, &trace.CreatedAt); err != nil {
		return fmt.Errorf("create decision trace: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit decision transaction: %w", err)
	}
	return nil
}
