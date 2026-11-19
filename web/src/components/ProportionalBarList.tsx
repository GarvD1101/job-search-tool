"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRightIcon } from "./Icons";

export interface BarItem {
  id: string;
  label: string;
  code?: string;
  count: number;
  href?: string;
}

interface ProportionalBarListProps {
  items: BarItem[];
  total?: number;
  initialLimit?: number;
  toggleLabel?: string;
  barColor?: "canvas" | "amber" | "reject";
}

export default function ProportionalBarList({
  items,
  total,
  initialLimit,
  toggleLabel = "SHOW ALL",
  barColor = "canvas",
}: ProportionalBarListProps) {
  const [expanded, setExpanded] = useState(false);

  if (!items || items.length === 0) {
    return (
      <div className="p-4 text-center font-mono text-xs text-ink-muted bg-canvas">
        No records available
      </div>
    );
  }

  const maxCount = Math.max(...items.map((i) => i.count), 1);
  const totalCount = total || items.reduce((acc, i) => acc + i.count, 0) || 1;

  const displayedItems =
    initialLimit && !expanded ? items.slice(0, initialLimit) : items;

  const getBarBg = () => {
    switch (barColor) {
      case "amber":
        return "bg-amber-wash border-r border-amber-signal/30";
      case "reject":
        return "bg-status-reject/10 border-r border-status-reject/20";
      case "canvas":
      default:
        return "bg-canvas border-r border-grid";
    }
  };

  return (
    <div className="space-y-1.5 font-mono text-xs">
      <div className="space-y-1">
        {displayedItems.map((item) => {
          const widthPct = Math.max(
            (item.count / maxCount) * 100,
            item.count > 0 ? 2 : 0
          );
          const sharePct = ((item.count / totalCount) * 100).toFixed(1);

          const content = (
            <div className="relative overflow-hidden border border-grid/60 bg-surface rounded-[2px] h-8 flex items-center justify-between px-3 group hover:border-ink transition-colors">
              {/* Proportional background fill */}
              <div
                className={`absolute inset-y-0 left-0 ${getBarBg()} transition-all duration-300`}
                style={{ width: `${widthPct}%` }}
              />

              {/* Foreground Label */}
              <div className="relative z-10 flex items-center space-x-2 truncate pr-2">
                {item.code && (
                  <span className="text-[10px] text-ink-muted font-bold uppercase tracking-wider shrink-0">
                    [{item.code}]
                  </span>
                )}
                <span className="text-ink truncate font-sans text-xs group-hover:text-amber-signal transition-colors font-medium">
                  {item.label}
                </span>
                {item.href && (
                  <ArrowUpRightIcon
                    size={11}
                    className="opacity-0 group-hover:opacity-100 text-amber-signal shrink-0 transition-opacity"
                  />
                )}
              </div>

              {/* Foreground Counts */}
              <div className="relative z-10 shrink-0 flex items-center space-x-2 font-mono text-[11px] tabular-nums">
                <span className="font-bold text-ink">{item.count}</span>
                <span className="text-ink-muted text-[10px]">({sharePct}%)</span>
              </div>
            </div>
          );

          if (item.href) {
            return (
              <Link key={item.id} href={item.href} className="block">
                {content}
              </Link>
            );
          }

          return <div key={item.id}>{content}</div>;
        })}
      </div>

      {initialLimit && items.length > initialLimit && (
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="w-full py-1.5 border border-grid hover:border-ink bg-canvas hover:bg-surface text-ink font-mono text-[11px] uppercase tracking-wider font-semibold transition-colors rounded-[2px]"
          >
            {expanded
              ? "[ COLLAPSE LIST ]"
              : `[ ${toggleLabel} (${items.length - initialLimit} MORE) ]`}
          </button>
        </div>
      )}
    </div>
  );
}
