"use client";

import { useState } from "react";
import { formatUsd } from "@/lib/formatters";

interface ModelPricingData {
  monthly_cost_usd: number;
  annual_cost_usd: number;
}

interface PipelineScenarioData {
  models: Record<string, ModelPricingData>;
}

interface ServingScenarioData {
  daily_active_users?: number;
  dau?: number;
  supabase?: { tier: string; monthly_cost_usd?: number };
  vercel?: { tier: string; monthly_cost_usd?: number };
  breakdown_monthly_usd?: {
    llm?: number;
    supabase?: number;
    vercel?: number;
  };
}

interface CostSimulatorProps {
  pipelineScenarios: Record<string, PipelineScenarioData>;
  servingScenarios: Record<string, ServingScenarioData>;
}

export default function CostSimulator({
  pipelineScenarios,
  servingScenarios,
}: CostSimulatorProps) {
  const [selectedDau, setSelectedDau] = useState<string>("10000");
  const [selectedVolume, setSelectedVolume] = useState<string>("600");
  const [selectedModel, setSelectedModel] = useState<string>("openai/gpt-oss-20b");

  // Retrieve current selections
  const pipelineData = pipelineScenarios[selectedVolume]?.models[selectedModel];
  const servingData = servingScenarios[selectedDau];

  const llmMonthly = pipelineData?.monthly_cost_usd || 0;
  const supabaseMonthly = servingData?.breakdown_monthly_usd?.supabase || 0;
  const vercelMonthly = servingData?.breakdown_monthly_usd?.vercel || 0;
  const infraMonthly = supabaseMonthly + vercelMonthly;

  const totalMonthly = llmMonthly + infraMonthly;
  const totalAnnual = totalMonthly * 12;
  const dauNum = parseInt(selectedDau, 10) || 1;
  const costPer1kDau = (totalMonthly / dauNum) * 1000;

  const llmSharePct = totalMonthly > 0 ? (llmMonthly / totalMonthly) * 100 : 0;
  const infraSharePct = 100 - llmSharePct;

  return (
    <div className="space-y-4">
      {/* Control Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-grid border border-grid font-mono text-xs">
        {/* Control 1: User Scale */}
        <div className="bg-surface p-4 space-y-2">
          <label className="text-[10px] text-ink-muted uppercase tracking-wider block font-semibold">
            USER SCALE (DAU)
          </label>
          <div className="grid grid-cols-4 gap-1">
            {[
              { key: "1000", label: "1K" },
              { key: "10000", label: "10K" },
              { key: "50000", label: "50K" },
              { key: "250000", label: "250K" },
            ].map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setSelectedDau(t.key)}
                className={`py-1.5 border rounded-[2px] transition-colors ${
                  selectedDau === t.key
                    ? "bg-ink text-white border-ink font-bold"
                    : "bg-canvas text-ink-secondary border-grid hover:border-ink"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Control 2: Daily Raw Volume */}
        <div className="bg-surface p-4 space-y-2">
          <label className="text-[10px] text-ink-muted uppercase tracking-wider block font-semibold">
            DAILY INGESTION VOLUME
          </label>
          <div className="grid grid-cols-3 gap-1">
            {[
              { key: "200", label: "200/D" },
              { key: "600", label: "600/D (BASE)" },
              { key: "2000", label: "2K/D" },
            ].map((v) => (
              <button
                key={v.key}
                type="button"
                onClick={() => setSelectedVolume(v.key)}
                className={`py-1.5 px-1 text-[11px] border rounded-[2px] transition-colors ${
                  selectedVolume === v.key
                    ? "bg-ink text-white border-ink font-bold"
                    : "bg-canvas text-ink-secondary border-grid hover:border-ink"
                }`}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>

        {/* Control 3: Groq Tagging Model */}
        <div className="bg-surface p-4 space-y-2">
          <label className="text-[10px] text-ink-muted uppercase tracking-wider block font-semibold">
            GROQ TAGGING MODEL
          </label>
          <div className="grid grid-cols-3 gap-1">
            {[
              { key: "openai/gpt-oss-20b", label: "20B (PROD)" },
              { key: "openai/gpt-oss-120b", label: "120B" },
              { key: "qwen/qwen3.8-27b", label: "QWEN 27B" },
            ].map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => setSelectedModel(m.key)}
                className={`py-1.5 px-1 text-[10px] border rounded-[2px] transition-colors truncate ${
                  selectedModel === m.key
                    ? "bg-ink text-white border-ink font-bold"
                    : "bg-canvas text-ink-secondary border-grid hover:border-ink"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Live Output Strip */}
      <div className="border border-grid bg-surface p-4 sm:p-5 space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono">
          <div>
            <span className="text-[10px] text-ink-muted uppercase block font-semibold">
              MONTHLY TOTAL
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-ink block mt-0.5 tabular-nums">
              {formatUsd(totalMonthly)}
            </span>
            <span className="text-[10px] text-ink-muted block mt-0.5 font-sans">
              LLM + DB + Hosting
            </span>
          </div>

          <div>
            <span className="text-[10px] text-ink-muted uppercase block font-semibold">
              ANNUAL TOTAL
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-ink block mt-0.5 tabular-nums">
              {formatUsd(totalAnnual)}
            </span>
            <span className="text-[10px] text-ink-muted block mt-0.5 font-sans">
              12-month projection
            </span>
          </div>

          <div>
            <span className="text-[10px] text-amber-signal uppercase block font-semibold">
              LLM SHARE
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-amber-signal block mt-0.5 tabular-nums">
              {formatUsd(llmMonthly)}
            </span>
            <span className="text-[10px] text-ink-muted block mt-0.5 font-sans">
              {llmSharePct < 0.1 ? "< 0.1%" : `${llmSharePct.toFixed(1)}%`} of total spend
            </span>
          </div>

          <div>
            <span className="text-[10px] text-ink-muted uppercase block font-semibold">
              COST / 1K DAU
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-ink block mt-0.5 tabular-nums">
              {formatUsd(costPer1kDau, 4)}
            </span>
            <span className="text-[10px] text-ink-muted block mt-0.5 font-sans">
              Unit serving efficiency
            </span>
          </div>
        </div>

        {/* LLM vs. Infrastructure Split Bar */}
        <div className="space-y-1.5 pt-2 border-t border-grid/60 font-mono text-xs">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-amber-signal font-semibold">
              LLM TAGGING: {formatUsd(llmMonthly)} ({llmSharePct < 0.1 ? "<0.1%" : `${llmSharePct.toFixed(1)}%`})
            </span>
            <span className="text-ink font-semibold">
              INFRASTRUCTURE: {formatUsd(infraMonthly)} ({infraSharePct > 99.9 ? ">99.9%" : `${infraSharePct.toFixed(1)}%`})
            </span>
          </div>

          <div className="h-4 w-full flex bg-canvas border border-grid rounded-[1px] overflow-hidden">
            <div
              style={{ width: `${Math.max(llmSharePct, 0.75)}%` }}
              className="bg-amber-signal h-full transition-all"
              title={`LLM Share: ${formatUsd(llmMonthly)}`}
            />
            <div
              style={{ width: `${Math.min(infraSharePct, 99.25)}%` }}
              className="bg-ink h-full transition-all"
              title={`Infra Share: ${formatUsd(infraMonthly)}`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
