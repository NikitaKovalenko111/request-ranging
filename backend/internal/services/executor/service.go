package executor

import (
	"context"
	"errors"
	"fmt"
	"time"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	executormodel "request-ranging/executor-balancer/internal/models/executor"
	"request-ranging/executor-balancer/internal/repository"
)

type postgresRepository interface {
	Upsert(ctx context.Context, value *executormodel.Executor) error
	GetByID(ctx context.Context, id string) (*executormodel.Executor, error)
}

type redisRepository interface {
	Upsert(ctx context.Context, value executormodel.Executor) error
}

type eventRepository interface {
	TryStart(ctx context.Context, value *eventmodel.ProcessedEvent) (bool, error)
	MarkProcessed(ctx context.Context, eventID string) error
}

type Service struct {
	postgres postgresRepository
	redis    redisRepository
	events   eventRepository
	now      func() time.Time
}

func NewService(postgres postgresRepository, redis redisRepository, events eventRepository) *Service {
	return &Service{postgres: postgres, redis: redis, events: events, now: time.Now}
}

func (s *Service) Apply(
	ctx context.Context,
	envelope eventmodel.Envelope,
	payload executormodel.SnapshotPayload,
) error {
	if err := payload.Validate(); err != nil {
		return err
	}
	started, err := s.events.TryStart(ctx, &eventmodel.ProcessedEvent{
		ID: envelope.ID, Type: envelope.Type, ReceivedAt: s.now().UTC(),
	})
	if err != nil {
		return fmt.Errorf("start event %q: %w", envelope.ID, err)
	}
	if !started {
		return nil
	}
	value := &executormodel.Executor{
		ID: payload.ID, Version: payload.Version, Active: payload.Active,
		Capacity: payload.Capacity, Skills: payload.Skills, Attributes: payload.Attributes,
	}
	current, err := s.postgres.GetByID(ctx, payload.ID)
	switch {
	case err == nil:
		if current.Version > payload.Version {
			return s.finish(ctx, envelope.ID)
		}
		value.CurrentLoad = current.CurrentLoad
		value.ActiveCount = current.ActiveCount
		value.PendingCount = current.PendingCount
		value.ProcessedToday = current.ProcessedToday
		value.LastAssignmentAt = current.LastAssignmentAt
		if current.Version == payload.Version {
			value = current
		}
	case errors.Is(err, repository.ErrNotFound):
	case err != nil:
		return fmt.Errorf("get executor for event %q: %w", envelope.ID, err)
	}

	if err := s.postgres.Upsert(ctx, value); err != nil {
		return fmt.Errorf("upsert executor event %q: %w", envelope.ID, err)
	}
	if err := s.redis.Upsert(ctx, *value); err != nil {
		return fmt.Errorf("sync executor event %q to redis: %w", envelope.ID, err)
	}
	return s.finish(ctx, envelope.ID)
}

func (s *Service) finish(ctx context.Context, eventID string) error {
	if err := s.events.MarkProcessed(ctx, eventID); err != nil {
		return fmt.Errorf("finish event %q: %w", eventID, err)
	}
	return nil
}
