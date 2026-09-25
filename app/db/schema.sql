-- AgentRedTeam database schema
-- Run this once to create all tables.
-- Safe to run multiple times: CREATE TABLE IF NOT EXISTS won't overwrite.

-- Stores one row per test run (one execution of the full pipeline)
CREATE TABLE IF NOT EXISTS test_runs (
    id              TEXT PRIMARY KEY,           -- short UUID, e.g. "9a80b095"
    agent_name      TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    trust_score     INTEGER,                    -- 0-100, NULL until scoring done
    total_cases     INTEGER NOT NULL DEFAULT 0,
    total_passed    INTEGER NOT NULL DEFAULT 0,
    total_failed    INTEGER NOT NULL DEFAULT 0,
    total_undecided INTEGER NOT NULL DEFAULT 0,
    summary         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Stores one row per generated attack test case
CREATE TABLE IF NOT EXISTS test_cases (
    id              TEXT PRIMARY KEY,           -- UUID from TestCase.id
    run_id          TEXT NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    template_id     TEXT NOT NULL,
    category        TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    order_id        TEXT,                       -- NULL for cases with no order
    attacker_goal   TEXT NOT NULL,
    filled_slots    JSONB NOT NULL DEFAULT '{}',
    generated_at    TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Stores one row per test result (agent response + scoring)
CREATE TABLE IF NOT EXISTS test_results (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    test_case_id    TEXT NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    run_id          TEXT NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    category        TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    reply           TEXT,                       -- NULL if agent errored
    tool_calls      JSONB NOT NULL DEFAULT '[]',
    refunds         JSONB NOT NULL DEFAULT '[]',
    turns           INTEGER NOT NULL,
    stopped         TEXT NOT NULL,              -- "completed", "max_turns", "error"
    rule_passed     BOOLEAN,                    -- NULL = rules didn't decide
    judge_passed    BOOLEAN,                    -- NULL = judge didn't run
    passed          BOOLEAN,                    -- final verdict
    failure_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for the most common queries
-- "Give me all results for run X"
CREATE INDEX IF NOT EXISTS idx_test_cases_run_id
    ON test_cases(run_id);

CREATE INDEX IF NOT EXISTS idx_test_results_run_id
    ON test_results(run_id);

-- "Give me all failures for run X"
CREATE INDEX IF NOT EXISTS idx_test_results_passed
    ON test_results(run_id, passed);

-- "Give me all results for category X"
CREATE INDEX IF NOT EXISTS idx_test_results_category
    ON test_results(category);
