# Fresher Radar — Industrial Swiss Grid UI/UX Overhaul Spec

> **Agent Execution Prompt:** Read this entire specification, inspect the existing `app/`, `components/`, and `tailwind.config.*` files to preserve all PostgreSQL queries and URL `searchParams`, and execute Phases 1–7 sequentially.

---

## 1. Objective & Non-Negotiable Constraints

Redesign **Fresher Radar** (`/`, `/stats`, `/costs`) into an **Industrial Swiss Grid / Technical Spec Sheet** interface (inspired by Braun industrial design, Teenage Engineering, and Bloomberg Light). The interface must communicate high-signal systems engineering with zero "AI template" artifacts.

* **Stack (Do Not Change):** Next.js `14.2.18` (App Router, RSC), React `18.3.1`, Tailwind CSS `^3.4.14`, TypeScript `^5.6.3`, `pg` `^8.13.1`.
* **Zero UI Libraries:** Do **not** install `shadcn/ui`, Radix, Lucide, Heroicons, Recharts, Tremor, or Framer Motion. Build all components, drawers, tabs, proportional bars, and 1.5px-stroke icons using native HTML, Tailwind utilities, and inline SVGs.
* **Preserve Backend & Data Integrity:** Do **not** alter SQL queries, `pg` pooling logic, database schemas, or server-side caching intervals unless strictly required to pass an existing field to a component. Keep pages as React Server Components and isolate interactivity into small, focused `'use client'` leaf components (`JobExplorer`, `JobDetailDrawer`, `CostSimulator`).
* **Anti-Slop Visual Rules:**
  * **No** gradients, glassmorphism, `backdrop-blur` cards, purple/indigo accents, or large drop shadows (`shadow-lg`/`shadow-xl`).
  * **No** `rounded-xl`/`rounded-2xl` pill cards. Use sharp structural geometry: `rounded-none` for grid cells/tables and `rounded-[2px]` max for buttons, inputs, and micro-badges.
  * **No** double borders. Use collapsed 1px hairline grids (`gap-px bg-[#D4D4CE] border border-[#D4D4CE]`) so cells share crisp 1px rules.
  * **All numeric values** (counts, percentages, tokens, dollar figures, dates, pagination) must use `font-mono tabular-nums whitespace-nowrap`.

---

## 2. Phase 1 — Design System & Typography Setup

### 2.1 Color Tokens

| Token | Hex | Tailwind Usage | Strict Role |
| :--- | :--- | :--- | :--- |
| **Canvas** | `#F4F4F0` | `bg-canvas` | Page drafting-board background, recessed table headers |
| **Surface** | `#FFFFFF` | `bg-surface` | Primary data cells, filter rail, drawer, active cards |
| **Surface Muted** | `#ECECE6` | `bg-surface-muted` | Row hover state, bar track backgrounds |
| **Gridline** | `#D4D4CE` | `border-grid / bg-grid` | Exposed 1px structural dividers & table rules |
| **Gridline Strong** | `#1A1A1A` | `border-ink` | Active focus borders, primary structural top rules |
| **Ink Primary** | `#111111` | `text-ink` | Primary headings, titles, key metrics |
| **Ink Secondary** | `#4A4A45` | `text-ink-secondary` | Body snippets, secondary labels |
| **Ink Muted** | `#73736C` | `text-ink-muted` | Micro-labels (`01 //`), timestamps, footnotes |
| **Accent (SAE/ECE Amber)** | `#FF7E00` | `bg-amber-signal / text-amber-signal` | Active nav underline, primary CTA, baseline row highlight, key engineering metrics |
| **Accent Wash** | `#FFF5EB` | `bg-amber-wash` | Subtle tint for baseline rows & active filter pills |
| **Status Live** | `#15803D` | `text-status-live / bg-status-live` | Live indicator dot & verified direct-ATS micro-tag only |
| **Status Reject** | `#B91C1C` | `text-status-reject` | Rule-rejection audit indicators only |

### 2.2 Font Configuration (`app/layout.tsx` & `tailwind.config.ts`)

Load `IBM_Plex_Sans` (weights `400`, `500`, `600`, `700`) and `IBM_Plex_Mono` (weights `400`, `500`, `600`) via `next/font/google`, attach CSS variables `--font-plex-sans` and `--font-plex-mono` to `<html>`, and configure `tailwind.config.ts`:

