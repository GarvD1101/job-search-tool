-- Database schema for fresher job search pipeline
-- Supabase free tier Postgres

-- Pipeline execution runs
CREATE TABLE IF NOT EXISTS runs (
    id BIGSERIAL PRIMARY KEY,
    trigger TEXT NOT NULL DEFAULT 'manual',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'partial', 'failed')),
    stats JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Raw posts storage (pruned after 7 days)
CREATE TABLE IF NOT EXISTS raw_posts (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_posts_fetched_at ON raw_posts (fetched_at);
CREATE INDEX IF NOT EXISTS idx_raw_posts_source_id ON raw_posts (source, source_id);

-- Canonical jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    canonical_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location_text TEXT NOT NULL DEFAULT '',
    description TEXT,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    sources TEXT[] NOT NULL DEFAULT '{}',
    posted_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'needs_review', 'pending_tag')),
    post_type TEXT CHECK (post_type IS NULL OR post_type IN ('job', 'internship', 'trainee', 'fellowship', 'course_or_workshop', 'event', 'other')),
    is_fresher BOOLEAN,
    role TEXT CHECK (role IS NULL OR role IN (
        'backend', 'frontend', 'fullstack', 'mobile', 'data_analyst', 'ml_ai',
        'devops_cloud', 'qa', 'security', 'product', 'design', 'marketing',
        'sales_bd', 'ops_support', 'finance', 'hr', 'content', 'other'
    )),
    city TEXT CHECK (city IS NULL OR city IN (
        'bengaluru', 'hyderabad', 'pune', 'mumbai', 'delhi_ncr',
        'chennai', 'kolkata', 'ahmedabad', 'other_india', 'unknown'
    )),
    is_remote BOOLEAN NOT NULL DEFAULT FALSE,
    multi_city BOOLEAN NOT NULL DEFAULT FALSE,
    rule_decision TEXT,
    rule_reason TEXT,
    tag_source TEXT CHECK (tag_source IS NULL OR tag_source IN ('rule', 'llm')),
    tagger_model TEXT,
    prompt_version TEXT,
    fts TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'C')
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_jobs_canonical_key ON jobs (canonical_key);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_role ON jobs (role);
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs (city);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs (posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen_at ON jobs (first_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_fts ON jobs USING GIN (fts);

-- LLM call log for auditing and cost tracking
CREATE TABLE IF NOT EXISTS llm_calls (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES runs(id) ON DELETE SET NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    batch_size INTEGER NOT NULL DEFAULT 1,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_run_id ON llm_calls (run_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created_at ON llm_calls (created_at DESC);

-- Enable Row Level Security on every table with no policies
-- This prevents the public Data API from accessing the data.
-- Direct connections using the database owner role bypass RLS.
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;

