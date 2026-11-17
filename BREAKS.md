# BREAKS.md

Log of real failures encountered during development, root causes, fixes, and lessons learned.

## 2026-11-17 15:53  Python launcher py not recognized in PowerShell
Symptom: Running py -3.12 --version returned CommandNotFoundException.
Root cause: The Python launcher directory was not registered on PATH in the terminal session, whereas python was directly available as Python 3.12.0.
Fix: Used python -m venv .venv to initialize the virtual environment directly with Python 3.12.
Commit: pending
Next time: Check Get-Command python and installed binaries before assuming py.exe is on PATH.

## 2026-11-17 15:55  Pip package installation blocked by sandbox network isolation
Symptom: Running pip install in sandbox mode failed with Errno 11001 getaddrinfo failed.
Root cause: Sandbox isolation blocks outbound network access to external hosts including PyPI.
Fix: Executed pip installation with network access enabled outside the sandbox.
Commit: pending
Next time: Package installation from remote package indexes must be executed with network access.

## 2026-11-17 16:00  Environment variables not propagated to existing process session
Symptom: Process environment variables JOOBLE_API_KEY and SUPABASE_DB_URL were missing in the current shell session.
Root cause: User environment variables added after the process launched are not automatically propagated to running sessions without restarting or reading from registry.
Fix: Added Windows registry fallback in scripts/apply_schema.py to retrieve User-level environment variables when process environment is stale.
Commit: pending
Next time: Check user registry directly or restart terminal session when verifying newly created variables.

## 2026-11-17 16:06  Groq API models request blocked with HTTP 403 Forbidden
Symptom: GET request to https://api.groq.com/openai/v1/models failed with HTTP Error 403: Forbidden.
Root cause: Default Python-urllib User-Agent header was rejected by Cloudflare or Groq edge firewall.
Fix: Configured an explicit User-Agent header (curl or fresher-radar/0.1) on outgoing HTTP requests.
Commit: pending
Next time: Always specify a descriptive or standard User-Agent header for external API interactions.
