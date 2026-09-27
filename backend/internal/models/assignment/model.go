package assignment

import "time"

type Status string

const (
	StatusPending   Status = "pending"
	StatusConfirmed Status = "confirmed"
	StatusCancelled Status = "cancelled"
	StatusFailed    Status = "failed"
)

type Assignment struct {
	ID            string
	OrderID       string
	ExecutorID    string
	Status        Status
	OrderWeight   float64
	ReservationID string
	ErrorMessage  *string
	CreatedAt     time.Time
	ConfirmedAt   *time.Time
	UpdatedAt     time.Time
}
