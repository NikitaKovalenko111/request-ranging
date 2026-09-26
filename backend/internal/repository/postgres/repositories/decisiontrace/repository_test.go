package decisiontracerepo

import (
	"context"
	"testing"
	"time"

	"github.com/DATA-DOG/go-sqlmock"
)

func TestGetLatestByOrderID(t *testing.T) {
	database, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock.New() error = %v", err)
	}
	defer database.Close()
	now := time.Now().UTC()
	mock.ExpectQuery(`(?s)SELECT id, order_id, assignment_id, trace, processing_time_ms, created_at.*FROM decision_traces`).
		WithArgs("order-1").
		WillReturnRows(sqlmock.NewRows([]string{
			"id", "order_id", "assignment_id", "trace", "processing_time_ms", "created_at",
		}).AddRow(1, "order-1", nil, []byte(`{"eligible":3}`), 15, now))

	value, err := New(database).GetLatestByOrderID(context.Background(), "order-1")
	if err != nil {
		t.Fatalf("GetLatestByOrderID() error = %v", err)
	}
	if value.Data["eligible"] != float64(3) {
		t.Fatalf("trace data = %#v", value.Data)
	}
}
