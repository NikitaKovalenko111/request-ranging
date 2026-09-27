package order

import (
	"context"
	"testing"

	assignmentmodel "request-ranging/executor-balancer/internal/models/assignment"
	eventmodel "request-ranging/executor-balancer/internal/models/event"
	ordermodel "request-ranging/executor-balancer/internal/models/order"
)

type fakeOrders struct{ value *ordermodel.Order }

func (f *fakeOrders) Upsert(_ context.Context, value *ordermodel.Order) error {
	f.value = value
	return nil
}
func (f *fakeOrders) GetByID(context.Context, string) (*ordermodel.Order, error) { return f.value, nil }

type fakeAssignments struct{ value *assignmentmodel.Assignment }

func (f *fakeAssignments) GetLatestByOrderID(context.Context, string) (*assignmentmodel.Assignment, error) {
	return f.value, nil
}

type fakeEvents struct{ processed bool }

func (f *fakeEvents) TryStart(context.Context, *eventmodel.ProcessedEvent) (bool, error) {
	return true, nil
}
func (f *fakeEvents) MarkProcessed(context.Context, string) error {
	f.processed = true
	return nil
}

type fakeWorkload struct {
	executorID string
	weight     float64
}

func (f *fakeWorkload) Complete(_ context.Context, _ string, executorID string, weight float64) (bool, error) {
	f.executorID = executorID
	f.weight = weight
	return true, nil
}

func TestApplyStatusReleasesConfirmedAssignment(t *testing.T) {
	orders := &fakeOrders{value: &ordermodel.Order{ID: "order-1", Status: ordermodel.StatusProcessed, Version: 1}}
	assignments := &fakeAssignments{value: &assignmentmodel.Assignment{
		ID: "assignment-1", OrderID: "order-1", ExecutorID: "executor-1",
		Status: assignmentmodel.StatusConfirmed, OrderWeight: 0.7,
	}}
	events := &fakeEvents{}
	workload := &fakeWorkload{}
	service := NewService(orders, assignments, events, workload)
	err := service.ApplyStatus(context.Background(), eventmodel.Envelope{ID: "event-1", Type: ordermodel.EventTypeStatusChanged}, ordermodel.StatusChangedPayload{
		ID: "order-1", PreviousStatus: ordermodel.StatusProcessed, Status: ordermodel.StatusAccept, Version: 2,
	})
	if err != nil {
		t.Fatalf("ApplyStatus() error = %v", err)
	}
	if workload.executorID != "executor-1" || workload.weight != 0.7 || !events.processed {
		t.Fatalf("workload=%+v processed=%v", workload, events.processed)
	}
}
