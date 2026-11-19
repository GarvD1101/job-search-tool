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
