package executor

import "time"

type Executor struct {
	ID              string
	Version         int64
	Active          bool
	Capacity        float64
	DailyLimit      *int
	DailyCount      int
	DailyCountDate  time.Time
	ConfirmedWeight float64
	PendingWeight   float64
	OpenOrders      int
	Attributes      map[string]any
	LastAssignedAt  *time.Time
	CreatedAt       time.Time
	UpdatedAt       time.Time
}
