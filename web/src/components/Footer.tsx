import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white mt-12 py-8 text-xs text-slate-500">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <p className="font-medium text-slate-700">
            Fresher Radar; entry-level jobs and internships in India.
          </p>
          <p className="mt-1">
            Data sourced from public boards via Jooble API and Greenhouse public endpoints.
          </p>
          <p className="mt-0.5 text-slate-400">
            Role, city, and fresher classifications are tagged by an LLM (openai/gpt-oss-20b).
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <Link href="/" className="hover:text-slate-900 transition-colors">
            Jobs
          </Link>
          <span className="text-slate-300">|</span>
          <Link href="/stats" className="hover:text-slate-900 transition-colors">
            Pipeline Stats
          </Link>
        </div>
      </div>
    </footer>
  );
}
