"""Database invariant checker for job search pipeline.

Invariants checked:
(a) No duplicate (source, source_id) in jobs.
(b) Every raw post has exactly one jobs row (no orphans on either side).
(c) No pending_tag row whose rule decision is reject.
(d) Status counts sum to total jobs count.
(e) Tagged count (tag_source = 'llm') never decreases across runs.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def check_invariants(db_url: str | None = None) -> tuple[bool, dict[str, Any]]:
    """Verify all 5 database invariants.

    Returns:
        (passed, results_dict)
    """
    target_url = db_url or os.environ.get("SUPABASE_DB_URL")
    if not target_url:
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() in ("SUPABASE_DB_URL", "DATABASE_URL"):
                        target_url = v.strip().strip('"\'')
                        break

    if not target_url:
        return False, {"error": "No database URL configured"}

    results: dict[str, Any] = {
        "passed": True,
        "violations": [],
        "metrics": {},
    }

    with psycopg.connect(target_url) as conn:
        with conn.cursor() as cur:
            # (a) No duplicate (source, source_id)
            cur.execute("""
                SELECT source, source_id, count(*)
                FROM jobs
                GROUP BY source, source_id
                HAVING count(*) > 1;
            """)
            dup_sources = cur.fetchall()
            results["metrics"]["duplicate_source_source_id_count"] = len(dup_sources)
            if dup_sources:
                results["passed"] = False
                results["violations"].append(
                    f"Invariant A failed: Found {len(dup_sources)} duplicate "
                    "(source, source_id) entries."
                )

            # (b) Every raw post has exactly one jobs row
            cur.execute("""
                SELECT count(*)
                FROM raw_posts r
                LEFT JOIN jobs j ON r.source = j.source AND r.source_id = j.source_id
                WHERE j.id IS NULL;
            """)
            missing_in_jobs = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM jobs j
                LEFT JOIN raw_posts r ON j.source = r.source AND j.source_id = r.source_id
                WHERE r.id IS NULL;
            """)
            orphan_jobs = cur.fetchone()[0]

            cur.execute("SELECT count(*) FROM raw_posts;")
            raw_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM jobs;")
            jobs_count = cur.fetchone()[0]

            results["metrics"]["raw_posts_count"] = raw_count
            results["metrics"]["jobs_count"] = jobs_count
            results["metrics"]["raw_missing_in_jobs"] = missing_in_jobs
            results["metrics"]["orphan_jobs_without_raw"] = orphan_jobs

            if missing_in_jobs > 0 or orphan_jobs > 0:
                results["passed"] = False
                results["violations"].append(
                    f"Invariant B failed: raw_posts missing in jobs={missing_in_jobs}, "
                    f"orphan jobs without raw={orphan_jobs}"
                )

            # (c) No pending_tag row whose latest rule decision is reject
            cur.execute("""
                SELECT count(*)
                FROM jobs
                WHERE status = 'pending_tag' AND rule_decision = 'reject';
            """)
            pending_rejects = cur.fetchone()[0]
            results["metrics"]["pending_tag_with_reject_rule"] = pending_rejects
            if pending_rejects > 0:
                results["passed"] = False
                results["violations"].append(
                    f"Invariant C failed: Found {pending_rejects} pending_tag rows with "
                    "rule_decision = reject."
                )

            # (d) Status counts sum to total jobs count
            cur.execute("""
                SELECT status, count(*)
                FROM jobs
                GROUP BY status;
            """)
            status_counts = dict(cur.fetchall())
            sum_status = sum(status_counts.values())
            results["metrics"]["status_counts"] = status_counts
            results["metrics"]["sum_of_status_counts"] = sum_status
            if sum_status != jobs_count:
                results["passed"] = False
                results["violations"].append(
                    f"Invariant D failed: Sum of status counts ({sum_status}) != "
                    f"total jobs ({jobs_count})."
                )

            # (e) Tagged count never decreases
            cur.execute("SELECT count(*) FROM jobs WHERE tag_source = 'llm';")
            current_tagged = cur.fetchone()[0]
            results["metrics"]["current_tagged_count"] = current_tagged

            # Query previous runs for maximum recorded tagged count
            cur.execute("""
                SELECT stats->'invariants'->'metrics'->>'current_tagged_count'
                FROM runs
                WHERE stats->'invariants'->'metrics'->>'current_tagged_count' IS NOT NULL
                ORDER BY id DESC
                LIMIT 5;
            """)
            prev_tagged_records = [
                int(row[0]) for row in cur.fetchall() if row[0] is not None
            ]
            prev_max_tagged = max(prev_tagged_records) if prev_tagged_records else 440
            results["metrics"]["previous_max_tagged_count"] = prev_max_tagged

            if current_tagged < prev_max_tagged:
                results["passed"] = False
                results["violations"].append(
                    f"Invariant E failed: Current tagged count ({current_tagged}) < "
                    f"previous max ({prev_max_tagged})."
                )

    return results["passed"], results


if __name__ == "__main__":
    passed, res = check_invariants()
    print("=" * 60)
    print(f"DATABASE INVARIANTS STATUS: {'PASSED' if passed else 'FAILED'}")
    print("=" * 60)
    print("Metrics:")
    for k, v in res.get("metrics", {}).items():
        print(f"  - {k}: {v}")
    if res.get("violations"):
        print("\nViolations:")
        for v in res["violations"]:
            print(f"  * {v}")
    print("=" * 60)
    sys.exit(0 if passed else 1)
