package executor

import (
	"context"
	"fmt"

	eventmodel "request-ranging/executor-balancer/internal/models/event"
	executormodel "request-ranging/executor-balancer/internal/models/executor"
	kafkatransport "request-ranging/executor-balancer/internal/transport/kafka"
	"request-ranging/executor-balancer/internal/transport/kafka/handlers/shared"
)

type Processor interface {
	Apply(ctx context.Context, envelope eventmodel.Envelope, payload executormodel.SnapshotPayload) error
}

type Handler struct{ processor Processor }

func New(processor Processor) *Handler { return &Handler{processor: processor} }

func (h *Handler) Handle(ctx context.Context, body []byte) error {
	var envelope eventmodel.Envelope
	if err := shared.DecodeStrict(body, &envelope); err != nil {
		return kafkatransport.Permanent(fmt.Errorf("decode AIS executor envelope: %w", err))
	}
	if err := envelope.Validate(); err != nil {
		return kafkatransport.Permanent(fmt.Errorf("validate AIS executor envelope: %w", err))
	}
	if envelope.Type != executormodel.EventTypeCreated && envelope.Type != executormodel.EventTypeUpdated {
		return kafkatransport.Permanent(fmt.Errorf("unsupported AIS executor event_type %q", envelope.Type))
	}
	var payload executormodel.SnapshotPayload
	if err := shared.DecodeStrict(envelope.Payload, &payload); err != nil {
		return kafkatransport.Permanent(fmt.Errorf("decode %s payload: %w", envelope.Type, err))
	}
	if err := payload.Validate(); err != nil {
		return kafkatransport.Permanent(err)
	}
	return h.processor.Apply(ctx, envelope, payload)
}
