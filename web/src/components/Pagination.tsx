"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChevronLeftIcon, ChevronRightIcon } from "./Icons";

export default function Pagination({
  currentPage,
  totalPages,
}: {
  currentPage: number;
  totalPages: number;
}) {
  const searchParams = useSearchParams();

  if (totalPages <= 1) return null;

  const createPageUrl = (pageNumber: number) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", pageNumber.toString());
    return `/?${params.toString()}`;
  };

  const currPadded = String(currentPage).padStart(2, "0");
  const totalPadded = String(totalPages).padStart(2, "0");

  return (
    <nav
      role="navigation"
      aria-label="Pagination Navigation"
      className="bg-canvas border-t border-grid px-4 py-3 flex items-center justify-between font-mono text-xs"
    >
      <div>
        {currentPage > 1 ? (
          <Link
            href={createPageUrl(currentPage - 1)}
            className="border border-grid hover:border-ink bg-surface px-3 py-1.5 rounded-[2px] text-ink hover:text-amber-signal transition-colors inline-flex items-center gap-1 font-semibold"
          >
            <ChevronLeftIcon size={13} />
            <span>PREV</span>
          </Link>
        ) : (
          <span className="border border-grid/60 bg-surface/50 px-3 py-1.5 rounded-[2px] text-ink-muted/50 cursor-not-allowed inline-flex items-center gap-1">
            <ChevronLeftIcon size={13} />
            <span>PREV</span>
          </span>
        )}
      </div>

      <div className="font-semibold text-ink tracking-wider">
        PAGE {currPadded} OF {totalPadded}
      </div>

      <div>
        {currentPage < totalPages ? (
          <Link
            href={createPageUrl(currentPage + 1)}
            className="border border-grid hover:border-ink bg-surface px-3 py-1.5 rounded-[2px] text-ink hover:text-amber-signal transition-colors inline-flex items-center gap-1 font-semibold"
          >
            <span>NEXT</span>
            <ChevronRightIcon size={13} />
          </Link>
        ) : (
          <span className="border border-grid/60 bg-surface/50 px-3 py-1.5 rounded-[2px] text-ink-muted/50 cursor-not-allowed inline-flex items-center gap-1">
            <span>NEXT</span>
            <ChevronRightIcon size={13} />
          </span>
        )}
      </div>
    </nav>
  );
}
