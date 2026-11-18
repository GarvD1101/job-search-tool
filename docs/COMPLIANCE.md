# Source Compliance and Terms Log

Before adding any data source to the ingestion pipeline, it must be documented here and approved by the project owner.

## Jooble API

- Source Type: Official Partner REST API
- Target Regional Endpoint: https://in.jooble.org/api/{api_key}
- Documentation and Terms URL: https://jooble.org/api/about
- robots.txt Check Date: 2026-11-17
- Ingestion Method: POST requests with JSON payload (keywords, location, page)
- Observed Page Size: Exactly 20 jobs returned per page
- Rate Limits and Quotas: Total budget 100 requests per day (daily cron capped at 60, local development capped at 40, enforced by disk cache and data/usage_counter.json)
- Attribution Requirement: Always link back to the original post on Jooble and display the Jooble source badge in UI
- Contact Header: User-Agent set to fresher-radar/0.1 with contact email
- Redaction Requirement: The API key is in the URL path and must be redacted as <REDACTED> in all logs, cache file names, exceptions, and documentation
- Status: Approved

## Greenhouse Public Job Boards

- Source Type: Public ATS Job Board Endpoints
- Base API Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
- Documentation and Terms URL: https://boards-api.greenhouse.io/
- robots.txt Check Date: 2026-11-17
- Ingestion Method: GET requests to public board vacancy lists for authorized hiring companies
- Rate Limits and Quotas: Spaced with polite delays (0.2 seconds between boards) and exponential backoff on HTTP 429
- Filtering Policy: Only store posts with location in India, or remote postings explicitly open to India
- Attribution Requirement: Always link directly to original job posting URL and display company name and source badge
- Contact Header: User-Agent set to fresher-radar/0.1 with contact email
- Verified Board Tokens: 32 companies verified with live India postings in config/sources.yaml
- Status: Approved
