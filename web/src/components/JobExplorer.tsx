"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Job } from "@/lib/types";
import JobFilters from "./JobFilters";
import JobRow from "./JobRow";
import JobDetailDrawer from "./JobDetailDrawer";
import Pagination from "./Pagination";
import { SearchIcon } from "./Icons";

interface JobExplorerProps {
  jobs: Job[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export default function JobExplorer({
  jobs,
  total,
  page,
  pageSize,
  totalPages,
}: JobExplorerProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const currentQ = searchParams.get("q") || "";
  const [searchValue, setSearchValue] = useState(currentQ);

  // Synchronize searchValue when URL searchParams change
  useEffect(() => {
    setSearchValue(searchParams.get("q") || "");
  }, [searchParams]);

  // Global '/' keyboard shortcut to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSearchChange = (val: string) => {
    setSearchValue(val);
    const params = new URLSearchParams(searchParams.toString());
    if (val.trim()) {
      params.set("q", val.trim());
    } else {
      params.delete("q");
    }
    params.delete("page");
    startTransition(() => {
      router.push(`/?${params.toString()}`);
    });
  };

  const startItem = total > 0 ? (page - 1) * pageSize + 1 : 0;
  const endItem = Math.min(page * pageSize, total);
  const pagePadded = String(page).padStart(2, "0");
  const totalPagesPadded = String(totalPages).padStart(2, "0");

  return (
    <div className="space-y-4">
      {/* Top Command & Summary Bar */}
      <section
        aria-label="Search and Index Command Bar"
        className="bg-surface border border-grid p-3 sm:px-4 sm:py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
      >
        <div className="flex items-center space-x-3">
          <h1 className="font-mono text-xs sm:text-sm font-bold uppercase tracking-tight text-ink flex items-center gap-2">
            <span>01 // LIVE FRESHER INDEX</span>
          </h1>
          <span className="bg-ink text-white font-mono text-[11px] px-2 py-0.5 rounded-[2px] font-semibold tracking-wider">
            {total} ACTIVE
          </span>
        </div>

        <div className="relative w-full sm:w-[360px]">
          <div className="absolute left-3 top-2.5 text-ink-muted pointer-events-none">
            <SearchIcon size={14} />
          </div>
          <input
            ref={searchInputRef}
            type="search"
            value={searchValue}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search title, company, or skill..."
            className="w-full pl-8 pr-8 py-1.5 text-xs font-sans bg-canvas border border-grid rounded-[2px] focus:outline-none focus:border-ink focus:bg-surface text-ink placeholder:text-ink-muted transition-all"
          />
          <kbd className="absolute right-2.5 top-1.5 border border-grid bg-surface px-1.5 py-0.5 font-mono text-[10px] text-ink-muted rounded-[2px] pointer-events-none hidden sm:inline-block">
            /
          </kbd>
        </div>
      </section>

      {/* Two-Pane Layout */}
      <div className="lg:grid lg:grid-cols-[260px_1fr] border border-grid bg-grid gap-px">
        {/* Left Pane: Faceted Filter Rail */}
        <JobFilters />

        {/* Right Pane: Spec-Sheet Feed */}
        <main className="bg-surface flex flex-col min-w-0">
          {/* Feed Column Header Bar */}
          <div className="bg-canvas border-b border-grid px-4 py-2 flex items-center justify-between font-mono text-[11px] text-ink-muted shrink-0">
            <span className="font-semibold uppercase tracking-wider">
              SHOWING {startItem} to {endItem} OF {total} VERIFIED POSITIONS
            </span>
            <span>
              PAGE {pagePadded} / {totalPagesPadded}
            </span>
          </div>

          {/* Job Feed Rows */}
          {jobs.length > 0 ? (
            <div className="divide-y divide-grid bg-surface">
              {jobs.map((job) => (
                <JobRow
                  key={job.id}
                  job={job}
                  onSelect={(j) => setSelectedJob(j)}
                />
              ))}
            </div>
          ) : (
            <div className="bg-surface p-12 text-center font-mono space-y-2">
              <div className="text-amber-signal text-sm font-bold">
                00 // NO POSITIONS FOUND
              </div>
              <p className="text-xs text-ink-secondary max-w-sm mx-auto font-sans leading-relaxed">
                No active postings match the current filter set. Try clearing query parameters or broadening role and city selections.
              </p>
            </div>
          )}

          {/* Precision Pagination Bar */}
          <Pagination currentPage={page} totalPages={totalPages} />
        </main>
      </div>

      {/* Slide-Over Detail Drawer */}
      <JobDetailDrawer
        job={selectedJob}
        onClose={() => setSelectedJob(null)}
      />
    </div>
  );
}
