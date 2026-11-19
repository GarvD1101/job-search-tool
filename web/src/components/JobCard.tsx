import { formatCity, formatPostType, formatRole } from "@/lib/taxonomy";
import { Job } from "@/lib/types";

function formatDate(iso: string | null): string {
  if (!iso) return "Recently";
  const date = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor(
    (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "1 day ago";
  if (diffDays < 30) return `${diffDays} days ago`;

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

export default function JobCard({ job }: { job: Job }) {
  const sourceName = job.origin_site && job.origin_site !== "unknown"
    ? job.origin_site
    : job.source;

  return (
    <article className="bg-white rounded-lg border border-slate-200 p-5 hover:border-slate-300 transition-colors flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-semibold text-slate-900 leading-snug line-clamp-2">
              {job.title}
            </h2>
            <p className="text-sm font-medium text-slate-600 mt-1 truncate">
              {job.company}
            </p>
          </div>

          <span className="shrink-0 text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
            {sourceName}
          </span>
        </div>

        {/* Location & Metadata */}
        <div className="flex items-center space-x-2 text-xs text-slate-500 mt-3">
          <span className="font-medium text-slate-700">
            {formatCity(job.city, job.is_remote)}
          </span>
          {job.location_text && (
            <span className="truncate text-slate-400">
              ({job.location_text})
            </span>
          )}
        </div>

        {/* Snippet */}
        {job.description && (
          <p className="text-xs text-slate-600 mt-3 line-clamp-3 leading-relaxed">
            {job.description}
          </p>
        )}
      </div>

      <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-100">
            {formatRole(job.role)}
          </span>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
            {formatPostType(job.post_type)}
          </span>
          <span className="text-xs text-slate-400 ml-1">
            {formatDate(job.posted_at)}
          </span>
        </div>

        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 inline-flex items-center text-xs font-semibold text-sky-600 hover:text-sky-800 hover:underline"
        >
          Open original &rarr;
        </a>
      </div>
    </article>
  );
}
