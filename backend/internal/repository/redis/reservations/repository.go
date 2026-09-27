package reservations

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"time"

	redisclient "github.com/redis/go-redis/v9"

	reservationmodel "request-ranging/executor-balancer/internal/models/reservation"
	"request-ranging/executor-balancer/internal/repository"
)

var (
	ErrReservationState = errors.New("reservation has unexpected state")
)

type evaluator interface {
	Eval(ctx context.Context, script string, keys []string, args ...any) *redisclient.Cmd
}

type Repository struct {
	redis evaluator
	ttl   time.Duration
}

func New(redis evaluator, ttl time.Duration) *Repository {
	return &Repository{redis: redis, ttl: ttl}
}

func (r *Repository) TryReserve(ctx context.Context, value *reservationmodel.Reservation) (bool, error) {
	if value.ID == "" || value.OrderID == "" || value.ExecutorID == "" || value.Weight <= 0 {
		return false, fmt.Errorf("reserve executor: invalid reservation")
	}
	if r.ttl <= 0 {
		return false, fmt.Errorf("reserve executor: TTL must be positive")
	}
	now := time.Now().UTC()
	value.Status = reservationmodel.StatusPending
	value.CreatedAt = now
	value.ExpiresAt = now.Add(r.ttl)

	code, err := r.redis.Eval(ctx, tryReserveScript, []string{
		executorKey(value.ExecutorID),
		executorReservationKey(value.ExecutorID),
		orderReservationKey(value.OrderID),
		reservationKey(value.ID),
		pendingReservationsKey,
	},
		value.ID, value.OrderID, value.ExecutorID,
		strconv.FormatFloat(value.Weight, 'f', -1, 64),
		now.Format(time.RFC3339Nano), value.ExpiresAt.UnixMilli(), r.ttl.Milliseconds(),
	).Int64()
	if err != nil {
		return false, fmt.Errorf("reserve executor %q: %w", value.ExecutorID, err)
	}
	switch code {
	case 1:
		return true, nil
	case 2:
		return false, repository.ErrAlreadyReserved
	default:
		return false, nil
	}
}

func (r *Repository) Refresh(ctx context.Context, value *reservationmodel.Reservation) error {
	if value.ID == "" || value.OrderID == "" || value.ExecutorID == "" {
		return fmt.Errorf("refresh reservation: invalid reservation")
	}
	now := time.Now().UTC()
	value.ExpiresAt = now.Add(r.ttl)
	code, err := r.redis.Eval(ctx, refreshScript, []string{
		executorReservationKey(value.ExecutorID), orderReservationKey(value.OrderID),
		reservationKey(value.ID), pendingReservationsKey,
	}, value.ID, value.ExpiresAt.UnixMilli(), r.ttl.Milliseconds()).Int64()
	if err != nil {
		return fmt.Errorf("refresh reservation %q: %w", value.ID, err)
	}
	if code != 1 {
		return fmt.Errorf("refresh reservation %q: %w", value.ID, ErrReservationState)
	}
	return nil
}

func (r *Repository) Confirm(ctx context.Context, value reservationmodel.Reservation, confirmedAt time.Time) error {
	code, err := r.redis.Eval(ctx, confirmScript, []string{
		executorKey(value.ExecutorID), executorReservationKey(value.ExecutorID),
		orderReservationKey(value.OrderID), reservationKey(value.ID), pendingReservationsKey,
		confirmationKey(value.ID),
	}, value.ID, confirmedAt.UTC().Format(time.RFC3339Nano),
		int64((30*24*time.Hour)/time.Millisecond), strconv.FormatFloat(value.Weight, 'f', -1, 64)).Int64()
	if err != nil {
		return fmt.Errorf("confirm reservation %q: %w", value.ID, err)
	}
	if code != 1 {
		return fmt.Errorf("confirm reservation %q: %w", value.ID, ErrReservationState)
	}
	return nil
}

