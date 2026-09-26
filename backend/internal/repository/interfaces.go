package repository

import (
	"context"
	"errors"

	"request-ranging/executor-balancer/internal/models/assignment"
	"request-ranging/executor-balancer/internal/models/decisiontrace"
	"request-ranging/executor-balancer/internal/models/event"
	"request-ranging/executor-balancer/internal/models/executor"
	"request-ranging/executor-balancer/internal/models/order"
	"request-ranging/executor-balancer/internal/models/rule"
)

var ErrNotFound = errors.New("entity not found")

type OrderRepository interface {
	Upsert(ctx context.Context, value *order.Order) error
	GetByID(ctx context.Context, id string) (*order.Order, error)
	List(ctx context.Context, status *order.Status, limit, offset int) ([]order.Order, error)
}

type ExecutorRepository interface {
	Upsert(ctx context.Context, value *executor.Executor) error
	GetByID(ctx context.Context, id string) (*executor.Executor, error)
	ListActive(ctx context.Context) ([]executor.Executor, error)
}

type RuleRepository interface {
	Create(ctx context.Context, value *rule.Rule) error
	Update(ctx context.Context, value *rule.Rule) error
	Delete(ctx context.Context, id string) error
	GetByID(ctx context.Context, id string) (*rule.Rule, error)
	List(ctx context.Context, activeOnly bool) ([]rule.Rule, error)
}

type AssignmentRepository interface {
	Create(ctx context.Context, value *assignment.Assignment) error
	GetByID(ctx context.Context, id string) (*assignment.Assignment, error)
	GetLatestByOrderID(ctx context.Context, orderID string) (*assignment.Assignment, error)
	SetStatus(ctx context.Context, id string, status assignment.Status, errorMessage *string) error
}

type DecisionTraceRepository interface {
	Create(ctx context.Context, value *decisiontrace.DecisionTrace) error
	GetLatestByOrderID(ctx context.Context, orderID string) (*decisiontrace.DecisionTrace, error)
}

type EventRepository interface {
	TryStart(ctx context.Context, value *event.ProcessedEvent) (bool, error)
	MarkProcessed(ctx context.Context, eventID string) error
	GetByID(ctx context.Context, eventID string) (*event.ProcessedEvent, error)
}
