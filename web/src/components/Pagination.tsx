"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

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

  return (
    <nav
      role="navigation"
      aria-label="Pagination"
      className="flex items-center justify-between border-t border-slate-200 px-4 py-4 sm:px-0 mt-8"
    >
      <div className="flex w-0 flex-1">
        {currentPage > 1 ? (
          <Link
            href={createPageUrl(currentPage - 1)}
            className="inline-flex items-center border-t-2 border-transparent pr-1 pt-4 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-slate-800"
          >
            &larr; Previous
          </Link>
        ) : (
          <span className="inline-flex items-center border-t-2 border-transparent pr-1 pt-4 text-sm font-medium text-slate-300 cursor-not-allowed">
            &larr; Previous
          </span>
        )}
      </div>

      <div className="hidden md:flex">
        <span className="inline-flex items-center border-t-2 border-sky-500 px-4 pt-4 text-sm font-medium text-sky-600">
          Page {currentPage} of {totalPages}
        </span>
      </div>

      <div className="flex w-0 flex-1 justify-end">
        {currentPage < totalPages ? (
          <Link
            href={createPageUrl(currentPage + 1)}
            className="inline-flex items-center border-t-2 border-transparent pl-1 pt-4 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-slate-800"
          >
            Next &rarr;
          </Link>
        ) : (
          <span className="inline-flex items-center border-t-2 border-transparent pl-1 pt-4 text-sm font-medium text-slate-300 cursor-not-allowed">
            Next &rarr;
          </span>
        )}
      </div>
    </nav>
  );
}
