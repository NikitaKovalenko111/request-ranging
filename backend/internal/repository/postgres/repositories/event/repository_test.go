package eventrepo

import (
	"context"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
)

func TestTryStartDuplicate(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	mock.ExpectExec(`(?s)INSERT INTO processed_events.*ON CONFLICT \(event_id\) DO NOTHING`).
		WithArgs("event-1", "OrderCreated", nil).
		WillReturnResult(sqlmock.NewResult(0, 0))

	started, err := New(database).TryStart(context.Background(), &eventmodel.ProcessedEvent{
		ID: "event-1", Type: "OrderCreated",
	})
	if err != nil {
		t.Fatalf("TryStart() error = %v", err)
	}
	if started {
		t.Fatal("TryStart() = true for duplicate event")
	}
}
