# Fresher Job Search Tool

A live web tool for Indian freshers. It collects real entry-level job and internship posts from public sources, eliminates duplicates, tags roles and cities using an LLM, and displays them on a searchable interface that refreshes daily.

[![CI](https://github.com/GarvD1101/job-search-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/GarvD1101/job-search-tool/actions/workflows/ci.yml)

## Live Deployment

- Web application: TBD (deployed on Vercel in Phase 5)
- Automated daily refresh: Visible under GitHub Actions workflows

## Architecture

```
Sources (Jooble API + Greenhouse public boards)
   -> fetch (adapters, disk cache, request rate limits)
   -> normalise (canonical job fields, strip recruiter contacts)
   -> rule filter (fresher criteria, India check, post type)
   -> dedup (exact key, then fuzzy cross-source matching)
   -> LLM tagging (Groq batching, response caching, taxonomy validation)
   -> Postgres database (Supabase Session pooler)
   -> Next.js on Vercel (search, filters, statistics, cost breakdown)
```

## Three Measured Numbers

1. Tagging Accuracy: Hand-evaluated against 50 blind-labeled posts in eval/labels.csv (measured via scripts/score.py).
2. Cost per 1,000 Posts: Calculated from logged LLM tokens and official Groq list prices.
3. Refresh Reliability: Automated daily run logs recorded in the runs database table.

## Getting Started

### Prerequisites

- Python 3.12
- PostgreSQL instance (Supabase Session pooler on port 5432)

### Setup

1. Clone the repository:
   ```powershell
   git clone https://github.com/GarvD1101/job-search-tool.git
   cd job-search-tool
   ```

2. Create and activate a Python 3.12 virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   pip install -e ".[dev]"
   ```

4. Configure environment variables in .env (see .env.example):
   ```
   JOOBLE_API_KEY=...
   GROQ_API_KEY=...
   SUPABASE_DB_URL=...
   CONTACT_EMAIL=...
   ```

5. Apply database schema:
   ```powershell
   python scripts/apply_schema.py
   ```

6. Run tests and linting:
   ```powershell
   python scripts/check_secrets.py
   ruff check .
   pytest
   ```
