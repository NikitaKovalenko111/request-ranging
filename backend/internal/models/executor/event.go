package executor

import (
	"fmt"
	"strings"
)

const (
	EventTypeCreated = "ExecutorCreated"
	EventTypeUpdated = "ExecutorUpdated"
)

type SnapshotPayload struct {
	ID         string         `json:"executor_id"`
	Active     bool           `json:"active"`
	Capacity   float64        `json:"capacity"`
	DailyLimit *int           `json:"daily_limit,omitempty"`
	Version    int64          `json:"version"`
	Attributes map[string]any `json:"attributes"`
}

func (p SnapshotPayload) Validate() error {
	if strings.TrimSpace(p.ID) == "" || p.Version <= 0 || p.Capacity <= 0 {
		return fmt.Errorf("invalid executor snapshot payload")
	}
	if p.Attributes == nil {
		return fmt.Errorf("invalid executor snapshot payload: attributes are required")
	}
	return nil
}
