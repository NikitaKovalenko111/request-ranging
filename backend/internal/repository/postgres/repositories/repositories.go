package repositories

import (
	"database/sql"

	"request-ranging/executor-balancer/internal/repository"
	assignmentrepo "request-ranging/executor-balancer/internal/repository/postgres/repositories/assignment"
	decisiontracerepo "request-ranging/executor-balancer/internal/repository/postgres/repositories/decisiontrace"
	eventrepo "request-ranging/executor-balancer/internal/repository/postgres/repositories/event"
	executorrepo "request-ranging/executor-balancer/internal/repository/postgres/repositories/executor"
	orderrepo "request-ranging/executor-balancer/internal/repository/postgres/repositories/order"
	rulerepo "request-ranging/executor-balancer/internal/repository/postgres/repositories/rule"
)

type Repositories struct {
	Orders         repository.OrderRepository
	Executors      repository.ExecutorRepository
	Rules          repository.RuleRepository
	Assignments    repository.AssignmentRepository
	DecisionTraces repository.DecisionTraceRepository
	Events         repository.EventRepository
}

func New(database *sql.DB) Repositories {
	return Repositories{
		Orders:         orderrepo.New(database),
		Executors:      executorrepo.New(database),
		Rules:          rulerepo.New(database),
		Assignments:    assignmentrepo.New(database),
		DecisionTraces: decisiontracerepo.New(database),
		Events:         eventrepo.New(database),
	}
}
