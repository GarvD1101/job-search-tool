import os
from pathlib import Path

import psycopg

env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))

db_url = os.environ.get("SUPABASE_DB_URL")

with psycopg.connect(db_url, autocommit=True) as conn:
    with conn.cursor() as cur:
        # Step 1: Expire
        cur.execute("""
            UPDATE jobs
            SET status = 'expired'
            WHERE status IN ('active', 'pending_tag')
              AND (
                last_seen_at < NOW() - INTERVAL '14 days'
                OR posted_at < NOW() - INTERVAL '45 days'
              );
        """)
        expired_count = cur.rowcount
        print(f"Step 1 (Expire): Marked {expired_count} jobs as expired.")

        # Step 2: Untagged rejects
        cur.execute("""
            UPDATE jobs
            SET status = 'rejected'
            WHERE (tag_source IS NULL OR tag_source = 'rule')
              AND rule_decision = 'reject'
              AND status = 'pending_tag';
        """)
        rejected_count = cur.rowcount
        print(f"Step 2 (Untagged Rejects): Updated {rejected_count} rows to rejected.")

        # Step 3: Prune raw_posts
        cur.execute("""
            DELETE FROM raw_posts
            WHERE fetched_at < NOW() - INTERVAL '7 days';
        """)
        pruned_count = cur.rowcount
        print(f"Step 3 (Prune Raw Posts): Deleted {pruned_count} raw posts older than 7 days.")