```ts
// tailwind.config.ts (extend block)
theme: {
  extend: {
    fontFamily: {
      sans: ['var(--font-plex-sans)', 'system-ui', 'sans-serif'],
      mono: ['var(--font-plex-mono)', 'ui-monospace', 'monospace'],
    },
    colors: {
      canvas: '#F4F4F0',
      surface: '#FFFFFF',
      'surface-muted': '#ECECE6',
      grid: '#D4D4CE',
      ink: {
        DEFAULT: '#111111',
        secondary: '#4A4A45',
        muted: '#73736C',
      },
      amber: {
        signal: '#FF7E00',
        hover: '#E06F00',
        wash: '#FFF5EB',
      },
      status: {
        live: '#15803D',
        reject: '#B91C1C',
      },
    },
  },
}
```

### 2.3 Section Micro-Header Pattern

Every major section across all three pages uses a standardized Swiss spec-sheet header bar:
* **Format:** `01 // SECTION TITLE` in `font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted`, paired with an optional right-aligned mono subtitle or status stamp, separated from content by `border-b border-grid`.

---

## 3. Phase 2 — Display-Layer Data Sanitization (`src/lib/formatters.ts`)

Create a pure TypeScript utility module to fix every raw-data artifact currently visible in the UI without touching the underlying PostgreSQL tables:

1. **`formatLocation(raw: string): string`**
   * Fixes duplicate city strings like `Mumbai (Mumbai)`, `Chennai (Chennai)`, `Kolkata (Kolkatta)`, `India (India)`, and `Bengaluru (Bangalore)`.
   * Logic:
     * Parse `"Primary (Secondary)"`.
     * Fix known typos (`Kolkatta` -> `Kolkata`, `Bangalore` -> `Bengaluru`).
     * If normalized `Primary === Secondary` (case-insensitive) or `Secondary` is an alias of `Primary` (`Bengaluru`/`Bangalore`, `Delhi NCR`/`Delhi`), return `Primary` only.
     * Preserve meaningful sub-locations like `Mumbai (Kharghar)` -> `Mumbai · Kharghar` and `Hyderabad (Secunderabad)` -> `Hyderabad · Secunderabad`, or `Remote (work from home)` -> `Remote`.
2. **`cleanJobSnippet(raw: string): string`**
   * Fixes raw scraper artifacts currently leaking onto cards: leading ellipses `..Overview`, markdown hashes `# Position Overview`, duplicated phrases like `No experience required No experience required`, and mangled contact masks `(***) )`.
   * Logic: Strip leading dots/bullets/hashes (`^[\.\s#•\-]+`), collapse repeated adjacent phrases (`\b(.{10,40}?)\s+\1\b` case-insensitive), remove empty/broken phone masks `\(\*+\)\s*\)?`, collapse excess whitespace, and trim cleanly.
3. **`formatUsd(amount: number, decimals = 2): string`**
   * Fixes the inverted currency formatting (`10.59$`) and line-wrapped currency symbols (`256.52` followed by `$` on a new line) in the Serving Scenarios table.
   * Always return strictly prefixed `$` strings (e.g., `$10.59`, `$256.52`, `$0.0043`) and render every currency cell with `font-mono tabular-nums whitespace-nowrap`.
4. **`formatRejectionReason(rawKey: string): { code: string; label: string; groupKey: string }`**
   * Fixes raw backend keys (`seniority`, `experience_required`, `stale`, `unclear_fresher_fit`, `not_a_job_post`, `min_1_year_experience`, `not_india`) and raw dedup hashes (`tier2_fuzzy_match_of_dfa2d9c0`) leaking into `/stats`.
   * Map known keys to crisp human labels + monospace telemetry codes:
     * `seniority` -> `{ groupKey: 'seniority', code: 'SENIORITY', label: 'Senior / Mid-Level Role' }`
     * `experience_required` -> `{ groupKey: 'experience_required', code: 'EXP_REQ', label: 'Prior Experience Required' }`
     * `min_1_year_experience` -> `{ groupKey: 'min_1_year_experience', code: 'MIN_1YR', label: 'Minimum 1+ Year Specified' }`
     * `stale` -> `{ groupKey: 'stale', code: 'STALE_POST', label: 'Expired / Stale Listing' }`
     * `unclear_fresher_fit` -> `{ groupKey: 'unclear_fresher_fit', code: 'UNCLEAR_FIT', label: 'Unclear Entry-Level Fit' }`
     * `not_a_job_post` -> `{ groupKey: 'not_a_job_post', code: 'NON_JOB', label: 'Non-Job Content' }`
     * `not_india` -> `{ groupKey: 'not_india', code: 'NON_INDIA', label: 'Outside India' }`
     * Regex `/^tier2_fuzzy_match_/i` -> aggregate all matches into `{ groupKey: 'tier2_fuzzy_match', code: 'FUZZY_DUP', label: 'Tier-2 Fuzzy Duplicate' }` (summing their counts).
