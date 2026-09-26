package order

import "testing"

func TestStatusIsValid(t *testing.T) {
	tests := []struct {
		status Status
		valid  bool
	}{
		{status: StatusProcessed, valid: true},
		{status: StatusAwait, valid: true},
		{status: StatusAccept, valid: true},
		{status: StatusReject, valid: true},
		{status: Status("unknown"), valid: false},
	}
	for _, test := range tests {
		if got := test.status.IsValid(); got != test.valid {
			t.Errorf("Status(%q).IsValid() = %t, want %t", test.status, got, test.valid)
		}
	}
}
