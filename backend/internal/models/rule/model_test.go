package rule

import "testing"

func TestOperatorIsValid(t *testing.T) {
	validOperators := []Operator{
		OperatorEqual, OperatorNotEqual, OperatorGreater, OperatorGreaterOrEqual,
		OperatorLess, OperatorLessOrEqual, OperatorIn, OperatorNotIn, OperatorBetween, OperatorContains,
	}
	for _, operator := range validOperators {
		if !operator.IsValid() {
			t.Errorf("Operator(%q).IsValid() = false", operator)
		}
	}
	if Operator("LIKE").IsValid() {
		t.Error("Operator(LIKE).IsValid() = true, want false")
	}
}
