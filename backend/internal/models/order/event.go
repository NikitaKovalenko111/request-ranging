package order

import (
	"fmt"
	"strings"
)

const (
	EventTypeCreated       = "OrderCreated"
	EventTypeUpdated       = "OrderUpdated"
	EventTypeStatusChanged = "OrderStatusChanged"
)

type SnapshotPayload struct {
	ID         string         `json:"order_id"`
	ParentID   *string        `json:"parent_id"`
	Status     Status         `json:"status"`
	Weight     float64        `json:"weight"`
	Version    int64          `json:"version"`
	Attributes map[string]any `json:"attributes"`
}

type StatusChangedPayload struct {
	ID             string `json:"order_id"`
	PreviousStatus Status `json:"previous_status"`
	Status         Status `json:"status"`
	Version        int64  `json:"version"`
}

func (p SnapshotPayload) Validate() error {
	if strings.TrimSpace(p.ID) == "" || p.Version <= 0 || p.Weight <= 0 || !p.Status.IsValid() {
		return fmt.Errorf("invalid order snapshot payload")
	}
	if p.Attributes == nil {
		return fmt.Errorf("invalid order snapshot payload: attributes are required")
	}
	return nil
}

func (p StatusChangedPayload) Validate() error {
	if strings.TrimSpace(p.ID) == "" || p.Version <= 0 || !p.Status.IsValid() || !p.PreviousStatus.IsValid() {
		return fmt.Errorf("invalid OrderStatusChanged payload")
	}
	return nil
}
