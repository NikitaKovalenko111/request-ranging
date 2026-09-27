package reservations

import (
	"context"
	"errors"
	"testing"
	"time"

	redisclient "github.com/redis/go-redis/v9"

	reservationmodel "request-ranging/executor-balancer/internal/models/reservation"
	repositorypkg "request-ranging/executor-balancer/internal/repository"
)

type fakeEvaluator struct {
	values []any
	err    error
	calls  int
}

func (f *fakeEvaluator) Eval(_ context.Context, _ string, _ []string, _ ...any) *redisclient.Cmd {
	f.calls++
	command := redisclient.NewCmd(context.Background())
	if f.err != nil {
		command.SetErr(f.err)
		return command
	}
	value := f.values[0]
	f.values = f.values[1:]
	command.SetVal(value)
	return command
}

func TestTryReserve(t *testing.T) {
	evaluator := &fakeEvaluator{values: []any{int64(1)}}
	store := New(evaluator, 30*time.Second)
	value := &reservationmodel.Reservation{ID: "reservation-1", OrderID: "42", ExecutorID: "7", Weight: 0.7}
	reserved, err := store.TryReserve(context.Background(), value)
	if err != nil {
		t.Fatalf("TryReserve() error = %v", err)
	}
	if !reserved || value.Status != reservationmodel.StatusPending || value.ExpiresAt.IsZero() {
		t.Fatalf("unexpected reservation: reserved=%v value=%+v", reserved, value)
	}
}

func TestTryReserveOrderAlreadyReserved(t *testing.T) {
	store := New(&fakeEvaluator{values: []any{int64(2)}}, 30*time.Second)
	_, err := store.TryReserve(context.Background(), &reservationmodel.Reservation{
		ID: "reservation-1", OrderID: "42", ExecutorID: "7", Weight: 0.7,
	})
	if !errors.Is(err, repositorypkg.ErrAlreadyReserved) {
		t.Fatalf("TryReserve() error = %v, want ErrAlreadyReserved", err)
	}
}

func TestConfirmAndCancel(t *testing.T) {
	evaluator := &fakeEvaluator{values: []any{int64(1), int64(1)}}
	store := New(evaluator, 30*time.Second)
	value := reservationmodel.Reservation{ID: "reservation-1", OrderID: "42", ExecutorID: "7", Weight: 0.7}
	if err := store.Confirm(context.Background(), value, time.Now()); err != nil {
		t.Fatalf("Confirm() error = %v", err)
	}
	if err := store.Cancel(context.Background(), value); err != nil {
		t.Fatalf("Cancel() error = %v", err)
	}
}