5. **`normalizeOriginBoard(raw: string): string`**
   * Consolidates split board names like `greenhouse` and `boards.greenhouse.io` under a clean display label (`boards.greenhouse.io (Direct ATS)`), while summing counts in the `/stats` display transform.
6. **`getCompanyMonogram(company: string): string`**
   * Returns 1–2 uppercase initials (e.g., `Playto Labs` -> `PL`, `Enterpret` -> `EN`) for sharp `28x28px` technical company badges.

---

## 4. Phase 3 — Global Chrome (`Header`, `Footer`, `Icons`)

### 4.1 Inline Icon Set (`src/components/Icons.tsx`)
Create lightweight, 14px–16px inline SVGs (`strokeWidth={1.75}`, crisp square linecaps) for: `Search`, `ArrowUpRight` (replaces inconsistent `Open original -` / `Open original →` text arrows), `X`, `SlidersHorizontal`, `ChevronLeft`, `ChevronRight`, `Check`, `ExternalLink`, `Activity`, `Layers`, `Cpu`.

### 4.2 Sticky Telemetry Header (`Header.tsx`)
* **Container:** Full-width `sticky top-0 z-30 bg-surface border-b border-grid`. Max-width `max-w-[1380px] mx-auto px-4 sm:px-6 h-14`.
* **Left:** Brand lockup — sharp `10px x 10px` `#FF7E00` square mark + `FRESHER RADAR` (`font-mono text-sm font-semibold tracking-tight text-ink`) + hidden-on-mobile vertical hairline + `IND // 0–1 YRS` micro-tag.
* **Center:** Unified 3-tab navigation with zero label mismatch:
  * `01 LIVE JOBS` (`/`)
  * `02 STATS` (`/stats`)
  * `03 COSTS` (`/costs`)
  * **Active State:** `text-ink font-semibold` with a full-height `border-b-2 border-amber-signal` flush against the header bottom border.
* **Right:** Compact system status pill — `6px` square `#15803D` dot + `SYNCED` + timestamp (e.g., `19 Nov, 17:34 IST`) in `font-mono text-[11px] text-ink-muted tabular-nums`.

### 4.3 Aligned Footer (`Footer.tsx`)
* Fix the current nav/footer mismatch (where top nav says `Live Jobs | Stats | Costs` but footer says `Jobs | Pipeline | Stats`).
* Render a crisp top-bordered (`border-t border-grid bg-surface`) 2-row architectural colophon:
  * Left: `Fresher Radar` — Entry-level jobs & internships in India. Sources: Jooble API & Greenhouse public endpoints. Classifier: `openai/gpt-oss-20b`.
  * Right: Exact matching links `Live Jobs`, `Stats`, `Costs`.

---

## 5. Phase 4 — Page 1: Live Jobs (`/`)

Replace the current 2-column bulky card grid with a **Faceted Filter Rail + High-Velocity Spec-Sheet Feed + Slide-Over Detail Drawer**.

### 5.1 Top Command & Summary Bar
* Compact horizontal strip (`bg-surface border border-grid`) directly below the header:
  * Left: Page title (`LIVE FRESHER INDEX`) + crisp active count badge (`361 ACTIVE` in `bg-ink text-white font-mono text-xs px-2 py-0.5`).
  * Right: Full-width-on-mobile / `360px`-on-desktop search input (`Search title, company, or skill...`) with a mono `/` shortcut badge (`key === '/'` focuses the input when not typing).

