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
                "last_verified": m_spec.get("last_verified", "2026-11-20"),
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
    dau_tiers = [1000, 10000, 100000, 1000000]
    serving_scenarios = {}

    def calculate_serving_case(users: int, cdn_hit_rate: float) -> dict[str, Any]:
        monthly_searches = users * 5 * 30
        cdn_hits = round(monthly_searches * cdn_hit_rate)
        origin_requests = monthly_searches - cdn_hits
        total_bandwidth_gb = round((monthly_searches * 10) / (1024 * 1024), 2)
        origin_egress_gb = round((origin_requests * 10) / (1024 * 1024), 2)

        # --- Vercel Calculations ---
        # Base Pro seat: $20.00/mo, includes 1M function invocations and $20 usage credit.
        base_vercel = 20.0
        usage_credit = 20.0

        # Function invocation overage: $0.60 per 1M beyond 1M included
        func_overage_m = max(0.0, (origin_requests - 1_000_000) / 1_000_000)
        raw_func_fee = round(func_overage_m * 0.60, 2)

        # Model A: Flat Rate CDN Tiers (September 2026)
        # Covers CDN requests and Data Transfer (50 TB allowance)
        if monthly_searches <= 1_000_000:
            flat_cdn_addon = 0.0
            flat_cdn_tier_label = "Included with Pro (1M req, 1 TB transfer)"
            flat_binding_cdn = "1M CDN requests, 1 TB transfer"
        elif monthly_searches <= 10_000_000:
            flat_cdn_addon = 20.0
            flat_cdn_tier_label = "Flat Rate Tier 1 ($20/mo, 10M req, 50 TB)"
            flat_binding_cdn = "10M CDN requests, 50 TB transfer"
        elif monthly_searches <= 50_000_000:
            flat_cdn_addon = 100.0
            flat_cdn_tier_label = "Flat Rate Tier 2 ($100/mo, 50M req, 50 TB)"
            flat_binding_cdn = "50M CDN requests, 50 TB transfer"
        elif monthly_searches <= 150_000_000:
            flat_cdn_addon = 300.0
            flat_cdn_tier_label = "Flat Rate Tier 3 ($300/mo, 150M req, 50 TB)"
            flat_binding_cdn = "150M CDN requests, 50 TB transfer"
        else:
            flat_cdn_addon = 300.0 + (
                (monthly_searches - 150_000_000) / 50_000_000
            ) * 100.0
            flat_cdn_tier_label = (
                f"Flat Rate Custom (${flat_cdn_addon:.2f}/mo, 50 TB)"
            )
            flat_binding_cdn = f"{monthly_searches/1_000_000:.0f}M CDN requests, 50 TB transfer"

        # In Flat Rate model, the $20 usage credit absorbs function overage fees
        flat_net_func_fee = max(0.0, raw_func_fee - usage_credit)
        vercel_flat_total = round(base_vercel + flat_cdn_addon + flat_net_func_fee, 2)

        # Model B: On-Demand Metered Model
        # Includes 10M Edge Requests, 1M Function Invocations, 1 TB Data Transfer
        edge_overage_m = max(0.0, (monthly_searches - 10_000_000) / 1_000_000)
        raw_edge_fee = round(edge_overage_m * 2.00, 2)
        bw_overage_gb = max(0.0, total_bandwidth_gb - 1024.0)
        raw_bw_fee = round(bw_overage_gb * 0.15, 2)

        total_metered_usage_fees = raw_edge_fee + raw_func_fee + raw_bw_fee
        metered_net_usage_fee = max(0.0, total_metered_usage_fees - usage_credit)
        vercel_metered_total = round(base_vercel + metered_net_usage_fee, 2)

        # Published binding limit string for Vercel
        v_binding_items = [flat_binding_cdn]
        if origin_requests > 1_000_000:
            v_binding_items.append(
                f"{origin_requests / 1_000_000:.2f}M function invocations"
            )
        else:
            v_binding_items.append("1M function invocations")
        vercel_published_binding = "; ".join(v_binding_items)

        # --- Supabase Calculations ---
        # Base Pro: $25.00/mo per org, includes $10.00 compute credit.
        # Micro ($10 list): $0 net addon. Pooler connections: 200.
        # Small ($15 list): $5 net addon. Pooler connections: 400.
        # Medium ($60 list): $50 net addon. Pooler connections: 600.
        # Included egress: 250 GB. Past 250 GB: $0.09 per GB.
        egress_overage_gb = max(0.0, origin_egress_gb - 250.0)
        egress_overage_cost = round(egress_overage_gb * 0.09, 2)

        if users <= 10000:
            supa_compute_addon_net = 0.0
            supa_tier_label = "Pro + Micro Compute (200 pooler conn)"
            supa_binding_items = ["200 pooler connections", "250 GB egress"]
            supa_assumption = "Micro compute is sufficient for <= 150k queries/month"
        elif users == 100000:
            if cdn_hit_rate >= 0.80:
                supa_compute_addon_net = 0.0
                supa_tier_label = "Pro + Micro Compute (200 pooler conn)"
                supa_binding_items = ["200 pooler connections", "250 GB egress"]
                supa_assumption = "Micro compute handles 1.5M cached queries/month"
            else:
                supa_compute_addon_net = 50.0  # Medium: $60 - $10 credit
                supa_tier_label = "Pro + Medium Compute (600 pooler conn)"
                supa_binding_items = ["600 pooler connections", "250 GB egress"]
                supa_assumption = "Medium compute assumed to sustain 7.5M queries/month"
        else:  # 1,000,000 users
            supa_compute_addon_net = 50.0  # Medium: $60 - $10 credit
            supa_tier_label = "Pro + Medium Compute (600 pooler conn)"
            if egress_overage_cost > 0:
                supa_binding_items = [
                    "600 pooler connections",
                    (
                        f"250 GB egress ({egress_overage_gb:.1f} GB overage: "
                        f"${egress_overage_cost:.2f})"
                    ),
                ]
            else:
                supa_binding_items = ["600 pooler connections", "250 GB egress"]
            supa_assumption = (
                "Medium compute assumed; at 150M searches, sales discussion "
                "for enterprise SLA is typical"
            )

        supabase_total = round(
            25.0 + supa_compute_addon_net + egress_overage_cost, 2
        )
        supabase_published_binding = "; ".join(supa_binding_items)

        # Full-stack Totals (Using Flat Rate CDN as default, with On-Demand comparison)
        total_monthly_flat = round(
            vercel_flat_total + supabase_total + baseline_llm_monthly, 2
        )
        total_weekly_flat = round((total_monthly_flat * 7) / 30, 2)
        total_annual_flat = round(total_monthly_flat * 12, 2)
        cost_per_1000_flat = round((total_monthly_flat / users) * 1000, 4)

        total_monthly_metered = round(
            vercel_metered_total + supabase_total + baseline_llm_monthly, 2
        )
        total_weekly_metered = round((total_monthly_metered * 7) / 30, 2)
        total_annual_metered = round(total_monthly_metered * 12, 2)
        cost_per_1000_metered = round((total_monthly_metered / users) * 1000, 4)

        enterprise_note = ""
        if users >= 1000000:
            enterprise_note = (
                "Computed using published self-serve list rates. At 150M searches/mo, "
                "teams typically negotiate custom enterprise agreements for volume discounts."
            )

        return {
            "cdn_hit_ratio_pct": int(cdn_hit_rate * 100),
            "monthly_searches": monthly_searches,
            "monthly_cdn_cache_hits": cdn_hits,
            "monthly_origin_requests": origin_requests,
            "monthly_bandwidth_gb": total_bandwidth_gb,
            "monthly_origin_egress_gb": origin_egress_gb,
            "vercel": {
                "flat_rate_model": {
                    "tier": flat_cdn_tier_label,
                    "cdn_addon_usd": flat_cdn_addon,
                    "raw_func_fee_usd": raw_func_fee,
                    "applied_credit_usd": min(usage_credit, raw_func_fee),
                    "monthly_cost_usd": vercel_flat_total,
                },
                "on_demand_model": {
                    "tier": "Pro + On-Demand Overages",
                    "raw_edge_fee_usd": raw_edge_fee,
                    "raw_func_fee_usd": raw_func_fee,
                    "raw_bw_fee_usd": raw_bw_fee,
                    "applied_credit_usd": min(usage_credit, total_metered_usage_fees),
                    "monthly_cost_usd": vercel_metered_total,
                },
                "tier": flat_cdn_tier_label,
                "monthly_cost_usd": vercel_flat_total,
                "published_binding_limits": vercel_published_binding,
                "pricing_type": "published list price (includes $20 monthly usage credit)",
                "source_url": "https://vercel.com/pricing",
                "last_verified": "2026-11-20",
            },
            "supabase": {
                "tier": supa_tier_label,
                "monthly_cost_usd": supabase_total,
                "base_pro_usd": 25.0,
                "compute_addon_net_usd": supa_compute_addon_net,
                "egress_overage_usd": egress_overage_cost,
                "published_binding_limits": supabase_published_binding,
                "architecture_assumption": supa_assumption,
                "pricing_type": "published list price (includes $10 monthly compute credit)",
                "source_url": "https://supabase.com/pricing",
                "last_verified": "2026-11-20",
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
                "supabase": supabase_total,
                "vercel": vercel_flat_total,
                "database": supabase_total,
                "hosting": vercel_flat_total,
            },
            "total_weekly_cost_usd": total_weekly_flat,
            "total_monthly_cost_usd": total_monthly_flat,
            "total_annual_cost_usd": total_annual_flat,
            "cost_per_1000_users_usd": cost_per_1000_flat,
            "on_demand_totals": {
                "total_weekly_cost_usd": total_weekly_metered,
                "total_monthly_cost_usd": total_monthly_metered,
                "total_annual_cost_usd": total_annual_metered,
                "cost_per_1000_users_usd": cost_per_1000_metered,
            },
            "enterprise_note": enterprise_note,
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
            "enterprise_note": baseline_case["enterprise_note"],
        }

    report = {
        "title": "Fresher Radar Cost & Scale Projections",
        "generated_at": "2026-11-20",
        "notes": (
            "Projections derived from official pricing pages (vercel.com/pricing, "
            "supabase.com/pricing, groq.com/pricing). All tiers reflect published list rates, "
            "including Vercel $20 usage credit, Vercel Flat Rate CDN capacity tiers, and "
            "Supabase $10 compute credit."
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
    print("FULL-STACK SERVING SCENARIOS WITH CDN SENSITIVITY (FLAT RATE CDN)")
    print("=" * 70)
    print(
        f"{'DAU':<8} | {'CDN':<5} | {'Origin Reqs':<12} | {'Supabase':<10} | "
        f"{'Vercel Flat':<12} | {'Monthly Total':<13} | {'Weekly (7d)':<11} | {'Annual (365d)'}"
    )
    print("-" * 95)
    for dau_str, data in report["serving_scenarios"].items():
        dau = data["daily_active_users"]
        for case_key in ["baseline_90_pct_cdn", "sensitivity_50_pct_cdn"]:
            c = data[case_key]
            cdn_lbl = f"{c['cdn_hit_ratio_pct']}%"
            origin_lbl = f"{c['monthly_origin_requests'] / 1_000:,.0f}k"
            supa_cost = f"${c['supabase']['monthly_cost_usd']:.2f}"
            vercel_cost = f"${c['vercel']['monthly_cost_usd']:.2f}"
            m_tot = f"${c['total_monthly_cost_usd']:.2f}"
            w_tot = f"${c['total_weekly_cost_usd']:.2f}"
            a_tot = f"${c['total_annual_cost_usd']:.2f}"
            print(
                f"{dau:<8} | {cdn_lbl:<5} | {origin_lbl:<12} | {supa_cost:<10} | "
                f"{vercel_cost:<12} | {m_tot:<13} | {w_tot:<11} | {a_tot}"
            )


if __name__ == "__main__":
    generate_cost_report()
