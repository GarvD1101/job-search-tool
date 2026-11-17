# Source Compliance and Terms Log

Before adding any data source to the ingestion pipeline, it must be documented here and approved by the project owner.

## Jooble API

- Source Type: Official Partner REST API
- Documentation and Terms URL: https://jooble.org/api/about
- robots.txt Check Date: 2026-11-17
- Ingestion Method: POST requests to official JSON API endpoint
- Rate Limits and Quotas: Total budget 100 requests per day (cron limited to 60, local development limited to 40, enforced by disk cache and local counter)
- Attribution Requirement: Always link back to the original post on Jooble and display the Jooble source badge in UI
- Contact Header: User-Agent set to fresher-radar/0.1 with contact email
- Status: Approved

## Greenhouse Public Job Boards

- Source Type: Public ATS Job Board Endpoints
- Documentation and Terms URL: https://boards-api.greenhouse.io/
- robots.txt Check Date: 2026-11-17
- Ingestion Method: GET requests to public board vacancy lists for authorized hiring companies
- Rate Limits and Quotas: 50 requests per day, spaced with exponential backoff
- Attribution Requirement: Always link directly to original job posting URL
- Contact Header: User-Agent set to fresher-radar/0.1 with contact email
- Status: Approved
