package event

import "time"

type ProcessedEvent struct {
	ID          string
	Type        string
	ReceivedAt  time.Time
	ProcessedAt *time.Time
}
