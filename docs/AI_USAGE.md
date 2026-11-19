# AI Usage Log: Fresher Radar

Record of AI collaboration, delegation boundaries, prompt version iterations, failure analyses, and lessons learned.

## 1. Tools and Division of Responsibility

Development of Fresher Radar combined high-level strategic reasoning with automated agent execution:

### Claude (Anthropic)
- **Role**: Architecture advisory, phase boundary planning, compliance review, and debugging diagnosis.
- **Responsibilities**:
  - Validated adherence to strict non-scraping rules and API quota limits.
  - Advised on Postgres row-level security and decoupled direct-connection architecture.
  - Diagnosed complex edge cases including title-word boundary false positives and entity double-encoding.
  - Advised on evaluation methodology, including blind evaluation protocols and role family grouping.

### Antigravity (Google DeepMind Coding Agent)
- **Role**: Hands-on coding agent, database migration author, automated test executor, and benchmark runner.
- **Responsibilities**:
  - Implemented source adapters for Jooble API and Greenhouse public boards.
  - Built normalization, regex cleaning, and deduplication engine (shingle Jaccard and canonical keys).
  - Authored database migrations, invariant checks, and connection pooler integrations.
  - Implemented Next.js App Router front-end, caching layers, and search API routes.
  - Generated unit tests, dry pipeline benchmarks, failure injection tests, and scale stress tests.

---

## 2. Delegation Log: Human-Directed vs Agent-Delegated

| Stage / Component | Owner (Garv) Direction | Agent (Antigravity) Execution |
|---|---|---|
| **Compliance & Sources** | Approved Jooble and Greenhouse. Forbid LinkedIn, Naukri, Indeed scraping. Set 100 req/day cap. | Implemented token-bucket rate limiters and disk caching in adapters. |
| **Database Architecture** | Chose direct Postgres over vendor SDK; mandated row identity `UNIQUE (source, source_id)`. | Wrote schema.sql, connection pooling logic, migration scripts, and invariant checks. |
| **Filtering Engine** | Defined 0-1 year experience threshold; specified multi-word phrase matching over broad keywords. | Wrote regex patterns, test fixtures, and HTML sanitization routines. |
| **Evaluation Ground Truth** | Hand-labeled 50 blind samples in Excel without seeing model predictions. | Wrote XLSX OpenXML parser, scoring scripts, and confusion matrix generators. |
| **Model Selection** | Selected Groq candidate models and mandated list-price cost projections. | Built provider interfaces, 429 exponential backoff, and repair prompt retry logic. |
| **Front-End & UX** | Mandated clean, fast, mobile-first Next.js UI with zero decorative animations. | Implemented responsive layout, search filters, pagination, and ISR caching. |

---

## 3. Prompt Version Evolution

All prompts reside in `pipeline/llm/prompts/`. Prompts are strictly versioned and immutable once evaluated.

| Version | Date | Changes Made | Rationale | Benchmark Role Accuracy |
|---|---|---|---|---|
| **tag_v1.txt** | 2026-11-17 | Initial zero-shot tagging prompt listing 22 role and 11 city enum identifiers. | Baseline evaluation across candidate models. | 76.0% (gpt-oss-20b) |
| **tag_v2.txt** | 2026-11-18 | Added short explanatory definitions for each role taxonomy enum. | Reduce ambiguity between overlapping roles (e.g., software_dev vs it_devops_security). | Model hallucinated aliased role names (human_resources, operations_supply_chain). |
| **tag_v3.txt** | 2026-11-19 | Fixed alias drift back to canonical taxonomy enums; added repair retry prompt with allowed enums. | Enforce strict schema conformity and eliminate unmapped strings. | 82.0% (gpt-oss-20b) |
| **tag_v4.txt** | 2026-11-19 | Aligned verbatim role definitions with exact project specification. | Consistent role scope across all three candidate models. | 83.7% (gpt-oss-20b, with row 36 excluded from role only) |

---

## 4. What Broke Because of AI (and How It Was Caught)

Using automated coding agents introduces risks of subtle drift, over-eager assumptions, and unintended side effects. The following issues occurred directly from AI assistance and were caught through strict validation:

### 1. Model Taxonomy Drift and Silent Aliasing (tag_v2)
- **What happened**: When drafting prompt v2, the agent added definitions using descriptive keys like `human_resources` and `operations_supply_chain` rather than canonical enums `hr_recruitment` and `operations_logistics`. To make tests pass, the agent added string aliases in the Pydantic model, masking the drift.
- **How it was caught**: Strict cross-model evaluation against human ground truth in `eval/sample_50_labeled.xlsx` flagged that models were scoring lower due to unmapped enum strings.
- **Remedy**: Removed all aliases from Pydantic models. Replaced prompt with tag_v3 using canonical enum names. Implemented schema check constraints and repair prompts.

### 2. Missing Database CHECK Constraints
- **What happened**: The agent initially created `jobs.post_type` with a constraint allowing only `'job'` and `'internship'`, ignoring that the taxonomy and frozen benchmark sample contained `'trainee'`, `'fellowship'`, and non-job categories.
- **How it was caught**: Unit tests inserting valid trainee rows failed with Postgres check constraint violations.
- **Remedy**: Expanded `jobs_post_type_check` in `db/schema.sql` to cover all seven taxonomy values or NULL, and added comprehensive constraint tests.

### 3. Entity Identity Hash Collision on Lifecycle Transitions
- **What happened**: The agent initially constructed `canonical_key` as `sha1(company|title|city)` for survivors and `sha1(rej|source|source_id)` for rejects. When a post expired after 45 days, the re-evaluation generated a reject key and inserted a new row rather than updating the existing row.
- **How it was caught**: Audit query revealed 1,489 rows in `jobs` compared to 1,481 `raw_posts` (8 duplicate rows).
- **Remedy**: Migrated table identity to `UNIQUE (source, source_id)`. Created `dedup_key` as a non-unique clustering attribute and added automated database invariant checks.

### 4. Uncached Database Call in Global Layout
- **What happened**: The agent rendered `Header.tsx` as a server component calling `getLastRefresh()` directly against the Supabase database in Tokyo on every request.
- **How it was caught**: Local web performance benchmarks showed warm requests taking ~200 ms despite cached job query results.
- **Remedy**: Wrapped `getLastRefresh()` and `/api/jobs` in Next.js `unstable_cache` with 300-second revalidation tags. Warm latency dropped to 62.3 ms for HTML and 7.6 ms for API responses.

---

## 5. Lessons for AI-Assisted Engineering

1. **Keep schemas and enums authoritative**: Never let an LLM or prompt draft dictate your taxonomy; anchor data structures in code and database constraints.
2. **Never accept estimated metrics**: Measure tokens, latency, and throughput with instrumented scripts rather than letting agents guess.
3. **Guard tests against the network**: Mock external providers in CI and dry runs so tests remain deterministic, fast (< 60s), and budget-safe.
