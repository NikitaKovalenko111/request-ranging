package rulerepo

import (
	"context"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"

	rulemodel "request-ranging/executor-balancer/internal/models/rule"
)

func TestCreate(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	now := time.Now().UTC()
	mock.ExpectQuery(`(?s)INSERT INTO rules.*RETURNING created_at, updated_at`).
		WithArgs("rule-1", "VIP", true, 10, sqlmock.AnyArg(), rulemodel.OperatorEqual, sqlmock.AnyArg(), "VIP is not allowed").
		WillReturnRows(sqlmock.NewRows([]string{"created_at", "updated_at"}).AddRow(now, now))

	value := &rulemodel.Rule{
		ID: "rule-1", Name: "VIP", Active: true, Priority: 10,
		LeftOperand:   rulemodel.Operand{Source: rulemodel.OperandSourceOrder, Field: "vip"},
		Operator:      rulemodel.OperatorEqual,
		RightOperand:  rulemodel.Operand{Source: rulemodel.OperandSourceExecutor, Field: "vip_allowed"},
		FailureReason: "VIP is not allowed",
	}
	if err := New(database).Create(context.Background(), value); err != nil {
		t.Fatalf("Create() error = %v", err)
	}
	if value.CreatedAt.IsZero() || value.UpdatedAt.IsZero() {
		t.Fatal("Create() did not populate timestamps")
	}
}
