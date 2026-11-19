"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";
import { CITIES, POST_TYPES, ROLES } from "@/lib/taxonomy";

export default function SearchAndFilters({
  totalCount,
}: {
  totalCount: number;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const currentQ = searchParams.get("q") || "";
  const currentRole = searchParams.get("role") || "";
  const currentCity = searchParams.get("city") || "";
  const currentPostType = searchParams.get("post_type") || "";

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page"); // reset to page 1 on filter change
      startTransition(() => {
        router.push(`/?${params.toString()}`);
      });
    },
    [router, searchParams]
  );

  const resetAll = useCallback(() => {
    startTransition(() => {
      router.push("/");
    });
  }, [router]);

  const hasFilters = Boolean(
    currentQ || currentRole || currentCity || currentPostType
  );

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5 mb-6">
      {/* Search Input */}
      <div className="mb-4">
        <label htmlFor="search-input" className="sr-only">
          Search job title, skills, or company
        </label>
        <div className="relative">
          <input
            id="search-input"
            type="search"
            placeholder="Search by title, skills, or company..."
            defaultValue={currentQ}
            onChange={(e) => updateParam("q", e.target.value)}
            className="w-full pl-4 pr-10 py-2.5 text-sm bg-slate-50 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 focus:bg-white transition-all text-slate-900"
          />
          {isPending && (
            <div className="absolute right-3 top-3 text-xs text-slate-400">
              ...
            </div>
          )}
        </div>
      </div>

      {/* Filter Selects */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Role Select */}
        <div>
          <label htmlFor="role-select" className="block text-xs font-medium text-slate-600 mb-1">
            Role
          </label>
          <select
            id="role-select"
            value={currentRole}
            onChange={(e) => updateParam("role", e.target.value)}
            className="w-full py-2 px-3 text-sm bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
          >
            <option value="">All Roles</option>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {/* City Select */}
        <div>
          <label htmlFor="city-select" className="block text-xs font-medium text-slate-600 mb-1">
            City
          </label>
          <select
            id="city-select"
            value={currentCity}
            onChange={(e) => updateParam("city", e.target.value)}
            className="w-full py-2 px-3 text-sm bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
          >
            <option value="">All Cities</option>
            {CITIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Post Type Select */}
        <div>
          <label htmlFor="type-select" className="block text-xs font-medium text-slate-600 mb-1">
            Post Type
          </label>
          <select
            id="type-select"
            value={currentPostType}
            onChange={(e) => updateParam("post_type", e.target.value)}
            className="w-full py-2 px-3 text-sm bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 text-slate-800"
          >
            <option value="">All Types</option>
            {POST_TYPES.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Result Count and Clear Filters */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 text-xs">
        <span className="font-medium text-slate-600">
          Showing <strong className="text-slate-900">{totalCount}</strong> active fresher {totalCount === 1 ? "position" : "positions"}
        </span>

        {hasFilters && (
          <button
            type="button"
            onClick={resetAll}
            className="text-sky-600 hover:text-sky-800 font-medium hover:underline"
          >
            Clear all filters
          </button>
        )}
      </div>
    </div>
  );
}
