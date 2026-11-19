import costsData from "@/../data/costs.json";

export const metadata = {
  title: "Cost & Scale Projections | Fresher Radar",
  description: "Measured LLM tagging expenses versus full-stack infrastructure costs at scale.",
};

export default function CostsPage() {
  const pipelineScenarios = costsData.pipeline_scenarios;
  const servingScenarios = costsData.serving_scenarios;

  return (
    <div className="space-y-10 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Cost & Scale Projections
        </h1>
        <p className="text-sm text-slate-600 mt-2">
          Deterministic projections derived from 95 measured LLM tagging calls and official infrastructure pricing tiers. Figures are projections from documented assumptions.
        </p>
      </div>

      {/* Core Architectural Finding */}
      <div className="bg-sky-50 border border-sky-200 rounded-lg p-5">
        <h2 className="text-sm font-bold text-sky-900">
          Core Architectural Finding: LLM Tagging vs Infrastructure Scale
        </h2>
        <p className="text-xs sm:text-sm text-sky-800 mt-1.5 leading-relaxed">
          LLM tagging cost depends strictly on daily raw posts ingested, not on user traffic. At our baseline volume of 600 raw posts per day, tagging costs only <strong>$0.38 per month</strong> ($4.66 per year) with openai/gpt-oss-20b. In contrast, database storage, connection poolers, and serverless hosting scale with user traffic and represent over <strong>99% of total operating expenses</strong> at scale.
        </p>
      </div>

      {/* Traffic & Cost Formula Chain */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
        <h2 className="text-sm font-bold text-slate-900">
          Serving Traffic & Cost Modeling Chain
        </h2>
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-700 bg-slate-50 p-3 rounded border border-slate-100">
          <span className="font-semibold text-slate-900">Users (DAU)</span>
          <span>&rarr;</span>
          <span>Active share (100% daily)</span>
          <span>&rarr;</span>
          <span>5 searches / session</span>
          <span>&rarr;</span>
          <span>80% CDN hit ratio</span>
          <span>&rarr;</span>
          <span>20% pooler origin requests</span>
          <span>&rarr;</span>
          <span className="font-semibold text-sky-700">Compute + DB Tier Cost</span>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          Each user session performs 5 searches per day. Edge caching serves 80% of searches directly from the CDN. The remaining 20% execute server-side through the Postgres transaction pooler. Bandwidth is estimated at 10 KB average payload per response.
        </p>
      </div>

      {/* Section 1: Pipeline Tagging Scenarios */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            1. Pipeline Tagging Scenarios (LLM API Only)
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Projections across daily ingestion tiers using measured token metrics (218.25 input tokens, 73.68 output tokens per post) and a measured 55.35% survivor rate after deterministic rule filters.
          </p>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-900 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Raw Posts / Day</th>
                <th className="px-4 py-3">Tagged Posts</th>
                <th className="px-4 py-3">Groq Model</th>
                <th className="px-4 py-3 text-right">Daily Cost</th>
                <th className="px-4 py-3 text-right">Weekly (7d)</th>
                <th className="px-4 py-3 text-right">Monthly (30d)</th>
                <th className="px-4 py-3 text-right">Annual (365d)</th>
                <th className="px-4 py-3 text-right">Cost / 1k Raw</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {Object.entries(pipelineScenarios).flatMap(([rawVol, sData]) =>
                Object.entries(sData.models).map(([modelId, mData], idx) => {
                  const isFirst = idx === 0;
                  const isBaseline = rawVol === "600" && modelId === "openai/gpt-oss-20b";
                  return (
                    <tr
                      key={`${rawVol}-${modelId}`}
                      className={isBaseline ? "bg-emerald-50/60 font-medium" : "hover:bg-slate-50"}
                    >
                      {isFirst ? (
                        <td
                          rowSpan={3}
                          className="px-4 py-3 font-semibold text-slate-900 border-r border-slate-100 align-top"
                        >
                          {rawVol} / day
                        </td>
                      ) : null}
                      {isFirst ? (
                        <td
                          rowSpan={3}
                          className="px-4 py-3 text-slate-600 border-r border-slate-100 align-top"
                        >
                          {sData.tagged_posts_per_day}
                        </td>
                      ) : null}
                      <td className="px-4 py-2.5 font-mono text-slate-800">
                        {modelId.replace("openai/", "").replace("qwen/", "")}
                        {isBaseline ? (
                          <span className="ml-2 inline-block px-1.5 py-0.5 text-[10px] bg-emerald-100 text-emerald-800 rounded font-sans font-semibold">
                            Baseline
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono">${mData.daily_cost_usd.toFixed(4)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">${mData.weekly_cost_usd.toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">${mData.monthly_cost_usd.toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono">${mData.annual_cost_usd.toFixed(2)}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-emerald-700 font-semibold">
                        ${mData.cost_per_1000_raw_posts_usd.toFixed(4)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 2: Serving Scenarios */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            2. Serving Scenarios (Full Stack: LLM + Database + Hosting)
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Weekly, monthly, and annual expenditure across user tiers based on real plan limits. Vercel Hobby is personal use only; commercial launches assume Pro tier.
          </p>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-900 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-3 py-3">DAU</th>
                <th className="px-3 py-3">Monthly Vol</th>
                <th className="px-3 py-3">Supabase Tier</th>
                <th className="px-3 py-3">Vercel Tier</th>
                <th className="px-3 py-3 text-right">LLM / Mo</th>
                <th className="px-3 py-3 text-right">Weekly (7d)</th>
                <th className="px-3 py-3 text-right">Monthly (30d)</th>
                <th className="px-3 py-3 text-right">Annual (365d)</th>
                <th className="px-3 py-3 text-right">Cost / 1k DAU</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {Object.entries(servingScenarios).map(([dauStr, sData]) => {
                const dau = parseInt(dauStr, 10);
                return (
                  <tr key={dauStr} className="hover:bg-slate-50">
                    <td className="px-3 py-3 font-semibold text-slate-900 font-mono">
                      {dau.toLocaleString()}
                    </td>
                    <td className="px-3 py-3 text-slate-600 font-mono text-[11px]">
                      {(sData.monthly_searches / 1_000_000).toFixed(1)}M req
                      <span className="block text-slate-400 font-sans text-[10px]">{sData.monthly_bandwidth_gb} GB</span>
                    </td>
                    <td className="px-3 py-3">
                      <span className="font-medium text-slate-800 block">{sData.supabase.tier}</span>
                      <span className="text-[10px] text-slate-400 block">{sData.supabase.plan_limit}</span>
                    </td>
                    <td className="px-3 py-3">
                      <span className="font-medium text-slate-800 block">{sData.vercel.tier}</span>
                      <span className="text-[10px] text-slate-400 block">{sData.vercel.plan_limit}</span>
                      {sData.vercel.basis ? (
                        <span className="text-[10px] text-amber-700 block mt-0.5">Basis: {sData.vercel.basis}</span>
                      ) : null}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-slate-600">
                      ${sData.breakdown_monthly_usd.llm.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-slate-700">
                      ${sData.total_weekly_cost_usd.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono font-bold text-slate-900">
                      ${sData.total_monthly_cost_usd.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono font-semibold text-slate-800">
                      ${sData.total_annual_cost_usd.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-sky-700 font-semibold">
                      ${sData.cost_per_1000_users_usd.toFixed(4)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Verified Sources & Pricing Basis */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-5 text-xs text-slate-600 space-y-3">
        <h3 className="font-bold text-slate-800 text-sm">
          Verified Pricing Sources and Plan Assumptions
        </h3>
        <ul className="list-disc list-inside space-y-1.5 text-slate-600">
          <li>
            <strong>Groq API List Prices</strong>: gpt-oss-20b ($0.075/1M in, $0.30/1M out), gpt-oss-120b ($0.15/1M in, $0.60/1M out), qwen3.8-27b ($0.80/1M in, $4.00/1M out). Source:{" "}
            <a href="https://groq.com/pricing/" target="_blank" rel="noopener noreferrer" className="text-sky-600 hover:underline">
              groq.com/pricing
            </a>{" "}
            (Last verified: 2026-11-19).
          </li>
          <li>
            <strong>Supabase Postgres</strong>: Free tier ($0/mo, 500 MB DB, 5 GB egress, 200 pool connections); Pro tier ($25/mo, 8 GB DB, 250 GB egress, 10,000 pool connections); Team tier ($599/mo, 16 GB DB, SOC2 compliance). Source:{" "}
            <a href="https://supabase.com/pricing" target="_blank" rel="noopener noreferrer" className="text-sky-600 hover:underline">
              supabase.com/pricing
            </a>{" "}
            (Last verified: 2026-11-19).
          </li>
          <li>
            <strong>Vercel Web Hosting</strong>: Hobby tier ($0/mo, 100 GB bandwidth, strictly personal and non-commercial); Pro tier ($20/seat/mo, 1 TB bandwidth); Enterprise tier (custom pricing, basis: estimated contract of $500/mo for 150M edge requests/mo, 1.5 TB bandwidth, and enterprise SLA). Source:{" "}
            <a href="https://vercel.com/pricing" target="_blank" rel="noopener noreferrer" className="text-sky-600 hover:underline">
              vercel.com/pricing
            </a>{" "}
            (Last verified: 2026-11-19).
          </li>
          <li>
            <strong>Commercial Deployment Note</strong>: Because Vercel Hobby is restricted to non-commercial personal projects, any real public launch requires at minimum Vercel Pro ($20/mo) and Supabase Pro ($25/mo).
          </li>
        </ul>
      </div>
    </div>
  );
}
