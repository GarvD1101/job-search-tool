"""Launch the Next.js production server for local browser testing.

Ensures the database connection is routed through port 6543
and starts 'pnpm start' on port 3000.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

env = os.environ.copy()
env["PATH"] = "C:\\nvm4w\\nodejs;" + env.get("PATH", "")

env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip("'\""))

raw_url = env.get("DATABASE_URL") or env.get("SUPABASE_DB_URL")
if raw_url:
    p = urlparse(raw_url)
    pooler_port = 6543
    netloc = f"{p.username}:{p.password}@{p.hostname}:{pooler_port}"
    clean_db_url = urlunparse((p.scheme, netloc, p.path, "", "", ""))
    env["DATABASE_URL"] = clean_db_url
    env["SUPABASE_DB_URL"] = clean_db_url

web_dir = Path("web").resolve()
print("Starting Next.js production server on http://localhost:3000...")
sys.stdout.flush()

subprocess.run(
    ["cmd.exe", "/c", "pnpm", "start"],
    cwd=str(web_dir),
    env=env,
)
