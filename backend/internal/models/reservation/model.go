package reservation

import "time"

type Status string

const (
	StatusPending   Status = "pending"
	StatusConfirmed Status = "confirmed"
	StatusCancelled Status = "cancelled"
	StatusExpired   Status = "expired"
)

type Reservation struct {
	ID         string
	OrderID    string
	ExecutorID string
	Weight     float64
	Status     Status
	CreatedAt  time.Time
	ExpiresAt  time.Time
}