### 5.2 Two-Pane Layout (`lg:grid lg:grid-cols-[260px_1fr] border border-grid bg-grid gap-px`)
Inspect existing `app/page.tsx` and `JobFilters.tsx` first to preserve exact URL query parameters (e.g., `q`, `role`, `city`, `type`, `page`) so deep links and server-side filtering remain 100% intact.

#### A. Left Faceted Filter Rail (`JobFilters.tsx`, Sticky on Desktop, Collapsible Drawer on Mobile)
* White surface (`bg-surface p-4`), sticky (`lg:sticky lg:top-14 lg:max-h-[calc(100vh-3.5rem)] lg:overflow-y-auto`).
* Sections separated by `border-b border-grid py-3`:
  1. **Active Filters Header:** Shows active filter count + `CLEAR ALL` button in `font-mono text-[11px] text-amber-signal` when any filter is applied.
  2. **Post Type (Quick Segmented Buttons):** `All`, `Job`, `Internship`, `Trainee` rendered as crisp 1px-bordered toggle tiles (active = `bg-ink text-white border-ink`).
  3. **Role Taxonomy:** Clean native `<select>` styled with `rounded-[2px] border-grid bg-canvas font-sans text-sm` **plus** top 6 quick-click role chips underneath for 1-click interview demos.
  4. **Metro Area / City:** Clean native `<select>` **plus** quick-click chips (`Bengaluru`, `Mumbai`, `Delhi NCR`, `Hyderabad`, `Pune`, `Remote`).
  5. **Direct Source Highlight:** Visual legend explaining `DIRECT ATS` (Greenhouse) vs `AGGREGATOR` (Jooble) badges.

#### B. Right Structured Job Spec-Sheet Feed (`JobFeed.tsx` + `JobRow.tsx`)
* **Feed Column Header Bar (`bg-canvas border-b border-grid px-4 py-2`):**
  * Displays `SHOWING 1–20 OF 361 VERIFIED POSITIONS` (`font-mono text-[11px] uppercase text-ink-muted`) on the left, and active page indicator (`PAGE 01 / 19`) on the right.
* **Structured Row Design (`JobRow.tsx`):**
  * Single-column stacked list (`divide-y divide-grid bg-surface`). Each row is clickable to open the preview drawer (`hover:bg-surface-muted/60 transition-colors cursor-pointer group`).
  * **Row Anatomy (3 crisp horizontal bands, zero clutter):**
    * **Top Line:**
      * Left: Sharp `28x28px` monogram square (`border border-grid bg-canvas font-mono text-[11px] font-semibold flex items-center justify-center`) + **Job Title** (`text-[15px] font-semibold text-ink group-hover:text-amber-signal`) + **Company Name** (`text-sm text-ink-secondary`).
      * Right: **Posted Recency** (`Today`, `2d ago` in `font-mono text-[11px] text-ink-muted tabular-nums`; if `Today`, add tiny `#FF7E00` dot).
    * **Middle Line (Sanitized Snippet):**
      * Single 2-line clamped (`line-clamp-2`) preview passed through `cleanJobSnippet()`, `text-[13px] leading-relaxed text-ink-secondary pl-10`.
    * **Bottom Telemetry Strip (`pl-10 flex flex-wrap items-center justify-between gap-2`):**
      * Left badges (sharp `rounded-[2px] border border-grid px-1.5 py-0.5 font-mono text-[11px]`):
        * **Location:** Cleaned via `formatLocation()` (e.g., `Bengaluru`, `Mumbai`, `Remote`).
        * **Role Taxonomy:** e.g., `Software Dev`, `Sales & BD`.
        * **Post Type:** Styled distinctly (`INTERNSHIP` in `bg-amber-wash text-ink border-amber-signal/40`, `TRAINEE` in `bg-canvas`, `JOB` in `bg-surface`).
        * **Source Domain:** e.g., `highlisted.com`, `internshala.com`; if Greenhouse, style as `GREENHOUSE · DIRECT ATS` with `border-status-live/40 text-status-live`.
      * Right actions: `INSPECT` text button + direct `<a target="_blank" rel="noopener noreferrer">` `OPEN ↗` link (`e.stopPropagation()` so clicking Apply opens immediately without toggling drawer).

