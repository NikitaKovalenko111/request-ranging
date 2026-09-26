package shared

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"

	"request-ranging/executor-balancer/internal/repository"
)

func EncodeJSON(value any) ([]byte, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, fmt.Errorf("encode json: %w", err)
	}
	return encoded, nil
}

func EncodeMap(value map[string]any) ([]byte, error) {
	if value == nil {
		value = map[string]any{}
	}
	return EncodeJSON(value)
}

func DecodeJSON(encoded []byte, destination any) error {
	if err := json.Unmarshal(encoded, destination); err != nil {
		return fmt.Errorf("decode json: %w", err)
	}
	return nil
}

func MapNotFound(err error) error {
	if errors.Is(err, sql.ErrNoRows) {
		return repository.ErrNotFound
	}
	return err
}

func NormalizePage(limit, offset int) (int, int) {
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	if offset < 0 {
		offset = 0
	}
	return limit, offset
}
