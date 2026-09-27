package ais

import "time"

type AssignmentRequest struct {
	AssignmentID string    `json:"assignment_id"`
	OrderID      string    `json:"order_id"`
	ExecutorID   string    `json:"executor_id"`
	DecidedAt    time.Time `json:"decided_at"`
}

type AssignmentResponse struct {
	AssignmentID string    `json:"assignment_id"`
	OrderID      string    `json:"order_id"`
	ExecutorID   string    `json:"executor_id"`
	Status       string    `json:"status"`
	ConfirmedAt  time.Time `json:"confirmed_at"`
}

type ErrorResponse struct {
	Code      string `json:"code"`
	Message   string `json:"message"`
	Retryable bool   `json:"retryable"`
}

type OrderResponse struct {
	OrderID            string  `json:"order_id"`
	AssignedExecutorID *string `json:"assigned_executor_id"`
}
