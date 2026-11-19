"""Tests for database invariants and job lifecycle transitions.

Requirement A.6:
- A survivor that becomes stale on a later run leaves exactly one row:
  - rejected if untagged
  - expired if tagged
- No orphan rows (every raw post has exactly one job row)
- Tagged fields intact when transitioned to expired
"""

import sqlite3
from datetime import datetime, timedelta, timezone

from pipeline.dedup import ProcessedJob
from pipeline.normalize import NormalizedJob


class FakeJobsDB:
    """In-memory SQLite database simulating schema.sql upsert and expire logic."""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE raw_posts (
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (source, source_id)
            );

            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                dedup_key TEXT,
                canonical_key TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location_text TEXT NOT NULL DEFAULT '',
                description TEXT,
                url TEXT NOT NULL,
                origin_site TEXT NOT NULL DEFAULT 'unknown',
                sources TEXT NOT NULL DEFAULT '[]',
                posted_at TIMESTAMP,
                first_seen_at TIMESTAMP NOT NULL,
                last_seen_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_tag',
                duplicate_of TEXT,
                post_type TEXT,
                is_fresher INTEGER,
                role TEXT,
                city TEXT,
                is_remote INTEGER NOT NULL DEFAULT 0,
                rule_decision TEXT,
                rule_reason TEXT,
                tag_source TEXT,
                tagger_model TEXT,
                prompt_version TEXT,
                UNIQUE (source, source_id)
            );
        """)

    def insert_raw_post(self, source: str, source_id: str, fetched_at: datetime) -> None:
        self.conn.execute(
            "INSERT INTO raw_posts (source, source_id, fetched_at, payload) VALUES (?, ?, ?, ?)",
            (source, source_id, fetched_at, "{}"),
        )
        self.conn.commit()

    def upsert_job(self, pj: ProcessedJob, seen_at: datetime) -> None:
        sql = """
        INSERT INTO jobs (
            source, source_id, dedup_key, canonical_key, title, company,
            location_text, description, url, origin_site, sources, posted_at,
            first_seen_at, last_seen_at, status, duplicate_of,
            rule_decision, rule_reason, tag_source
        )
        VALUES (
            :source, :source_id, :dedup_key, :canonical_key, :title, :company,
            :location_text, :description, :url, :origin_site, :sources, :posted_at,
            :seen_at, :seen_at, :status, :duplicate_of,
            :rule_decision, :rule_reason, 'rule'
        )
        ON CONFLICT (source, source_id)
        DO UPDATE SET
            dedup_key = EXCLUDED.dedup_key,
            canonical_key = EXCLUDED.canonical_key,
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
            last_seen_at = EXCLUDED.last_seen_at;
        """
        params = {
            "source": pj.job.source,
            "source_id": str(pj.job.source_id),
            "dedup_key": pj.dedup_key or pj.canonical_key,
            "canonical_key": pj.canonical_key,
            "title": pj.job.title,
            "company": pj.job.company,
            "location_text": pj.job.location_text,
            "description": pj.job.description,
            "url": pj.job.url,
            "origin_site": pj.job.origin_site,
            "sources": str(pj.sources or [pj.job.source]),
            "posted_at": pj.job.posted_at,
            "seen_at": seen_at,
            "status": pj.status,
            "duplicate_of": pj.duplicate_of,
            "rule_decision": pj.rule_decision,
            "rule_reason": pj.rule_reason,
        }
        self.conn.execute(sql, params)
        self.conn.commit()

    def tag_job(self, source: str, source_id: str, role: str, city: str, post_type: str) -> None:
        self.conn.execute(
            """
            UPDATE jobs SET
                status = 'active',
                tag_source = 'llm',
                tagger_model = 'openai/gpt-oss-20b',
                role = ?,
                city = ?,
                post_type = ?,
                is_fresher = 1
            WHERE source = ? AND source_id = ?
            """,
            (role, city, post_type, source, source_id),
        )
        self.conn.commit()

    def expire_and_prune(self, now: datetime) -> dict[str, int]:
        counts = {"expired": 0, "untagged_rejected": 0, "pruned_raw": 0}
        cutoff_seen = now - timedelta(days=14)
        cutoff_posted = now - timedelta(days=45)
        cutoff_raw = now - timedelta(days=7)

        # 1. Expire active or pending_tag jobs older than 14d unseen or posted > 45d
        cur = self.conn.execute(
            """
            UPDATE jobs
            SET status = 'expired'
            WHERE status IN ('active', 'pending_tag')
              AND (last_seen_at < ? OR posted_at < ?)
            """,
            (cutoff_seen, cutoff_posted),
        )
        counts["expired"] = cur.rowcount

        # 2. Untagged rows that fail rules become rejected
        cur2 = self.conn.execute(
            """
            UPDATE jobs
            SET status = 'rejected'
            WHERE (tag_source IS NULL OR tag_source = 'rule')
              AND rule_decision = 'reject'
              AND status = 'pending_tag'
            """
        )
        counts["untagged_rejected"] = cur2.rowcount

        # 3. Prune raw_posts older than 7 days
        cur3 = self.conn.execute(
            "DELETE FROM raw_posts WHERE fetched_at < ?",
            (cutoff_raw,),
        )
        counts["pruned_raw"] = cur3.rowcount
        self.conn.commit()
        return counts

    def get_job(self, source: str, source_id: str) -> sqlite3.Row | None:
        cur = self.conn.execute(
            "SELECT * FROM jobs WHERE source = ? AND source_id = ?",
            (source, source_id),
        )
        return cur.fetchone()


def test_survivor_becoming_stale_when_untagged_becomes_rejected():
    """An untagged survivor evaluated as stale on later run leaves exactly 1 rejected row."""
    db = FakeJobsDB()
    t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc)

    # 1. First run: Fresh job (posted 5 days ago)
    posted_fresh = t0 - timedelta(days=5)
    norm = NormalizedJob(
        source="jooble",
        source_id="job_untagged_1",
        origin_site="jooble",
        title="Junior Software Engineer",
        company="Acme Corp",
        location_text="Bengaluru",
        description="Fresh graduate role 0-1 years.",
        url="https://in.jooble.org/desc/job_untagged_1",
        posted_at=posted_fresh,
    )
    db.insert_raw_post(norm.source, norm.source_id, t0)

    # Survivor initially
    pj1 = ProcessedJob(
        job=norm,
        rule_decision="accept",
        rule_reason="fresher_signal_matched",
        canonical_key="key_1",
        status="pending_tag",
        sources=["jooble"],
        dedup_key="key_1",
    )
    db.upsert_job(pj1, seen_at=t0)

    row1 = db.get_job(norm.source, norm.source_id)
    assert row1 is not None
    assert row1["status"] == "pending_tag"
    assert row1["rule_decision"] == "accept"

    # 2. Second run: Time passes, job date is now 50 days old (>45 days)
    # Filter engine evaluates it as stale -> rule_decision = 'reject', status = 'rejected'
    norm_stale = NormalizedJob(
        source="jooble",
        source_id="job_untagged_1",
        origin_site="jooble",
        title="Junior Software Engineer",
        company="Acme Corp",
        location_text="Bengaluru",
        description="Fresh graduate role 0-1 years.",
        url="https://in.jooble.org/desc/job_untagged_1",
        posted_at=t1 - timedelta(days=50),
    )
    pj2 = ProcessedJob(
        job=norm_stale,
        rule_decision="reject",
        rule_reason="stale",
        canonical_key="rej_key_1",
        status="rejected",
        sources=["jooble"],
        dedup_key="rej_key_1",
    )
    db.upsert_job(pj2, seen_at=t1)

    # Assert: Exactly 1 row in jobs, status is rejected, no duplicate row
    cur = db.conn.execute(
        "SELECT count(*) FROM jobs WHERE source = 'jooble' AND source_id = 'job_untagged_1';"
    )
    assert cur.fetchone()[0] == 1

    row2 = db.get_job(norm.source, norm.source_id)
    assert row2["status"] == "rejected"
    assert row2["rule_decision"] == "reject"
    assert row2["rule_reason"] == "stale"
    assert row2["tag_source"] == "rule"


def test_survivor_becoming_stale_when_tagged_becomes_expired_with_fields_intact():
    """A tagged survivor evaluated as stale on later run leaves exactly 1 expired row."""
    db = FakeJobsDB()
    t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 11, 19, 10, 0, tzinfo=timezone.utc)

    # 1. First run: Fresh job, accepted and tagged
    posted_fresh = t0 - timedelta(days=5)
    norm = NormalizedJob(
        source="greenhouse",
        source_id="stripe_101",
        origin_site="greenhouse",
        title="Software Engineer, Intern",
        company="Stripe",
        location_text="Bengaluru",
        description="Software development internship.",
        url="https://boards.greenhouse.io/stripe/jobs/101",
        posted_at=posted_fresh,
    )
    db.insert_raw_post(norm.source, norm.source_id, t0)

    pj = ProcessedJob(
        job=norm,
        rule_decision="accept",
        rule_reason="fresher_signal_matched",
        canonical_key="key_stripe_101",
        status="pending_tag",
        sources=["greenhouse"],
        dedup_key="key_stripe_101",
    )
    db.upsert_job(pj, seen_at=t0)

    # Job is tagged by LLM
    db.tag_job(
        "greenhouse", "stripe_101", role="software_dev", city="bengaluru", post_type="internship"
    )

    tagged_row = db.get_job("greenhouse", "stripe_101")
    assert tagged_row["status"] == "active"
    assert tagged_row["tag_source"] == "llm"
    assert tagged_row["role"] == "software_dev"
    assert tagged_row["city"] == "bengaluru"

    # 2. Later run: Posting date becomes 50 days old (>45 days)
    # The filter stage evaluates it as stale, but save_jobs preserves status for tagged rows
    norm_stale = NormalizedJob(
        source="greenhouse",
        source_id="stripe_101",
        origin_site="greenhouse",
        title="Software Engineer, Intern",
        company="Stripe",
        location_text="Bengaluru",
        description="Software development internship.",
        url="https://boards.greenhouse.io/stripe/jobs/101",
        posted_at=t1 - timedelta(days=50),
    )
    pj_stale = ProcessedJob(
        job=norm_stale,
        rule_decision="reject",
        rule_reason="stale",
        canonical_key="rej_stripe_101",
        status="rejected",
        sources=["greenhouse"],
        dedup_key="rej_stripe_101",
    )
    db.upsert_job(pj_stale, seen_at=t1)

    # Save_jobs preserves active status because tag_source == 'llm'
    mid_row = db.get_job("greenhouse", "stripe_101")
    assert mid_row["status"] == "active"
    assert mid_row["role"] == "software_dev"

    # 3. Expire step runs: because posted_at > 45 days, it transitions to expired
    exp_counts = db.expire_and_prune(now=t1)
    assert exp_counts["expired"] == 1

    # Assert: Exactly one row, status is expired, tagged fields completely intact
    cur = db.conn.execute(
        "SELECT count(*) FROM jobs WHERE source = 'greenhouse' AND source_id = 'stripe_101';"
    )
    assert cur.fetchone()[0] == 1

    final_row = db.get_job("greenhouse", "stripe_101")
    assert final_row["status"] == "expired"
    assert final_row["tag_source"] == "llm"
    assert final_row["tagger_model"] == "openai/gpt-oss-20b"
    assert final_row["role"] == "software_dev"
    assert final_row["city"] == "bengaluru"
    assert final_row["post_type"] == "internship"
    assert final_row["is_fresher"] == 1
