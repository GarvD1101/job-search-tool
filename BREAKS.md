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

## 2026-11-17 16:22  CI editable pip install failed on flat-layout discovery
Symptom: GitHub Actions CI failed during pip install -e ".[dev]" with error "Multiple top-level packages discovered in a flat-layout: ['db', 'config']".
Root cause: pyproject.toml lacked explicit setuptools package discovery settings. Setuptools automatic discovery encountered multiple non-package directories at repository root and aborted.
Fix: Added explicit [build-system] and [tool.setuptools.packages.find] to pyproject.toml, targeting pipeline packages and excluding non-package root directories.
Commit: pending
Next time: Explicitly configure package discovery in pyproject.toml when using a flat layout with non-code root directories.

## 2026-11-17 16:36  Jooble API returned HTTP 403 on global domain
Symptom: POST request to https://jooble.org/api/<REDACTED> returned HTTP Error 403: Forbidden.
Root cause: Jooble issues domain-specific regional API keys. An API key created for the Indian portal must be queried via in.jooble.org rather than the global jooble.org domain.
Fix: Configured base_url in config/sources.yaml and pipeline/sources/jooble.py to https://in.jooble.org/api.
Commit: pending
Next time: Verify regional domain bindings when working with international aggregator partner keys.

## 2026-11-17 16:39  Candidate Greenhouse tokens failed with HTTP 404
Symptom: 28 out of 43 initial Indian startup candidate tokens (e.g. postman, razorpay, swiggy, cred) returned HTTP 404 from boards-api.greenhouse.io.
Root cause: Those organizations use alternative ATS providers or customized enterprise board slugs rather than public greenhouse.io tokens.
Fix: Created an automated validation probe and discovered 32 confirmed, active companies hiring in India with public Greenhouse boards.
Commit: pending
Next time: Probe ATS endpoints against public lists before hardcoding company board tokens.

## 2026-11-17 17:10  Cached sample fallback caused synthetic duplication across all queries
Symptom: All 48 Jooble queries reported 20 posts and Greenhouse boards returned 2 posts each in dev mode.
Root cause: Missing query-specific cache files caused adapters to fall back to jooble_sample.json and greenhouse_sample.json for every query and board.
Fix: Removed fallback to sample stubs. Configured adapters so that in cache mode, missing files log a cache miss and return zero posts. Each query writes its own discrete cache file immediately upon live receipt.
Commit: pending
Next time: Never fall back to a single shared fixture file when testing multi-query pagination pipelines.

## 2026-11-17 17:15  Httpx client logged Jooble API key in live request URLs
Symptom: Httpx default logger outputted full request URLs containing the Jooble API key at INFO level during live queries.
Root cause: Jooble API requires passing the key as a URL path segment, and httpx logs outgoing URLs by default when logger is set to INFO.
Fix: Suppressed httpx and httpcore loggers to WARNING level, and registered a RedactKeyFilter on the root logger to sanitize any occurrences of the key.
Commit: pending
Next time: Ensure third-party HTTP client loggers are silenced or filtered whenever sensitive tokens reside in URL paths.

## 2026-11-17 18:03  Missing standard module re import in pipeline run entrypoint
Symptom: Invoking python -m pipeline.run --stage filter crashed with NameError: name 're' is not defined.
Root cause: Added title regular expression audit logic to run_filter_stage in pipeline/run.py without importing re at module top.
Fix: Added import re to pipeline/run.py.
Commit: pending
Next time: Run static linting (ruff check) before invoking new CLI command stages.

## 2026-11-18 19:14  Entity-encoded HTML tags in Greenhouse descriptions escaped tag stripping
Symptom: Normalized descriptions from Greenhouse contained raw HTML tags like <h3> and <p>.
Root cause: Greenhouse payload was entity-encoded (&lt;h3&gt;). clean_text ran HTML_TAG_REGEX.sub before html.unescape, so tags were not stripped and were subsequently unescaped into raw HTML tags.
Fix: Updated clean_text in pipeline/normalize.py to loop unescape (up to 3 passes to handle double-encoding), strip scripts, styles, comments, and HTML tags, unescape once more, and normalize whitespace.
Commit: pending
Next time: Unescape HTML entities before running tag-stripping regular expressions.

## 2026-11-18 19:16  Overly broad single-word keywords falsely rejected real job posts
Symptom: 19 legitimate job posts (e.g. CA Article Trainees, Admission Counsellors at institutes, Junior Associate AR, Marine Engineers, Databricks engineers) were rejected with rule_reason not_a_job_post.
Root cause: Standalone words admission, cohort, and course in not_job_keywords matched on general phrases like "patient admission", "admission control", "cohort analysis", "CA course", and "during the course of employment".
Fix: Removed single words admission, cohort, and course from not_job_keywords. Replaced them with specific multi-word program advertising patterns (admissions open, join our cohort, certification course), and added title role exemptions for real occupations (e.g. article trainee, admission counsellor, telecaller, customer success manager, associate ar, marine engineer).
Commit: pending
Next time: Never use broad common nouns as standalone rejection keywords; require phrase-level context for non-job classification.

## 2026-11-18 19:20  Unit test for UsageCounter failed due to live Supabase DB query
Symptom: test_usage_counter_not_incremented_on_cache_hit failed with assert 2 == 0.
Root cause: UsageCounter.__init__ fell back to os.environ.get("SUPABASE_DB_URL") when db_url was not provided, connecting to the real DB table instead of isolating to the temporary test file.
Fix: Added use_db=False parameter to UsageCounter and updated unit tests to disable DB access for isolated tests.
Commit: pending
Next time: Explicitly isolate test dependencies from environment variables connecting to remote services.

## 2026-11-19 08:45  Role Taxonomy Drift in Tagging Prompt v2 and Model Aliasing
Symptom: In benchmark scoring, all models produced role classifications "human_resources" and "operations_supply_chain" which mismatched ground truth labels (hr_recruitment, operations_logistics), while JSON validity incorrectly reported 100%.
Root cause: During prompt v2 drafting, role definition keys were added as human_resources, finance_accounting, and operations_supply_chain instead of canonical taxonomy enum values. Role enum in pipeline/llm/base.py was also given temporary aliases for these strings, so Pydantic passed them without validation errors.
Fix: Restored Role enum to strictly the 22 canonical taxonomy roles in base.py and taxonomy.yaml. Created tag_v3.txt with correct canonical names (hr_recruitment, finance_banking, operations_logistics). Updated repair prompt to explicitly restate the allowed enum lists for role, city, and post_type on validation failure.
Commit: pending
Next time: Never introduce model-level enum aliases that drift from the database schema CHECK constraints and ground-truth taxonomy.

## 2026-11-19 10:28  Database post_type CHECK Constraint Rejected Valid Taxonomy Enums
Symptom: Schema check constraint jobs_post_type_check only permitted values 'job' and 'internship', risking constraint violation for valid posts with post_type 'trainee' or non-job classifications.
Root cause: The initial database schema definition restricted post_type to ('job', 'internship') while the application PostType enum and benchmark posts included 'trainee', 'fellowship', 'course_or_workshop', 'event', and 'other'.
Fix: Updated jobs_post_type_check in db/schema.sql to allow all seven taxonomy post_type values ('job', 'internship', 'trainee', 'fellowship', 'course_or_workshop', 'event', 'other') or NULL. Applied the schema to Supabase and added unit tests in tests/test_bootstrap.py.
Commit: pending
Next time: Align database schema check constraints directly with the application enums from day one.

