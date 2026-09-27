package decision

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"strconv"
	"time"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	tracemodel "request-ranging/executor-balancer/internal/models/decisiontrace"
	executormodel "request-ranging/executor-balancer/internal/models/executor"
	ordermodel "request-ranging/executor-balancer/internal/models/order"
	reservationmodel "request-ranging/executor-balancer/internal/models/reservation"
	"request-ranging/executor-balancer/internal/repository"
)

var (
	ErrOrderAlreadyAssigned = errors.New("order already has an active assignment")
	ErrNoCandidateReserved  = errors.New("no decision candidate could be reserved")
	ErrDecisionIntegrity    = errors.New("decision result integrity violation")
)

type orderRepository interface {
	GetByID(ctx context.Context, id string) (*ordermodel.Order, error)
}

type executorRepository interface {
	GetByID(ctx context.Context, id string) (*executormodel.Executor, error)
}

type assignmentRepository interface {
	GetLatestByOrderID(ctx context.Context, orderID string) (*assignmentmodel.Assignment, error)
}

type decisionRepository interface {
	CreateAssignmentWithTrace(ctx context.Context, assignment *assignmentmodel.Assignment, trace *tracemodel.DecisionTrace) error
}

type traceRepository interface {
	Create(ctx context.Context, trace *tracemodel.DecisionTrace) error
}

type reservationRepository interface {
	TryReserve(ctx context.Context, value *reservationmodel.Reservation) (bool, error)
	Cancel(ctx context.Context, value reservationmodel.Reservation) error
}

type IDGenerator func() (string, error)

type Service struct {
	orders       orderRepository
	executors    executorRepository
	assignments  assignmentRepository
	decisions    decisionRepository
	traces       traceRepository
	reservations reservationRepository
	generateID   IDGenerator
	now          func() time.Time
}

type Outcome struct {
	Assignment  *assignmentmodel.Assignment
	Reservation *reservationmodel.Reservation
	Candidate   *decisionmodel.BalancedCandidate
}

func NewService(
	orders orderRepository,
	executors executorRepository,
	assignments assignmentRepository,
	decisions decisionRepository,
	traces traceRepository,
	reservations reservationRepository,
) *Service {
	return &Service{
		orders: orders, executors: executors, assignments: assignments,
		decisions: decisions, traces: traces, reservations: reservations,
		generateID: randomID, now: time.Now,
	}
}

func (s *Service) Process(ctx context.Context, result decisionmodel.Result) (Outcome, error) {
	startedAt := s.now()
	if err := result.Validate(); err != nil {
		return Outcome{}, err
	}
	orderID := strconv.FormatInt(result.OrderID, 10)
	orderValue, err := s.orders.GetByID(ctx, orderID)
	if err != nil {
		return Outcome{}, fmt.Errorf("get decision order %q: %w", orderID, err)
	}
	if err := s.ensureOrderIsNotAssigned(ctx, orderID); err != nil {
		return Outcome{}, err
	}

	traceData, err := result.ToMap()
	if err != nil {
		return Outcome{}, err
	}
	attempts := make([]map[string]any, 0, len(result.BalancedCandidates))

	for index := range result.BalancedCandidates {
		candidate := result.BalancedCandidates[index]
		executorValue, err := s.executors.GetByID(ctx, candidate.ExecutorID)
		if err != nil {
			if errors.Is(err, repository.ErrNotFound) {
				return Outcome{}, fmt.Errorf("%w: unknown executor %q", ErrDecisionIntegrity, candidate.ExecutorID)
			}
			return Outcome{}, fmt.Errorf("get candidate executor %q: %w", candidate.ExecutorID, err)
		}
		if !executorValue.Active {
			attempts = append(attempts, attempt(candidate, "inactive"))
			continue
		}

		reservationID, err := s.generateID()
		if err != nil {
			return Outcome{}, fmt.Errorf("generate reservation ID: %w", err)
		}
		reservationValue := reservationmodel.Reservation{
			ID: reservationID, OrderID: orderID, ExecutorID: candidate.ExecutorID, Weight: orderValue.Weight,
		}
		reserved, err := s.reservations.TryReserve(ctx, &reservationValue)
		if errors.Is(err, repository.ErrAlreadyReserved) {
			return Outcome{}, ErrOrderAlreadyAssigned
		}
		if err != nil {
			return Outcome{}, fmt.Errorf("reserve candidate %q: %w", candidate.ExecutorID, err)
		}
		if !reserved {
			attempts = append(attempts, attempt(candidate, "busy"))
			continue
		}

		assignmentID, err := s.generateID()
		if err != nil {
			return Outcome{}, errors.Join(
				fmt.Errorf("generate assignment ID: %w", err),
				s.reservations.Cancel(ctx, reservationValue),
			)
		}
		assignmentValue := &assignmentmodel.Assignment{
			ID: assignmentID, OrderID: orderID, ExecutorID: candidate.ExecutorID,
			Status: assignmentmodel.StatusPending, OrderWeight: orderValue.Weight,
			ReservationID: reservationValue.ID,
		}
		traceData["reservation_attempts"] = append(attempts, attempt(candidate, "reserved"))
		traceData["selected_executor_id"] = candidate.ExecutorID
		trace := &tracemodel.DecisionTrace{
			OrderID: orderID, AssignmentID: &assignmentValue.ID, Data: traceData,
			ProcessingTimeMS: s.now().Sub(startedAt).Milliseconds(),
		}
		if err := s.decisions.CreateAssignmentWithTrace(ctx, assignmentValue, trace); err != nil {
			cancelErr := s.reservations.Cancel(ctx, reservationValue)
			return Outcome{}, errors.Join(fmt.Errorf("persist decision: %w", err), cancelErr)
		}
		return Outcome{
			Assignment: assignmentValue, Reservation: &reservationValue, Candidate: &candidate,
		}, nil
	}

	traceData["reservation_attempts"] = attempts
	trace := &tracemodel.DecisionTrace{
		OrderID: orderID, Data: traceData,
		ProcessingTimeMS: s.now().Sub(startedAt).Milliseconds(),
	}
	if err := s.traces.Create(ctx, trace); err != nil {
		return Outcome{}, errors.Join(ErrNoCandidateReserved, fmt.Errorf("persist rejected decision: %w", err))
	}
	return Outcome{}, ErrNoCandidateReserved
}

func (s *Service) ensureOrderIsNotAssigned(ctx context.Context, orderID string) error {
	value, err := s.assignments.GetLatestByOrderID(ctx, orderID)
	if errors.Is(err, repository.ErrNotFound) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("get latest assignment for order %q: %w", orderID, err)
	}
	if value.Status == assignmentmodel.StatusPending || value.Status == assignmentmodel.StatusConfirmed {
		return ErrOrderAlreadyAssigned
	}
	return nil
}

func attempt(candidate decisionmodel.BalancedCandidate, status string) map[string]any {
	return map[string]any{
		"executor_id": candidate.ExecutorID,
		"rank":        candidate.Rank,
		"status":      status,
	}
}

func randomID() (string, error) {
	var bytes [16]byte
	if _, err := rand.Read(bytes[:]); err != nil {
		return "", err
	}
	bytes[6] = (bytes[6] & 0x0f) | 0x40
	bytes[8] = (bytes[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", bytes[0:4], bytes[4:6], bytes[6:8], bytes[8:10], bytes[10:16]), nil
}
