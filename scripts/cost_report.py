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

    # 2. Serving Scenarios (1,000 / 10,000 / 100,000 / 1,000,000 users)
    # Sensitivity analysis: 90% CDN hit vs 50% CDN hit
    dau_tiers = [1000, 10000, 100000, 1000000]
    serving_scenarios = {}

    def calculate_serving_case(users: int, cdn_hit_rate: float) -> dict[str, Any]:
        monthly_searches = users * 5 * 30
        cdn_hits = round(monthly_searches * cdn_hit_rate)
        origin_requests = monthly_searches - cdn_hits
        total_bandwidth_gb = round((monthly_searches * 10) / (1024 * 1024), 2)
        origin_egress_gb = round((origin_requests * 10) / (1024 * 1024), 2)

        if users == 1000000:
            vercel_tier = "Enterprise"
            vercel_monthly = None
            vercel_binding_limit = (
                f"Edge Requests ({monthly_searches / 1_000_000:.0f}M) and "
                f"Bandwidth ({total_bandwidth_gb / 1024:.2f} TB > 1 TB) "
                "exceed self-serve thresholds"
            )
            vercel_pricing_type = "contact sales"

            supabase_tier = "Enterprise / Team"
            supabase_monthly = None
            supabase_binding_limit = (
                f"Dedicated cluster throughput required for "
                f"{origin_requests / 1_000_000:.0f}M database queries/month"
            )
            supabase_pricing_type = "contact sales"
        else:
            # Vercel Pro derivation
            base_vercel = 20.0  # 1 seat Pro
            edge_overage_m = max(0.0, (monthly_searches - 10_000_000) / 1_000_000)
            edge_cost = edge_overage_m * 2.00
            func_overage_m = max(0.0, (origin_requests - 1_000_000) / 1_000_000)
            func_cost = func_overage_m * 0.40
            bw_overage_gb = max(0.0, total_bandwidth_gb - 1024.0)
            bw_cost = bw_overage_gb * 0.15

            vercel_monthly = round(base_vercel + edge_cost + func_cost + bw_cost, 2)
            if edge_cost > 0 or func_cost > 0 or bw_cost > 0:
                vercel_tier = f"Pro + Usage (${vercel_monthly:.2f}/mo)"
            else:
                vercel_tier = "Pro ($20/mo)"

            v_limits = []
            if edge_cost > 0:
                v_limits.append(
                    f"Edge Requests ({monthly_searches / 1_000_000:.0f}M > 10M included)"
                )
            if func_cost > 0:
                v_limits.append(
                    f"Function Invocations ({origin_requests / 1_000_000:.2f}M > 1M included)"
                )
            if bw_cost > 0:
                v_limits.append(
                    f"Bandwidth ({total_bandwidth_gb:.1f} GB > 1 TB included)"
                )
            if not v_limits:
                if origin_requests > 500_000:
                    v_limits.append(
                        f"Function Invocations ({origin_requests / 1_000:.0f}k / 1M allowance)"
                    )
                else:
                    v_limits.append("Base 1-seat Pro subscription")
            vercel_binding_limit = "; ".join(v_limits)
            vercel_pricing_type = "published list price"

            # Supabase derivation
            if users == 100000 and cdn_hit_rate < 0.60:
                # 7.5M origin queries requires Medium Compute upgrade
                supabase_tier = "Pro + Medium Compute ($85/mo)"
                supabase_monthly = 85.0
                supabase_binding_limit = (
                    "Postgres compute RAM and connection pooler throughput "
                    "(7.5M queries/mo)"
                )
            else:
                supabase_tier = "Pro ($25/mo)"
                supabase_monthly = 25.0
                if users == 1000:
                    supabase_binding_limit = (
                        "Base Pro subscription (Free covers 1.43 GB egress, "
                        "lacks commercial SLA)"
                    )
                elif users == 10000:
                    if cdn_hit_rate >= 0.80:
                        supabase_binding_limit = (
                            "Base Pro subscription (Free covers 1.43 GB egress, "
                            "lacks SLA/pausing protection)"
                        )
                    else:
                        supabase_binding_limit = (
                            "Egress (7.15 GB) exceeds 5 GB Free tier cap; "
                            "mandates Pro tier"
                        )
                elif users == 100000:
                    supabase_binding_limit = (
                        "Connection pooler concurrency (1.5M queries/mo)"
                    )
                else:
                    supabase_binding_limit = "Base Pro subscription"
            supabase_pricing_type = "published list price"

        if vercel_monthly is not None and supabase_monthly is not None:
            total_monthly = round(
                vercel_monthly + supabase_monthly + baseline_llm_monthly, 2
            )
            total_weekly = round((total_monthly * 7) / 30, 2)
            total_annual = round(total_monthly * 12, 2)
            cost_per_1000 = round((total_monthly / users) * 1000, 4)
        else:
            total_monthly = None
            total_weekly = None
            total_annual = None
            cost_per_1000 = None

        return {
            "cdn_hit_ratio_pct": int(cdn_hit_rate * 100),
            "monthly_searches": monthly_searches,
            "monthly_cdn_cache_hits": cdn_hits,
            "monthly_origin_requests": origin_requests,
            "monthly_bandwidth_gb": total_bandwidth_gb,
            "monthly_origin_egress_gb": origin_egress_gb,
            "supabase": {
                "tier": supabase_tier,
                "monthly_cost_usd": supabase_monthly,
                "binding_limit": supabase_binding_limit,
                "pricing_type": supabase_pricing_type,
                "source_url": "https://supabase.com/pricing",
                "last_verified": "2026-11-19",
            },
            "vercel": {
                "tier": vercel_tier,
                "monthly_cost_usd": vercel_monthly,
                "binding_limit": vercel_binding_limit,
                "pricing_type": vercel_pricing_type,
                "source_url": "https://vercel.com/pricing",
                "last_verified": "2026-11-19",
            },
            "llm": {
                "model": "openai/gpt-oss-20b",
                "pipeline_volume": "600 raw posts/day",
                "monthly_cost_usd": baseline_llm_monthly,
                "dependency_note": (
                    "LLM cost scales strictly with raw posts ingested, "
                    "independent of user volume"
                ),
            },
            "breakdown_monthly_usd": {
                "llm": baseline_llm_monthly,
                "database": supabase_monthly,
                "hosting": vercel_monthly,
            },
            "total_weekly_cost_usd": total_weekly,
            "total_monthly_cost_usd": total_monthly,
            "total_annual_cost_usd": total_annual,
            "cost_per_1000_users_usd": cost_per_1000,
        }

    for dau in dau_tiers:
        baseline_case = calculate_serving_case(dau, 0.90)
        sensitivity_case = calculate_serving_case(dau, 0.50)

        serving_scenarios[str(dau)] = {
            "daily_active_users": dau,
            "monthly_searches": baseline_case["monthly_searches"],
            "monthly_bandwidth_gb": baseline_case["monthly_bandwidth_gb"],
            "baseline_90_pct_cdn": baseline_case,
            "sensitivity_50_pct_cdn": sensitivity_case,
            # Top-level pointers for backwards compatibility with CostSimulator
            "supabase": baseline_case["supabase"],
            "vercel": baseline_case["vercel"],
            "llm": baseline_case["llm"],
            "breakdown_monthly_usd": baseline_case["breakdown_monthly_usd"],
            "total_weekly_cost_usd": baseline_case["total_weekly_cost_usd"],
            "total_monthly_cost_usd": baseline_case["total_monthly_cost_usd"],
            "total_annual_cost_usd": baseline_case["total_annual_cost_usd"],
            "cost_per_1000_users_usd": baseline_case["cost_per_1000_users_usd"],
        }

    report = {
        "title": "Fresher Radar Cost & Scale Projections",
        "generated_at": "2026-11-20",
        "notes": (
            "Projections derived from official pricing pages and measured pipeline parameters."
        ),
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
            w_cost = f"${m_data['weekly_cost_usd']:.4f}"
            m_cost = f"${m_data['monthly_cost_usd']:.4f}"
            a_cost = f"${m_data['annual_cost_usd']:.2f}"
            per_1k = f"${m_data['cost_per_1000_raw_posts_usd']:.4f}"
            print(
                f"{short_name:<22} | {d_cost:<10} | {w_cost:<11} | "
                f"{m_cost:<13} | {a_cost:<12} | {per_1k}"
            )

    print("\n" + "=" * 70)
    print("FULL-STACK SERVING SCENARIOS WITH CDN SENSITIVITY (90% vs 50%)")
    print("=" * 70)
    print(
        f"{'DAU':<8} | {'CDN':<5} | {'Origin Reqs':<12} | {'Supabase Tier':<22} | "
        f"{'Vercel Tier':<20} | {'Monthly Total':<13} | {'Weekly (7d)':<11} | {'Annual (365d)'}"
    )
    print("-" * 115)
    for dau_str, data in report["serving_scenarios"].items():
        dau = data["daily_active_users"]
        for case_key in ["baseline_90_pct_cdn", "sensitivity_50_pct_cdn"]:
            c = data[case_key]
            cdn_lbl = f"{c['cdn_hit_ratio_pct']}%"
            origin_lbl = f"{c['monthly_origin_requests'] / 1_000:,.0f}k"
            supa_tier = c["supabase"]["tier"]
            vercel_tier = c["vercel"]["tier"]
            m_tot = (
                f"${c['total_monthly_cost_usd']:.2f}"
                if c["total_monthly_cost_usd"] is not None
                else "contact sales"
            )
            w_tot = (
                f"${c['total_weekly_cost_usd']:.2f}"
                if c["total_weekly_cost_usd"] is not None
                else "contact sales"
            )
            a_tot = (
                f"${c['total_annual_cost_usd']:.2f}"
                if c["total_annual_cost_usd"] is not None
                else "contact sales"
            )
            print(
                f"{dau:<8} | {cdn_lbl:<5} | {origin_lbl:<12} | {supa_tier:<22} | "
                f"{vercel_tier:<20} | {m_tot:<13} | {w_tot:<11} | {a_tot}"
            )


if __name__ == "__main__":
    generate_cost_report()
