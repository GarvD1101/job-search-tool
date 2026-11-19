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
        # Relabel runs 13 and 14 to manual
        update_sql = """
        UPDATE runs SET trigger = 'manual'
        WHERE id IN (13, 14) AND trigger = 'schedule';
        """
        cur.execute(update_sql)
        print(f"Updated {cur.rowcount} runs to trigger='manual'.")

        # Query runs 11 to 14
        cur.execute("""
            SELECT id, trigger, started_at,
                   stats->>'stage' as stage,
                   stats->'source_counts' as source_counts
            FROM runs
            WHERE id >= 11
            ORDER BY id ASC;
        """)
        print("\nRuns 11 to 14 in database:")
        for r in cur.fetchall():
            print(f"Run {r[0]}: trigger={r[1]}, started_at={r[2]}, stage={r[3]}, sources={r[4]}")
