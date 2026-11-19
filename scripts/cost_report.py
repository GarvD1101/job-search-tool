"""Cost projection report for Fresher Radar pipeline and web serving.

Reads measured parameters from config/cost_assumptions.yaml and generates
deterministic projections for pipeline tagging and web serving tiers.
Outputs:
  - docs/results/costs.json
  - web/data/costs.json
"""

import json
from pathlib import Path
from typing import Any

import yaml


def generate_cost_report() -> dict[str, Any]:
    config_path = Path("config/cost_assumptions.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        assumptions = yaml.safe_load(f)

    pipeline_metrics = assumptions["measured_pipeline_metrics"]
    survivor_rate = pipeline_metrics["survivor_rate"]
    models = pipeline_metrics["models"]

    # 1. Pipeline Tagging Scenarios
    pipeline_scenarios = {}
    raw_volumes = [200, 600, 2000]

    for volume in raw_volumes:
        tagged_per_day = round(volume * survivor_rate, 2)
        model_projections = {}

        for model_name, m_spec in models.items():
            in_tok_per_post = m_spec["input_tokens_per_post"]
            out_tok_per_post = m_spec["output_tokens_per_post"]
            reas_tok_per_post = m_spec["reasoning_tokens_per_post"]

            in_price = m_spec["input_price_per_1m"]
            out_price = m_spec["output_price_per_1m"]

            daily_in_tokens = round(tagged_per_day * in_tok_per_post)
            daily_out_tokens = round(tagged_per_day * out_tok_per_post)
            daily_reas_tokens = round(tagged_per_day * reas_tok_per_post)
            daily_total_tokens = daily_in_tokens + daily_out_tokens

            daily_cost = (
                (daily_in_tokens * in_price) + (daily_out_tokens * out_price)
            ) / 1_000_000
            weekly_cost = daily_cost * 7
            monthly_cost = daily_cost * 30
            annual_cost = daily_cost * 365
            cost_per_1000_raw = (daily_cost / volume) * 1000

            model_projections[model_name] = {
                "daily_tagged_posts": tagged_per_day,
                "daily_input_tokens": daily_in_tokens,
                "daily_output_tokens": daily_out_tokens,
                "daily_reasoning_tokens": daily_reas_tokens,
                "daily_total_tokens": daily_total_tokens,
                "daily_cost_usd": round(daily_cost, 6),
                "weekly_cost_usd": round(weekly_cost, 4),
                "monthly_cost_usd": round(monthly_cost, 4),
                "annual_cost_usd": round(annual_cost, 4),
                "cost_per_1000_raw_posts_usd": round(cost_per_1000_raw, 4),
                "pricing_type": m_spec.get("pricing_type", "published list price"),
                "source_url": m_spec.get("source_url", "https://groq.com/pricing/"),
                "last_verified": m_spec.get("last_verified", "2026-11-19"),
            }

        pipeline_scenarios[str(volume)] = {
            "raw_posts_per_day": volume,
            "tagged_posts_per_day": tagged_per_day,
            "survivor_share_pct": round(survivor_rate * 100, 2),
            "models": model_projections,
        }

    # Baseline daily LLM cost for baseline model (openai/gpt-oss-20b at 600 raw/day)
    baseline_llm_monthly = pipeline_scenarios["600"]["models"]["openai/gpt-oss-20b"][
        "monthly_cost_usd"
    ]

    # 2. Serving Scenarios
    dau_tiers = [1000, 10000, 100000, 1000000]
    serving_scenarios = {}

    tier_specs = {
        1000: {
            "supabase_tier": "Free ($0/mo)",
            "supabase_monthly": 0.0,
            "supabase_limit": "500 MB DB, 5 GB egress, 200 pool connections",
            "supabase_pricing_type": "published list price",
            "supabase_source_url": "https://supabase.com/pricing",
            "supabase_last_verified": "2026-11-19",
            "vercel_tier": "Hobby ($0/mo)",
            "vercel_monthly": 0.0,
            "vercel_limit": "100 GB bandwidth, fair use execution",
            "vercel_pricing_type": "published list price (non-commercial only)",
            "vercel_basis": "Personal non-commercial projects; commercial launch requires Pro",
            "vercel_source_url": "https://vercel.com/pricing",
            "vercel_last_verified": "2026-11-19",
        },
        10000: {
            "supabase_tier": "Pro ($25/mo)",
            "supabase_monthly": 25.0,
            "supabase_limit": "8 GB DB, 250 GB egress, 10,000 pool connections",
            "supabase_pricing_type": "published list price",
            "supabase_source_url": "https://supabase.com/pricing",
            "supabase_last_verified": "2026-11-19",
            "vercel_tier": "Pro ($20/mo)",
            "vercel_monthly": 20.0,
            "vercel_limit": "1 TB bandwidth, 1,000 GB-hrs serverless execution",
            "vercel_pricing_type": "published list price",
            "vercel_basis": "1 team seat included on Pro plan",
            "vercel_source_url": "https://vercel.com/pricing",
            "vercel_last_verified": "2026-11-19",
        },
        100000: {
            "supabase_tier": "Pro + Compute ($45/mo)",
            "supabase_monthly": 45.0,
            "supabase_limit": "Pro ($25) + $20 Small dedicated compute upgrade",
            "supabase_pricing_type": "published list price",
            "supabase_source_url": "https://supabase.com/pricing",
            "supabase_last_verified": "2026-11-19",
            "vercel_tier": "Pro + Usage ($50/mo)",
            "vercel_monthly": 50.0,
            "vercel_limit": "Pro base ($20) + $30 bandwidth/function overage",
            "vercel_pricing_type": "published list price plus usage formula",
            "vercel_basis": "Pro base $20/mo + $30 usage overage",
            "vercel_source_url": "https://vercel.com/pricing",
            "vercel_last_verified": "2026-11-19",
        },
        1000000: {
            "supabase_tier": "Team ($599/mo)",
            "supabase_monthly": 599.0,
            "supabase_limit": "Team tier with SLA, 16 GB DB, SOC2 compliance",
            "supabase_pricing_type": "published list price",
            "supabase_source_url": "https://supabase.com/pricing",
            "supabase_last_verified": "2026-11-19",
            "vercel_tier": "Enterprise (estimate, custom pricing: $500/mo)",
            "vercel_monthly": 500.0,
            "vercel_limit": "Custom contract with multi-region CDN and enterprise SLA",
            "vercel_pricing_type": "estimate, custom pricing",
            "vercel_basis": "Estimated contract: 150M edge req/mo, 1.5 TB bandwidth",
            "vercel_source_url": "https://vercel.com/pricing",
            "vercel_last_verified": "2026-11-19",
        },
    }

    for dau in dau_tiers:
        spec = tier_specs[dau]
        daily_searches = dau * 5
        monthly_searches = daily_searches * 30
        cdn_hits = round(monthly_searches * 0.80)
        db_queries = round(monthly_searches * 0.20)
        bandwidth_gb = round((monthly_searches * 10) / (1024 * 1024), 2)

        db_monthly = spec["supabase_monthly"]
        hosting_monthly = spec["vercel_monthly"]
        llm_monthly = baseline_llm_monthly

        total_monthly = db_monthly + hosting_monthly + llm_monthly
        total_weekly = round((total_monthly * 7) / 30, 2)
        total_annual = round(total_monthly * 12, 2)
        cost_per_1000_dau = round((total_monthly / dau) * 1000, 4)

        serving_scenarios[str(dau)] = {
            "daily_active_users": dau,
            "monthly_searches": monthly_searches,
            "monthly_cdn_cache_hits": cdn_hits,
            "monthly_db_queries": db_queries,
            "monthly_bandwidth_gb": bandwidth_gb,
            "supabase": {
                "tier": spec["supabase_tier"],
                "monthly_cost_usd": db_monthly,
                "plan_limit": spec["supabase_limit"],
                "pricing_type": spec["supabase_pricing_type"],
                "source_url": spec["supabase_source_url"],
                "last_verified": spec["supabase_last_verified"],
            },
            "vercel": {
                "tier": spec["vercel_tier"],
                "monthly_cost_usd": hosting_monthly,
                "plan_limit": spec["vercel_limit"],
                "pricing_type": spec["vercel_pricing_type"],
                "basis": spec["vercel_basis"],
                "source_url": spec["vercel_source_url"],
                "last_verified": spec["vercel_last_verified"],
            },
            "llm": {
                "model": "openai/gpt-oss-20b",
                "pipeline_volume": "600 raw posts/day",
                "monthly_cost_usd": llm_monthly,
                "dependency_note": "LLM cost scales with raw posts ingested, independent of DAU",
            },
            "breakdown_monthly_usd": {
                "llm": llm_monthly,
                "database": db_monthly,
                "hosting": hosting_monthly,
            },
            "total_weekly_cost_usd": total_weekly,
            "total_monthly_cost_usd": round(total_monthly, 2),
            "total_annual_cost_usd": total_annual,
            "cost_per_1000_users_usd": cost_per_1000_dau,
        }

    report = {
        "title": "Fresher Radar Cost & Scale Projections",
        "generated_at": "2026-11-19",
        "notes": "Figures are projections based on measured parameters and documented assumptions.",
        "pipeline_assumptions": {
            "survivor_rate": survivor_rate,
            "rejection_rate": pipeline_metrics["rejection_rate"],
        },
        "pipeline_scenarios": pipeline_scenarios,
        "serving_scenarios": serving_scenarios,
    }

    # Save to docs/results/costs.json
    results_dir = Path("docs/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "costs.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save to web/data/costs.json
    web_data_dir = Path("web/data")
    web_data_dir.mkdir(parents=True, exist_ok=True)
    with open(web_data_dir / "costs.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print_console_summary(report)
    return report


def print_console_summary(report: dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("PIPELINE TAGGING COST SCENARIOS (LLM API ONLY)")
    print("=" * 70)
    for vol_str, data in report["pipeline_scenarios"].items():
        raw_vol = data["raw_posts_per_day"]
        tagged = data["tagged_posts_per_day"]
        print(f"\nScenario: {raw_vol} raw posts/day -> {tagged} tagged survivors/day")
        print(
            f"{'Model':<22} | {'Daily Cost':<10} | {'Weekly (7d)':<11} | "
            f"{'Monthly (30d)':<13} | {'Annual (365d)':<12} | {'Cost/1k raw'}"
        )
        print("-" * 85)
        for m_name, m_data in data["models"].items():
            short_name = m_name.replace("openai/", "").replace("qwen/", "")
            d_cost = f"${m_data['daily_cost_usd']:.4f}"
            w_cost = f"${m_data['weekly_cost_usd']:.2f}"
            m_cost = f"${m_data['monthly_cost_usd']:.2f}"
            a_cost = f"${m_data['annual_cost_usd']:.2f}"
            k_cost = f"${m_data['cost_per_1000_raw_posts_usd']:.4f}"
            print(
                f"{short_name:<22} | {d_cost:<10} | {w_cost:<11} | "
                f"{m_cost:<13} | {a_cost:<12} | {k_cost}"
            )

    print("\n" + "=" * 70)
    print("SERVING COST SCENARIOS (FULL STACK: LLM + DB + HOSTING)")
    print("=" * 70)
    print(
        f"{'DAU':<10} | {'Supabase Tier':<22} | {'Vercel Tier':<25} | "
        f"{'Weekly (7d)':<11} | {'Monthly (30d)':<13} | {'Annual':<10} | {'Cost/1k DAU'}"
    )
    print("-" * 115)
    for dau_str, data in report["serving_scenarios"].items():
        dau = f"{int(dau_str):,}"
        sb_tier = data["supabase"]["tier"]
        vc_tier = data["vercel"]["tier"]
        wk = f"${data['total_weekly_cost_usd']:.2f}"
        tot_mo = f"${data['total_monthly_cost_usd']:.2f}"
        ann = f"${data['total_annual_cost_usd']:.2f}"
        per_k = f"${data['cost_per_1000_users_usd']:.4f}"
        print(
            f"{dau:<10} | {sb_tier:<22} | {vc_tier:<25} | "
            f"{wk:<11} | {tot_mo:<13} | {ann:<10} | {per_k}"
        )
    print("=" * 70 + "\n")


if __name__ == "__main__":
    generate_cost_report()
