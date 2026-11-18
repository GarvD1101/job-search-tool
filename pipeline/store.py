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
        status = EXCLUDED.status,
        duplicate_of = EXCLUDED.duplicate_of,
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
