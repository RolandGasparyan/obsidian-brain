-- L99 Governance Migration
-- Backward compatible — bot continues running without GOVERNANCE_ENABLED=true.
-- Safe to run multiple times (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

ALTER TABLE trades
    ADD COLUMN IF NOT EXISTS risk_level        VARCHAR(20) DEFAULT 'LEVEL_NORMAL';

ALTER TABLE trades
    ADD COLUMN IF NOT EXISTS allocation_weight FLOAT       DEFAULT 1.0;

CREATE TABLE IF NOT EXISTS governance_events (
    id               SERIAL PRIMARY KEY,
    timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type       VARCHAR(30),
    old_state        VARCHAR(30),
    new_state        VARCHAR(30),
    reason           TEXT,
    metrics_snapshot JSONB
);

-- Verify:
-- \d trades
-- \d governance_events
