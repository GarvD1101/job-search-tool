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
              TABLE 02 // SERVING SCENARIOS WITH CDN SENSITIVITY (LLM + DATABASE + HOSTING)
            </h2>
            <span className="font-mono text-[10px] text-ink-muted">
              90% BASELINE VS 50% SENSITIVITY · FLAT RATE & ON-DEMAND MODELS
            </span>
          </div>

          <div className="overflow-x-auto border border-grid bg-surface">
            <table className="w-full text-left text-xs font-sans text-ink">
              <thead className="bg-canvas border-b border-grid text-ink-muted font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2.5 font-semibold">DAU</th>
                  <th className="px-3 py-2.5 font-semibold">CDN CACHE</th>
                  <th className="px-3 py-2.5 font-semibold">MONTHLY VOL</th>
                  <th className="px-3 py-2.5 font-semibold">SUPABASE TIER & PUBLISHED LIMITS</th>
                  <th className="px-3 py-2.5 font-semibold">VERCEL TIER & PUBLISHED LIMITS</th>
                  <th className="px-3 py-2.5 text-right font-semibold">LLM / MO</th>
                  <th className="px-3 py-2.5 text-right font-semibold">WEEKLY (7D)</th>
                  <th className="px-3 py-2.5 text-right font-semibold">MONTHLY (30D)</th>
                  <th className="px-3 py-2.5 text-right font-semibold">ANNUAL (365D)</th>
                  <th className="px-3 py-2.5 text-right font-semibold">COST / 1K DAU</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-grid/60">
                {Object.entries(servingScenarios).map(([dauStr, sData]) => {
                  const dau = parseInt(dauStr, 10);
                  const cases = [
                    { ...sData.baseline_90_pct_cdn, label: "90% (BASE)", isBase: true },
                    { ...sData.sensitivity_50_pct_cdn, label: "50% (SENS)", isBase: false },
                  ];

                  return cases.map((c, idx) => {
                    const isFirst = idx === 0;

                    return (
                      <tr
                        key={`${dauStr}-${c.cdn_hit_ratio_pct}`}
                        className={`hover:bg-surface-muted/60 transition-colors ${
                          c.isBase ? "bg-canvas/30" : ""
                        }`}
                      >
                        <td className="px-3 py-2.5 font-mono font-bold text-ink text-xs tabular-nums">
                          {isFirst ? dau.toLocaleString() : ""}
                        </td>

                        <td className="px-3 py-2.5 font-mono text-[11px]">
                          <span
                            className={`px-1.5 py-0.5 border text-[10px] font-semibold ${
                              c.isBase
                                ? "bg-status-live/10 border-status-live/30 text-status-live"
                                : "bg-amber-wash border-amber-signal/30 text-amber-signal"
                            }`}
                          >
                            {c.label}
                          </span>
                        </td>

                        <td className="px-3 py-2.5 font-mono text-[11px] text-ink-secondary tabular-nums">
                          <span>{(c.monthly_searches / 1_000_000).toFixed(1)}M req</span>
                          <span className="block text-ink-muted text-[10px]">
                            {c.monthly_origin_requests ? `${(c.monthly_origin_requests / 1_000).toLocaleString()}k origin` : ""} · {c.monthly_bandwidth_gb} GB
                          </span>
                        </td>

                        <td className="px-3 py-2.5">
                          <span className="font-mono font-semibold text-ink text-xs block truncate">
                            {c.supabase.tier} (${formatUsd(c.supabase.monthly_cost_usd)}/mo)
                          </span>
                          <span className="font-mono text-[10px] text-ink-muted block truncate mt-0.5 max-w-[240px]">
                            Limits: {c.supabase.published_binding_limits}
                          </span>
                          {c.supabase.architecture_assumption && (
                            <span className="font-sans text-[10px] text-ink-muted/80 block truncate mt-0.5 max-w-[240px]">
                              Assumption: {c.supabase.architecture_assumption}
                            </span>
                          )}
                        </td>

                        <td className="px-3 py-2.5">
                          <span className="font-mono font-semibold text-ink text-xs block truncate">
                            {c.vercel.tier} (${formatUsd(c.vercel.monthly_cost_usd)}/mo)
                          </span>
                          <span className="font-mono text-[10px] text-ink-muted block truncate mt-0.5 max-w-[240px]">
                            Limits: {c.vercel.published_binding_limits}
                          </span>
                          {c.vercel.on_demand_model && (
                            <span className="font-mono text-[10px] text-ink-muted/80 block truncate mt-0.5 max-w-[240px]">
                              On-Demand Model: {formatUsd(c.vercel.on_demand_model.monthly_cost_usd)}/mo (Total: {formatUsd(c.on_demand_totals?.total_monthly_cost_usd || c.total_monthly_cost_usd)}/mo)
                            </span>
                          )}
                        </td>

                        <td className="px-3 py-2.5 text-right font-mono tabular-nums whitespace-nowrap text-ink-muted">
                          {formatUsd(c.breakdown_monthly_usd.llm, 2)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums whitespace-nowrap text-ink">
                          {formatUsd(c.total_weekly_cost_usd, 2)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums whitespace-nowrap font-bold text-ink">
                          {formatUsd(c.total_monthly_cost_usd, 2)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums whitespace-nowrap font-semibold text-ink">
                          {formatUsd(c.total_annual_cost_usd, 2)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono tabular-nums whitespace-nowrap font-bold text-amber-signal">
                          {formatUsd(c.cost_per_1000_users_usd, 4)}
                        </td>
                      </tr>
                    );
                  });
                })}
              </tbody>
            </table>
          </div>

          {/* Commercial Deployment & Official Pricing Mechanics Callout */}
          <div className="bg-canvas border border-grid p-3.5 font-mono text-xs text-ink-secondary space-y-2">
            <span className="font-bold text-ink uppercase tracking-wider block text-[11px]">
              VERIFIED OFFICIAL PRICING MECHANICS AND TIER ASSUMPTIONS
            </span>
            <div className="space-y-1.5 font-sans text-[11px] leading-relaxed">
              <p>
                <strong>1. Vercel Function Invocations and Usage Credit:</strong> Pro seat ($20/seat/mo) includes 1M function invocations and a $20 monthly usage credit. Invocations past 1M cost $0.60 per 1M. The $20 usage credit absorbs invocation overages and data transfer charges before additional billing.
              </p>
              <p>
                <strong>2. Vercel Flat Rate CDN vs On-Demand Metered CDN:</strong> In September 2026, Vercel introduced Flat Rate CDN capacity tiers (Included with Pro up to 1M req and 1 TB transfer; Tier 1 is $20/mo for 10M req and 50 TB; Tier 2 is $100/mo for 50M req; Tier 3 is $300/mo for 150M req). Table 02 defaults to Flat Rate CDN and displays the On-Demand Metered model ($2.00/1M edge requests over 10M) in the table subtext.
              </p>
              <p>
                <strong>3. Supabase Compute Credit and Connection Pooling:</strong> Pro is $25/mo per organization and includes a $10 monthly compute credit. Micro compute ($10 list) is net $0 extra. Small compute ($15 list) is net $5 extra. Medium compute ($60 list) is net $50 extra ($75 total). Egress overage past 250 GB is $0.09/GB. Published connection pooler limits are 200 on Micro, 400 on Small, and 600 on Medium. Free tier auto-pauses after 1 week of inactivity and lacks point-in-time backups, so a production launch assumes Pro.
              </p>
              <p>
                <strong>4. Published Limits vs Assumptions:</strong> The binding limits column lists only published hard limits (pooler connections, requests, invocations, egress). Hardware sizing choices (e.g. Medium compute for 7.5M queries/month) are labeled as architectural assumptions.
              </p>
              <p>
                <strong>5. 1,000,000 Users Scale:</strong> Fully computed from published list rates. At 90% CDN hit, monthly cost is $395.38 ($320 Vercel + $75 Supabase + $0.38 LLM). At 50% CDN, monthly cost is $461.65 ($344.40 Vercel + $116.87 Supabase + $0.38 LLM). While organizations at 150M monthly requests typically negotiate enterprise agreements for volume discounts, published self-serve rates yield exact computed projections.
              </p>
            </div>
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
              LAST VERIFIED: 2026-11-20
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
                Pro: $25/mo per org with $10 compute credit. Micro ($10 list, net $0, 200 pooler conn). Small ($15 list, net $5, 400 pooler conn). Medium ($60 list, net $50, 600 pooler conn). Egress: 250 GB included, $0.09/GB overage.
              </p>
            </div>
            <div className="pt-2 border-t border-grid/60 text-[10px] text-ink-muted">
              LAST VERIFIED: 2026-11-20
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
                Pro: $20/seat/mo with $20 usage credit. Function overage: $0.60/1M. Flat Rate CDN: Included (1M req, 1 TB), Tier 1 ($20, 10M req, 50 TB), Tier 2 ($100, 50M req), Tier 3 ($300, 150M req). Metered CDN: $2.00/1M edge requests over 10M.
              </p>
            </div>
            <div className="pt-2 border-t border-grid/60 text-[10px] text-ink-muted">
              LAST VERIFIED: 2026-11-20
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
