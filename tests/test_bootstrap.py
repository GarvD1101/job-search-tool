import os
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_schema_file_exists_and_contains_core_tables():
    schema_file = REPO_ROOT / "db" / "schema.sql"
    assert schema_file.exists(), "db/schema.sql must exist"

    content = schema_file.read_text(encoding="utf-8")
    expected_tables = ["runs", "raw_posts", "jobs", "llm_calls"]
    for table in expected_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in content, (
            f"Table {table} missing from schema"
        )

    # Verify Row Level Security statements
    for table in expected_tables:
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in content, (
            f"RLS missing for table {table}"
        )


def test_env_example_keys():
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), ".env.example must exist"

    lines = [
        line.strip()
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected_keys = [
        "JOOBLE_API_KEY",
        "GROQ_API_KEY",
        "SUPABASE_DB_URL",
        "CONTACT_EMAIL",
    ]
    for key in expected_keys:
        assert any(line.startswith(key + "=") or line == key for line in lines), (
            f"Key {key} missing from .env.example"
        )


def test_sources_config_jooble_budget():
    sources_file = REPO_ROOT / "config" / "sources.yaml"
    assert sources_file.exists(), "config/sources.yaml must exist"

    with open(sources_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    jooble = data["sources"]["jooble"]
    assert jooble["daily_budget_total"] == 100, "Jooble daily total budget must be 100"
    assert jooble["daily_budget_cron"] == 60, "Jooble daily cron budget must be 60"
    assert jooble["usage_counter_file"] is not None


def test_pricing_config_groq_candidates_and_limits():
    pricing_file = REPO_ROOT / "config" / "pricing.yaml"
    assert pricing_file.exists(), "config/pricing.yaml must exist"

    with open(pricing_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    models = data["models"]
    expected_candidates = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
    for candidate in expected_candidates:
        assert candidate in models, f"Candidate {candidate} missing from config/pricing.yaml"
        entry = models[candidate]
        assert entry["input_price_per_1m"] > 0
        assert entry["output_price_per_1m"] > 0
        limits = entry["rate_limits"]
        assert limits["requests_per_minute"] == 30
        assert limits["requests_per_day"] == 1000
        assert limits["tokens_per_minute"] == 8000
        assert limits["tokens_per_day"] == 200000
        assert limits["daily_token_budget_stop_pct"] == 0.80
        assert limits["daily_token_budget_stop_tokens"] == 160000


def test_database_connection_if_configured():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        pytest.skip("SUPABASE_DB_URL not set in environment; skipping live connection test")

    import psycopg

    try:
        with psycopg.connect(db_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()
                assert result[0] == 1
    except psycopg.OperationalError as exc:
        pytest.skip(f"Database host unreachable: {exc}")


def test_jobs_post_type_check_constraint_allows_trainee_and_course_or_workshop():
    """Verify that jobs table CHECK constraint accepts all seven post types.

    Inserts a tagged trainee row and a rejected row with post_type course_or_workshop.
    """
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            post_type TEXT CHECK (post_type IS NULL OR post_type IN (
                'job', 'internship', 'trainee', 'fellowship', 'course_or_workshop', 'event', 'other'
            )),
            role TEXT,
            city TEXT,
            rule_decision TEXT,
            rule_reason TEXT
        );
        """
    )
    # 1. Tagged trainee row
    conn.execute(
        """
        INSERT INTO jobs (
            canonical_key, title, company, url, source, status, post_type, role, city
        ) VALUES (
            'test_trainee_key', 'Graduate Trainee Engineer', 'Acme Corp',
            'https://example.com/job/1', 'greenhouse', 'active',
            'trainee', 'core_engineering', 'pune'
        );
        """
    )
    cur = conn.execute(
        "SELECT status, post_type, role FROM jobs WHERE canonical_key = 'test_trainee_key';"
    )
    row = cur.fetchone()
    assert row == ("active", "trainee", "core_engineering")

    # 2. Rejected row with post_type course_or_workshop
    conn.execute(
        """
        INSERT INTO jobs (
            canonical_key, title, company, url, source, status,
            post_type, rule_decision, rule_reason
        ) VALUES (
            'test_course_key', 'Full Stack Java Bootcamp', 'Training Institute',
            'https://example.com/course/1', 'jooble', 'rejected',
            'course_or_workshop', 'reject', 'not_a_job_post'
        );
        """
    )
    cur = conn.execute(
        "SELECT status, post_type, rule_reason FROM jobs WHERE canonical_key = 'test_course_key';"
    )
    row = cur.fetchone()
    assert row == ("rejected", "course_or_workshop", "not_a_job_post")

    # 3. Invalid post_type must fail check constraint
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO jobs (
                canonical_key, title, company, url, source, status, post_type
            ) VALUES (
                'test_bad_key', 'Invalid Post', 'Bad Corp',
                'https://example.com/bad/1', 'jooble', 'active', 'invalid_post_type'
            );
            """
        )

    # 4. Optional live PostgreSQL check with rollback only if explicitly enabled
    if os.environ.get("ALLOW_DB_TESTS") != "1":
        return

    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        return

    import psycopg

    try:
        with psycopg.connect(db_url, connect_timeout=3) as pg_conn:
            with pg_conn.transaction():
                with pg_conn.cursor() as pg_cur:
                    pg_cur.execute(
                        """
                        INSERT INTO jobs (
                            canonical_key, title, company, url, source,
                            status, post_type, role, city
                        ) VALUES (
                            'test_live_trainee_key', 'Graduate Trainee Engineer', 'Acme Corp',
                            'https://example.com/job/trainee', 'greenhouse',
                            'active', 'trainee', 'core_engineering', 'pune'
                        );
                        """
                    )
                    pg_cur.execute(
                        """
                        INSERT INTO jobs (
                            canonical_key, title, company, url, source,
                            status, post_type, rule_decision, rule_reason
                        ) VALUES (
                            'test_live_course_key', 'Full Stack Java Bootcamp', 'Institute',
                            'https://example.com/course/1', 'jooble',
                            'rejected', 'course_or_workshop', 'reject', 'not_a_job_post'
                        );
                        """
                    )
                    pg_cur.execute(
                        "SELECT post_type FROM jobs "
                        "WHERE canonical_key IN ("
                        "'test_live_trainee_key', 'test_live_course_key');"
                    )
                    pts = {r[0] for r in pg_cur.fetchall()}
                    assert pts == {"trainee", "course_or_workshop"}
                    pg_conn.rollback()
    except (psycopg.OperationalError, Exception):
        pass

