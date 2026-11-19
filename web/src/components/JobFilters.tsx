"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";
import { CITIES, POST_TYPES, ROLES } from "@/lib/taxonomy";

const QUICK_ROLES = [
  { value: "software_dev", label: "Software Dev" },
  { value: "data_analytics", label: "Data & Analytics" },
  { value: "it_devops_security", label: "DevOps & IT" },
  { value: "sales_bd", label: "Sales & BD" },
  { value: "customer_support", label: "Support" },
  { value: "marketing", label: "Marketing" },
];

const QUICK_CITIES = [
  { value: "bengaluru", label: "Bengaluru" },
  { value: "mumbai", label: "Mumbai" },
  { value: "delhi_ncr", label: "Delhi NCR" },
  { value: "hyderabad", label: "Hyderabad" },
  { value: "pune", label: "Pune" },
  { value: "remote", label: "Remote" },
];

export default function JobFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

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
      params.delete("page"); // reset pagination on filter change
      startTransition(() => {
        router.push(`/?${params.toString()}`);
      });
    },
    [router, searchParams]
  );

  const resetAll = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("role");
    params.delete("city");
    params.delete("post_type");
    params.delete("page");
    startTransition(() => {
      const q = params.get("q");
      router.push(q ? `/?q=${encodeURIComponent(q)}` : "/");
    });
  }, [router, searchParams]);

  const activeCount = [currentRole, currentCity, currentPostType].filter(Boolean).length;

  return (
    <aside className="bg-surface p-4 text-xs font-sans lg:sticky lg:top-14 lg:max-h-[calc(100vh-3.5rem)] lg:overflow-y-auto space-y-4">
      {/* Active Filters Header */}
      <div className="flex items-center justify-between border-b border-grid pb-2.5">
        <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-muted">
          01 // FILTERS
          {activeCount > 0 && (
            <span className="ml-1.5 text-ink font-bold">({activeCount})</span>
          )}
        </div>

        {activeCount > 0 && (
          <button
            type="button"
            onClick={resetAll}
            className="font-mono text-[10px] text-amber-signal hover:underline uppercase tracking-wider font-semibold"
          >
            CLEAR ALL
          </button>
        )}
      </div>

      {/* Post Type Segmented Buttons */}
      <div className="border-b border-grid pb-3.5">
        <label className="font-mono text-[10px] uppercase text-ink-muted tracking-wider block mb-2 font-semibold">
          POST TYPE
        </label>
        <div className="grid grid-cols-2 gap-1 font-mono text-[11px]">
          <button
            type="button"
            onClick={() => updateParam("post_type", "")}
            className={`py-1.5 px-2 border rounded-[2px] transition-colors ${
              !currentPostType
                ? "bg-ink text-white border-ink font-semibold"
                : "bg-canvas text-ink-secondary border-grid hover:border-ink"
            }`}
          >
            ALL
          </button>
          {POST_TYPES.map((pt) => (
            <button
              key={pt.value}
              type="button"
              onClick={() => updateParam("post_type", pt.value)}
              className={`py-1.5 px-2 border rounded-[2px] transition-colors uppercase ${
                currentPostType === pt.value
                  ? "bg-ink text-white border-ink font-semibold"
                  : "bg-canvas text-ink-secondary border-grid hover:border-ink"
              }`}
            >
              {pt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Role Taxonomy */}
      <div className="border-b border-grid pb-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="role-select"
            className="font-mono text-[10px] uppercase text-ink-muted tracking-wider font-semibold"
          >
            ROLE TAXONOMY
          </label>
          {currentRole && (
            <button
              type="button"
              onClick={() => updateParam("role", "")}
              className="font-mono text-[10px] text-ink-muted hover:text-ink underline"
            >
              RESET
            </button>
          )}
        </div>

        <select
          id="role-select"
          value={currentRole}
          onChange={(e) => updateParam("role", e.target.value)}
          className="w-full p-2 bg-canvas border border-grid rounded-[2px] text-xs text-ink focus:outline-none focus:border-ink font-sans"
        >
          <option value="">All Roles (22 Categories)</option>
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>

        {/* Quick Role Chips */}
        <div className="flex flex-wrap gap-1 pt-1">
          {QUICK_ROLES.map((r) => {
            const isSelected = currentRole === r.value;
            return (
              <button
                key={r.value}
                type="button"
                onClick={() => updateParam("role", isSelected ? "" : r.value)}
                className={`text-[10px] font-mono px-1.5 py-0.5 border rounded-[2px] transition-colors ${
                  isSelected
                    ? "bg-ink text-white border-ink font-semibold"
                    : "bg-canvas text-ink-secondary border-grid hover:border-ink"
                }`}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Metro Area / City */}
      <div className="border-b border-grid pb-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="city-select"
            className="font-mono text-[10px] uppercase text-ink-muted tracking-wider font-semibold"
          >
            METRO AREA
          </label>
          {currentCity && (
            <button
              type="button"
              onClick={() => updateParam("city", "")}
              className="font-mono text-[10px] text-ink-muted hover:text-ink underline"
            >
              RESET
            </button>
          )}
        </div>

        <select
          id="city-select"
          value={currentCity}
          onChange={(e) => updateParam("city", e.target.value)}
          className="w-full p-2 bg-canvas border border-grid rounded-[2px] text-xs text-ink focus:outline-none focus:border-ink font-sans"
        >
          <option value="">All Metro Areas</option>
          {CITIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>

        {/* Quick City Chips */}
        <div className="flex flex-wrap gap-1 pt-1">
          {QUICK_CITIES.map((c) => {
            const isSelected = currentCity === c.value;
            return (
              <button
                key={c.value}
                type="button"
                onClick={() => updateParam("city", isSelected ? "" : c.value)}
                className={`text-[10px] font-mono px-1.5 py-0.5 border rounded-[2px] transition-colors ${
                  isSelected
                    ? "bg-ink text-white border-ink font-semibold"
                    : "bg-canvas text-ink-secondary border-grid hover:border-ink"
                }`}
              >
                {c.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Direct Source Legend */}
      <div className="pt-1 space-y-2 text-[11px] text-ink-muted">
        <span className="font-mono text-[10px] uppercase tracking-wider block font-semibold text-ink-secondary">
          SOURCE VERIFICATION
        </span>
        <div className="space-y-1.5 text-[10px] font-mono leading-tight">
          <div className="flex items-start gap-1.5">
            <span className="w-1.5 h-1.5 bg-status-live shrink-0 mt-1" />
            <span>
              <strong className="text-status-live">DIRECT ATS:</strong> Pulled straight from verified company Greenhouse boards.
            </span>
          </div>
          <div className="flex items-start gap-1.5">
            <span className="w-1.5 h-1.5 bg-grid shrink-0 mt-1" />
            <span>
              <strong className="text-ink">AGGREGATOR:</strong> Ingested via Jooble partner API and rule-verified.
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
