package assignment

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"time"

	"request-ranging/executor-balancer/internal/integration/ais"
	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	reservationmodel "request-ranging/executor-balancer/internal/models/reservation"
	decisionservice "request-ranging/executor-balancer/internal/services/decision"
)

type decisionService interface {
	ProcessFrom(ctx context.Context, result decisionmodel.Result, minimumRank int) (decisionservice.Outcome, error)
}

type assignmentRepository interface {
	GetLatestByOrderID(ctx context.Context, orderID string) (*assignmentmodel.Assignment, error)
	SetStatus(ctx context.Context, id string, status assignmentmodel.Status, errorMessage *string) error
}

type reservationRepository interface {
	Refresh(ctx context.Context, value *reservationmodel.Reservation) error
	Confirm(ctx context.Context, value reservationmodel.Reservation, confirmedAt time.Time) error
	Cancel(ctx context.Context, value reservationmodel.Reservation) error
}

type aisClient interface {
	Assign(ctx context.Context, value ais.AssignmentRequest) (ais.AssignmentResponse, error)
}

type Service struct {
	decisions    decisionService
	assignments  assignmentRepository
	reservations reservationRepository
	ais          aisClient
	delays       []time.Duration
	wait         func(context.Context, time.Duration) error
}

func NewService(
	decisions decisionService,
	assignments assignmentRepository,
	reservations reservationRepository,
	aisClient aisClient,
) *Service {
	return &Service{
		decisions: decisions, assignments: assignments, reservations: reservations, ais: aisClient,
		delays: []time.Duration{500 * time.Millisecond, time.Second}, wait: waitContext,
	}
}

func (s *Service) ProcessDecision(ctx context.Context, result decisionmodel.Result) error {
	minimumRank := 1
	for {
		outcome, err := s.decisions.ProcessFrom(ctx, result, minimumRank)
		if errors.Is(err, decisionservice.ErrOrderAlreadyAssigned) {
			outcome, err = s.resume(ctx, result)
		}
		if err != nil {
			return err
		}
		if outcome.Assignment.Status == assignmentmodel.StatusConfirmed {
			if outcome.Assignment.ConfirmedAt == nil {
				return fmt.Errorf("confirmed assignment %q has no confirmed_at", outcome.Assignment.ID)
			}
			if err := s.reservations.Confirm(ctx, *outcome.Reservation, *outcome.Assignment.ConfirmedAt); err != nil {
				return fmt.Errorf("reconcile confirmed assignment in redis: %w", err)
			}
			return nil
		}
		response, err := s.sendWithRetry(ctx, outcome)
		if err == nil {
			if err := s.assignments.SetStatus(ctx, outcome.Assignment.ID, assignmentmodel.StatusConfirmed, nil); err != nil {
				return fmt.Errorf("confirm assignment in postgres: %w", err)
			}
			if err := s.reservations.Confirm(ctx, *outcome.Reservation, response.ConfirmedAt); err != nil {
				return fmt.Errorf("confirm assignment in redis: %w", err)
			}
			return nil
		}

		apiError := new(ais.APIError)
		tryNext := errors.As(err, &apiError) && apiError.StatusCode == http.StatusUnprocessableEntity
		status := assignmentmodel.StatusFailed
		if tryNext {
			status = assignmentmodel.StatusCancelled
		}
		message := err.Error()
		statusErr := s.assignments.SetStatus(ctx, outcome.Assignment.ID, status, &message)
		cancelErr := s.reservations.Cancel(ctx, *outcome.Reservation)
		if statusErr != nil || cancelErr != nil {
			return errors.Join(err, statusErr, cancelErr)
		}
		if !tryNext {
			if errors.As(err, &apiError) && !apiError.Retryable {
				return nil
			}
			return err
		}
		minimumRank = outcome.Candidate.Rank + 1
	}
}

func (s *Service) resume(ctx context.Context, result decisionmodel.Result) (decisionservice.Outcome, error) {
	value, err := s.assignments.GetLatestByOrderID(ctx, result.OrderID)
	if err != nil {
		return decisionservice.Outcome{}, fmt.Errorf("load existing assignment: %w", err)
	}
	if value.Status != assignmentmodel.StatusPending && value.Status != assignmentmodel.StatusConfirmed {
		return decisionservice.Outcome{}, fmt.Errorf("existing assignment %q has status %q", value.ID, value.Status)
	}
	var candidate *decisionmodel.BalancedCandidate
	for index := range result.BalancedCandidates {
		if result.BalancedCandidates[index].ExecutorID == value.ExecutorID {
			candidate = &result.BalancedCandidates[index]
			break
		}
	}
	if candidate == nil {
		return decisionservice.Outcome{}, fmt.Errorf("existing assignment executor %q is absent from decision result", value.ExecutorID)
	}
	reservationValue := &reservationmodel.Reservation{
		ID: value.ReservationID, OrderID: value.OrderID, ExecutorID: value.ExecutorID,
		Weight: value.OrderWeight, Status: reservationmodel.StatusPending,
	}
	return decisionservice.Outcome{Assignment: value, Reservation: reservationValue, Candidate: candidate}, nil
}

func (s *Service) sendWithRetry(ctx context.Context, outcome decisionservice.Outcome) (ais.AssignmentResponse, error) {
	request := ais.AssignmentRequest{
		AssignmentID: outcome.Assignment.ID,
		OrderID:      outcome.Assignment.OrderID,
		ExecutorID:   outcome.Assignment.ExecutorID,
		DecidedAt:    outcome.Assignment.CreatedAt,
	}
	var lastErr error
	for attempt := 0; attempt <= len(s.delays); attempt++ {
		if err := s.reservations.Refresh(ctx, outcome.Reservation); err != nil {
			return ais.AssignmentResponse{}, fmt.Errorf("refresh reservation before AIS request: %w", err)
		}
		response, err := s.ais.Assign(ctx, request)
		if err == nil {
			return response, nil
		}
		lastErr = err
		if !retryable(err) || attempt == len(s.delays) {
			break
		}
		if err := s.wait(ctx, s.delays[attempt]); err != nil {
			return ais.AssignmentResponse{}, err
		}
	}
	return ais.AssignmentResponse{}, lastErr
}

func retryable(err error) bool {
	apiError := new(ais.APIError)
	if errors.As(err, &apiError) {
		return apiError.Retryable
	}
	return true
}

func waitContext(ctx context.Context, duration time.Duration) error {
	timer := time.NewTimer(duration)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
