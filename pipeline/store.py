import logging
import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from pipeline.sources.base import RawPost

logger = logging.getLogger(__name__)


def get_db_url() -> str | None:
    return os.environ.get("SUPABASE_DB_URL")


def save_raw_posts(posts: list[RawPost], db_url: str | None = None) -> int:
    """Save raw posts to PostgreSQL database with idempotent upsert.

    Returns:
        Number of raw posts inserted or updated.
    """
    target_url = db_url or get_db_url()
    if not target_url:
        logger.info("SUPABASE_DB_URL not set. Skipping database insertion.")
        return 0

    if not posts:
        return 0

    insert_sql = """
    INSERT INTO raw_posts (source, source_id, fetched_at, payload)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (source, source_id)
    DO UPDATE SET
        fetched_at = EXCLUDED.fetched_at,
        payload = EXCLUDED.payload;
    """

    records = [
        (
            post.source,
            post.source_id,
            post.fetched_at,
            Jsonb(post.payload),
        )
        for post in posts
    ]

    try:
        with psycopg.connect(target_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.executemany(insert_sql, records)
                return len(records)
    except Exception as exc:
        safe_msg = str(exc)
        if "@" in safe_msg:
            safe_msg = "Database connection error (credentials masked)"
        logger.error("Failed saving raw posts to database: %s", safe_msg)
        raise RuntimeError(f"Database raw_posts insertion failed: {safe_msg}") from None


def start_pipeline_run(trigger: str = "manual", db_url: str | None = None) -> int | None:
    target_url = db_url or get_db_url()
    if not target_url:
        return None

    insert_sql = """
    INSERT INTO runs (trigger, started_at, status, stats)
    VALUES (%s, %s, 'running', '{}'::jsonb)
    RETURNING id;
    """
    try:
        with psycopg.connect(target_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(insert_sql, (trigger, datetime.now(timezone.utc)))
                row = cur.fetchone()
                return int(row[0]) if row else None
    except Exception as exc:
        logger.warning("Could not record start of run in database: %s", exc)
        return None


def finish_pipeline_run(
    run_id: int | None,
    status: str,
    stats: dict[str, Any],
    db_url: str | None = None,
) -> None:
    if run_id is None:
        return

    target_url = db_url or get_db_url()
    if not target_url:
        return

    update_sql = """
    UPDATE runs
    SET finished_at = %s,
        status = %s,
        stats = %s
    WHERE id = %s;
    """
    try:
        with psycopg.connect(target_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    update_sql,
                    (datetime.now(timezone.utc), status, Jsonb(stats), run_id),
                )
    except Exception as exc:
        logger.warning("Could not record completion of run in database: %s", exc)


def load_raw_posts(db_url: str | None = None) -> list[RawPost]:
    target_url = db_url or get_db_url()
    if not target_url:
        logger.warning("SUPABASE_DB_URL not set. Cannot load raw_posts from DB.")
        return []

    query = """
    SELECT source, source_id, fetched_at, payload
    FROM raw_posts
    ORDER BY fetched_at ASC;
    """
    try:
        with psycopg.connect(target_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [
                    RawPost(
                        source=row[0],
                        source_id=row[1],
                        fetched_at=row[2],
                        payload=row[3],
                    )
                    for row in rows
                ]
    except Exception as exc:
        safe_msg = str(exc)
        if "@" in safe_msg:
            safe_msg = "Database connection error (credentials masked)"
        logger.error("Failed loading raw_posts: %s", safe_msg)
        raise RuntimeError(f"Database raw_posts load failed: {safe_msg}") from None


def save_jobs(jobs_to_save: list[Any], db_url: str | None = None) -> int:
    target_url = db_url or get_db_url()
    if not target_url or not jobs_to_save:
        return 0

    upsert_sql = """
    INSERT INTO jobs (
        canonical_key, title, company, location_text, description, url,
        source, origin_site, sources, posted_at, status, duplicate_of,
        rule_decision, rule_reason, tag_source, first_seen_at, last_seen_at
    )
    VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, 'rule', NOW(), NOW()
    )
    ON CONFLICT (canonical_key)
    DO UPDATE SET
        title = EXCLUDED.title,
        company = EXCLUDED.company,
        location_text = EXCLUDED.location_text,
        description = EXCLUDED.description,
        url = EXCLUDED.url,
        origin_site = EXCLUDED.origin_site,
        sources = EXCLUDED.sources,
        posted_at = EXCLUDED.posted_at,
        status = CASE
            WHEN jobs.tag_source = 'llm' THEN jobs.status
            WHEN jobs.status IN ('active', 'expired', 'needs_review') THEN jobs.status
            ELSE EXCLUDED.status
        END,
        duplicate_of = CASE
            WHEN jobs.status IN ('active', 'expired', 'needs_review') THEN jobs.duplicate_of
            ELSE EXCLUDED.duplicate_of
        END,
        rule_decision = EXCLUDED.rule_decision,
        rule_reason = EXCLUDED.rule_reason,
        last_seen_at = NOW();
    """
    records = [
        (
            pj.canonical_key,
            pj.job.title,
            pj.job.company,
            pj.job.location_text,
            pj.job.description,
            pj.job.url,
            pj.job.source,
            pj.job.origin_site,
            pj.sources or [pj.job.source],
            pj.job.posted_at,
            pj.status,
            pj.duplicate_of,
            pj.rule_decision,
            pj.rule_reason,
        )
        for pj in jobs_to_save
    ]
    try:
        with psycopg.connect(target_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.executemany(upsert_sql, records)
                return len(records)
    except Exception as exc:
        safe_msg = str(exc)
        if "@" in safe_msg:
            safe_msg = "Database connection error (credentials masked)"
        logger.error("Failed saving jobs to database: %s", safe_msg)
        raise RuntimeError(f"Database jobs insertion failed: {safe_msg}") from None


def record_llm_call(
    model: str,
    prompt_version: str,
    batch_size: int,
    input_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    latency_ms: int,
    status: str = "success",
    run_id: int | None = None,
    db_url: str | None = None,
) -> int | None:
    target_url = db_url or get_db_url()
    if not target_url:
        return None

    insert_sql = """
    INSERT INTO llm_calls (
        run_id, model, prompt_version, batch_size, input_tokens,
        output_tokens, reasoning_tokens, latency_ms, status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id;
    """
    try:
        with psycopg.connect(target_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    (
                        run_id,
                        model,
                        prompt_version,
                        batch_size,
                        input_tokens,
                        output_tokens,
                        reasoning_tokens,
                        latency_ms,
                        status,
                    ),
                )
                row = cur.fetchone()
                return int(row[0]) if row else None
    except Exception as exc:
        logger.warning("Could not record llm_call in database: %s", exc)
        return None


def get_today_token_usage(model: str, db_url: str | None = None) -> int:
    target_url = db_url or get_db_url()
    if not target_url:
        return 0

    query = """
    SELECT COALESCE(SUM(input_tokens + output_tokens), 0)
    FROM llm_calls
    WHERE model = %s
      AND created_at >= CURRENT_DATE AT TIME ZONE 'UTC';
    """
    try:
        with psycopg.connect(target_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (model,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception as exc:
        logger.warning("Could not query today's token usage from database: %s", exc)
        return 0


def load_pending_jobs(limit: int | None = None, db_url: str | None = None) -> list[dict[str, Any]]:
    target_url = db_url or get_db_url()
    if not target_url:
        return []

    query = """
    SELECT id, canonical_key, title, company, location_text, description, url, source, posted_at
    FROM jobs
    WHERE status = 'pending_tag'
    ORDER BY posted_at DESC NULLS LAST
    """
    if limit is not None and limit > 0:
        query += f" LIMIT {int(limit)}"

    try:
        with psycopg.connect(target_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "canonical_key": row[1],
                        "title": row[2],
                        "company": row[3],
                        "location_text": row[4],
                        "description": row[5],
                        "url": row[6],
                        "source": row[7],
                        "posted_at": row[8],
                    }
                    for row in rows
                ]
    except Exception as exc:
        logger.error("Failed loading pending jobs: %s", exc)
        return []


def update_tagged_jobs(tagged_records: list[dict[str, Any]], db_url: str | None = None) -> int:
    target_url = db_url or get_db_url()
    if not target_url or not tagged_records:
        return 0

    update_sql = """
    UPDATE jobs
    SET status = %s,
        role = %s,
        city = %s,
        post_type = %s,
        is_fresher = %s,
        is_remote = %s,
        rule_reason = COALESCE(%s, rule_reason),
        tag_source = %s,
        tagger_model = %s,
        prompt_version = %s
    WHERE canonical_key = %s;
    """
    records = [
        (
            rec["status"],
            rec.get("role"),
            rec.get("city"),
            rec.get("post_type"),
            rec.get("is_fresher"),
            rec.get("is_remote", False),
            rec.get("rule_reason"),
            rec.get("tag_source", "llm"),
            rec.get("tagger_model"),
            rec.get("prompt_version"),
            rec["canonical_key"],
        )
        for rec in tagged_records
    ]
    try:
        with psycopg.connect(target_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.executemany(update_sql, records)
                return len(records)
    except Exception as exc:
        logger.error("Failed updating tagged jobs: %s", exc)
        raise


def get_job_stats(db_url: str | None = None) -> dict[str, Any]:
    """Query current jobs status, reject reasons, and tagged role/city distributions."""
    target_url = db_url or get_db_url()
    if not target_url:
        return {}

    stats: dict[str, Any] = {
        "status_counts": {},
        "rejected_reasons": {},
        "role_distribution": {},
        "city_distribution": {},
        "total_jobs": 0,
    }
    try:
        with psycopg.connect(target_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT status, count(*) FROM jobs GROUP BY status;")
                for s, c in cur.fetchall():
                    stats["status_counts"][s] = c
                    stats["total_jobs"] += c

                cur.execute(
                    "SELECT COALESCE(rule_reason, 'unknown'), count(*) "
                    "FROM jobs WHERE status = 'rejected' "
                    "GROUP BY rule_reason ORDER BY count(*) DESC;"
                )
                for r, c in cur.fetchall():
                    stats["rejected_reasons"][r] = c

                cur.execute(
                    "SELECT role, count(*) FROM jobs "
                    "WHERE role IS NOT NULL GROUP BY role ORDER BY count(*) DESC;"
                )
                for r, c in cur.fetchall():
                    stats["role_distribution"][r] = c

                cur.execute(
                    "SELECT city, count(*) FROM jobs "
                    "WHERE city IS NOT NULL GROUP BY city ORDER BY count(*) DESC;"
                )
                for city, c in cur.fetchall():
                    stats["city_distribution"][city] = c
    except Exception as exc:
        logger.warning("Could not fetch job stats from database: %s", exc)

    return stats

