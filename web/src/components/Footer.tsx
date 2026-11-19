import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-grid bg-surface mt-16 py-8 text-xs text-ink-secondary">
      <div className="max-w-[1380px] mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <p className="font-mono text-xs font-semibold text-ink">
            FRESHER RADAR <span className="font-normal text-ink-muted">// Spec-Grade Index</span>
          </p>
          <p className="text-ink-secondary text-[11px] leading-relaxed">
            Entry-level jobs and internships in India (0-1 years). Sources: Jooble API and Greenhouse public ATS endpoints.
          </p>
          <p className="font-mono text-[10px] text-ink-muted">
            Taxonomy classification: openai/gpt-oss-20b · Cache TTL: 300s · Zero tracking
          </p>
        </div>

        <div className="flex items-center space-x-6 font-mono text-[11px] tracking-wider shrink-0 pt-2 md:pt-0">
          <Link
            href="/"
            className="text-ink-secondary hover:text-amber-signal transition-colors"
          >
            01 LIVE JOBS
          </Link>
          <span className="text-grid">/</span>
          <Link
            href="/stats"
            className="text-ink-secondary hover:text-amber-signal transition-colors"
          >
            02 STATS
          </Link>
          <span className="text-grid">/</span>
          <Link
            href="/costs"
            className="text-ink-secondary hover:text-amber-signal transition-colors"
          >
            03 COSTS
          </Link>
        </div>
      </div>
    </footer>
  );
}
