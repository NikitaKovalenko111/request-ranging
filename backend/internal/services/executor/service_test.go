package executor

import (
	"context"
	"testing"
	"time"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	executormodel "request-ranging/executor-balancer/internal/models/executor"
	"request-ranging/executor-balancer/internal/repository"
)

type fakePostgres struct {
	current *executormodel.Executor
	saved   *executormodel.Executor
}

func (f *fakePostgres) Upsert(_ context.Context, value *executormodel.Executor) error {
	copyValue := *value
	f.saved = &copyValue
	return nil
}

func (f *fakePostgres) GetByID(context.Context, string) (*executormodel.Executor, error) {
	if f.current == nil {
		return nil, repository.ErrNotFound
	}
	return f.current, nil
}

type fakeRedis struct{ saved *executormodel.Executor }

func (f *fakeRedis) Upsert(_ context.Context, value executormodel.Executor) error {
	f.saved = &value
	return nil
}

type fakeEvents struct{ processed bool }

func (f *fakeEvents) TryStart(context.Context, *eventmodel.ProcessedEvent) (bool, error) {
	return true, nil
}
func (f *fakeEvents) MarkProcessed(context.Context, string) error {
	f.processed = true
	return nil
}

func TestApplyStoresSkillsAndPreservesRuntime(t *testing.T) {
	lastAssignmentAt := time.Date(2026, 9, 27, 9, 0, 0, 0, time.UTC)
	postgres := &fakePostgres{current: &executormodel.Executor{
		ID: "executor-1", Version: 1, Active: true, Capacity: 1,
		CurrentLoad: 0.7, ActiveCount: 1, ProcessedToday: 3,
		LastAssignmentAt: &lastAssignmentAt,
	}}
	redis := &fakeRedis{}
	events := &fakeEvents{}
	service := NewService(postgres, redis, events)
	err := service.Apply(context.Background(), eventmodel.Envelope{ID: "event-1", Type: executormodel.EventTypeUpdated}, executormodel.SnapshotPayload{
		ID: "executor-1", Version: 2, Active: true, Capacity: 2,
		Skills: []string{"Go", "PostgreSQL"}, Attributes: map[string]any{},
	})
	if err != nil {
		t.Fatalf("Apply() error = %v", err)
	}
	if postgres.saved == nil || len(postgres.saved.Skills) != 2 || postgres.saved.CurrentLoad != 0.7 || postgres.saved.ActiveCount != 1 {
		t.Fatalf("saved executor = %+v", postgres.saved)
	}
	if redis.saved == nil || !events.processed {
		t.Fatalf("redis=%+v eventProcessed=%v", redis.saved, events.processed)
	}
}