func (r *Repository) Cancel(ctx context.Context, value reservationmodel.Reservation) error {
	code, err := r.redis.Eval(ctx, cancelScript, []string{
		executorKey(value.ExecutorID), executorReservationKey(value.ExecutorID),
		orderReservationKey(value.OrderID), reservationKey(value.ID), pendingReservationsKey,
	}, value.ID, strconv.FormatFloat(value.Weight, 'f', -1, 64)).Int64()
	if err != nil {
		return fmt.Errorf("cancel reservation %q: %w", value.ID, err)
	}
	if code != 1 {
		return fmt.Errorf("cancel reservation %q: %w", value.ID, ErrReservationState)
	}
	return nil
}

func (r *Repository) Complete(ctx context.Context, eventID, executorID string, weight float64) (bool, error) {
	if eventID == "" || executorID == "" || weight <= 0 {
		return false, fmt.Errorf("complete assignment: invalid arguments")
	}
	code, err := r.redis.Eval(ctx, completeScript, []string{
		executorKey(executorID), completionKey(eventID),
	}, strconv.FormatFloat(weight, 'f', -1, 64), int64((30*24*time.Hour)/time.Millisecond)).Int64()
	if err != nil {
		return false, fmt.Errorf("complete assignment for executor %q: %w", executorID, err)
	}
	return code == 1, nil
}

func (r *Repository) CancelExpired(ctx context.Context, now time.Time, limit int) (int64, error) {
	if limit <= 0 {
		limit = 100
	}
	count, err := r.redis.Eval(ctx, cancelExpiredScript, []string{pendingReservationsKey},
		now.UTC().UnixMilli(), limit,
	).Int64()
	if err != nil {
		return 0, fmt.Errorf("cancel expired reservations: %w", err)
	}
	return count, nil
}

func executorKey(id string) string            { return "executor:" + id }
func executorReservationKey(id string) string { return "executor:reservation:" + id }
func orderReservationKey(id string) string    { return "order:reservation:" + id }
func reservationKey(id string) string         { return "reservation:" + id }
func completionKey(eventID string) string     { return "completion:event:" + eventID }
func confirmationKey(id string) string        { return "reservation:confirmed:" + id }

const pendingReservationsKey = "reservations:pending"

const tryReserveScript = `
if redis.call('EXISTS', KEYS[1]) == 0 or redis.call('HGET', KEYS[1], 'active') ~= '1' then
    return 0
end
local capacity = tonumber(redis.call('HGET', KEYS[1], 'capacity'))
local current_load = tonumber(redis.call('HGET', KEYS[1], 'current_load')) or 0
local order_weight = tonumber(ARGV[4])
if capacity == nil or order_weight == nil or current_load + order_weight > capacity then
    return 0
end
if redis.call('EXISTS', KEYS[3]) == 1 then
    return 2
end
if redis.call('EXISTS', KEYS[2]) == 1 then
    return 0
end
redis.call('SET', KEYS[2], ARGV[1], 'PX', ARGV[7])
redis.call('SET', KEYS[3], ARGV[1], 'PX', ARGV[7])
redis.call('HSET', KEYS[4],
    'status', 'pending',
    'order_id', ARGV[2],
    'executor_id', ARGV[3],
    'weight', ARGV[4],
    'created_at', ARGV[5],
    'expires_at_ms', ARGV[6])
redis.call('HINCRBY', KEYS[1], 'pending_count', 1)
redis.call('HINCRBYFLOAT', KEYS[1], 'current_load', ARGV[4])
redis.call('ZADD', KEYS[5], ARGV[6], ARGV[1])
return 1`

const refreshScript = `
if redis.call('HGET', KEYS[3], 'status') ~= 'pending' then return 0 end
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
redis.call('PEXPIRE', KEYS[1], ARGV[3])
redis.call('PEXPIRE', KEYS[2], ARGV[3])
redis.call('HSET', KEYS[3], 'expires_at_ms', ARGV[2])
redis.call('ZADD', KEYS[4], ARGV[2], ARGV[1])
return 1`

