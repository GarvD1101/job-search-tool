"use client";

import { useEffect, useState } from "react";
import { Job } from "@/lib/types";
import { formatCity, formatPostType, formatRole } from "@/lib/taxonomy";
import {
  cleanJobSnippet,
  formatLocation,
  getCompanyMonogram,
  normalizeOriginBoard,
} from "@/lib/formatters";
import { ArrowUpRightIcon, CheckIcon, XIcon } from "./Icons";

interface JobDetailDrawerProps {
  job: Job | null;
  onClose: () => void;
}

export default function JobDetailDrawer({ job, onClose }: JobDetailDrawerProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    if (job) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [job, onClose]);

  if (!job) return null;

  const monogram = getCompanyMonogram(job.company);
  const locationDisplay = formatLocation(job.location_text || formatCity(job.city, job.is_remote));
  const roleDisplay = formatRole(job.role);
  const postTypeDisplay = formatPostType(job.post_type).toUpperCase();
  const sourceDisplay = normalizeOriginBoard(job.origin_site || job.source);
  const cleanedDescription = cleanJobSnippet(job.description);

  const handleCopy = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(job.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink/30 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <aside
        className="relative z-50 w-full max-w-xl bg-surface border-l border-ink flex flex-col h-full overflow-hidden shadow-none"
        aria-label="Job Details"
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-grid bg-canvas flex items-start justify-between gap-4">
          <div className="flex items-start space-x-3 min-w-0">
            <div className="w-9 h-9 border border-grid bg-surface font-mono text-xs font-bold flex items-center justify-center shrink-0 text-ink">
              {monogram}
            </div>
            <div className="min-w-0">
              <h2 className="text-base sm:text-lg font-bold text-ink leading-snug truncate">
                {job.title}
              </h2>
              <p className="font-mono text-xs text-ink-secondary mt-0.5 truncate">
                {job.company}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 border border-grid hover:border-ink bg-surface text-ink-muted hover:text-ink transition-colors rounded-[2px] shrink-0"
            aria-label="Close drawer"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Spec Grid */}
        <div className="grid grid-cols-2 gap-px bg-grid border-b border-grid font-mono text-xs shrink-0">
          <div className="bg-surface p-3">
            <span className="text-[10px] text-ink-muted uppercase tracking-wider block">
              LOCATION
            </span>
            <span className="font-semibold text-ink block mt-0.5 truncate">
              {locationDisplay}
            </span>
          </div>

          <div className="bg-surface p-3">
            <span className="text-[10px] text-ink-muted uppercase tracking-wider block">
              ROLE TAXONOMY
            </span>
            <span className="font-semibold text-ink block mt-0.5 truncate">
              {roleDisplay}
            </span>
          </div>

          <div className="bg-surface p-3">
            <span className="text-[10px] text-ink-muted uppercase tracking-wider block">
              POST TYPE
            </span>
            <span className="font-semibold text-ink block mt-0.5 truncate">
              {postTypeDisplay}
            </span>
          </div>

          <div className="bg-surface p-3">
            <span className="text-[10px] text-ink-muted uppercase tracking-wider block">
              SOURCE PORTAL
            </span>
            <span className="font-semibold text-ink block mt-0.5 truncate">
              {sourceDisplay}
            </span>
          </div>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted border-b border-grid pb-1.5">
            01 // DESCRIPTION SPECIFICATION
          </div>

          <div className="text-sm leading-relaxed text-ink-secondary whitespace-pre-line font-sans">
            {cleanedDescription || "No detailed description provided in original listing."}
          </div>

          <div className="pt-4 border-t border-grid">
            <div className="font-mono text-[10px] text-ink-muted bg-canvas p-3 border border-grid rounded-[2px] leading-relaxed">
              <span className="font-semibold text-ink block mb-0.5">
                TELEMETRY NOTE
              </span>
              Role, city, and fresher parameters are classified by openai/gpt-oss-20b against the canonical project taxonomy. Prior experience thresholds and non-job advertisements are filtered deterministically before tagging.
            </div>
          </div>
        </div>

        {/* Sticky Action Footer */}
        <div className="p-4 border-t border-grid bg-surface flex items-center gap-3 shrink-0">
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-amber-signal hover:bg-amber-hover text-white font-mono font-semibold py-2.5 px-4 text-xs tracking-wider uppercase text-center flex items-center justify-center gap-1.5 rounded-[2px] transition-colors"
          >
            <span>OPEN ORIGINAL POSTING</span>
            <ArrowUpRightIcon size={14} />
          </a>

          <button
            type="button"
            onClick={handleCopy}
            className="border border-grid hover:border-ink bg-canvas hover:bg-surface text-ink font-mono text-xs py-2.5 px-3.5 rounded-[2px] transition-colors flex items-center gap-1 shrink-0"
          >
            {copied ? (
              <>
                <CheckIcon size={14} className="text-status-live" />
                <span>COPIED</span>
              </>
            ) : (
              <span>COPY LINK</span>
            )}
          </button>
        </div>
      </aside>
    </div>
  );
}