#### C. Slide-Over Job Detail Drawer (`JobDetailDrawer.tsx`, Client Component)
* Opens when clicking any job row; closes on `Esc`, backdrop click, or `×` button.
* Fixed right panel (`fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-surface border-l border-ink flex flex-col`).
* **Header:** Monogram + Title + Company + Close button.
* **Spec Grid (`grid-cols-2 gap-px bg-grid border-y border-grid`):** 4 sharp metadata cells (`LOCATION`, `ROLE TAXONOMY`, `POST TYPE`, `SOURCE PORTAL`).
* **Body:** Full sanitized description (`cleanJobSnippet()`), plus a subtle mono disclaimer noting LLM classification by `openai/gpt-oss-20b`.
* **Sticky Footer:** Full-width `#FF7E00` (`hover:bg-amber-hover`) primary button: `OPEN ORIGINAL POSTING ↗` + secondary `COPY LINK` button.

### 5.3 Precision Pagination (`Pagination.tsx`)
* Hairline-bordered footer bar below the feed: `[ ← PREV ]` | `PAGE 01 OF 19` (`font-mono tabular-nums`) | `[ NEXT → ]`. Disable boundary buttons cleanly with `opacity-40 cursor-not-allowed`.

---

## 6. Phase 5 — Page 2: Pipeline & System Stats (`/stats`)

Transform `/stats` into a 5-section **Numbered Telemetry Console** that visually tells the filtering/cost-control story at a glance and allows **cross-page drilldowns** into Live Jobs.

### `01 // CORE TELEMETRY` (4-Column Collapsed Hairline KPI Strip)
`grid grid-cols-2 lg:grid-cols-4 gap-px bg-grid border border-grid`:
1. **ACTIVE JOBS:** Verified 0–1 yr fresher roles
2. **RAW POSTS (7D):** 7-day rolling ingestion window
3. **DEDUPLICATED:** 2-tier dedup engine
4. **BYPASSED LLM:** Highlighted in `text-amber-signal` with subtle top accent border (`border-t-2 border-t-amber-signal`); Sub-label: `Filtered free before LLM API`

### `02 // INGESTION & FILTERING FUNNEL` (Pure CSS Horizontal Visual)
* Full-width white module (`border border-grid bg-surface p-5`) showing how raw posts narrow down to active verified jobs:
  * Compute segment widths dynamically from live DB numbers (Rule-Rejected before LLM, Deduplicated, LLM-Filtered/Other, Active Verified Jobs).
  * Render a crisp `h-7 w-full flex gap-[2px]` segmented bar:
    * Active Jobs (`bg-amber-signal`)
    * Rule-Bypassed (`bg-ink`)
    * Deduplicated (`bg-[#73736C]`)
    * Remaining/LLM-Rejected (`bg-[#D4D4CE]`)
  * Render a clean 4-column mono legend directly beneath with exact counts and `% of raw`.

### `03 // LLM TOKEN LEDGER (openai/gpt-oss-20b)`
* 5-column horizontal hairline ledger (`grid-cols-2 sm:grid-cols-5 gap-px bg-grid border border-grid`) for:
  * `API CALLS`
  * `INPUT TOKENS`
  * `OUTPUT TOKENS`
  * `REASONING TOKENS`
  * `LIST-PRICE SPEND` (highlighted in `bg-amber-wash text-ink font-semibold`)
* Single-line mono footnote bar (`bg-canvas px-4 py-2 border-x border-b border-grid text-[11px] font-mono text-ink-muted`): Groq list pricing `$0.075/1M in · $0.30/1M out (reasoning billed as output)`.

