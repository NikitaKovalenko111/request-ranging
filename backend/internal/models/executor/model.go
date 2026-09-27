package executor

import "time"

type Executor struct {
	ID               string
	Version          int64
	Active           bool
	Capacity         float64
	CurrentLoad      float64
	ActiveCount      int
	PendingCount     int
	ProcessedToday   int
	Skills           []string
	Attributes       map[string]any
	LastAssignmentAt *time.Time
	CreatedAt        time.Time
	UpdatedAt        time.Time
}
