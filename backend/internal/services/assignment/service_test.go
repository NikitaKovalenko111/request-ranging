package assignment

import (
	"context"
	"net/http"
	"testing"
	"time"

	"request-ranging/executor-balancer/internal/integration/ais"
	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	reservationmodel "request-ranging/executor-balancer/internal/models/reservation"
	decisionservice "request-ranging/executor-balancer/internal/services/decision"
)

type fakeDecisions struct {
	outcomes []decisionservice.Outcome
	ranks    []int
}

func (f *fakeDecisions) ProcessFrom(_ context.Context, _ decisionmodel.Result, minimumRank int) (decisionservice.Outcome, error) {
	f.ranks = append(f.ranks, minimumRank)
	value := f.outcomes[0]
	f.outcomes = f.outcomes[1:]
	return value, nil
}

type statusChange struct {
	id     string
	status assignmentmodel.Status
}

type fakeAssignments struct {
	changes []statusChange
	latest  *assignmentmodel.Assignment
}

func (f *fakeAssignments) GetLatestByOrderID(context.Context, string) (*assignmentmodel.Assignment, error) {
	return f.latest, nil
}

func (f *fakeAssignments) SetStatus(_ context.Context, id string, status assignmentmodel.Status, _ *string) error {
	f.changes = append(f.changes, statusChange{id: id, status: status})
	return nil
}

type fakeReservations struct {
	refreshed int
	confirmed int
	cancelled int
}

func (f *fakeReservations) Refresh(_ context.Context, _ *reservationmodel.Reservation) error {
	f.refreshed++
	return nil
}
func (f *fakeReservations) Confirm(_ context.Context, _ reservationmodel.Reservation, _ time.Time) error {
	f.confirmed++
	return nil
}
func (f *fakeReservations) Cancel(_ context.Context, _ reservationmodel.Reservation) error {
	f.cancelled++
	return nil
}

type aisResult struct {
	response ais.AssignmentResponse
	err      error
}

type fakeAIS struct{ results []aisResult }

func (f *fakeAIS) Assign(context.Context, ais.AssignmentRequest) (ais.AssignmentResponse, error) {
	value := f.results[0]
	f.results = f.results[1:]
	return value.response, value.err
}

func TestProcessDecisionRetriesTemporaryAISFailure(t *testing.T) {
	decisions := &fakeDecisions{outcomes: []decisionservice.Outcome{testOutcome(1)}}
	assignments := &fakeAssignments{}
	reservations := &fakeReservations{}
	aisClient := &fakeAIS{results: []aisResult{
		{err: &ais.APIError{StatusCode: http.StatusServiceUnavailable, Retryable: true}},
		{response: confirmedResponse(1)},
	}}
	service := NewService(decisions, assignments, reservations, aisClient)
	service.delays = []time.Duration{0}
	service.wait = func(context.Context, time.Duration) error { return nil }
	if err := service.ProcessDecision(context.Background(), decisionmodel.Result{}); err != nil {
		t.Fatalf("ProcessDecision() error = %v", err)
	}
	if reservations.refreshed != 2 || reservations.confirmed != 1 || len(assignments.changes) != 1 || assignments.changes[0].status != assignmentmodel.StatusConfirmed {
		t.Fatalf("unexpected workflow state: reservations=%+v changes=%+v", reservations, assignments.changes)
	}
}

func TestProcessDecisionTriesNextCandidateAfter422(t *testing.T) {
	decisions := &fakeDecisions{outcomes: []decisionservice.Outcome{testOutcome(1), testOutcome(2)}}
	assignments := &fakeAssignments{}
	reservations := &fakeReservations{}
	aisClient := &fakeAIS{results: []aisResult{
		{err: &ais.APIError{StatusCode: http.StatusUnprocessableEntity}},
		{response: confirmedResponse(2)},
	}}
	service := NewService(decisions, assignments, reservations, aisClient)
	if err := service.ProcessDecision(context.Background(), decisionmodel.Result{}); err != nil {
		t.Fatalf("ProcessDecision() error = %v", err)
	}
	if len(decisions.ranks) != 2 || decisions.ranks[0] != 1 || decisions.ranks[1] != 2 {
		t.Fatalf("minimum ranks = %v", decisions.ranks)
	}
	if reservations.cancelled != 1 || reservations.confirmed != 1 || assignments.changes[0].status != assignmentmodel.StatusCancelled {
		t.Fatalf("unexpected workflow state: reservations=%+v changes=%+v", reservations, assignments.changes)
	}
}

func testOutcome(rank int) decisionservice.Outcome {
	now := time.Date(2026, 9, 27, 10, 0, 0, 0, time.UTC)
	assignmentID := "assignment-1"
	executorID := "executor-1"
	if rank == 2 {
		assignmentID = "assignment-2"
		executorID = "executor-2"
	}
	return decisionservice.Outcome{
		Assignment: &assignmentmodel.Assignment{
			ID: assignmentID, OrderID: "order-1", ExecutorID: executorID,
			OrderWeight: 0.5, Status: assignmentmodel.StatusPending, CreatedAt: now,
		},
		Reservation: &reservationmodel.Reservation{
			ID: "reservation-" + executorID, OrderID: "order-1", ExecutorID: executorID, Weight: 0.5,
		},
		Candidate: &decisionmodel.BalancedCandidate{ExecutorID: executorID, Rank: rank},
	}
}

func confirmedResponse(rank int) ais.AssignmentResponse {
	outcome := testOutcome(rank)
	return ais.AssignmentResponse{
		AssignmentID: outcome.Assignment.ID,
		OrderID:      outcome.Assignment.OrderID,
		ExecutorID:   outcome.Assignment.ExecutorID,
		Status:       "confirmed", ConfirmedAt: time.Now(),
	}
}
