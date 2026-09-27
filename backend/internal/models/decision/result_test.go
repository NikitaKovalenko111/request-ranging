package decision

import (
	"encoding/json"
	"errors"
	"testing"
)

func TestResultUnmarshalAndValidate(t *testing.T) {
	payload := []byte(`{
		"event_type":"ExecutorDecisionCompleted",
		"event_version":1,
		"occurred_at":"2026-09-27T10:00:00+00:00",
		"order_id":42,
		"balanced_candidates":[{
			"executor_id":"7","rank":1,"ml_score":0.82,"effective_load":0.2,
			"capacity":1.0,"active_count":1,"pending_count":0,"processed_today":5,
			"last_assignment_at":"2026-09-27T09:59:00+00:00"
		}]
	}`)
	var result Result
	if err := json.Unmarshal(payload, &result); err != nil {
		t.Fatalf("json.Unmarshal() error = %v", err)
	}
	if err := result.Validate(); err != nil {
		t.Fatalf("Validate() error = %v", err)
	}
	if result.OrderID != 42 || result.BalancedCandidates[0].ExecutorID != "7" {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestResultValidateRejectsInvalidCandidates(t *testing.T) {
	result := validResult()
	result.BalancedCandidates = append(result.BalancedCandidates, result.BalancedCandidates[0])
	result.BalancedCandidates[1].Rank = 2
	if err := result.Validate(); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("Validate() error = %v, want ErrInvalidResult", err)
	}
}

func validResult() Result {
	var result Result
	_ = json.Unmarshal([]byte(`{
		"event_type":"ExecutorDecisionCompleted","event_version":1,
		"occurred_at":"2026-09-27T10:00:00Z","order_id":42,
		"balanced_candidates":[{
			"executor_id":"7","rank":1,"ml_score":0.82,"effective_load":0.2,
			"capacity":1,"active_count":1,"pending_count":0,"processed_today":5,
			"last_assignment_at":null
		}]
	}`), &result)
	return result
}
