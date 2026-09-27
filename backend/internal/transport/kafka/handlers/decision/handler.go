package decision

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"

	decisionmodel "request-ranging/executor-balancer/internal/models/decision"
	kafkatransport "request-ranging/executor-balancer/internal/transport/kafka"
)

type Handler struct {
	process func(ctx context.Context, result decisionmodel.Result) error
}

func New(process func(context.Context, decisionmodel.Result) error) *Handler {
	return &Handler{process: process}
}

func (h *Handler) Handle(ctx context.Context, payload []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(payload))
	decoder.DisallowUnknownFields()
	var result decisionmodel.Result
	if err := decoder.Decode(&result); err != nil {
		return kafkatransport.Permanent(fmt.Errorf("decode ExecutorDecisionCompleted: %w", err))
	}
	if err := ensureJSONEnded(decoder); err != nil {
		return kafkatransport.Permanent(err)
	}
	if err := result.Validate(); err != nil {
		return kafkatransport.Permanent(err)
	}
	if err := h.process(ctx, result); err != nil {
		return fmt.Errorf("process ExecutorDecisionCompleted for order %q: %w", result.OrderID, err)
	}
	return nil
}

func ensureJSONEnded(decoder *json.Decoder) error {
	var extra any
	if err := decoder.Decode(&extra); !errorsIsEOF(err) {
		if err == nil {
			return fmt.Errorf("decode ExecutorDecisionCompleted: multiple JSON values")
		}
		return fmt.Errorf("decode ExecutorDecisionCompleted: %w", err)
	}
	return nil
}

func errorsIsEOF(err error) bool { return err == io.EOF }