### `04 // TAXONOMY, GEOGRAPHY & RULE AUDIT` (2-Column Proportional Bar Lists)
Build a reusable `<ProportionalBarList/>` component (pure Tailwind, zero chart libraries):
* Each row renders inside a `relative` container with an absolute background fill bar (`bg-canvas` or `bg-amber-wash` with `style={{ width: `${(count / maxCount) * 100}%` }}`), left-aligned label, and right-aligned `font-mono tabular-nums` count + `%`.
* Arrange into a crisp 2-column grid (`grid-cols-1 lg:grid-cols-2 gap-6`):
  1. **Active Jobs by Role Taxonomy (Interactive Drilldown):**
     * Display top 10 roles by default with a crisp `[ SHOW ALL ROLES ]` client toggle so the page doesn't stretch awkwardly.
     * **Each row is a `<Link>` to `/?role=<encodedRole>`** with a subtle `↗` on hover.
  2. **Active Jobs by Metro Area (Interactive Drilldown):**
     * **Each row is a `<Link>` to `/?city=<encodedCity>`**.
  3. **Posts Rejected by Rule Reason (Sanitized Audit):**
     * Pass every key through `formatRejectionReason()` so raw keys and dedup hashes render cleanly as `[SENIORITY] Senior / Mid-Level Role`, `[EXP_REQ] Prior Experience Required`, and `[FUZZY_DUP] Tier-2 Fuzzy Duplicate` with a subtle `bg-status-reject/10` proportional bar.
  4. **Source Platforms & Top Origin Boards:**
     * Top mini-split bar showing `Jooble` vs `Greenhouse`.
     * Proportional list of origin boards normalized via `normalizeOriginBoard()` (merging `greenhouse` and `boards.greenhouse.io` cleanly).

### `05 // PIPELINE EXECUTION LOG`
* Compact 3-cell hairline bar at the bottom (`grid-cols-1 md:grid-cols-3 gap-px bg-grid border border-grid`):
  * `TRIGGER COUNT`
  * `LATEST OVERALL RUN`
  * `SCHEDULED CADENCE`

---

## 7. Phase 6 — Page 3: Cost & Scale Projections (`/costs`)

Turn `/costs` into an interactive **FinOps Engineering Console** that fixes every table bug and proves the core architectural thesis live.

### `01 // CORE ARCHITECTURAL FINDING`
* High-contrast technical callout (`bg-surface border border-grid border-l-4 border-l-amber-signal p-5`):
  * Mono kicker: `01 // EXECUTIVE FINDING — LLM TAGGING VS INFRASTRUCTURE SCALE`
  * Crisp 2-sentence thesis: At `600` raw posts/day, LLM tagging costs `$0.38/mo` (`$4.66/yr`) on `openai/gpt-oss-20b`; database storage, connection poolers, and hosting scale with DAU and exceed `99%` of operating costs at scale.

### `02 // INTERACTIVE UNIT-ECONOMICS SIMULATOR` (`CostSimulator.tsx`, Client Component)
Place this directly above the reference tables using the exact deterministic model data already computed on `/costs`:
* **Control Strip (`grid-cols-1 md:grid-cols-3 gap-px bg-grid border border-grid`):**
  1. **User Scale (DAU):** Segmented buttons `1K` | `10K` | `100K` | `1M` (default: `10K`).
  2. **Daily Raw Volume:** Segmented buttons `200/d` | `600/d (Base)` | `2,000/d` (default: `600/d`).
  3. **Groq Tagging Model:** Segmented buttons `gpt-oss-20b` | `gpt-oss-120b` | `qwen3.8-27b` (default: `gpt-oss-20b`).
* **Live Output Strip (4-column KPI bar + Cost-Share Bar):**
  * Shows live computed **Monthly Total**, **Annual Total**, **LLM Share (`$/mo`)**, and **Cost per 1K DAU** (`font-mono tabular-nums`).
  * Below the KPIs: A full-width **LLM vs. Infrastructure Split Bar** (`h-4 flex w-full bg-canvas`) showing the exact percentage of monthly spend going to `LLM Tagging` (`bg-amber-signal`, minimum `3px` visible sliver when `<1%`) vs `Database + Hosting Infra` (`bg-ink`).

### `03 // SERVING TRAFFIC & COST MODELING SCHEMATIC`
* Clean **Horizontal Architectural Flow Diagram** (pure CSS boxes + crisp SVG right arrows, wraps neatly on mobile):
  * `[ USERS (DAU) ]` -> `[ 5 SEARCHES / SESSION ]` -> **Split Node:** `[ 80% EDGE CDN HIT ($0 DB) ]` & `[ 20% POSTGRES POOLER ]` -> `[ SUPABASE + VERCEL TIER COST ]`.
  * Footer strip noting `10 KB avg response payload · 218.25 in / 73.68 out tokens · 55.35% post-rule survivor rate`.

### `04 // PROJECTION MATRICES (FINANCIAL-GRADE TABLES)`
Both tables must be wrapped in `overflow-x-auto border border-grid bg-surface` with crisp headers (`bg-canvas text-[11px] font-mono uppercase tracking-wider text-ink-muted border-b border-grid`).

