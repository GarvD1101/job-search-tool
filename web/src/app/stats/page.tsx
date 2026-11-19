import { getStats } from "@/lib/jobs";
import { formatCity, formatRole } from "@/lib/taxonomy";

export const revalidate = 300;

export default async function StatsPage() {
  const stats = await getStats();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Pipeline & System Statistics
        </h1>
        <p className="text-sm text-slate-600 mt-1.5">
          Live verification metrics from the database; refreshes every 5 minutes.
        </p>
      </div>

      {/* Top Level Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider block">
            Active Jobs
          </span>
          <span className="text-2xl font-bold text-slate-900 mt-1 block">
            {stats.total_active}
          </span>
          <span className="text-xs text-emerald-600 font-medium mt-0.5 block">
            Verified freshers
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider block">
            Raw Posts Fetched
          </span>
          <span className="text-2xl font-bold text-slate-900 mt-1 block">
            {stats.total_raw}
          </span>
          <span className="text-xs text-slate-500 mt-0.5 block">
            7-day rolling window
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider block">
            Duplicates Removed
          </span>
          <span className="text-2xl font-bold text-slate-900 mt-1 block">
            {stats.total_duplicates}
          </span>
          <span className="text-xs text-slate-500 mt-0.5 block">
            2-tier dedup engine
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider block">
            Bypassed LLM
          </span>
          <span className="text-2xl font-bold text-sky-600 mt-1 block">
            {stats.non_llm_share_pct}%
          </span>
          <span className="text-xs text-slate-500 mt-0.5 block">
            Filtered by deterministic rules
          </span>
        </div>
      </div>

      {/* LLM Usage & List Price Cost */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="text-base font-bold text-slate-900 mb-4">
          LLM Tagging Usage & List-Price Spend (openai/gpt-oss-20b)
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs">
          <div>
            <span className="text-slate-500 block">Total API Calls</span>
            <span className="text-lg font-semibold text-slate-900 mt-1 block">
              {stats.llm_usage.total_calls}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Input Tokens</span>
            <span className="text-lg font-semibold text-slate-900 mt-1 block">
              {stats.llm_usage.input_tokens.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Output Tokens</span>
            <span className="text-lg font-semibold text-slate-900 mt-1 block">
              {stats.llm_usage.output_tokens.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Reasoning Tokens</span>
            <span className="text-lg font-semibold text-slate-900 mt-1 block">
              {stats.llm_usage.reasoning_tokens.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">List-Price Cost</span>
            <span className="text-lg font-bold text-emerald-600 mt-1 block">
              ${stats.llm_usage.list_price_cost.toFixed(4)}
            </span>
          </div>
        </div>
        <p className="text-xs text-slate-400 mt-3 border-t border-slate-100 pt-3">
          Groq list prices: $0.075 per 1M input tokens, $0.30 per 1M output tokens. Reasoning tokens are billed as output tokens.
        </p>
      </div>

      {/* Grid of Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Source & Origin Site */}
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="text-sm font-bold text-slate-900 mb-3">
            Active Jobs by Source Platform
          </h2>
          <div className="space-y-2 mb-6">
            {stats.source_counts.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                <span className="font-medium text-slate-700 capitalize">{s.name}</span>
                <span className="font-semibold text-slate-900">{s.count}</span>
              </div>
            ))}
          </div>

          <h2 className="text-sm font-bold text-slate-900 mb-3">
            Top Origin Boards / Portals
          </h2>
          <div className="space-y-1.5">
            {stats.origin_counts.slice(0, 10).map((o) => (
              <div key={o.name} className="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                <span className="font-mono text-slate-600 truncate max-w-xs">{o.name}</span>
                <span className="font-semibold text-slate-900">{o.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Rule Rejections */}
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="text-sm font-bold text-slate-900 mb-3">
            Posts Rejected by Rule Reason
          </h2>
          <div className="space-y-2">
            {stats.reject_reasons.map((r) => (
              <div key={r.reason} className="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                <span className="font-mono text-slate-700">{r.reason}</span>
                <span className="font-semibold text-slate-900">{r.count}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-4">
            Deterministic rule filters reject senior positions, experience thresholds, and stale posts before calling LLM APIs.
          </p>
        </div>

        {/* Role Distribution */}
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="text-sm font-bold text-slate-900 mb-3">
            Active Jobs by Role Taxonomy
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {stats.role_counts.map((r) => (
              <div key={r.name} className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-700 truncate">{formatRole(r.name)}</span>
                <span className="font-semibold text-slate-900 ml-2">{r.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* City Distribution */}
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="text-sm font-bold text-slate-900 mb-3">
            Active Jobs by Metro Area
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {stats.city_counts.map((c) => (
              <div key={c.name} className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-700 truncate">{formatCity(c.name)}</span>
                <span className="font-semibold text-slate-900 ml-2">{c.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline Runs by Event Trigger */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 md:col-span-2">
          <h2 className="text-sm font-bold text-slate-900 mb-3">
            Pipeline Runs by Event Trigger
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <span className="text-slate-500 font-medium block mb-2">Run Count by Trigger Type</span>
              {stats.runs_by_event && stats.runs_by_event.length > 0 ? (
                stats.runs_by_event.map((r) => (
                  <div key={r.event} className="flex items-center justify-between py-1 border-b border-slate-100">
                    <span className="font-mono text-slate-700">{r.event}</span>
                    <span className="font-semibold text-slate-900">{r.count}</span>
                  </div>
                ))
              ) : (
                <p className="text-slate-500">No runs recorded.</p>
              )}
            </div>
            <div className="bg-slate-50 border border-slate-100 rounded p-3 space-y-2">
              <div>
                <span className="text-slate-500 block">Latest Scheduled Run</span>
                <span className="text-sm font-bold text-slate-900 block mt-0.5">
                  {stats.latest_scheduled_run
                    ? new Date(stats.latest_scheduled_run).toLocaleString("en-IN", {
                        timeZone: "Asia/Kolkata",
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }) + " IST"
                    : "Pending first scheduled run"}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-200">
                <span className="text-slate-500 block">Latest Overall Run</span>
                <span className="text-sm font-bold text-slate-900 block mt-0.5">
                  {stats.last_run?.started_at
                    ? new Date(stats.last_run.started_at).toLocaleString("en-IN", {
                        timeZone: "Asia/Kolkata",
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }) + " IST"
                    : "None recorded"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
