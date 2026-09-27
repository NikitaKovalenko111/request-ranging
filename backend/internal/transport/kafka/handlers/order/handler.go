package order

import (
	"context"
	"fmt"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	ordermodel "request-ranging/executor-balancer/internal/models/order"
	kafkatransport "request-ranging/executor-balancer/internal/transport/kafka"
	"request-ranging/executor-balancer/internal/transport/kafka/handlers/shared"
)

type Processor interface {
	ApplySnapshot(ctx context.Context, envelope eventmodel.Envelope, payload ordermodel.SnapshotPayload) error
	ApplyStatus(ctx context.Context, envelope eventmodel.Envelope, payload ordermodel.StatusChangedPayload) error
}

type Handler struct{ processor Processor }

func New(processor Processor) *Handler { return &Handler{processor: processor} }

func (h *Handler) Handle(ctx context.Context, body []byte) error {
	var envelope eventmodel.Envelope
	if err := shared.DecodeStrict(body, &envelope); err != nil {
		return kafkatransport.Permanent(fmt.Errorf("decode AIS order envelope: %w", err))
	}
	if err := envelope.Validate(); err != nil {
		return kafkatransport.Permanent(fmt.Errorf("validate AIS order envelope: %w", err))
	}
	switch envelope.Type {
	case ordermodel.EventTypeCreated, ordermodel.EventTypeUpdated:
		var payload ordermodel.SnapshotPayload
		if err := shared.DecodeStrict(envelope.Payload, &payload); err != nil {
			return kafkatransport.Permanent(fmt.Errorf("decode %s payload: %w", envelope.Type, err))
		}
		if err := payload.Validate(); err != nil {
			return kafkatransport.Permanent(err)
		}
		return h.processor.ApplySnapshot(ctx, envelope, payload)
	case ordermodel.EventTypeStatusChanged:
		var payload ordermodel.StatusChangedPayload
		if err := shared.DecodeStrict(envelope.Payload, &payload); err != nil {
			return kafkatransport.Permanent(fmt.Errorf("decode %s payload: %w", envelope.Type, err))
		}
		if err := payload.Validate(); err != nil {
			return kafkatransport.Permanent(err)
		}
		return h.processor.ApplyStatus(ctx, envelope, payload)
	default:
		return kafkatransport.Permanent(fmt.Errorf("unsupported AIS order event_type %q", envelope.Type))
	}
}
