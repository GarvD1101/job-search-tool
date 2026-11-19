import costsData from "@/../data/costs.json";
import { formatUsd } from "@/lib/formatters";
import CostSimulator from "@/components/CostSimulator";
import { ArrowUpRightIcon, ChevronRightIcon } from "@/components/Icons";

export const metadata = {
  title: "Cost & Scale Projections // FinOps Console",
  description: "Measured LLM tagging expenses versus full-stack infrastructure costs at scale.",
};

export default function CostsPage() {
  const pipelineScenarios = costsData.pipeline_scenarios;
  const servingScenarios = costsData.serving_scenarios;

  return (
    <div className="space-y-8 max-w-[1380px] mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="font-mono text-base sm:text-lg font-bold tracking-tight text-ink uppercase flex items-center gap-2">
          <span>03 // FINOPS & SCALE PROJECTIONS</span>
        </h1>
        <p className="text-xs text-ink-secondary mt-1 font-sans">
          Deterministic economic models derived from 95 instrumented tagging calls and official infrastructure pricing tiers.
        </p>
      </div>

      {/* SECTION 1: CORE ARCHITECTURAL FINDING */}
      <section aria-label="Core Architectural Finding">
        <div className="bg-surface border border-grid border-l-4 border-l-amber-signal p-4 sm:p-5 space-y-1.5">
          <span className="font-mono text-[10px] sm:text-[11px] font-bold text-amber-signal uppercase tracking-wider block">
            01 // EXECUTIVE FINDING: LLM TAGGING VS INFRASTRUCTURE SCALE
          </span>
          <p className="text-xs sm:text-sm text-ink font-sans leading-relaxed">
            At <strong>600 raw posts/day</strong>, LLM tagging costs only <strong>$0.38/mo ($4.66/yr)</strong> on <code>openai/gpt-oss-20b</code>.
            Because tagging cost scales strictly with upstream post ingestion rather than website traffic, database connection poolers, edge caching, and serverless hosting represent over <strong>99% of operating expenses</strong> as user scale grows.
          </p>
        </div>
      </section>

      {/* SECTION 2: INTERACTIVE UNIT-ECONOMICS SIMULATOR */}
      <section aria-label="Unit-Economics Simulator" className="space-y-2">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          02 // INTERACTIVE UNIT-ECONOMICS SIMULATOR
        </div>
        <CostSimulator
          pipelineScenarios={pipelineScenarios}
          servingScenarios={servingScenarios}
        />
      </section>

      {/* SECTION 3: SERVING TRAFFIC & COST MODELING SCHEMATIC */}
      <section aria-label="Serving Architecture Schematic" className="space-y-2">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          03 // SERVING TRAFFIC & COST MODELING SCHEMATIC
        </div>

        <div className="bg-surface border border-grid p-4 sm:p-5 space-y-4">
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-2 font-mono text-xs">
            {/* Step 1 */}
            <div className="border border-grid bg-canvas p-3 flex-1 flex flex-col justify-between">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">STAGE 01</span>
              <span className="font-bold text-ink mt-1 block">USERS (DAU)</span>
              <span className="text-[10px] text-ink-secondary block mt-0.5">15% daily active rate</span>
            </div>

            <div className="hidden lg:flex items-center text-ink-muted px-1">
              <ChevronRightIcon size={16} />
            </div>

            {/* Step 2 */}
            <div className="border border-grid bg-canvas p-3 flex-1 flex flex-col justify-between">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">STAGE 02</span>
              <span className="font-bold text-ink mt-1 block">5 SEARCHES / SESSION</span>
              <span className="text-[10px] text-ink-secondary block mt-0.5">Avg user engagement</span>
            </div>

            <div className="hidden lg:flex items-center text-ink-muted px-1">
              <ChevronRightIcon size={16} />
            </div>

            {/* Step 3: Split Node */}
            <div className="border border-amber-signal/30 bg-amber-wash p-3 flex-[1.4] flex flex-col justify-between">
              <span className="text-[10px] text-amber-signal uppercase block font-semibold">STAGE 03 // CACHE SPLIT</span>
              <div className="flex items-center justify-between mt-1 text-[11px]">
                <span className="font-bold text-status-live">80% EDGE HIT ($0 DB)</span>
                <span className="text-grid">/</span>
                <span className="font-bold text-ink">20% POOLER QUERY</span>
              </div>
              <span className="text-[10px] text-ink-muted block mt-0.5 font-sans">
                Next.js unstable_cache (300s TTL)
              </span>
            </div>

            <div className="hidden lg:flex items-center text-ink-muted px-1">
              <ChevronRightIcon size={16} />
            </div>

            {/* Step 4 */}
            <div className="border border-grid bg-canvas p-3 flex-1 flex flex-col justify-between">
              <span className="text-[10px] text-ink-muted uppercase block font-semibold">STAGE 04</span>
              <span className="font-bold text-ink mt-1 block">INFRA TIER COST</span>
              <span className="text-[10px] text-ink-secondary block mt-0.5">Supabase + Vercel</span>
            </div>
          </div>

          <div className="pt-2 border-t border-grid/60 font-mono text-[11px] text-ink-muted flex flex-wrap items-center justify-between gap-2">
            <span>MODEL PARAMETERS // 10 KB avg payload · 218.25 in / 73.68 out tokens · 55.35% survivor rate</span>
            <span>TOKEN THROTTLE: 8,000 TPM CEILING</span>
          </div>
        </div>
      </section>

      {/* SECTION 4: PROJECTION MATRICES */}
      <section aria-label="Financial-Grade Projection Tables" className="space-y-6">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          04 // PROJECTION MATRICES (FINANCIAL-GRADE TABLES)
        </div>

        {/* Table 1: Pipeline Tagging Scenarios */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
              TABLE 01 // PIPELINE TAGGING SCENARIOS (LLM API ONLY)
            </h2>
            <span className="font-mono text-[10px] text-ink-muted">
              GROQ OFFICIAL LIST PRICES
            </span>
          </div>

          <div className="overflow-x-auto border border-grid bg-surface">
            <table className="w-full text-left text-xs font-sans text-ink">
              <thead className="bg-canvas border-b border-grid text-ink-muted font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="px-3.5 py-2.5 font-semibold">RAW POSTS / DAY</th>
                  <th className="px-3.5 py-2.5 font-semibold">TAGGED POSTS</th>
                  <th className="px-3.5 py-2.5 font-semibold">GROQ MODEL</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">DAILY</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">WEEKLY (7D)</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">MONTHLY (30D)</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">ANNUAL (365D)</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">COST / 1K RAW</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-grid/60">
                {Object.entries(pipelineScenarios).flatMap(([rawVol, sData], tierIdx) =>
                  Object.entries(sData.models).map(([modelId, mData], idx) => {
                    const isFirst = idx === 0;
                    const isBaseline =
                      rawVol === "600" && modelId === "openai/gpt-oss-20b";
                    const shortModel = modelId
                      .replace("openai/", "")
                      .replace("qwen/", "");

                    return (
                      <tr
                        key={`${rawVol}-${modelId}`}
                        className={`transition-colors ${
                          isBaseline
                            ? "bg-amber-wash font-semibold"
                            : "hover:bg-surface-muted/60"
                        } ${isFirst && tierIdx > 0 ? "border-t-2 border-t-grid" : ""}`}
                      >
                        {isFirst ? (
                          <td
                            rowSpan={3}
                            className="px-3.5 py-3 font-mono font-bold text-ink border-r border-grid align-top text-xs"
                          >
                            {rawVol} / day
                          </td>
                        ) : null}

                        {isFirst ? (
                          <td
                            rowSpan={3}
                            className="px-3.5 py-3 font-mono text-ink-secondary border-r border-grid align-top text-xs"
                          >
                            {sData.tagged_posts_per_day}
                          </td>
                        ) : null}

                        <td className="px-3.5 py-2.5 font-mono text-ink text-xs flex items-center gap-2">
                          <span>{shortModel}</span>
                          {isBaseline && (
                            <span className="bg-amber-signal text-white font-mono text-[10px] px-1.5 py-0.5 rounded-[2px] font-semibold tracking-wider">
                              BASELINE
                            </span>
                          )}
                        </td>

                        <td className="px-3.5 py-2.5 text-right font-mono tabular-nums whitespace-nowrap text-ink">
                          {formatUsd(mData.daily_cost_usd, 4)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-mono tabular-nums whitespace-nowrap text-ink">
                          {formatUsd(mData.weekly_cost_usd, 2)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-mono tabular-nums whitespace-nowrap text-ink">
                          {formatUsd(mData.monthly_cost_usd, 2)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-mono tabular-nums whitespace-nowrap text-ink">
                          {formatUsd(mData.annual_cost_usd, 2)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-mono tabular-nums whitespace-nowrap font-bold text-amber-signal">
                          {formatUsd(mData.cost_per_1000_raw_posts_usd, 4)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Table 2: Serving Scenarios */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
              TABLE 02 // SERVING SCENARIOS (FULL STACK: LLM + DATABASE + HOSTING)
            </h2>
            <span className="font-mono text-[10px] text-ink-muted">
              CDN CACHED SERVING
            </span>
          </div>

          <div className="overflow-x-auto border border-grid bg-surface">
            <table className="w-full text-left text-xs font-sans text-ink">
              <thead className="bg-canvas border-b border-grid text-ink-muted font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="px-3.5 py-2.5 font-semibold">DAU</th>
                  <th className="px-3.5 py-2.5 font-semibold">MONTHLY VOL</th>
                  <th className="px-3.5 py-2.5 font-semibold">SUPABASE TIER</th>
                  <th className="px-3.5 py-2.5 font-semibold">VERCEL TIER</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">LLM / MO</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">WEEKLY (7D)</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">MONTHLY (30D)</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">ANNUAL (365D)</th>
                  <th className="px-3.5 py-2.5 text-right font-semibold">COST / 1K DAU</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-grid/60">
                {Object.entries(servingScenarios).map(([dauStr, sData]) => {
                  const dau = parseInt(dauStr, 10);
                  const isCommercialBaseline = dau === 10000;

                  // Clean 2-line formatting for Supabase
                  const supaTierLine1 = sData.supabase.tier;
                  const supaTierLine2 = sData.supabase.plan_limit;

                  // Clean 2-line formatting for Vercel
                  const vercelTierLine1 = sData.vercel.tier;
                  const vercelTierLine2 = sData.vercel.basis
                    ? `Estimate: ${sData.vercel.basis}`
                    : sData.vercel.plan_limit;

                  return (
                    <tr
                      key={dauStr}
                      className={`hover:bg-surface-muted/60 transition-colors ${
                        isCommercialBaseline ? "bg-canvas/50" : ""
                      }`}
                    >
                      <td className="px-3.5 py-3 font-mono font-bold text-ink text-xs tabular-nums">
                        {dau.toLocaleString()}
                      </td>

                      <td className="px-3.5 py-3 font-mono text-[11px] text-ink-secondary tabular-nums">
                        <span>{(sData.monthly_searches / 1_000_000).toFixed(1)}M req</span>
                        <span className="block text-ink-muted text-[10px]">
                          {sData.monthly_bandwidth_gb} GB egress
                        </span>
                      </td>

                      <td className="px-3.5 py-3">
                        <span className="font-mono font-semibold text-ink text-xs block truncate">
                          {supaTierLine1}
                        </span>
                        <span className="font-mono text-[10px] text-ink-muted block truncate mt-0.5">
                          {supaTierLine2}
                        </span>
                      </td>

                      <td className="px-3.5 py-3">
                        <span className="font-mono font-semibold text-ink text-xs block truncate">
                          {vercelTierLine1}
                        </span>
                        <span className="font-mono text-[10px] text-ink-muted block truncate mt-0.5 max-w-[200px]">
                          {vercelTierLine2}
                        </span>
                      </td>

                      <td className="px-3.5 py-3 text-right font-mono tabular-nums whitespace-nowrap text-ink-muted">
                        {formatUsd(sData.breakdown_monthly_usd.llm, 2)}
                      </td>
                      <td className="px-3.5 py-3 text-right font-mono tabular-nums whitespace-nowrap text-ink">
                        {formatUsd(sData.total_weekly_cost_usd, 2)}
                      </td>
                      <td className="px-3.5 py-3 text-right font-mono tabular-nums whitespace-nowrap font-bold text-ink">
                        {formatUsd(sData.total_monthly_cost_usd, 2)}
                      </td>
                      <td className="px-3.5 py-3 text-right font-mono tabular-nums whitespace-nowrap font-semibold text-ink">
                        {formatUsd(sData.total_annual_cost_usd, 2)}
                      </td>
                      <td className="px-3.5 py-3 text-right font-mono tabular-nums whitespace-nowrap font-bold text-amber-signal">
                        {formatUsd(sData.cost_per_1000_users_usd, 4)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Commercial Deployment Callout */}
          <div className="bg-canvas border border-grid p-3.5 font-mono text-xs text-ink-secondary space-y-1">
            <span className="font-bold text-ink uppercase tracking-wider block text-[11px]">
              COMMERCIAL DEPLOYMENT NOTE
            </span>
            <p className="text-[11px] leading-relaxed font-sans">
              Vercel Hobby is strictly restricted to personal, non-commercial use. Commercial launch assumes Vercel Pro ($20/seat/mo) and Supabase Pro ($25/mo), establishing a baseline operating floor of $45.00/mo.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 5: VERIFIED PRICING SOURCES & ASSUMPTIONS */}
      <section aria-label="Verified Pricing Sources" className="space-y-2">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
          05 // VERIFIED PRICING SOURCES & ASSUMPTIONS
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-grid border border-grid font-mono text-xs">
          {/* Card 1 */}
          <div className="bg-surface p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink">01 // GROQ API</span>
                <a
                  href="https://groq.com/pricing/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-signal hover:underline flex items-center gap-0.5 text-[11px]"
                >
                  <span>PRICING</span>
                  <ArrowUpRightIcon size={12} />
                </a>
              </div>
              <p className="text-[11px] text-ink-secondary font-sans mt-2 leading-relaxed">
                Official list rates: gpt-oss-20b ($0.075/1M in, $0.30/1M out), gpt-oss-120b ($0.15/$0.60), qwen3.8-27b ($0.80/$4.00). Free tier grants $0.00 actual spend up to 200k TPD.
              </p>
            </div>
            <div className="pt-2 border-t border-grid/60 text-[10px] text-ink-muted">
              LAST VERIFIED: 2026-11-19
            </div>
          </div>

          {/* Card 2 */}
          <div className="bg-surface p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink">02 // SUPABASE POSTGRES</span>
                <a
                  href="https://supabase.com/pricing"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-signal hover:underline flex items-center gap-0.5 text-[11px]"
                >
                  <span>PRICING</span>
                  <ArrowUpRightIcon size={12} />
                </a>
              </div>
              <p className="text-[11px] text-ink-secondary font-sans mt-2 leading-relaxed">
                Free: $0/mo (500 MB DB, 5 GB egress, 200 pool connections). Pro: $25/mo (8 GB DB, 250 GB egress, 10,000 pool connections). Team: $599/mo (16 GB DB, SOC2).
              </p>
            </div>
            <div className="pt-2 border-t border-grid/60 text-[10px] text-ink-muted">
              LAST VERIFIED: 2026-11-19
            </div>
          </div>

          {/* Card 3 */}
          <div className="bg-surface p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink">03 // VERCEL HOSTING</span>
                <a
                  href="https://vercel.com/pricing"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-signal hover:underline flex items-center gap-0.5 text-[11px]"
                >
                  <span>PRICING</span>
                  <ArrowUpRightIcon size={12} />
                </a>
              </div>
              <p className="text-[11px] text-ink-secondary font-sans mt-2 leading-relaxed">
                Hobby: $0/mo (100 GB BW, personal only). Pro: $20/seat/mo (1 TB BW, commercial). Enterprise: Custom quote (contract estimate: $500/mo for 150M edge req, 1.5 TB BW, SLA).
              </p>
            </div>
            <div className="pt-2 border-t border-grid/60 text-[10px] text-ink-muted">
              LAST VERIFIED: 2026-11-19
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
