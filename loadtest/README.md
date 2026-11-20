# Load Testing Guide

This directory contains the k6 load testing suite for Fresher Radar.

## Safety Notice
Never run stress or load tests against the live free-tier deployment on Vercel or Supabase. Load tests must run strictly against a local production build (`next start`) with a local database or isolated staging database.

## Prerequisites

Install k6:
- Windows (winget):
  ```powershell
  winget install k6 --source winget
  ```
- Windows (choco):
  ```powershell
  choco install k6
  ```
- macOS (Homebrew):
  ```bash
  brew install k6
  ```
- Linux (Debian/Ubuntu):
  ```bash
  sudo gpg -k
  sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
  echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
  sudo apt-get update
  sudo apt-get install k6
  ```

## Test Plan Structure (`search.js`)

The test simulates realistic fresher job searches with a mix of:
- Text search queries ("developer", "intern", "analyst", "engineer", "trainee", etc.)
- Role filters (`software_dev`, `data_analytics`, `marketing`, `sales_bd`, etc.)
- City filters (`bengaluru`, `pune`, `hyderabad`, `mumbai`, `delhi_ncr`, `remote`, etc.)
- Pagination (pages 1 to 4)
- Traffic split: 70% API requests (`/api/jobs`), 30% Server-Side Rendered HTML pages (`/`)
- User think time: 0.5s to 1.5s randomized between requests

### Test Stages
1. Smoke: 5 concurrent virtual users for 1 minute.
2. Load: 50 concurrent virtual users for 3 minutes.
3. Ramp-down: Scales down to 0 users over 30 seconds.

### Performance Thresholds
- `http_req_duration`: 95th percentile latency must be under 500 ms (`p(95) < 500ms`).
- `http_req_failed`: Error rate must be under 1 percent (`rate < 0.01`).

## Execution Instructions

> **Network Latency Note**:
> When running tests against the live deployment from a local workstation in Delhi, measured HTTP response latencies include international network transit time (approximately 120 ms to 160 ms round trip) to the Tokyo-hosted Supabase PostgreSQL database (`ap-northeast-1`) and Vercel edge deployment.

1. **Smoke Test against Live Deployment** (5 concurrent users for 1 minute):
   ```powershell
   k6 run --vus 5 --duration 1m -e BASE_URL=https://job-search-tool-rho.vercel.app --summary-export docs/results/k6_smoke_live.json loadtest/search.js
   ```

2. **Reduced Load Test against Live Deployment** (20 concurrent users for 2 minutes):
   ```powershell
   k6 run --vus 20 --duration 2m -e BASE_URL=https://job-search-tool-rho.vercel.app --summary-export docs/results/k6_reduced_live.json loadtest/search.js
   ```

3. **Full Profile Stress Test on Local Production Build** (50 concurrent users for 3 minutes):
   Start the local production server:
   ```powershell
   cd web
   pnpm run build
   pnpm run start
   ```
   Execute the full load profile in a separate shell:
   ```powershell
   k6 run --vus 50 --duration 3m -e BASE_URL=http://localhost:3000 --summary-export docs/results/k6_full.json loadtest/search.js
   ```
