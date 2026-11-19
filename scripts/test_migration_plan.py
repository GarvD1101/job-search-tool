import hashlib
import os
import re
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

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # 1. Load raw posts
        cur.execute("SELECT source, source_id, payload FROM raw_posts;")
        raw_rows = cur.fetchall()

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

        # 2. Load jobs
        cur.execute("""
            SELECT id, canonical_key, source, url, status, tag_source,
                   rule_decision, rule_reason, title, company, first_seen_at
            FROM jobs
            ORDER BY id ASC;
        """)
        job_rows = cur.fetchall()

        raw_to_jobs = defaultdict(list)
        for j in job_rows:
            jid, ckey, jsrc, jurl, status, tag_src, r_dec, r_reason, title, comp, fs_at = j
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

            raw_to_jobs[matched].append({
                "id": jid,
                "canonical_key": ckey,
                "status": status,
                "tag_source": tag_src,
                "first_seen_at": fs_at,
            })

        # Count tagged rows before
        tagged_before = sum(1 for j in job_rows if j[5] == "llm")
        print(f"Total jobs before: {len(job_rows)}")
        print(f"Tagged rows before (tag_source = 'llm'): {tagged_before}")

        # Dry run resolution
        keep_ids = []
        delete_ids = []
        for (src, src_id), jlist in raw_to_jobs.items():
            if len(jlist) == 1:
                keep_ids.append(jlist[0]["id"])
            else:
                # Sort: prefer tagged (tag_source == 'llm'), then newest id DESC
                sorted_jobs = sorted(
                    jlist,
                    key=lambda x: (1 if x["tag_source"] == "llm" else 0, x["id"]),
                    reverse=True
                )
                winner = sorted_jobs[0]
                losers = sorted_jobs[1:]
                keep_ids.append(winner["id"])
                for loser in losers:
                    delete_ids.append(loser["id"])

        print(f"Rows to keep: {len(keep_ids)}")
        print(f"Rows to delete: {len(delete_ids)} (IDs: {delete_ids})")

        # Check tagged count among kept rows
        kept_job_map = {j[0]: j for j in job_rows if j[0] in set(keep_ids)}
        tagged_after = sum(1 for j in kept_job_map.values() if j[5] == "llm")
        print(f"Tagged rows among kept (tag_source = 'llm'): {tagged_after}")
