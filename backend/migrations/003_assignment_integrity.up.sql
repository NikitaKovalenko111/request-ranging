BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS assignments_one_active_per_order_idx
    ON assignments (order_id)
    WHERE status IN ('pending', 'confirmed');

COMMIT;
