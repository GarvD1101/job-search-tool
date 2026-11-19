import Link from "next/link";
import { getLastRefresh } from "@/lib/jobs";
import HeaderNav from "./HeaderNav";

function formatHeaderTime(iso: string | null): string {
  if (!iso) return "DAILY 09:00 IST";
  const date = new Date(iso);
  const datePart = date.toLocaleDateString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
  });
  const timePart = date.toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${datePart}, ${timePart} IST`;
}

export default async function Header() {
  const lastRun = await getLastRefresh().catch(() => null);
  const timeDisplay = formatHeaderTime(
    lastRun?.finished_at || lastRun?.started_at || null
  );

  return (
    <header className="sticky top-0 z-30 w-full bg-surface border-b border-grid">
      <div className="max-w-[1380px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand Lockup */}
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 bg-amber-signal shrink-0 rounded-[1px]" />
            <span className="font-mono text-sm font-semibold tracking-tight text-ink">
              FRESHER RADAR
            </span>
          </Link>
          <span className="hidden sm:block h-3.5 w-px bg-grid" />
          <span className="hidden sm:block font-mono text-[10px] text-ink-muted tracking-wider uppercase">
            IND // 0-1 YRS
          </span>
        </div>

        {/* Center Navigation */}
        <div className="h-full">
          <HeaderNav />
        </div>

        {/* Right Status Indicator */}
        <div className="flex items-center space-x-2 font-mono text-[11px] text-ink-muted tabular-nums">
          <span className="w-1.5 h-1.5 bg-status-live rounded-none shrink-0" />
          <span className="hidden md:inline font-semibold text-ink">SYNCED</span>
          <span className="hidden sm:inline text-grid">/</span>
          <span className="truncate max-w-[130px] sm:max-w-none">
            {timeDisplay}
          </span>
        </div>
      </div>
    </header>
  );
}
