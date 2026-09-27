package event

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

const (
	Version1           = 1
	SourceAISSimulator = "ais-simulator"
)

type Envelope struct {
	ID         string          `json:"event_id"`
	Type       string          `json:"event_type"`
	Version    int             `json:"event_version"`
	OccurredAt time.Time       `json:"occurred_at"`
	Source     string          `json:"source"`
	Payload    json.RawMessage `json:"payload"`
}

func (e Envelope) Validate() error {
	if strings.TrimSpace(e.ID) == "" {
		return fmt.Errorf("event_id must not be empty")
	}
	if strings.TrimSpace(e.Type) == "" {
		return fmt.Errorf("event_type must not be empty")
	}
	if e.Version != Version1 {
		return fmt.Errorf("unsupported event_version %d", e.Version)
	}
	if e.OccurredAt.IsZero() {
		return fmt.Errorf("occurred_at is required")
	}
	if e.Source != SourceAISSimulator {
		return fmt.Errorf("source must be %q", SourceAISSimulator)
	}
	if len(e.Payload) == 0 || string(e.Payload) == "null" {
		return fmt.Errorf("payload is required")
	}
	return nil
}
