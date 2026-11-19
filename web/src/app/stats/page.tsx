import { getStats } from "@/lib/jobs";
import { formatCity, formatRole } from "@/lib/taxonomy";
import {
  formatRejectionReason,
  formatUsd,
  normalizeOriginBoard,
} from "@/lib/formatters";
import ProportionalBarList, { BarItem } from "@/components/ProportionalBarList";

export const revalidate = 300;

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "None recorded";
  const date = new Date(iso);
  return (
    date.toLocaleDateString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "numeric",
      month: "short",
      year: "numeric",
    }) +
    ", " +
    date.toLocaleTimeString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }) +
    " IST"
  );
}

export default async function StatsPage() {
  const stats = await getStats();

  // 1. Process Rule Rejection Reasons (Group and sanitize)
  const groupedRejections: Record<string, { code: string; label: string; count: number }> = {};
  for (const r of stats.reject_reasons) {
    const formatted = formatRejectionReason(r.reason);
    if (!groupedRejections[formatted.groupKey]) {
      groupedRejections[formatted.groupKey] = {
        code: formatted.code,
        label: formatted.label,
        count: 0,
      };
    }
    groupedRejections[formatted.groupKey].count += r.count;
  }
  const rejectionBarItems: BarItem[] = Object.entries(groupedRejections)
    .map(([groupKey, data]) => ({
      id: groupKey,
      code: data.code,
      label: data.label,
      count: data.count,
    }))
    .sort((a, b) => b.count - a.count);

  const totalRejections = rejectionBarItems.reduce((acc, i) => acc + i.count, 0);

  // 2. Process Origin Boards (Normalize and group)
  const groupedOrigins: Record<string, number> = {};
  for (const o of stats.origin_counts) {
    const normalized = normalizeOriginBoard(o.name);
    groupedOrigins[normalized] = (groupedOrigins[normalized] || 0) + o.count;
  }
  const originBarItems: BarItem[] = Object.entries(groupedOrigins)
    .map(([name, count]) => ({
      id: name,
      label: name,
      count,
    }))
    .sort((a, b) => b.count - a.count);

  // 3. Process Roles (with interactive link drilldowns)
  const roleBarItems: BarItem[] = stats.role_counts.map((r) => ({
    id: r.name,
    label: formatRole(r.name),
    count: r.count,
    href: `/?role=${encodeURIComponent(r.name)}`,
  }));

  // 4. Process Cities (with interactive link drilldowns)
  const cityBarItems: BarItem[] = stats.city_counts.map((c) => ({
    id: c.name,
    label: formatCity(c.name),
    count: c.count,
    href: `/?city=${encodeURIComponent(c.name)}`,
  }));

  // 5. Ingestion Funnel Proportions
  const rawTotal = stats.total_raw || 1;
  const activeCount = stats.total_active;
  const dedupCount = stats.total_duplicates;
  const ruleRejectCount = totalRejections;
  const remainingCount = Math.max(0, rawTotal - activeCount - dedupCount - ruleRejectCount);

  const activePct = Math.round((activeCount / rawTotal) * 1000) / 10;
  const rulePct = Math.round((ruleRejectCount / rawTotal) * 1000) / 10;
  const dedupPct = Math.round((dedupCount / rawTotal) * 1000) / 10;
  const remPct = Math.max(0, Math.round((100 - activePct - rulePct - dedupPct) * 10) / 10);

  // 6. Source split (Jooble vs Greenhouse)
  const joobleCount = stats.source_counts.find((s) => s.name === "jooble")?.count || 0;
  const greenhouseCount = stats.source_counts.find((s) => s.name === "greenhouse")?.count || 0;
  const sourceTotal = joobleCount + greenhouseCount || 1;
  const ghPct = Math.round((greenhouseCount / sourceTotal) * 100);
  const jooblePct = 100 - ghPct;

  return (
    <div className="space-y-8 max-w-[1380px] mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="font-mono text-base sm:text-lg font-bold tracking-tight text-ink uppercase flex items-center gap-2">
          <span>02 // PIPELINE & SYSTEM TELEMETRY</span>
        </h1>
        <p className="text-xs text-ink-secondary mt-1 font-sans">
          Deterministic verification metrics, LLM token ledgers, and classification distributions refreshed from PostgreSQL every 300s.
        </p>
      </div>

      {/* SECTION 1: CORE TELEMETRY STRIP */}
      <section aria-label="Core Telemetry KPIs">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-grid border border-grid">
          {/* Card 1 */}
          <div className="bg-surface p-4 flex flex-col justify-between">
            <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider block font-semibold">
              01 // ACTIVE JOBS
            </span>
            <div className="mt-2">
              <span className="font-mono text-3xl font-bold tracking-tight text-ink tabular-nums">
                {stats.total_active}
              </span>
              <span className="text-[11px] text-status-live block mt-1 font-medium">
                Verified 0-1 yr freshers
              </span>
            </div>
          </div>

          {/* Card 2 */}
          <div className="bg-surface p-4 flex flex-col justify-between">
            <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider block font-semibold">
              02 // RAW POSTS (7D)
            </span>
            <div className="mt-2">
              <span className="font-mono text-3xl font-bold tracking-tight text-ink tabular-nums">
                {stats.total_raw}
              </span>
              <span className="text-[11px] text-ink-muted block mt-1 font-mono">
                7-day rolling window
              </span>
            </div>
          </div>

          {/* Card 3 */}
          <div className="bg-surface p-4 flex flex-col justify-between">
            <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider block font-semibold">
              03 // DEDUPLICATED
            </span>
            <div className="mt-2">
              <span className="font-mono text-3xl font-bold tracking-tight text-ink tabular-nums">
                {stats.total_duplicates}
              </span>
              <span className="text-[11px] text-ink-muted block mt-1 font-mono">
                Exact + fuzzy shingle
              </span>
            </div>
          </div>

          {/* Card 4 (Highlighted Accent) */}
          <div className="bg-surface p-4 flex flex-col justify-between border-t-2 border-t-amber-signal">
            <span className="font-mono text-[10px] text-amber-signal uppercase tracking-wider block font-semibold">
              04 // BYPASSED LLM
            </span>
            <div className="mt-2">
              <span className="font-mono text-3xl font-bold tracking-tight text-amber-signal tabular-nums">
                {stats.non_llm_share_pct}%
              </span>
              <span className="text-[11px] text-ink-secondary block mt-1 font-medium">
                Filtered free before LLM API
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2: INGESTION & FILTERING FUNNEL */}
      <section aria-label="Ingestion and Filtering Funnel" className="space-y-2">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          02 // INGESTION & FILTERING FUNNEL
        </div>

        <div className="bg-surface border border-grid p-4 sm:p-5 space-y-4">
          <div className="text-xs text-ink-secondary leading-relaxed font-sans">
            How raw upstream postings narrow down into verified entry-level fresher positions. Deterministic rules reject senior roles and non-job spam before touching LLM token budgets.
          </div>

          {/* Segmented Pure-CSS Bar */}
          <div className="h-7 w-full flex gap-[2px] bg-canvas p-[2px] border border-grid overflow-hidden rounded-[1px]">
            <div
              style={{ width: `${Math.max(activePct, 3)}%` }}
              className="bg-amber-signal h-full transition-all"
              title={`Active Jobs: ${activeCount} (${activePct}%)`}
            />
            <div
              style={{ width: `${Math.max(rulePct, 3)}%` }}
              className="bg-ink h-full transition-all"
              title={`Rule-Bypassed: ${ruleRejectCount} (${rulePct}%)`}
            />
            <div
              style={{ width: `${Math.max(dedupPct, 2)}%` }}
              className="bg-[#73736C] h-full transition-all"
              title={`Deduplicated: ${dedupCount} (${dedupPct}%)`}
            />
            {remPct > 0 && (
              <div
                style={{ width: `${Math.max(remPct, 2)}%` }}
                className="bg-[#D4D4CE] h-full transition-all"
                title={`Other / Evaluated: ${remainingCount} (${remPct}%)`}
              />
            )}
          </div>

          {/* 4-Column Funnel Legend */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 font-mono text-xs border-t border-grid/60">
            <div className="flex items-start space-x-2">
              <span className="w-2.5 h-2.5 bg-amber-signal shrink-0 mt-0.5 rounded-[1px]" />
              <div>
                <span className="text-ink-muted text-[10px] block uppercase">ACTIVE VERIFIED</span>
                <span className="font-bold text-ink tabular-nums text-sm">{activeCount}</span>
                <span className="text-ink-muted text-[10px] ml-1">({activePct}%)</span>
              </div>
            </div>

            <div className="flex items-start space-x-2">
              <span className="w-2.5 h-2.5 bg-ink shrink-0 mt-0.5 rounded-[1px]" />
              <div>
                <span className="text-ink-muted text-[10px] block uppercase">RULE BYPASSED</span>
                <span className="font-bold text-ink tabular-nums text-sm">{ruleRejectCount}</span>
                <span className="text-ink-muted text-[10px] ml-1">({rulePct}%)</span>
              </div>
            </div>

            <div className="flex items-start space-x-2">
              <span className="w-2.5 h-2.5 bg-[#73736C] shrink-0 mt-0.5 rounded-[1px]" />
              <div>
                <span className="text-ink-muted text-[10px] block uppercase">DEDUPLICATED</span>
                <span className="font-bold text-ink tabular-nums text-sm">{dedupCount}</span>
                <span className="text-ink-muted text-[10px] ml-1">({dedupPct}%)</span>
              </div>
            </div>

            <div className="flex items-start space-x-2">
              <span className="w-2.5 h-2.5 bg-[#D4D4CE] shrink-0 mt-0.5 rounded-[1px]" />
              <div>
                <span className="text-ink-muted text-[10px] block uppercase">OTHER / EVAL</span>
                <span className="font-bold text-ink tabular-nums text-sm">{remainingCount}</span>
                <span className="text-ink-muted text-[10px] ml-1">({remPct}%)</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: LLM TOKEN LEDGER */}
      <section aria-label="LLM Token Ledger" className="space-y-2">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          03 // LLM TOKEN LEDGER (openai/gpt-oss-20b)
        </div>

        <div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-grid border border-grid font-mono">
            <div className="bg-surface p-3 sm:p-4">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">
                API CALLS
              </span>
              <span className="text-lg font-bold text-ink block mt-1 tabular-nums">
                {stats.llm_usage.total_calls}
              </span>
            </div>

            <div className="bg-surface p-3 sm:p-4">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">
                INPUT TOKENS
              </span>
              <span className="text-lg font-bold text-ink block mt-1 tabular-nums">
                {stats.llm_usage.input_tokens.toLocaleString()}
              </span>
            </div>

            <div className="bg-surface p-3 sm:p-4">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">
                OUTPUT TOKENS
              </span>
              <span className="text-lg font-bold text-ink block mt-1 tabular-nums">
                {stats.llm_usage.output_tokens.toLocaleString()}
              </span>
            </div>

            <div className="bg-surface p-3 sm:p-4">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">
                REASONING TOKENS
              </span>
              <span className="text-lg font-bold text-ink block mt-1 tabular-nums">
                {stats.llm_usage.reasoning_tokens.toLocaleString()}
              </span>
            </div>

            <div className="bg-amber-wash p-3 sm:p-4 col-span-2 sm:col-span-1">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">
                LIST-PRICE SPEND
              </span>
              <span className="text-lg font-bold text-ink block mt-1 tabular-nums">
                {formatUsd(stats.llm_usage.list_price_cost, 4)}
              </span>
            </div>
          </div>

          {/* Footnote Bar */}
          <div className="bg-canvas px-4 py-2 border-x border-b border-grid text-[11px] font-mono text-ink-muted flex items-center justify-between">
            <span>
              Groq list pricing: $0.075/1M input · $0.30/1M output (reasoning tokens billed as output tokens).
            </span>
            <span className="hidden md:inline font-semibold text-ink">ACTUAL SPEND: $0.00 (FREE TIER)</span>
          </div>
        </div>
      </section>

      {/* SECTION 4: TAXONOMY, GEOGRAPHY & RULE AUDIT */}
      <section aria-label="Taxonomy Geography and Rule Audit" className="space-y-4">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          04 // TAXONOMY, GEOGRAPHY & RULE AUDIT
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sub-Card 1: Role Taxonomy with Link Drilldown */}
          <div className="bg-surface border border-grid p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-grid pb-2">
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
                ACTIVE JOBS BY ROLE TAXONOMY
              </h2>
              <span className="font-mono text-[10px] text-ink-muted">
                CLICK TO DRILL DOWN ↗
              </span>
            </div>
            <ProportionalBarList
              items={roleBarItems}
              total={stats.total_active}
              initialLimit={10}
              toggleLabel="SHOW ALL ROLES"
              barColor="canvas"
            />
          </div>

          {/* Sub-Card 2: Metro Area with Link Drilldown */}
          <div className="bg-surface border border-grid p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-grid pb-2">
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
                ACTIVE JOBS BY METRO AREA
              </h2>
              <span className="font-mono text-[10px] text-ink-muted">
                CLICK TO DRILL DOWN ↗
              </span>
            </div>
            <ProportionalBarList
              items={cityBarItems}
              total={stats.total_active}
              barColor="canvas"
            />
          </div>

          {/* Sub-Card 3: Sanitized Rule Rejections */}
          <div className="bg-surface border border-grid p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-grid pb-2">
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
                POSTS REJECTED BY RULE REASON
              </h2>
              <span className="font-mono text-[10px] text-ink-muted">
                {totalRejections} REJECTED
              </span>
            </div>
            <ProportionalBarList
              items={rejectionBarItems}
              total={totalRejections}
              barColor="reject"
            />
          </div>

          {/* Sub-Card 4: Sources & Top Origin Boards */}
          <div className="bg-surface border border-grid p-4 sm:p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-grid pb-2">
              <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
                SOURCE PLATFORMS & ORIGIN BOARDS
              </h2>
              <span className="font-mono text-[10px] text-ink-muted">
                {stats.total_active} ACTIVE
              </span>
            </div>

            {/* Top Split Bar for Source Platform */}
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-status-live font-semibold">
                  GREENHOUSE DIRECT ({greenhouseCount} · {ghPct}%)
                </span>
                <span className="text-ink-secondary">
                  JOOBLE API ({joobleCount} · {jooblePct}%)
                </span>
              </div>
              <div className="h-4 w-full flex bg-canvas border border-grid rounded-[1px] overflow-hidden">
                <div
                  style={{ width: `${ghPct}%` }}
                  className="bg-status-live h-full"
                  title={`Greenhouse: ${greenhouseCount}`}
                />
                <div
                  style={{ width: `${jooblePct}%` }}
                  className="bg-ink h-full"
                  title={`Jooble: ${joobleCount}`}
                />
              </div>
            </div>

            {/* Origin Boards List */}
            <div className="pt-2">
              <span className="font-mono text-[10px] text-ink-muted uppercase tracking-wider block mb-2 font-semibold">
                TOP ORIGIN BOARDS
              </span>
              <ProportionalBarList
                items={originBarItems.slice(0, 8)}
                total={stats.total_active}
                barColor="canvas"
              />
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 5: PIPELINE EXECUTION LOG */}
      <section aria-label="Pipeline Execution Log" className="space-y-2">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          05 // PIPELINE EXECUTION LOG
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-grid border border-grid font-mono text-xs">
          <div className="bg-surface p-4 space-y-1">
            <span className="text-[10px] text-ink-muted uppercase block font-semibold">
              RUNS BY TRIGGER
            </span>
            <div className="pt-1 space-y-1 text-ink">
              {stats.runs_by_event && stats.runs_by_event.length > 0 ? (
                stats.runs_by_event.map((r) => (
                  <div key={r.event} className="flex justify-between">
                    <span className="uppercase text-ink-secondary">{r.event}:</span>
                    <span className="font-bold tabular-nums">{r.count}</span>
                  </div>
                ))
              ) : (
                <span>No runs logged</span>
              )}
            </div>
          </div>

          <div className="bg-surface p-4 space-y-1">
            <span className="text-[10px] text-ink-muted uppercase block font-semibold">
              LATEST OVERALL RUN
            </span>
            <div className="pt-1 text-ink font-semibold">
              {formatTimestamp(stats.last_run?.started_at)}
            </div>
            <span className="text-[10px] text-status-live block">STATUS: SUCCESS</span>
          </div>

          <div className="bg-surface p-4 space-y-1">
            <span className="text-[10px] text-ink-muted uppercase block font-semibold">
              SCHEDULED CADENCE
            </span>
            <div className="pt-1 text-ink font-semibold">
              DAILY 03:30 UTC // 09:00 IST
            </div>
            <span className="text-[10px] text-ink-muted block font-sans">
              Automated GitHub Actions cron
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
