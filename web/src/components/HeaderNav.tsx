"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "01 LIVE JOBS" },
  { href: "/stats", label: "02 STATS" },
  { href: "/costs", label: "03 COSTS" },
];

export default function HeaderNav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center h-full space-x-1 sm:space-x-2">
      {NAV_ITEMS.map((item) => {
        const isActive =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`h-full flex items-center px-2.5 sm:px-3 font-mono text-[11px] sm:text-xs tracking-wider transition-colors border-b-2 ${
              isActive
                ? "border-amber-signal text-ink font-semibold"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
