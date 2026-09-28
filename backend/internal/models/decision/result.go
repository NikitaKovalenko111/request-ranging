package decision

import (
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"strings"
	"time"
)

const (
	EventTypeExecutorDecisionCompleted = "ExecutorDecisionCompleted"
	EventVersion1                      = 1
)

var ErrInvalidResult = errors.New("invalid executor decision result")

type Result struct {
	EventType          string              `json:"event_type"`
	EventVersion       int                 `json:"event_version"`
	OccurredAt         time.Time           `json:"occurred_at"`
	OrderID            string              `json:"order_id"`
	BalancedCandidates []BalancedCandidate `json:"balanced_candidates"`
}

type BalancedCandidate struct {
	ExecutorID       string     `json:"executor_id"`
	Rank             int        `json:"rank"`
	MLScore          float64    `json:"ml_score"`
	EffectiveLoad    float64    `json:"effective_load"`
	Capacity         float64    `json:"capacity"`
	ActiveCount      int        `json:"active_count"`
	PendingCount     int        `json:"pending_count"`
	ProcessedToday   int        `json:"processed_today"`
	LastAssignmentAt *time.Time `json:"last_assignment_at"`
}

func (r Result) Validate() error {
	if r.EventType != EventTypeExecutorDecisionCompleted {
		return fmt.Errorf("%w: event_type must be %q", ErrInvalidResult, EventTypeExecutorDecisionCompleted)
	}
	if r.EventVersion != EventVersion1 {
		return fmt.Errorf("%w: unsupported event_version %d", ErrInvalidResult, r.EventVersion)
	}
	if r.OccurredAt.IsZero() {
		return fmt.Errorf("%w: occurred_at is required", ErrInvalidResult)
	}
	if strings.TrimSpace(r.OrderID) == "" {
		return fmt.Errorf("%w: order_id must not be empty", ErrInvalidResult)
	}
	executorIDs := make(map[string]struct{}, len(r.BalancedCandidates))
	for index, candidate := range r.BalancedCandidates {
		expectedRank := index + 1
		if candidate.ExecutorID == "" {
			return fmt.Errorf("%w: candidate rank %d has empty executor_id", ErrInvalidResult, expectedRank)
		}
		if _, duplicate := executorIDs[candidate.ExecutorID]; duplicate {
			return fmt.Errorf("%w: duplicate executor_id %q", ErrInvalidResult, candidate.ExecutorID)
		}
		executorIDs[candidate.ExecutorID] = struct{}{}
		if candidate.Rank != expectedRank {
			return fmt.Errorf("%w: candidate %q has rank %d, expected %d", ErrInvalidResult, candidate.ExecutorID, candidate.Rank, expectedRank)
		}
		if !finite(candidate.MLScore) {
			return fmt.Errorf("%w: candidate %q has invalid ml_score", ErrInvalidResult, candidate.ExecutorID)
		}
		if !finite(candidate.EffectiveLoad) || candidate.EffectiveLoad < 0 {
			return fmt.Errorf("%w: candidate %q has invalid effective_load", ErrInvalidResult, candidate.ExecutorID)
		}
		if !finite(candidate.Capacity) || candidate.Capacity <= 0 {
			return fmt.Errorf("%w: candidate %q has invalid capacity", ErrInvalidResult, candidate.ExecutorID)
		}
		if candidate.ActiveCount < 0 || candidate.PendingCount < 0 || candidate.ProcessedToday < 0 {
			return fmt.Errorf("%w: candidate %q has negative counters", ErrInvalidResult, candidate.ExecutorID)
		}
	}
	return nil
}

func (r Result) ToMap() (map[string]any, error) {
	encoded, err := json.Marshal(r)
	if err != nil {
		return nil, fmt.Errorf("encode decision result: %w", err)
	}
	value := make(map[string]any)
	if err := json.Unmarshal(encoded, &value); err != nil {
		return nil, fmt.Errorf("decode decision result: %w", err)
	}
	return value, nil
}

func finite(value float64) bool {
	return !math.IsNaN(value) && !math.IsInf(value, 0)
}
