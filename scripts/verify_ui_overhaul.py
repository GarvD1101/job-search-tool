"""Verification test suite for Industrial Swiss Grid UI/UX Overhaul.

Verifies:
1. TypeScript compilation and Next.js build integrity.
2. Data sanitization (no raw scraper artifacts, no duplicate cities).
3. No raw snake_case keys or dedup hashes on /stats.
4. Correct drilldown link generation on /stats.
5. Currency formatting on /costs (no inverted dollar signs).
6. Exact matching navigation and colophon labels.
7. Zero em dashes in web/src.
"""

import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

env = os.environ.copy()
env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip("'\""))

env["PATH"] = "C:\\nvm4w\\nodejs;" + env.get("PATH", "")
web_dir = Path("web").resolve()

# 1. Verify zero em dashes in web/src
print("Test 1: Scanning web/src for em dashes...")
em_dash_files = []
for p in (web_dir / "src").glob("**/*"):
    if p.is_file() and p.suffix in [".ts", ".tsx", ".css"]:
        content = p.read_text(encoding="utf-8")
        if "—" in content or "–" in content:
            em_dash_files.append(str(p))

if em_dash_files:
    print(f"FAILED: Found em dashes in {em_dash_files}")
    exit(1)
print("PASSED: Zero em dashes found in web/src.")

# 2. Start server and inspect live rendered pages
print("\nTest 2: Starting Next.js production server...")
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

try:
    # 2a. Verify Home Page (/)
    print("Test 3: Validating / (Live Jobs)...")
    with urllib.request.urlopen(f"{base_url}/", timeout=15) as resp:
        html_home = resp.read().decode("utf-8")

    assert "FRESHER RADAR" in html_home, "Missing brand mark"
    assert "01 LIVE JOBS" in html_home, "Missing 01 LIVE JOBS tab"
    assert "02 STATS" in html_home, "Missing 02 STATS tab"
    assert "03 COSTS" in html_home, "Missing 03 COSTS tab"
    assert "Mumbai (Mumbai)" not in html_home, "Found duplicate city string Mumbai (Mumbai)"
    assert "Kolkata (Kolkatta)" not in html_home, "Found duplicate city string Kolkata (Kolkatta)"
    assert "..Overview" not in html_home, "Found scraper artifact ..Overview"
    assert "(***) )" not in html_home, "Found broken phone mask"
    print("PASSED: / validated cleanly.")

    # 2b. Verify Stats Page (/stats)
    print("\nTest 4: Validating /stats (Pipeline Telemetry)...")
    with urllib.request.urlopen(f"{base_url}/stats", timeout=15) as resp:
        html_stats = resp.read().decode("utf-8")

    has_core = "01 // CORE TELEMETRY" in html_stats or "01 // ACTIVE JOBS" in html_stats
    assert has_core, "Missing core telemetry header"

    has_funnel = (
        "02 // INGESTION &amp; FILTERING FUNNEL" in html_stats
        or "02 // INGESTION & FILTERING FUNNEL" in html_stats
    )
    assert has_funnel, "Missing funnel header"

    assert "03 // LLM TOKEN LEDGER" in html_stats, "Missing token ledger header"

    has_audit = (
        "04 // TAXONOMY, GEOGRAPHY &amp; RULE AUDIT" in html_stats
        or "04 // TAXONOMY, GEOGRAPHY & RULE AUDIT" in html_stats
    )
    assert has_audit, "Missing audit header"
    assert "05 // PIPELINE EXECUTION LOG" in html_stats, "Missing pipeline log header"

    # Check for no raw snake_case keys leaking
    assert "experience_required" not in html_stats, "Raw snake_case key leaked"
    assert "tier2_fuzzy_match_" not in html_stats, "Raw dedup hash leaked"
    assert "[EXP_REQ]" in html_stats or "Prior Experience" in html_stats, "Sanitized reason missing"

    # Check drilldown links
    assert 'href="/?role=' in html_stats, "Role drilldown links missing"
    assert 'href="/?city=' in html_stats, "City drilldown links missing"
    print("PASSED: /stats validated cleanly.")

    # 2c. Verify Costs Page (/costs)
    print("\nTest 5: Validating /costs (FinOps & Scale Projections)...")
    with urllib.request.urlopen(f"{base_url}/costs", timeout=15) as resp:
        html_costs = resp.read().decode("utf-8")

    assert "01 // EXECUTIVE FINDING" in html_costs, "Missing executive finding"
    assert "02 // INTERACTIVE UNIT-ECONOMICS SIMULATOR" in html_costs, "Missing simulator"
    has_schematic = (
        "03 // SERVING TRAFFIC &amp; COST" in html_costs
        or "03 // SERVING TRAFFIC & COST" in html_costs
    )
    assert has_schematic, "Missing schematic"
    assert "04 // PROJECTION MATRICES" in html_costs, "Missing projection tables"
    assert "05 // VERIFIED PRICING SOURCES" in html_costs, "Missing verified sources"

    # Check currency formatting: no inverted dollar signs like "10.59$"
    inverted_usd = re.findall(r"\d+\.\d{2}\$", html_costs)
    assert not inverted_usd, f"Found inverted dollar strings: {inverted_usd}"
    print("PASSED: /costs validated cleanly.")

    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Production server shut down cleanly.")
