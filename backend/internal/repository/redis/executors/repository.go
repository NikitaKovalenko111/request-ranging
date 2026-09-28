package executors

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	redisclient "github.com/redis/go-redis/v9"

	executormodel "request-ranging/executor-balancer/internal/models/executor"
)

const activeExecutorsKey = "executors:active"

type Repository struct {
	redis *redisclient.Client
}

func New(redis *redisclient.Client) *Repository { return &Repository{redis: redis} }

func (r *Repository) Upsert(ctx context.Context, value executormodel.Executor) error {
	_, err := r.redis.TxPipelined(ctx, func(pipe redisclient.Pipeliner) error {
		key := executorKey(value.ID)
		if !value.Active {
			pipe.Del(ctx, key)
			pipe.SRem(ctx, activeExecutorsKey, value.ID)
			return nil
		}
		writeActive(ctx, pipe, key, value)
		pipe.SAdd(ctx, activeExecutorsKey, value.ID)
		return nil
	})
	if err != nil {
		return fmt.Errorf("upsert executor %q in redis: %w", value.ID, err)
	}
	return nil
}

func (r *Repository) ReplaceActive(ctx context.Context, values []executormodel.Executor) error {
	oldIDs, err := r.redis.SMembers(ctx, activeExecutorsKey).Result()
	if err != nil {
		return fmt.Errorf("read active executors: %w", err)
	}
	newIDs := make(map[string]struct{}, len(values))
	for _, value := range values {
		if value.Active {
			newIDs[value.ID] = struct{}{}
		}
	}
	_, err = r.redis.TxPipelined(ctx, func(pipe redisclient.Pipeliner) error {
		for _, id := range oldIDs {
			if _, remainsActive := newIDs[id]; !remainsActive {
				pipe.Del(ctx, executorKey(id))
				pipe.SRem(ctx, activeExecutorsKey, id)
			}
		}
		for _, value := range values {
			if !value.Active {
				continue
			}
			writeActive(ctx, pipe, executorKey(value.ID), value)
			pipe.SAdd(ctx, activeExecutorsKey, value.ID)
		}
		return nil
	})
	if err != nil {
		return fmt.Errorf("replace active executors: %w", err)
	}
	return nil
}

func writeActive(ctx context.Context, pipe redisclient.Pipeliner, key string, value executormodel.Executor) {
	lastAssignmentAt := ""
	if value.LastAssignmentAt != nil {
		lastAssignmentAt = value.LastAssignmentAt.UTC().Format(time.RFC3339Nano)
	}
	skills, _ := json.Marshal(value.Skills)
	attributes, _ := json.Marshal(value.Attributes)
	pipe.HSet(ctx, key, map[string]any{
		"active":     boolAsInt(value.Active),
		"capacity":   strconv.FormatFloat(value.Capacity, 'f', -1, 64),
		"version":    value.Version,
		"skills":     string(skills),
		"attributes": string(attributes),
		"updated_at": time.Now().UTC().Format(time.RFC3339Nano),
	})
	pipe.HSetNX(ctx, key, "current_load", strconv.FormatFloat(value.CurrentLoad, 'f', -1, 64))
	pipe.HSetNX(ctx, key, "active_count", value.ActiveCount)
	pipe.HSetNX(ctx, key, "pending_count", value.PendingCount)
	pipe.HSetNX(ctx, key, "processed_today", value.ProcessedToday)
	pipe.HSetNX(ctx, key, "last_assignment_at", lastAssignmentAt)
}

func (r *Repository) ResetProcessedToday(ctx context.Context) (int64, error) {
	count, err := r.redis.Eval(ctx, resetProcessedTodayScript, []string{activeExecutorsKey}).Int64()
	if err != nil {
		return 0, fmt.Errorf("reset processed_today: %w", err)
	}
	return count, nil
}

func executorKey(id string) string { return "executor:" + id }

func boolAsInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

const resetProcessedTodayScript = `
local ids = redis.call('SMEMBERS', KEYS[1])
local reset = 0
for _, id in ipairs(ids) do
    local key = 'executor:' .. id
    if redis.call('EXISTS', key) == 1 then
        redis.call('HSET', key, 'processed_today', 0)
        reset = reset + 1
    end
end
return reset`
