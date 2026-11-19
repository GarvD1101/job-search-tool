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

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, trigger, started_at, finished_at, status,
                   stats->>'stage' as stage,
                   stats->'source_counts' as source_counts,
                   stats->>'trigger' as stats_trigger,
                   stats->'github' as github_info
            FROM runs
            WHERE id >= 11
            ORDER BY id ASC;
        """)
        for r in cur.fetchall():
            print(
                f"Run {r[0]}: trigger={r[1]}, started_at={r[2]}, status={r[4]}, "
                f"stage={r[5]}, sources={r[6]}, stats_trigger={r[7]}, github={r[8]}"
            )
