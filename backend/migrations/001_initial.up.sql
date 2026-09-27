BEGIN;

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('processed', 'await', 'accept', 'reject')),
    weight DOUBLE PRECISION NOT NULL CHECK (weight > 0),
    version BIGINT NOT NULL CHECK (version > 0),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    assigned_executor_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE executors (
    id TEXT PRIMARY KEY,
    version BIGINT NOT NULL CHECK (version > 0),
    active BOOLEAN NOT NULL,
    capacity DOUBLE PRECISION NOT NULL CHECK (capacity > 0),
    current_load DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (current_load >= 0),
    active_count INTEGER NOT NULL DEFAULT 0 CHECK (active_count >= 0),
    pending_count INTEGER NOT NULL DEFAULT 0 CHECK (pending_count >= 0),
    processed_today INTEGER NOT NULL DEFAULT 0 CHECK (processed_today >= 0),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_assignment_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE orders
    ADD CONSTRAINT orders_assigned_executor_fk
    FOREIGN KEY (assigned_executor_id) REFERENCES executors(id) ON DELETE SET NULL;

CREATE TABLE rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 0,
    left_operand JSONB NOT NULL,
    operator TEXT NOT NULL CHECK (operator IN ('=', '!=', '>', '>=', '<', '<=', 'IN', 'NOT IN', 'BETWEEN', 'CONTAINS')),
    right_operand JSONB NOT NULL,
    failure_reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE assignments (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    executor_id TEXT NOT NULL REFERENCES executors(id),
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'cancelled', 'failed')),
    order_weight DOUBLE PRECISION NOT NULL CHECK (order_weight > 0),
    reservation_id TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE decision_traces (
    id BIGSERIAL PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    assignment_id TEXT REFERENCES assignments(id),
    trace JSONB NOT NULL,
    processing_time_ms BIGINT NOT NULL CHECK (processing_time_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE processed_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX orders_parent_id_idx ON orders(parent_id);
CREATE INDEX orders_status_idx ON orders(status);
CREATE INDEX executors_active_idx ON executors(active);
CREATE INDEX rules_active_priority_idx ON rules(active, priority, id);
CREATE INDEX assignments_order_id_idx ON assignments(order_id);
CREATE INDEX assignments_executor_id_idx ON assignments(executor_id);
CREATE INDEX assignments_status_idx ON assignments(status);
CREATE INDEX decision_traces_order_id_idx ON decision_traces(order_id);
CREATE INDEX processed_events_processed_at_idx ON processed_events(processed_at);

COMMIT;