* **Table 1 — Pipeline Tagging Scenarios (LLM API Only):**
  * Strictly right-align every numeric column (`DAILY`, `WEEKLY`, `MONTHLY`, `ANNUAL`, `COST / 1K RAW`) with `font-mono tabular-nums whitespace-nowrap`.
  * Highlight the **`600/day · gpt-oss-20b`** baseline row with `bg-amber-wash` and an inline `BASELINE` micro-badge (`bg-amber-signal text-white font-mono text-[10px] px-1.5 py-0.5`).
  * Group volume tiers visually with a crisp `border-t-2 border-t-grid` between `200/day`, `600/day`, and `2000/day`.
* **Table 2 — Serving Scenarios (Full Stack: LLM + Database + Hosting):**
  * **Fix all currency formatting bugs:** Pass every value through `formatUsd()` with `whitespace-nowrap` so `$10.59` never renders as `10.59$` and `$256.52` never splits across lines.
  * **De-clutter Tier Columns:** Format `SUPABASE TIER` and `VERCEL TIER` cells cleanly in **2 compact lines max**:
    * Line 1 (bold mono): `Pro · $25/mo` (Supabase) / `Pro · $20/mo` (Vercel)
    * Line 2 (`text-[11px] text-ink-muted`): `8 GB DB · 250 GB egress` / `1 TB BW · 1K GB-hrs`
    * Move long disclaimers ("Personal non-commercial projects; commercial launch requires Pro") out of the table cells into a crisp `COMMERCIAL NOTE` callout directly below Table 2.

### `05 // VERIFIED PRICING SOURCES & ASSUMPTIONS`
* Render as a clean 3-column hairline grid (`grid-cols-1 md:grid-cols-3 gap-px bg-grid border border-grid`):
  1. **Groq API Pricing** (`groq.com/pricing`)
  2. **Supabase Postgres** (`supabase.com/pricing`)
  3. **Vercel Hosting** (`vercel.com/pricing`)
* Include `LAST VERIFIED: 2026-11-19` stamped in mono in each card footer, plus the single-line Commercial Deployment Note underneath (`Vercel Pro $20/mo + Supabase Pro $25/mo minimum`).

---

## 8. Antigravity Execution Order & Verification Checklist

Execute in this exact sequence:
1. Inspect existing `app/layout.tsx`, `app/page.tsx`, `app/stats/page.tsx`, `app/costs/page.tsx`, `tailwind.config.*`, and `components/` to map current prop types and query params.
2. Implement Phase 1 (`tailwind.config.ts`, `app/layout.tsx`, `app/globals.css`).
3. Implement Phase 2 (`src/lib/formatters.ts`) and Phase 3 (`Icons.tsx`, `Header.tsx`, `Footer.tsx`).
4. Refactor `/` (`JobFilters.tsx`, `JobFeed.tsx`, `JobRow.tsx`, `JobDetailDrawer.tsx`, `Pagination.tsx`).
5. Refactor `/stats` (5 telemetry sections + `<ProportionalBarList/>` with drilldown `<Link>`s).
6. Refactor `/costs` (`CostSimulator.tsx` + architectural flow + cleaned financial tables).
7. Run verification before finishing:
   * [ ] `npm run build` and `npx tsc --noEmit` succeed with zero errors.
   * [ ] Zero new packages added to `package.json`.
   * [ ] No duplicate city strings (`Mumbai (Mumbai)`, `Kolkata (Kolkatta)`) or scraper artifacts (`..Overview`, `# Position Overview`, `(***) )`) appear on `/`.
   * [ ] No raw snake_case keys (`experience_required`) or raw dedup hashes (`tier2_fuzzy_match_of_dfa2d9c0`) appear on `/stats`.
   * [ ] Clicking a Role or Metro bar on `/stats` navigates to `/` with that filter active.
   * [ ] No inverted (`10.59$`) or line-wrapped (`256.52` / `$`) dollar signs appear on `/costs` at `1440px`, `1280px`, or `390px` viewports.
   * [ ] Top navigation and footer route labels match 1:1 (`Live Jobs`, `Stats`, `Costs`).
   * [ ] Clicking any job row opens `JobDetailDrawer` smoothly; pressing `Esc` closes it; pressing `/` focuses job search.