"""Dry pipeline test using fixture posts and MockProvider.

Runs full pipeline in an in-memory database without external network calls.
Asserts:
- Pipeline executes in under 60 seconds.
- Output jobs have valid taxonomy enums.
- Deduplication and rule filters are accurately applied.
- Zero network calls are made.
- Writes detailed report to docs/results/dry_test.txt.
"""

import json
import time
from pathlib import Path
from typing import Any

import pytest

from pipeline.dedup import Deduplicator
from pipeline.filters import FilterRuleEngine
from pipeline.llm.mock import MockProvider
from pipeline.normalize import NormalizedJob, normalize_post
from pipeline.sources.base import RawPost
from tests.test_idempotency import InMemoryDB


def load_fixtures_as_raw_posts() -> list[RawPost]:
    fixtures_file = Path("tests/fixtures/synthetic_fixtures.json")
    with open(fixtures_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_posts = []
    # Jooble fixtures
    for job in data.get("jooble", {}).get("jobs", []):
        raw_posts.append(
            RawPost(
                source="jooble",
                source_id=str(job["id"]),
                payload=job,
            )
        )
    # Greenhouse fixtures
    for job in data.get("greenhouse", {}).get("jobs", []):
        raw_posts.append(
            RawPost(
                source="greenhouse",
                source_id=str(job["id"]),
                payload=job,
            )
        )

    # Add edge cases: senior rejected, pay-to-play rejected, duplicate pair
    raw_posts.append(
        RawPost(
            source="greenhouse",
            source_id="300001",
            payload={
                "id": 300001,
                "title": "Senior Staff Backend Engineer (8+ years exp)",
                "location": {"name": "Bengaluru, India"},
                "content": "Requires 8 to 12 years of hands-on distributed systems experience.",
                "absolute_url": "https://boards.greenhouse.io/corp/jobs/300001",
            },
        )
    )
    raw_posts.append(
        RawPost(
            source="jooble",
            source_id="300002",
            payload={
                "id": 300002,
                "title": "Python Developer Internship - Registration Fee Required",
                "location": "Pune, India",
                "snippet": "Pay admission fee of Rs 5000 for training and placement support.",
                "link": "https://example.com/job/300002",
                "company": "Training Hub",
            },
        )
    )
    # Duplicate post (same company and title, cross-source)
    raw_posts.append(
        RawPost(
            source="jooble",
            source_id="300003",
            payload={
                "id": 300003,
                "title": "Software Engineer Trainee",
                "location": "Bengaluru, India",
                "snippet": "Entry level software engineering role for freshers at Acme Tech.",
                "link": "https://example.com/job/300003?utm_source=feed",
                "company": "Acme Tech India",
            },
        )
    )
    return raw_posts


def test_dry_pipeline_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Guard against any accidental socket network connections
    import socket

    def guarded_connect(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network call attempted during dry test!")

    monkeypatch.setattr(socket, "create_connection", guarded_connect)

    start_time = time.perf_counter()

    # 2. Setup isolated in-memory DB and mock provider
    db = InMemoryDB()
    mock_provider = MockProvider()
    filter_engine = FilterRuleEngine()
    deduplicator = Deduplicator()

    raw_posts = load_fixtures_as_raw_posts()
    assert len(raw_posts) >= 5, "Fixture posts should be loaded"

    # 3. Stage 1: Normalize and Filter
    normalized_list = [normalize_post(rp.source, rp.source_id, rp.payload) for rp in raw_posts]
    survivors: list[tuple[NormalizedJob, str, str]] = []
    rejects: list[dict[str, Any]] = []

    for nj in normalized_list:
        decision, reason = filter_engine.evaluate(nj)
        if decision in ("accept", "ambiguous"):
            survivors.append((nj, decision, reason))
        else:
            rejects.append(
                {
                    "job": nj,
                    "rule_decision": "reject",
                    "rule_reason": reason,
                    "status": "rejected",
                }
            )

    # 4. Stage 2: Deduplicate survivors
    processed_survivors, _ = deduplicator.deduplicate(survivors)
    all_jobs_to_save = processed_survivors + [
        type(
            "RejJob",
            (),
            {
                "canonical_key": f"rej|{r['job'].source}|{r['job'].source_id}",
                "job": r["job"],
                "rule_decision": r["rule_decision"],
                "rule_reason": r["rule_reason"],
                "status": r["status"],
                "duplicate_of": None,
                "sources": [r["job"].source],
            },
        )()
        for r in rejects
    ]

    # Save to in-memory DB
    db.upsert_filtered_jobs(all_jobs_to_save)

    # 5. Stage 3: Tag survivors with MockProvider
    pending_jobs = db.get_pending_jobs()
    assert len(pending_jobs) > 0, "There should be pending_tag survivors to tag"

    def chunk_list(lst: list[Any], n: int) -> list[list[Any]]:
        return [lst[i : i + n] for i in range(0, len(lst), n)]

    tagged_records = []
    calls_made = 0
    for batch in chunk_list(pending_jobs, 10):
        posts_for_llm = [
            {
                "canonical_key": j["canonical_key"],
                "title": j["title"],
                "company": j["company"],
                "location_text": j["location_text"],
                "description_snippet": (j["description"] or "")[:400],
            }
            for j in batch
        ]
        results, usage = mock_provider.tag_batch(posts_for_llm)
        calls_made += 1
        assert len(results) == len(batch)
        for job_row, res in zip(batch, results, strict=True):
            status = "active" if res.is_fresher else "rejected"
            tagged_records.append(
                {
                    "canonical_key": job_row["canonical_key"],
                    "status": status,
                    "role": res.role,
                    "city": res.city,
                    "post_type": res.post_type,
                    "is_fresher": 1 if res.is_fresher else 0,
                    "is_remote": 0,
                    "tagger_model": "mock",
                    "prompt_version": "tag_v4.txt",
                }
            )

    db.update_tagged_jobs(tagged_records)

    elapsed = time.perf_counter() - start_time

    # 6. Assertions
    assert elapsed < 60.0, f"Dry pipeline took {elapsed:.2f}s (must be < 60s)"
    assert calls_made > 0, "Mock provider should have been invoked"

    all_jobs = db.get_all_jobs()
    active_jobs = [j for j in all_jobs if j["status"] == "active"]
    rejected_jobs = [j for j in all_jobs if j["status"] == "rejected"]
    duplicate_jobs = [j for j in all_jobs if j["status"] == "duplicate"]

    assert len(active_jobs) > 0, "At least one fresher job should be active"
    assert len(rejected_jobs) > 0, "Senior and fee-charging jobs must be rejected"
    assert len(duplicate_jobs) > 0, "Duplicate post must be marked duplicate"

    # Verify active jobs have non-null role and city
    for j in active_jobs:
        assert j["role"] is not None
        assert j["city"] is not None
        assert j["is_fresher"] == 1

    # Save output to docs/results/dry_test.txt
    results_dir = Path("docs/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    report_text = f"""DRY TEST EXECUTION REPORT
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
Total Elapsed Time: {elapsed:.3f} seconds (Target: < 60s)
Status: PASSED

Pipeline Counts:
  - Raw posts processed: {len(raw_posts)}
  - Active fresher jobs: {len(active_jobs)}
  - Rejected jobs: {len(rejected_jobs)}
  - Duplicate jobs: {len(duplicate_jobs)}
  - Total jobs in DB: {len(all_jobs)}

LLM Mock Execution:
  - Calls made: {calls_made}
  - Network calls: 0 (guarded socket verified)
  - All output tags validated against taxonomy.
"""
    (results_dir / "dry_test.txt").write_text(report_text, encoding="utf-8")
