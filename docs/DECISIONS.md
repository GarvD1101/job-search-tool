# Architectural Decisions and Approved Deviations

This document logs approved architectural decisions and plan deviations.

## 2026-11-17  Groq Model Scope, API Verification, and Token Budget Guard

This amendment overrides earlier amendments 2 and 4 regarding Groq candidate models and rate limits.

### 1. Live Groq Model Query
A live query was executed via `GET https://api.groq.com/openai/v1/models` using the configured `GROQ_API_KEY` (never logged or printed).

Result: Exactly 11 models returned for the account:
- Eligible Chat Models (Candidates):
  - `openai/gpt-oss-20b`
  - `openai/gpt-oss-120b`
  - `qwen/qwen3.8-27b`
- Non-candidate Models:
  - `allam-2-7b` (Arabic-focused language model, not suitable for India fresher tagging)
  - `meta-llama/llama-prompt-guard-2-22m` (prompt security classifier)
  - `meta-llama/llama-prompt-guard-2-86m` (prompt security classifier)
  - `openai/gpt-oss-safeguard-20b` (content moderation classifier)
  - `canopylabs/orpheus-arabic-saudi` (specialized model)
  - `canopylabs/orpheus-v1-english` (specialized model)
  - `whisper-large-v3` (audio transcription)
  - `whisper-large-v3-turbo` (audio transcription)
- Llama Chat Models:
  - Models such as `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, and `llama-4-scout` are absent from the account. They are removed from the plan.

### 2. Benchmark Candidates
The benchmark candidates are exactly:
1. `openai/gpt-oss-20b`
2. `openai/gpt-oss-120b`
3. `qwen/qwen3.8-27b`

### 3. Free-tier Limits
Verified in developer console and recorded in `config/pricing.yaml`:
- Requests per minute (RPM): 30
- Requests per day (RPD): 1,000
- Tokens per minute (TPM): 8,000
- Tokens per day (TPD): 200,000
These limits apply independently per model.

### 4. Token Budget Guard and Pending Queue
- Token usage per model per day is aggregated from the `llm_calls` table.
- Tagging terminates when daily token usage reaches 80 percent of the daily limit (160,000 tokens per day).
- Untagged posts receive status `pending_tag` in the `jobs` table and are processed on the subsequent run, oldest first.
- The user interface displays tagged posts only; the `/stats` endpoint reports the count of posts with status `pending_tag`.
- The provider client enforces a per-minute token throttle and exponential backoff on HTTP 429 status codes.

### 5. Token Reduction Protocol
- Batch size: 10 posts per call.
- Description truncation: Truncated to 600 characters for the tagging prompt (since aggregator snippets are compact).
- Reasoning parameters: Set `reasoning_effort: low` for GPT-OSS reasoning models. Disable thinking on Qwen if supported.
- Reasoning token logging: Reasoning tokens are logged in a dedicated `reasoning_tokens` column in `llm_calls`, as they count against output quotas.

### 6. Official List Pricing
Verified on the official Groq pricing documentation as of 2026-11-17:
- `openai/gpt-oss-20b`: $0.075 input / $0.30 output per 1M tokens.
- `openai/gpt-oss-120b`: $0.15 input / $0.60 output per 1M tokens.
- `qwen/qwen3.8-27b`: $0.80 input / $4.00 output per 1M tokens.

### 7. Development Discipline
- Dry runs using the live Groq API are strictly limited to at most 50 posts and logged, protecting the shared daily budget.
- MockProvider is utilized for test suites, CI, and high-volume dry runs.

---

## 2026-11-17  Step 2 Plan Amendments Approved by Owner

1. LLM Provider Scope:
   - Primary LLM provider is Groq.
   - Provider interface supports MockProvider and GroqProvider.
   - Gemini provider is not implemented unless explicitly requested later.

2. Source Scope:
   - Jooble API is the primary aggregator.
   - Greenhouse public job boards (approximately 30 Indian-hiring companies) serve as the second source.
   - Lever, Ashby, Careerjet, and Adzuna adapters are deferred unless requested.
   - Phase 1 gate target adjusted to at least 300 raw posts across 2 sources.
   - Definition of done requires 200+ unique valid fresher posts across 2 sources.

3. Repository Secrets:
   - Required repository secrets for GitHub Actions: JOOBLE_API_KEY, GROQ_API_KEY, SUPABASE_DB_URL.
   - Keys must never be committed to repository files or printed in logs.

4. Database Security and Row Level Security:
   - Row Level Security (RLS) enabled on all tables (runs, raw_posts, jobs, llm_calls) with zero policies.
   - Prevents unauthorized reads via PostgREST / public Data API.
   - Ingestion pipeline connects directly via Postgres owner role over the Supabase Session pooler (port 5432).
