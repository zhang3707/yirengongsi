-- AI Company MVP v1.0 — reference schema (Alembic is the source of truth).
-- Kept in sync with shared/models.py for runbook Step 5 verification.

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(40) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    role VARCHAR(40) NOT NULL DEFAULT 'member',
    workspace VARCHAR(80) NOT NULL DEFAULT 'default',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(40) PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    role VARCHAR(200) NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    domain VARCHAR(60) NOT NULL DEFAULT 'general',
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    model VARCHAR(80) NOT NULL DEFAULT 'mock-reasoner',
    memory_enabled BOOLEAN NOT NULL DEFAULT true,
    workflow VARCHAR(80) NOT NULL DEFAULT 'default',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    system_prompt TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS skills (
    id VARCHAR(40) PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    category VARCHAR(60) NOT NULL DEFAULT 'general',
    description TEXT NOT NULL DEFAULT '',
    input_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    handler VARCHAR(120) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(40) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    goal TEXT NOT NULL DEFAULT '',
    task_type VARCHAR(40) NOT NULL DEFAULT 'general',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_output TEXT NOT NULL DEFAULT '',
    acceptance_criteria TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority VARCHAR(10) NOT NULL DEFAULT 'P2',
    assigned_agent_id VARCHAR(40) REFERENCES agents(id),
    user_id VARCHAR(40) REFERENCES users(id),
    workspace VARCHAR(80) NOT NULL DEFAULT 'default',
    result TEXT,
    error TEXT,
    duration_ms INTEGER,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id VARCHAR(40) PRIMARY KEY,
    task_id VARCHAR(40) NOT NULL REFERENCES tasks(id),
    workflow VARCHAR(80) NOT NULL DEFAULT 'default',
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    current_step VARCHAR(60) NOT NULL DEFAULT '',
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    retries INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge (
    id VARCHAR(40) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    source VARCHAR(200) NOT NULL DEFAULT 'manual',
    workspace VARCHAR(80) NOT NULL DEFAULT 'default',
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logs (
    id VARCHAR(40) PRIMARY KEY,
    level VARCHAR(10) NOT NULL DEFAULT 'INFO',
    service VARCHAR(40) NOT NULL DEFAULT 'system',
    event VARCHAR(120) NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task_evaluations (
    id VARCHAR(40) PRIMARY KEY,
    task_id VARCHAR(40) NOT NULL REFERENCES tasks(id),
    quality INTEGER NOT NULL DEFAULT 3,
    minutes_before INTEGER NOT NULL DEFAULT 0,
    minutes_after INTEGER NOT NULL DEFAULT 0,
    time_saved_ratio DOUBLE PRECISION NOT NULL DEFAULT 0,
    experience INTEGER NOT NULL DEFAULT 3,
    trust INTEGER NOT NULL DEFAULT 3,
    reusable BOOLEAN NOT NULL DEFAULT false,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
    id VARCHAR(40) PRIMARY KEY,
    category VARCHAR(40) NOT NULL,
    summary VARCHAR(200) NOT NULL,
    scenario TEXT NOT NULL DEFAULT '',
    impact VARCHAR(20) NOT NULL DEFAULT 'medium',
    frequency VARCHAR(20) NOT NULL DEFAULT 'medium',
    suggestion TEXT NOT NULL DEFAULT '',
    task_id VARCHAR(40) REFERENCES tasks(id),
    reporter VARCHAR(120) NOT NULL DEFAULT '',
    priority VARCHAR(10) NOT NULL DEFAULT 'P2',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS ix_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS ix_logs_created_at ON logs(created_at);
CREATE INDEX IF NOT EXISTS ix_feedback_category ON feedback(category);