const confirmScript = `
if redis.call('EXISTS', KEYS[6]) == 1 then return 1 end
if redis.call('EXISTS', KEYS[1]) == 0 or redis.call('HGET', KEYS[1], 'active') ~= '1' then return 0 end
if redis.call('HGET', KEYS[4], 'status') ~= 'pending' then
    redis.call('HINCRBY', KEYS[1], 'active_count', 1)
    redis.call('HINCRBYFLOAT', KEYS[1], 'current_load', ARGV[4])
    redis.call('HSET', KEYS[1], 'last_assignment_at', ARGV[2])
    redis.call('SET', KEYS[6], '1', 'PX', ARGV[3])
    return 1
end
if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
if redis.call('GET', KEYS[3]) ~= ARGV[1] then return 0 end
redis.call('HINCRBY', KEYS[1], 'pending_count', -1)
redis.call('HINCRBY', KEYS[1], 'active_count', 1)
redis.call('HSET', KEYS[1], 'last_assignment_at', ARGV[2])
redis.call('DEL', KEYS[2], KEYS[3], KEYS[4])
redis.call('ZREM', KEYS[5], ARGV[1])
redis.call('SET', KEYS[6], '1', 'PX', ARGV[3])
return 1`

const cancelScript = `
if redis.call('HGET', KEYS[4], 'status') ~= 'pending' then return 0 end
if redis.call('GET', KEYS[2]) == ARGV[1] then redis.call('DEL', KEYS[2]) end
if redis.call('GET', KEYS[3]) == ARGV[1] then redis.call('DEL', KEYS[3]) end
if redis.call('EXISTS', KEYS[1]) == 1 then
    redis.call('HINCRBY', KEYS[1], 'pending_count', -1)
    redis.call('HINCRBYFLOAT', KEYS[1], 'current_load', -tonumber(ARGV[2]))
end
redis.call('DEL', KEYS[4])
redis.call('ZREM', KEYS[5], ARGV[1])
return 1`

const completeScript = `
if redis.call('EXISTS', KEYS[2]) == 1 then return 0 end
redis.call('SET', KEYS[2], '1', 'PX', ARGV[2])
if redis.call('EXISTS', KEYS[1]) == 0 then return 1 end
local weight = tonumber(ARGV[1])
local active_count = tonumber(redis.call('HGET', KEYS[1], 'active_count')) or 0
local current_load = tonumber(redis.call('HGET', KEYS[1], 'current_load')) or 0
redis.call('HSET', KEYS[1],
    'active_count', math.max(0, active_count - 1),
    'current_load', math.max(0, current_load - weight))
redis.call('HINCRBY', KEYS[1], 'processed_today', 1)
return 1`

const cancelExpiredScript = `
local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, ARGV[2])
local cancelled = 0
for _, id in ipairs(ids) do
    local reservation_key = 'reservation:' .. id
    if redis.call('HGET', reservation_key, 'status') == 'pending' then
        local executor_id = redis.call('HGET', reservation_key, 'executor_id')
        local order_id = redis.call('HGET', reservation_key, 'order_id')
        local weight = tonumber(redis.call('HGET', reservation_key, 'weight'))
        local executor_key = 'executor:' .. executor_id
        local executor_lock = 'executor:reservation:' .. executor_id
        local order_lock = 'order:reservation:' .. order_id
        if redis.call('GET', executor_lock) == id then redis.call('DEL', executor_lock) end
        if redis.call('GET', order_lock) == id then redis.call('DEL', order_lock) end
        if redis.call('EXISTS', executor_key) == 1 then
            redis.call('HINCRBY', executor_key, 'pending_count', -1)
            redis.call('HINCRBYFLOAT', executor_key, 'current_load', -weight)
        end
        redis.call('DEL', reservation_key)
        cancelled = cancelled + 1
    end
    redis.call('ZREM', KEYS[1], id)
end
return cancelled`
