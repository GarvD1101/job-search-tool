"""Migration script to transition jobs table to raw post identity:
1. Add source_id and dedup_key columns to jobs
2. Populate source_id and dedup_key for all jobs rows
3. Delete redundant duplicate rows for multi-job raw posts (preferring tagged, then newest)
4. Enforce NOT NULL and UNIQUE (source, source_id)
5. Drop old UNIQUE (canonical_key)
6. Verify 440 tagged rows preserved
"""

import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg

from pipeline.normalize import normalize_post

env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))

db_url = os.environ.get("SUPABASE_DB_URL")
if not db_url:
    print("Error: No SUPABASE_DB_URL found.")
    sys.exit(1)

with psycopg.connect(db_url, autocommit=False) as conn:
    with conn.cursor() as cur:
        print("Starting migration...")

        # Step 1: Add columns if not exist
        print("Adding source_id and dedup_key columns if missing...")
        cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_id TEXT;")
        cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS dedup_key TEXT;")

        # Step 2: Load raw_posts and jobs
        cur.execute("SELECT source, source_id, payload FROM raw_posts;")
        raw_rows = cur.fetchall()
        print(f"Loaded {len(raw_rows)} raw posts.")

        rej_to_raw = {}
        src_url_to_raw = {}
        jooble_id_to_raw = {}
        gh_url_to_raw = {}

        for src, src_id, payload in raw_rows:
            src_id_str = str(src_id)
            rej_key = hashlib.sha1(f"rej|{src}|{src_id_str}".encode("utf-8")).hexdigest()
            rej_to_raw[rej_key] = (src, src_id_str)
            norm = normalize_post(src, src_id_str, payload)
            src_url_to_raw[(src, norm.url)] = (src, src_id_str)
            if src == "jooble":
                jooble_id_to_raw[src_id_str] = (src, src_id_str)
            elif src == "greenhouse":
                gh_url_to_raw[norm.url] = (src, src_id_str)

        cur.execute("""
            SELECT id, canonical_key, source, url, status, tag_source, first_seen_at
            FROM jobs
            ORDER BY id ASC;
        """)
        job_rows = cur.fetchall()
        print(f"Loaded {len(job_rows)} jobs rows.")

        cur.execute("SELECT count(*) FROM jobs WHERE tag_source = 'llm';")
        tagged_before = cur.fetchone()[0]
        print(f"Tagged rows before migration: {tagged_before}")

        raw_to_jobs = defaultdict(list)
        job_source_ids = {}

        for j in job_rows:
            jid, ckey, jsrc, jurl, status, tag_src, fs_at = j
            matched = None
            if ckey in rej_to_raw:
                matched = rej_to_raw[ckey]
            elif (jsrc, jurl) in src_url_to_raw:
                matched = src_url_to_raw[(jsrc, jurl)]
            elif jsrc == "jooble":
                m = re.search(r"/desc/(-?\d+)", jurl)
                if m and m.group(1) in jooble_id_to_raw:
                    matched = jooble_id_to_raw[m.group(1)]
            elif jsrc == "greenhouse":
                if jurl in gh_url_to_raw:
                    matched = gh_url_to_raw[jurl]

            if not matched:
                raise RuntimeError(f"Unmatched job row id={jid}, url={jurl}")

            job_source_ids[jid] = matched[1]
            raw_to_jobs[matched].append({
                "id": jid,
                "canonical_key": ckey,
                "status": status,
                "tag_source": tag_src,
                "first_seen_at": fs_at,
            })

        # Step 3: Determine winners and losers for duplicates
        keep_ids = []
        delete_ids = []
        for (src, src_id), jlist in raw_to_jobs.items():
            if len(jlist) == 1:
                keep_ids.append(jlist[0]["id"])
            else:
                sorted_jobs = sorted(
                    jlist,
                    key=lambda x: (1 if x["tag_source"] == "llm" else 0, x["id"]),
                    reverse=True,
                )
                winner = sorted_jobs[0]
                losers = sorted_jobs[1:]
                keep_ids.append(winner["id"])
                for loser in losers:
                    delete_ids.append(loser["id"])

        print(f"Identified {len(delete_ids)} redundant rows to delete: {delete_ids}")

        # Delete redundant rows
        if delete_ids:
            cur.execute("DELETE FROM jobs WHERE id = ANY(%s);", (delete_ids,))
            print(f"Deleted {len(delete_ids)} rows from jobs.")

        # Update remaining rows with source_id and dedup_key
        print("Updating source_id and dedup_key for remaining rows...")
        update_data = [
            (job_source_ids[jid], jid)
            for jid in keep_ids
        ]
        cur.executemany(
            "UPDATE jobs SET source_id = %s, dedup_key = canonical_key WHERE id = %s;",
            update_data,
        )
        print("Updated all rows successfully.")

        # Step 4: Enforce constraints
        print("Altering column source_id SET NOT NULL...")
        cur.execute("ALTER TABLE jobs ALTER COLUMN source_id SET NOT NULL;")

        print("Dropping old jobs_canonical_key_key if exists...")
        cur.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_canonical_key_key;")

        print("Adding UNIQUE (source, source_id) constraint...")
        cur.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_source_source_id_key;")
        cur.execute(
            "ALTER TABLE jobs ADD CONSTRAINT jobs_source_source_id_key "
            "UNIQUE (source, source_id);"
        )

        print("Creating index on dedup_key...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_dedup_key ON jobs (dedup_key);")

        # Step 5: Verify post-migration state
        cur.execute("SELECT count(*) FROM jobs;")
        total_after = cur.fetchone()[0]

        cur.execute("SELECT count(*) FROM jobs WHERE tag_source = 'llm';")
        tagged_after = cur.fetchone()[0]

        print(f"Total jobs after migration: {total_after}")
        print(f"Tagged rows after migration: {tagged_after}")

        if tagged_before != tagged_after:
            conn.rollback()
            raise RuntimeError(
                f"FATAL: Tagged rows mismatch! Before={tagged_before}, After={tagged_after}"
            )

        conn.commit()
        print("Migration committed successfully!")
