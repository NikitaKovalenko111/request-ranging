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
	Skills     []string       `json:"skills"`
	Attributes map[string]any `json:"attributes"`
}

func (p SnapshotPayload) Validate() error {
	if strings.TrimSpace(p.ID) == "" || p.Version <= 0 || p.Capacity <= 0 {
		return fmt.Errorf("invalid executor snapshot payload")
	}
	if p.Attributes == nil {
		return fmt.Errorf("invalid executor snapshot payload: attributes are required")
	}
	seenSkills := make(map[string]struct{}, len(p.Skills))
	for _, skill := range p.Skills {
		skill = strings.TrimSpace(skill)
		if skill == "" {
			return fmt.Errorf("invalid executor snapshot payload: skill must not be empty")
		}
		if _, duplicate := seenSkills[skill]; duplicate {
			return fmt.Errorf("invalid executor snapshot payload: duplicate skill %q", skill)
		}
		seenSkills[skill] = struct{}{}
	}
	return nil
}
