package order

import (
	"context"
	"errors"
	"fmt"
	"time"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	eventmodel "request-ranging/executor-balancer/internal/models/event"
	ordermodel "request-ranging/executor-balancer/internal/models/order"
	"request-ranging/executor-balancer/internal/repository"
)

type orderRepository interface {
	Upsert(ctx context.Context, value *ordermodel.Order) error
	GetByID(ctx context.Context, id string) (*ordermodel.Order, error)
}

type assignmentRepository interface {
	GetLatestByOrderID(ctx context.Context, orderID string) (*assignmentmodel.Assignment, error)
}

type eventRepository interface {
	TryStart(ctx context.Context, value *eventmodel.ProcessedEvent) (bool, error)
	MarkProcessed(ctx context.Context, eventID string) error
}

type workloadRepository interface {
	Complete(ctx context.Context, eventID, executorID string, weight float64) (bool, error)
}

type Service struct {
	orders      orderRepository
	assignments assignmentRepository
	events      eventRepository
	workload    workloadRepository
	now         func() time.Time
}

func NewService(
	orders orderRepository,
	assignments assignmentRepository,
	events eventRepository,
	workload workloadRepository,
) *Service {
	return &Service{
		orders: orders, assignments: assignments, events: events, workload: workload, now: time.Now,
	}
}

func (s *Service) ApplySnapshot(
	ctx context.Context,
	envelope eventmodel.Envelope,
	payload ordermodel.SnapshotPayload,
) error {
	if err := payload.Validate(); err != nil {
		return err
	}
	started, err := s.begin(ctx, envelope)
	if err != nil || !started {
		return err
	}
	value := &ordermodel.Order{
		ID: payload.ID, ParentID: payload.ParentID, Status: payload.Status,
		Weight: payload.Weight, Version: payload.Version, Attributes: payload.Attributes,
	}
	if err := s.orders.Upsert(ctx, value); err != nil {
		return fmt.Errorf("upsert order event %q: %w", envelope.ID, err)
	}
	return s.finish(ctx, envelope.ID)
}

func (s *Service) ApplyStatus(
	ctx context.Context,
	envelope eventmodel.Envelope,
	payload ordermodel.StatusChangedPayload,
) error {
	if err := payload.Validate(); err != nil {
		return err
	}
	started, err := s.begin(ctx, envelope)
	if err != nil || !started {
		return err
	}
	current, err := s.orders.GetByID(ctx, payload.ID)
	if err != nil {
		return fmt.Errorf("get order for status event %q: %w", envelope.ID, err)
	}
	if payload.Version < current.Version {
		return s.finish(ctx, envelope.ID)
	}
	if payload.Version > current.Version {
		current.Status = payload.Status
		current.Version = payload.Version
		if err := s.orders.Upsert(ctx, current); err != nil {
			return fmt.Errorf("update order status event %q: %w", envelope.ID, err)
		}
	}
	if isTerminal(payload.Status) {
		if err := s.completeAssignment(ctx, envelope.ID, current); err != nil {
			return err
		}
	}
	return s.finish(ctx, envelope.ID)
}

func (s *Service) completeAssignment(ctx context.Context, eventID string, orderValue *ordermodel.Order) error {
	assignmentValue, err := s.assignments.GetLatestByOrderID(ctx, orderValue.ID)
	if errors.Is(err, repository.ErrNotFound) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("get assignment for completed order %q: %w", orderValue.ID, err)
	}
	if assignmentValue.Status != assignmentmodel.StatusConfirmed {
		return nil
	}
	if _, err := s.workload.Complete(ctx, eventID, assignmentValue.ExecutorID, assignmentValue.OrderWeight); err != nil {
		return fmt.Errorf("release executor load for order %q: %w", orderValue.ID, err)
	}
	return nil
}

func (s *Service) begin(ctx context.Context, envelope eventmodel.Envelope) (bool, error) {
	started, err := s.events.TryStart(ctx, &eventmodel.ProcessedEvent{
		ID: envelope.ID, Type: envelope.Type, ReceivedAt: s.now().UTC(),
	})
	if err != nil {
		return false, fmt.Errorf("start event %q: %w", envelope.ID, err)
	}
	return started, nil
}

func (s *Service) finish(ctx context.Context, eventID string) error {
	if err := s.events.MarkProcessed(ctx, eventID); err != nil {
		return fmt.Errorf("finish event %q: %w", eventID, err)
	}
	return nil
}

func isTerminal(status ordermodel.Status) bool {
	return status == ordermodel.StatusAccept || status == ordermodel.StatusReject || status == ordermodel.StatusAwait
}
