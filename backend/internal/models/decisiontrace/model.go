package decisiontrace

import "time"

type DecisionTrace struct {
	ID               int64
	OrderID          string
	AssignmentID     *string
	Data             map[string]any
	ProcessingTimeMS int64
	CreatedAt        time.Time
}
