import Link from "next/link";
import { getLastRefresh } from "@/lib/jobs";

function formatTimestamp(iso: string | null): string {
  if (!iso) return "Pending";
  const date = new Date(iso);
  return date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }) + " IST";
}

export default async function Header() {
  const lastRun = await getLastRefresh().catch(() => null);

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-2">
            <span className="font-bold text-xl text-slate-900 tracking-tight">
              Fresher Radar
            </span>
            <span className="text-xs bg-sky-100 text-sky-800 font-medium px-2 py-0.5 rounded-full">
              Live
            </span>
          </Link>
          <nav className="hidden sm:flex items-center space-x-4 text-sm font-medium">
            <Link
              href="/"
              className="text-slate-700 hover:text-sky-600 transition-colors"
            >
              Jobs
            </Link>
            <Link
              href="/stats"
              className="text-slate-700 hover:text-sky-600 transition-colors"
            >
              Stats
            </Link>
          </nav>
        </div>

        <div className="flex items-center space-x-4 text-xs sm:text-sm">
          <Link
            href="/stats"
            className="sm:hidden font-medium text-slate-700 hover:text-sky-600"
          >
            Stats
          </Link>
          {lastRun ? (
            <div className="text-right">
              <span className="text-slate-500 block text-xs">Last refreshed</span>
              <span className="text-slate-800 font-medium">
                {formatTimestamp(lastRun.finished_at || lastRun.started_at)}
              </span>
            </div>
          ) : (
            <div className="text-right text-slate-400 text-xs">
              Refreshed daily
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
