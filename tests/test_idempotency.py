"""End-to-end idempotency test against an in-memory fake database.

Flow: raw posts -> filter -> tag -> filter again -> tag again.
Asserts:
- Row counts unchanged after the second filter.
- Tagged rows keep role, city, status, and tag fields.
- Duplicates keep duplicate_of.
- Second tag run makes zero provider calls.
"""

import hashlib
import sqlite3
from typing import Any

from pipeline.dedup import Deduplicator
from pipeline.filters import FilterRuleEngine
from pipeline.llm.base import TagResult, Usage
from pipeline.llm.mock import MockProvider
from pipeline.normalize import NormalizedJob
from pipeline.tagger import get_cache_key, get_content_hash


class InMemoryDB:
    """In-memory SQLite database simulating schema.sql and store.py upsert logic."""

    def __init__(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE raw_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                payload TEXT NOT NULL
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
            """
        )

    def upsert_filtered_jobs(self, processed_jobs: list[Any]) -> None:
        """Upsert jobs using the exact logic from pipeline/store.py save_jobs."""
        sql = """
        INSERT INTO jobs (
            source, source_id, dedup_key, canonical_key, title, company,
            location_text, description, url, origin_site, sources, status,
            duplicate_of, rule_decision, rule_reason, tag_source
        )
        VALUES (
            :source, :source_id, :dedup_key, :canonical_key, :title, :company,
            :location_text, :description, :url, :origin_site, :sources, :status,
            :duplicate_of, :rule_decision, :rule_reason, 'rule'
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
            rule_reason = EXCLUDED.rule_reason;
        """
        for pj in processed_jobs:
            params = {
                "source": pj.job.source,
                "source_id": str(pj.job.source_id),
                "dedup_key": getattr(pj, "dedup_key", None) or pj.canonical_key,
                "canonical_key": pj.canonical_key,
                "title": pj.job.title,
                "company": pj.job.company,
                "location_text": pj.job.location_text,
                "description": pj.job.description,
                "url": pj.job.url,
                "origin_site": pj.job.origin_site,
                "sources": str(pj.sources or [pj.job.source]),
                "status": pj.status,
                "duplicate_of": pj.duplicate_of,
                "rule_decision": pj.rule_decision,
                "rule_reason": pj.rule_reason,
            }
            self.conn.execute(sql, params)
        self.conn.commit()

    def get_pending_jobs(self) -> list[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'pending_tag' ORDER BY id ASC;"
        )
        return cur.fetchall()

    def update_tagged_jobs(self, tagged_records: list[dict[str, Any]]) -> None:
        sql = """
        UPDATE jobs SET
            status = :status,
            role = :role,
            city = :city,
            post_type = :post_type,
            is_fresher = :is_fresher,
            is_remote = :is_remote,
            tag_source = 'llm',
            tagger_model = :tagger_model,
            prompt_version = :prompt_version
        WHERE canonical_key = :canonical_key;
        """
        for r in tagged_records:
            self.conn.execute(sql, r)
        self.conn.commit()

    def get_all_jobs(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM jobs ORDER BY id ASC;").fetchall()


class CountingMockProvider(MockProvider):
    """Mock provider tracking the number of calls made."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    def tag_batch(
        self, posts: list[dict[str, Any]], prompt_version: str = "tag_v1"
    ) -> tuple[list[TagResult], Usage]:
        self.call_count += 1
        results, usage = super().tag_batch(posts, prompt_version)
        return results, usage


def test_end_to_end_pipeline_idempotency():
    db = InMemoryDB()
    filter_engine = FilterRuleEngine()
    deduplicator = Deduplicator()
    mock_provider = CountingMockProvider()
    tag_cache: dict[str, TagResult] = {}

    # 1. Five Synthetic Raw Posts
    raw_posts = [
        # Post 1: Valid fresher internship
        NormalizedJob(
            source="jooble",
            source_id="j_101",
            title="Python Developer Intern",
            company="Alpha Tech",
            location_text="Bengaluru, Karnataka",
            description="Looking for interns with 0-1 years experience in Python.",
            salary=None,
            posted_at=None,
            url="https://example.com/j101",
            origin_site="jooble",
        ),
        # Post 2: Exact duplicate of Post 1 from Greenhouse
        NormalizedJob(
            source="greenhouse",
            source_id="gh_201",
            title="Python Developer Intern",
            company="Alpha Tech",
            location_text="Bengaluru",
            description="Looking for interns with 0-1 years experience in Python.",
            salary=None,
            posted_at=None,
            url="https://example.com/gh201",
            origin_site="greenhouse",
        ),
        # Post 3: Seniority reject
        NormalizedJob(
            source="jooble",
            source_id="j_102",
            title="Principal Architect",
            company="Enterprise Corp",
            location_text="Mumbai",
            description="10+ years experience in distributed cloud architecture.",
            salary=None,
            posted_at=None,
            url="https://example.com/j102",
            origin_site="jooble",
        ),
        # Post 4: ML Trainee fresher accept
        NormalizedJob(
            source="jooble",
            source_id="j_103",
            title="Machine Learning Trainee",
            company="AI Labs",
            location_text="Hyderabad",
            description="Fresher graduate trainee for computer vision and NLP models.",
            salary=None,
            posted_at=None,
            url="https://example.com/j103",
            origin_site="jooble",
        ),
        # Post 5: Non-fresher reject
        NormalizedJob(
            source="jooble",
            source_id="j_104",
            title="Java Backend Engineer",
            company="Beta Corp",
            location_text="Pune",
            description="Requires minimum 4-6 years experience in Spring Boot.",
            salary=None,
            posted_at=None,
            url="https://example.com/j104",
            origin_site="jooble",
        ),
    ]

    def run_filter():
        survivors = []
        rejects = []
        for post in raw_posts:
            decision, reason = filter_engine.evaluate(post)
            if decision in ("accept", "ambiguous"):
                survivors.append((post, decision, reason))
            else:
                rej_key = hashlib.sha1(f"rej|{post.source}|{post.source_id}".encode()).hexdigest()
                from pipeline.dedup import ProcessedJob
                rejects.append(
                    ProcessedJob(
                        job=post,
                        rule_decision=decision,
                        rule_reason=reason,
                        canonical_key=rej_key,
                        status="rejected",
                        sources=[post.source],
                        duplicate_of=None,
                        city_or_remote=None,
                    )
                )

        processed_survivors, _ = deduplicator.deduplicate(survivors)
        processed = processed_survivors + rejects
        db.upsert_filtered_jobs(processed)

    def run_tag():
        pending = db.get_pending_jobs()
        if not pending:
            return

        posts_to_call = []
        c_keys = []
        for job in pending:
            c_hash = get_content_hash(
                job["title"], job["company"], job["location_text"], job["description"]
            )
            key = get_cache_key(c_hash, "tag_v2", "mock")
            if key in tag_cache:
                # Cache hit
                res = tag_cache[key]
                is_act = res.post_type.value in ("job", "internship", "trainee") and res.is_fresher
                db.update_tagged_jobs(
                    [
                        {
                            "canonical_key": job["canonical_key"],
                            "status": "active" if is_act else "rejected",
                            "role": res.role.value,
                            "city": res.city.value,
                            "post_type": res.post_type.value,
                            "is_fresher": 1 if res.is_fresher else 0,
                            "is_remote": 1 if res.is_remote else 0,
                            "tagger_model": "mock",
                            "prompt_version": "tag_v2",
                        }
                    ]
                )
            else:
                posts_to_call.append(
                    {
                        "index": len(posts_to_call),
                        "title": job["title"],
                        "company": job["company"],
                        "location": job["location_text"],
                        "description": job["description"][:600],
                    }
                )
                c_keys.append((job["canonical_key"], key))

        if posts_to_call:
            results, _ = mock_provider.tag_batch(posts_to_call, "tag_v2")
            updates = []
            for idx, res in enumerate(results):
                can_key, cache_k = c_keys[idx]
                tag_cache[cache_k] = res
                is_act = res.post_type.value in ("job", "internship", "trainee") and res.is_fresher
                updates.append(
                    {
                        "canonical_key": can_key,
                        "status": "active" if is_act else "rejected",
                        "role": res.role.value,
                        "city": res.city.value,
                        "post_type": res.post_type.value,
                        "is_fresher": 1 if res.is_fresher else 0,
                        "is_remote": 1 if res.is_remote else 0,
                        "tagger_model": "mock",
                        "prompt_version": "tag_v2",
                    }
                )
            db.update_tagged_jobs(updates)

    # STEP 1: First Filter Run
    run_filter()
    jobs_after_filter1 = db.get_all_jobs()
    assert len(jobs_after_filter1) == 5

    status_counts_f1 = {row["status"]: 0 for row in jobs_after_filter1}
    for row in jobs_after_filter1:
        status_counts_f1[row["status"]] += 1

    assert status_counts_f1["pending_tag"] == 2
    assert status_counts_f1["duplicate"] == 1
    assert status_counts_f1["rejected"] == 2

    dup_row = [r for r in jobs_after_filter1 if r["status"] == "duplicate"][0]
    assert dup_row["duplicate_of"] is not None
    master_key = dup_row["duplicate_of"]

    # STEP 2: First Tag Run
    mock_provider.call_count = 0
    run_tag()
    assert mock_provider.call_count == 1  # 1 batch call made

    jobs_after_tag1 = db.get_all_jobs()
    tagged_rows_t1 = {
        r["canonical_key"]: (r["status"], r["role"], r["city"], r["tag_source"])
        for r in jobs_after_tag1
        if r["tag_source"] == "llm"
    }
    assert len(tagged_rows_t1) == 2
    for can_k, (status, role, city, tag_src) in tagged_rows_t1.items():
        assert status == "active"
        assert tag_src == "llm"
        assert role is not None
        assert city is not None

    # STEP 3: Second Filter Run (Re-run over all raw posts)
    run_filter()
    jobs_after_filter2 = db.get_all_jobs()

    # Assert 1: Row counts strictly unchanged after second filter
    assert len(jobs_after_filter2) == len(jobs_after_filter1)

    # Assert 2: Tagged rows preserve their status, role, city, tag_source
    for r in jobs_after_filter2:
        if r["canonical_key"] in tagged_rows_t1:
            prev_status, prev_role, prev_city, prev_src = tagged_rows_t1[r["canonical_key"]]
            assert r["status"] == prev_status
            assert r["role"] == prev_role
            assert r["city"] == prev_city
            assert r["tag_source"] == prev_src

    # Assert 3: Duplicates preserve duplicate_of
    dup_row_f2 = [r for r in jobs_after_filter2 if r["status"] == "duplicate"][0]
    assert dup_row_f2["duplicate_of"] == master_key

    # STEP 4: Second Tag Run
    mock_provider.call_count = 0
    run_tag()

    # Assert 4: Second tag run makes ZERO provider calls
    assert mock_provider.call_count == 0

    jobs_after_tag2 = db.get_all_jobs()
    assert len(jobs_after_tag2) == 5
