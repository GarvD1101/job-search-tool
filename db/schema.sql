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
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_posts_source_unique ON raw_posts (source, source_id);

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
    origin_site TEXT NOT NULL DEFAULT 'unknown',
    sources TEXT[] NOT NULL DEFAULT '{}',
    posted_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'needs_review', 'pending_tag', 'rejected', 'duplicate')),
    duplicate_of TEXT,
    post_type TEXT CHECK (post_type IS NULL OR post_type IN ('job', 'internship', 'trainee', 'fellowship', 'course_or_workshop', 'event', 'other')),
    is_fresher BOOLEAN,
    role TEXT CHECK (role IS NULL OR role IN (
        'software_dev', 'data_analytics', 'ml_ai', 'it_devops_security', 'qa_testing',
        'product_management', 'design', 'marketing', 'sales_bd', 'customer_support',
        'admin_back_office', 'hr_recruitment', 'finance_banking', 'operations_logistics',
        'content_writing', 'research', 'teaching_education', 'core_engineering',
        'healthcare', 'legal_compliance', 'hospitality_retail', 'other'
    )),
    city TEXT CHECK (city IS NULL OR city IN (
        'bengaluru', 'hyderabad', 'pune', 'mumbai', 'delhi_ncr',
        'chennai', 'kolkata', 'ahmedabad', 'other_india', 'remote', 'unknown'
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

-- Idempotent schema migrations for existing jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS origin_site TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS duplicate_of TEXT;
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_status_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_status_check CHECK (status IN ('active', 'expired', 'needs_review', 'pending_tag', 'rejected', 'duplicate'));
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_role_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_role_check CHECK (role IS NULL OR role IN (
    'software_dev', 'data_analytics', 'ml_ai', 'it_devops_security', 'qa_testing',
    'product_management', 'design', 'marketing', 'sales_bd', 'customer_support',
    'admin_back_office', 'hr_recruitment', 'finance_banking', 'operations_logistics',
    'content_writing', 'research', 'teaching_education', 'core_engineering',
    'healthcare', 'legal_compliance', 'hospitality_retail', 'other'
));
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_city_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_city_check CHECK (city IS NULL OR city IN (
    'bengaluru', 'hyderabad', 'pune', 'mumbai', 'delhi_ncr',
    'chennai', 'kolkata', 'ahmedabad', 'other_india', 'remote', 'unknown'
));
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_post_type_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_post_type_check CHECK (post_type IS NULL OR post_type IN (
    'job', 'internship', 'trainee', 'fellowship', 'course_or_workshop', 'event', 'other'
));

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

-- Source API usage counter shared across local dev and GitHub Actions cron
CREATE TABLE IF NOT EXISTS source_usage (
    day DATE NOT NULL,
    source TEXT NOT NULL,
    mode TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, source, mode)
);

-- Enable Row Level Security on every table with no policies
-- This prevents the public Data API from accessing the data.
-- Direct connections using the database owner role bypass RLS.
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_usage ENABLE ROW LEVEL SECURITY;

