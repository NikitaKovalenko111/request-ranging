package ais

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type APIError struct {
	StatusCode int
	Code       string
	Message    string
	Retryable  bool
}

func (e *APIError) Error() string {
	return fmt.Sprintf("AIS returned HTTP %d (%s): %s", e.StatusCode, e.Code, e.Message)
}

type Client struct {
	baseURL string
	http    *http.Client
}

func New(baseURL string, timeout time.Duration) (*Client, error) {
	parsed, err := url.ParseRequestURI(baseURL)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("AIS base URL must be absolute")
	}
	if timeout <= 0 {
		return nil, fmt.Errorf("AIS request timeout must be positive")
	}
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: timeout},
	}, nil
}

func (c *Client) Assign(ctx context.Context, value AssignmentRequest) (AssignmentResponse, error) {
	if value.AssignmentID == "" || value.OrderID == "" || value.ExecutorID == "" || value.DecidedAt.IsZero() {
		return AssignmentResponse{}, fmt.Errorf("invalid AIS assignment request")
	}
	body, err := json.Marshal(value)
	if err != nil {
		return AssignmentResponse{}, fmt.Errorf("encode AIS assignment: %w", err)
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/api/v1/assignments", bytes.NewReader(body))
	if err != nil {
		return AssignmentResponse{}, fmt.Errorf("create AIS assignment request: %w", err)
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Idempotency-Key", value.AssignmentID)

	response, err := c.http.Do(request)
	if err != nil {
		return AssignmentResponse{}, fmt.Errorf("send AIS assignment: %w", err)
	}
	defer response.Body.Close()
	limited := io.LimitReader(response.Body, 1<<20)
	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		var payload ErrorResponse
		if err := json.NewDecoder(limited).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
			return AssignmentResponse{}, fmt.Errorf("decode AIS HTTP %d error: %w", response.StatusCode, err)
		}
		return AssignmentResponse{}, &APIError{
			StatusCode: response.StatusCode, Code: payload.Code, Message: payload.Message,
			Retryable: payload.Retryable || response.StatusCode == http.StatusInternalServerError || response.StatusCode == http.StatusServiceUnavailable,
		}
	}
	var result AssignmentResponse
	decoder := json.NewDecoder(limited)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&result); err != nil {
		return AssignmentResponse{}, fmt.Errorf("decode AIS assignment response: %w", err)
	}
	if result.AssignmentID != value.AssignmentID || result.OrderID != value.OrderID || result.ExecutorID != value.ExecutorID || result.Status != "confirmed" || result.ConfirmedAt.IsZero() {
		return AssignmentResponse{}, fmt.Errorf("AIS assignment response does not match request")
	}
	return result, nil
}

func (c *Client) GetAssignedExecutor(ctx context.Context, orderID string) (string, error) {
	if strings.TrimSpace(orderID) == "" {
		return "", fmt.Errorf("order ID is required")
	}
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		c.baseURL+"/api/v1/orders/"+url.PathEscape(orderID),
		nil,
	)
	if err != nil {
		return "", fmt.Errorf("create AIS order request: %w", err)
	}
	response, err := c.http.Do(request)
	if err != nil {
		return "", fmt.Errorf("get AIS order: %w", err)
	}
	defer response.Body.Close()
	limited := io.LimitReader(response.Body, 1<<20)
	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		var payload ErrorResponse
		_ = json.NewDecoder(limited).Decode(&payload)
		return "", &APIError{
			StatusCode: response.StatusCode, Code: payload.Code, Message: payload.Message,
			Retryable: payload.Retryable || response.StatusCode >= http.StatusInternalServerError,
		}
	}
	var result OrderResponse
	if err := json.NewDecoder(limited).Decode(&result); err != nil {
		return "", fmt.Errorf("decode AIS order response: %w", err)
	}
	if result.OrderID != orderID {
		return "", fmt.Errorf("AIS order response does not match request")
	}
	if result.AssignedExecutorID == nil || strings.TrimSpace(*result.AssignedExecutorID) == "" {
		return "", fmt.Errorf("AIS order %q has no assigned executor", orderID)
	}
	return *result.AssignedExecutorID, nil
}
