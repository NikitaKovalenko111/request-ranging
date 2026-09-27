package rule

import "time"

type OperandSource string

const (
	OperandSourceOrder    OperandSource = "order"
	OperandSourceExecutor OperandSource = "executor"
	OperandSourceConstant OperandSource = "constant"
)

type Operand struct {
	Source OperandSource `json:"source"`
	Field  string        `json:"field,omitempty"`
	Value  any           `json:"value,omitempty"`
}

type Operator string

const (
	OperatorEqual          Operator = "="
	OperatorNotEqual       Operator = "!="
	OperatorGreater        Operator = ">"
	OperatorGreaterOrEqual Operator = ">="
	OperatorLess           Operator = "<"
	OperatorLessOrEqual    Operator = "<="
	OperatorIn             Operator = "IN"
	OperatorNotIn          Operator = "NOT IN"
	OperatorBetween        Operator = "BETWEEN"
	OperatorContains       Operator = "CONTAINS"
)

func (o Operator) IsValid() bool {
	switch o {
	case OperatorEqual, OperatorNotEqual, OperatorGreater, OperatorGreaterOrEqual,
		OperatorLess, OperatorLessOrEqual, OperatorIn, OperatorNotIn, OperatorBetween, OperatorContains:
		return true
	default:
		return false
	}
}

type Rule struct {
	ID            string
	Name          string
	Active        bool
	Priority      int
	LeftOperand   Operand
	Operator      Operator
	RightOperand  Operand
	FailureReason string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}
