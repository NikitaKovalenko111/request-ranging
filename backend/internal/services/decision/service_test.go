package decision

import (
	"context"
	"errors"
	"testing"
	"time"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	tracemodel "request-ranging/executor-balancer/internal/models/decisiontrace"
	executormodel "request-ranging/executor-balancer/internal/models/executor"
	ordermodel "request-ranging/executor-balancer/internal/models/order"
	reservationmodel "request-ranging/executor-balancer/internal/models/reservation"
	"request-ranging/executor-balancer/internal/repository"
)

type fakeOrders struct{ value *ordermodel.Order }

func (f fakeOrders) GetByID(context.Context, string) (*ordermodel.Order, error) { return f.value, nil }

type fakeExecutors struct {
	values map[string]*executormodel.Executor
}

func (f fakeExecutors) GetByID(_ context.Context, id string) (*executormodel.Executor, error) {
	value, ok := f.values[id]
	if !ok {
		return nil, repository.ErrNotFound
	}
	return value, nil
}

type fakeAssignments struct{ value *assignmentmodel.Assignment }

func (f fakeAssignments) GetLatestByOrderID(context.Context, string) (*assignmentmodel.Assignment, error) {
	if f.value == nil {
		return nil, repository.ErrNotFound
	}
	return f.value, nil
}

type fakeDecisions struct {
	err        error
	assignment *assignmentmodel.Assignment
	trace      *tracemodel.DecisionTrace
}

func (f *fakeDecisions) CreateAssignmentWithTrace(
	_ context.Context,
	assignment *assignmentmodel.Assignment,
	trace *tracemodel.DecisionTrace,
) error {
	f.assignment = assignment
	f.trace = trace
	return f.err
}

type fakeTraces struct{ trace *tracemodel.DecisionTrace }

func (f *fakeTraces) Create(_ context.Context, trace *tracemodel.DecisionTrace) error {
	f.trace = trace
	return nil
}

type fakeReservations struct {
	results   []bool
	cancelled []string
}

func (f *fakeReservations) TryReserve(_ context.Context, _ *reservationmodel.Reservation) (bool, error) {
	result := f.results[0]
	f.results = f.results[1:]
	return result, nil
}

func (f *fakeReservations) Cancel(_ context.Context, value reservationmodel.Reservation) error {
	f.cancelled = append(f.cancelled, value.ID)
	return nil
}

func TestProcessTriesCandidatesByRank(t *testing.T) {
	decisions := &fakeDecisions{}
	reservations := &fakeReservations{results: []bool{false, true}}
	service := newTestService(decisions, reservations)

	outcome, err := service.Process(context.Background(), validDecision())
	if err != nil {
		t.Fatalf("Process() error = %v", err)
	}
	if outcome.Candidate == nil || outcome.Candidate.ExecutorID != "executor-2" {
		t.Fatalf("selected candidate = %+v, want executor-2", outcome.Candidate)
	}
	if decisions.assignment == nil || decisions.assignment.ExecutorID != "executor-2" {
		t.Fatalf("persisted assignment = %+v", decisions.assignment)
	}
	attempts := decisions.trace.Data["reservation_attempts"].([]map[string]any)
	if len(attempts) != 2 || attempts[0]["status"] != "busy" || attempts[1]["status"] != "reserved" {
		t.Fatalf("unexpected attempts: %#v", attempts)
	}
}

func TestProcessCancelsReservationWhenDatabaseFails(t *testing.T) {
	decisions := &fakeDecisions{err: errors.New("database unavailable")}
	reservations := &fakeReservations{results: []bool{true}}
	service := newTestService(decisions, reservations)

	_, err := service.Process(context.Background(), validDecision())
	if err == nil {
		t.Fatal("Process() error = nil, want database error")
	}
	if len(reservations.cancelled) != 1 {
		t.Fatalf("cancelled reservations = %v, want one", reservations.cancelled)
	}
}

func TestProcessRejectsUnknownExecutor(t *testing.T) {
	service := newTestService(&fakeDecisions{}, &fakeReservations{results: []bool{true}})
	service.executors = fakeExecutors{values: map[string]*executormodel.Executor{}}
	_, err := service.Process(context.Background(), validDecision())
	if !errors.Is(err, ErrDecisionIntegrity) {
		t.Fatalf("Process() error = %v, want ErrDecisionIntegrity", err)
	}
}

func newTestService(decisions *fakeDecisions, reservations *fakeReservations) *Service {
	active := &executormodel.Executor{ID: "executor-1", Active: true, Capacity: 1}
	active2 := &executormodel.Executor{ID: "executor-2", Active: true, Capacity: 1}
	service := NewService(
		fakeOrders{value: &ordermodel.Order{ID: "42", Status: ordermodel.StatusProcessed, Weight: 0.7}},
		fakeExecutors{values: map[string]*executormodel.Executor{"executor-1": active, "executor-2": active2}},
		fakeAssignments{}, decisions, &fakeTraces{}, reservations,
	)
	ids := []string{"reservation-1", "reservation-2", "assignment-1"}
	service.generateID = func() (string, error) {
		id := ids[0]
		ids = ids[1:]
		return id, nil
	}
	service.now = func() time.Time { return time.Date(2026, 9, 27, 10, 0, 0, 0, time.UTC) }
	return service
}

func validDecision() decisionmodel.Result {
	now := time.Date(2026, 9, 27, 10, 0, 0, 0, time.UTC)
	return decisionmodel.Result{
		EventType:    decisionmodel.EventTypeExecutorDecisionCompleted,
		EventVersion: 1, OccurredAt: now, OrderID: 42,
		BalancedCandidates: []decisionmodel.BalancedCandidate{
			{ExecutorID: "executor-1", Rank: 1, MLScore: 0.82, EffectiveLoad: 0.2, Capacity: 1},
			{ExecutorID: "executor-2", Rank: 2, MLScore: 0.7, EffectiveLoad: 0.3, Capacity: 1},
		},
	}
}
