package order

import "time"

type Status string

const (
	StatusProcessed Status = "processed"
	StatusAwait     Status = "await"
	StatusAccept    Status = "accept"
	StatusReject    Status = "reject"
)

func (s Status) IsValid() bool {
	switch s {
	case StatusProcessed, StatusAwait, StatusAccept, StatusReject:
		return true
	default:
		return false
	}
}

type Order struct {
	ID                 string
	ParentID           *string
	Status             Status
	Weight             float64
	Version            int64
	Attributes         map[string]any
	AssignedExecutorID *string
	CreatedAt          time.Time
	UpdatedAt          time.Time
}
