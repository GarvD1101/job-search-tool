"""Script to test Next.js server locally, HTML and API routes."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
if not db_url:
    print("Error: No SUPABASE_DB_URL or DATABASE_URL found in .env")
    sys.exit(1)

env = os.environ.copy()
env["PATH"] = "C:\\nvm4w\\nodejs;" + env.get("PATH", "")
env["DATABASE_URL"] = db_url

web_dir = Path(__file__).resolve().parent.parent / "web"
proc = subprocess.Popen(
    ["cmd.exe", "/c", "pnpm", "start"],
    cwd=str(web_dir),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

time.sleep(3)
base_url = "http://127.0.0.1:3000"

try:
    for route in ["/", "/stats"]:
        t0 = time.perf_counter()
        req = urllib.request.Request(base_url + route)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            elapsed = (time.perf_counter() - t0) * 1000
            print(
                f"Route: {route} -> Status {resp.status}, "
                f"Size {len(body)} bytes, Latency {elapsed:.1f} ms"
            )

    # API queries
    queries = [
        ("Home Page (all active jobs)", "/", "/api/jobs"),
        ("Search 'developer'", "/?q=developer", "/api/jobs?q=developer"),
        (
            "Filter role=software_dev, city=bengaluru",
            "/?role=software_dev&city=bengaluru",
            "/api/jobs?role=software_dev&city=bengaluru",
        ),
    ]
    for name, page_path, api_path in queries:
        t0 = time.perf_counter()
        req = urllib.request.Request(base_url + api_path)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = (time.perf_counter() - t0) * 1000
            print(
                f"API {name}: {resp.status}, Total {data.get('total')}, "
                f"Latency {elapsed:.1f} ms"
            )
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
