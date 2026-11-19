"""Performance benchmark for local Next.js build using Supabase Transaction Pooler (port 6543).

Requirements:
- DATABASE_URL set to transaction pooler on port 6543 without query parameters.
- Wipes web/.next/cache before starting server to guarantee honest cold measurements.
- Measures true cold (uncached database round trip to Tokyo) and warm (cache hit).
- Tests 3 sample queries:
  1. Home page: / and /api/jobs
  2. Search: /?q=developer and /api/jobs?q=developer
  3. Filter: /?role=software_dev&city=bengaluru and /api/jobs?role=software_dev&city=bengaluru
  4. Stats page: /stats
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlunparse

env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))

raw_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
if not raw_url:
    print("Error: No database URL found in .env")
    sys.exit(1)

# Ensure transaction pooler on port 6543 with no query parameters
p = urlparse(raw_url)
pooler_port = 6543
netloc = f"{p.username}:{p.password}@{p.hostname}:{pooler_port}"
clean_db_url = urlunparse((p.scheme, netloc, p.path, "", "", ""))

print(f"Connecting via Transaction Pooler: {p.hostname}:{pooler_port}{p.path} (no query params)")

# 1. Honest cold reset: Delete web/.next/cache before test
web_dir = Path("web").resolve()
cache_dir = web_dir / ".next" / "cache"
if cache_dir.exists():
    print(f"Deleting Next.js cache at {cache_dir} for true cold measurement...")
    shutil.rmtree(cache_dir, ignore_errors=True)
else:
    print("No previous Next.js cache directory found.")

env = os.environ.copy()
env["PATH"] = "C:\\nvm4w\\nodejs;" + env.get("PATH", "")
env["DATABASE_URL"] = clean_db_url
env["SUPABASE_DB_URL"] = clean_db_url

print("Starting production server (next start) on port 3000...")
proc = subprocess.Popen(
    ["cmd.exe", "/c", "pnpm", "start"],
    cwd=str(web_dir),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

time.sleep(4)
base_url = "http://127.0.0.1:3000"

queries = [
    {
        "name": "Query 1: Home Page / Jobs List (all active jobs)",
        "api_url": "/api/jobs",
        "page_url": "/",
    },
    {
        "name": "Query 2: Search term 'developer'",
        "api_url": "/api/jobs?q=developer",
        "page_url": "/?q=developer",
    },
    {
        "name": "Query 3: Filter role=software_dev, city=bengaluru",
        "api_url": "/api/jobs?role=software_dev&city=bengaluru",
        "page_url": "/?role=software_dev&city=bengaluru",
    },
]

try:
    print("\n" + "=" * 65)
    print("HONEST PERFORMANCE BENCHMARK (COLD CACHE WIPED + WARM)")
    print("=" * 65)

    for q in queries:
        print(f"\n--- {q['name']} ---")

        # 1. API True Cold: hits the API first on a clean cache
        t0 = time.perf_counter()
        with urllib.request.urlopen(base_url + q["api_url"], timeout=20) as resp:
            data_cold = json.loads(resp.read().decode("utf-8"))
            api_cold = (time.perf_counter() - t0) * 1000

        # 2. API Warm: second request served from Next.js unstable_cache
        t0 = time.perf_counter()
        with urllib.request.urlopen(base_url + q["api_url"], timeout=15) as resp:
            data_warm = json.loads(resp.read().decode("utf-8"))
            api_warm = (time.perf_counter() - t0) * 1000

        # 3. HTML Warm / Rendered: requests server-rendered page
        t0 = time.perf_counter()
        with urllib.request.urlopen(base_url + q["page_url"], timeout=15) as resp:
            resp.read()
            html_warm = (time.perf_counter() - t0) * 1000

        total_matched = data_warm.get("total", 0)
        items_count = len(data_warm.get("items", []))

        print(f"Matched total jobs: {total_matched}")
        print(f"Page items count: {items_count}")
        print(f"API Route Latency: Cold = {api_cold:.1f} ms | Warm = {api_warm:.1f} ms")
        print(f"HTML SSR Latency (warm cache): {html_warm:.1f} ms")

    # Stats Page
    print("\n--- Stats Page (/stats) ---")
    t0 = time.perf_counter()
    with urllib.request.urlopen(base_url + "/stats", timeout=20) as resp:
        resp.read()
        stats_cold = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    with urllib.request.urlopen(base_url + "/stats", timeout=15) as resp:
        resp.read()
        stats_warm = (time.perf_counter() - t0) * 1000

    print(f"Stats Page Latency: Cold = {stats_cold:.1f} ms | Warm = {stats_warm:.1f} ms")

    # Costs Page
    print("\n--- Costs Page (/costs) ---")
    t0 = time.perf_counter()
    with urllib.request.urlopen(base_url + "/costs", timeout=15) as resp:
        resp.read()
        costs_time = (time.perf_counter() - t0) * 1000
    print(f"Costs Page Latency (prerendered static): {costs_time:.1f} ms")
    print("=" * 65 + "\n")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Production server shut down cleanly.")
