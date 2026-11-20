"use client";

import React from "react";
import { Job } from "@/lib/types";
import { formatCity, formatPostType, formatRole } from "@/lib/taxonomy";
import {
  cleanJobSnippet,
  formatLocation,
  getCompanyMonogram,
} from "@/lib/formatters";
import { ArrowUpRightIcon } from "./Icons";

interface JobRowProps {
  job: Job;
  onSelect: (job: Job) => void;
}

function formatRecency(iso: string | null): { text: string; isToday: boolean } {
  if (!iso) return { text: "Updated recently", isToday: false };
  const date = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor(
    (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (diffDays <= 0) return { text: "Updated Today", isToday: true };
  if (diffDays === 1) return { text: "Updated 1d ago", isToday: false };
  if (diffDays < 30) return { text: `Updated ${diffDays}d ago`, isToday: false };
  return {
    text: `Updated ${date.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}`,
    isToday: false,
  };
}

export default function JobRow({ job, onSelect }: JobRowProps) {
  const monogram = getCompanyMonogram(job.company);
  const locationText = formatLocation(
    job.location_text || formatCity(job.city, job.is_remote)
  );
  const roleText = formatRole(job.role);
  const postTypeText = formatPostType(job.post_type).toUpperCase();
  const recency = formatRecency(job.posted_at || job.first_seen_at);
  const snippet = cleanJobSnippet(job.description);

  const isGreenhouse =
    job.source === "greenhouse" ||
    (job.origin_site && job.origin_site.toLowerCase().includes("greenhouse"));

  const sourceLabel = isGreenhouse
    ? "GREENHOUSE · DIRECT ATS"
    : job.origin_site && job.origin_site !== "unknown"
    ? job.origin_site
    : job.source;

  const postTypeBadgeStyle =
    job.post_type === "internship"
      ? "bg-amber-wash text-ink border-amber-signal/40 font-semibold"
      : job.post_type === "trainee"
      ? "bg-canvas text-ink-secondary border-grid"
      : "bg-surface text-ink-secondary border-grid";

  return (
    <article
      onClick={() => onSelect(job)}
      className="p-4 sm:p-5 hover:bg-surface-muted/60 transition-colors cursor-pointer group flex flex-col justify-between"
    >
      <div>
        {/* Top Line */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start space-x-3 min-w-0">
            <div className="w-7 h-7 border border-grid bg-canvas font-mono text-[11px] font-semibold flex items-center justify-center shrink-0 text-ink group-hover:border-ink transition-colors">
              {monogram}
            </div>
            <div className="min-w-0">
              <h3 className="text-[15px] font-semibold text-ink group-hover:text-amber-signal transition-colors truncate">
                {job.title}
              </h3>
              <p className="text-xs sm:text-sm text-ink-secondary truncate mt-0.5 font-medium">
                {job.company}
              </p>
            </div>
          </div>

          <div className="shrink-0 flex items-center font-mono text-[11px] text-ink-muted tabular-nums whitespace-nowrap">
            {recency.isToday && (
              <span className="w-1.5 h-1.5 bg-amber-signal rounded-none inline-block mr-1.5" />
            )}
            <span>{recency.text}</span>
          </div>
        </div>

        {/* Middle Line: Sanitized Snippet */}
        {snippet && (
          <p className="text-[13px] leading-relaxed text-ink-secondary pl-10 mt-1.5 line-clamp-2">
            {snippet}
          </p>
        )}
      </div>

      {/* Bottom Telemetry Strip */}
      <div className="pl-10 mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-grid/40">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="rounded-[2px] border border-grid bg-surface px-1.5 py-0.5 font-mono text-[11px] text-ink-secondary">
            {locationText}
          </span>
          <span className="rounded-[2px] border border-grid bg-surface px-1.5 py-0.5 font-mono text-[11px] text-ink-secondary">
            {roleText}
          </span>
          <span
            className={`rounded-[2px] border px-1.5 py-0.5 font-mono text-[11px] ${postTypeBadgeStyle}`}
          >
            {postTypeText}
          </span>
          <span
            className={`rounded-[2px] border px-1.5 py-0.5 font-mono text-[11px] ${
              isGreenhouse
                ? "border-status-live/40 text-status-live bg-white font-semibold"
                : "border-grid bg-surface text-ink-muted"
            }`}
          >
            {sourceLabel}
          </span>
        </div>

        <div className="flex items-center space-x-3 shrink-0 font-mono text-[11px]">
          <span className="text-ink-muted group-hover:text-ink transition-colors uppercase tracking-wider underline underline-offset-2">
            INSPECT
          </span>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-amber-signal hover:text-amber-hover font-semibold flex items-center gap-1 transition-colors"
          >
            <span>OPEN</span>
            <ArrowUpRightIcon size={12} />
          </a>
        </div>
      </div>
    </article>
  );
}
