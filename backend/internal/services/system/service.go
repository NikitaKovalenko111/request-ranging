package system

import (
	"context"
	"sync"
	"time"
)

type DependencyChecker interface {
	Name() string
	Check(ctx context.Context) error
}

type DependencyStatus struct {
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
}

type Readiness struct {
	Status string                      `json:"status"`
	Checks map[string]DependencyStatus `json:"checks"`
}

type HealthService struct {
	timeout  time.Duration
	checkers []DependencyChecker
}

func NewHealthService(timeout time.Duration, checkers ...DependencyChecker) *HealthService {
	return &HealthService{timeout: timeout, checkers: checkers}
}

func (s *HealthService) Readiness(ctx context.Context) Readiness {
	result := Readiness{
		Status: "ready",
		Checks: make(map[string]DependencyStatus, len(s.checkers)),
	}

	var mutex sync.Mutex
	var waitGroup sync.WaitGroup
	for _, checker := range s.checkers {
		checker := checker
		waitGroup.Add(1)
		go func() {
			defer waitGroup.Done()

			checkContext, cancel := context.WithTimeout(ctx, s.timeout)
			defer cancel()
			err := checker.Check(checkContext)

			status := DependencyStatus{Status: "up"}
			if err != nil {
				status = DependencyStatus{Status: "down", Message: err.Error()}
			}

			mutex.Lock()
			result.Checks[checker.Name()] = status
			if err != nil {
				result.Status = "not_ready"
			}
			mutex.Unlock()
		}()
	}
	waitGroup.Wait()

	return result
}
