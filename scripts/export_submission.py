"""Export submission artifacts to docs/submission/.

Generates:
  1. docs/submission/jobs.csv
  2. docs/submission/eval_labels_vs_model.csv
  3. docs/submission/costs.csv
  4. docs/submission/prompts.md
  5. docs/submission/breaks.csv
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from scripts.score import normalize_token, read_xlsx_sheet


def export_jobs_csv(submission_dir: Path) -> int:
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("Warning: Database URL not found. Skipping jobs.csv export.")
        return 0

    query = """
    SELECT
        id, source, source_id, title, company, location_text,
        url, role, city, post_type, first_seen_at
    FROM jobs
    WHERE status = 'active'
    ORDER BY id ASC;
    """
    output_path = submission_dir / "jobs.csv"
    count = 0
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            count = len(rows)
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "id",
                        "source",
                        "source_id",
                        "title",
                        "company",
                        "location_text",
                        "url",
                        "role",
                        "city",
                        "post_type",
                        "first_seen_at",
                    ]
                )
                for r in rows:
                    writer.writerow(r)

    print(f"Exported {count} active jobs to {output_path}")
    return count


def export_eval_comparison_csv(submission_dir: Path) -> int:
    xlsx_path = Path("eval/sample_50_labeled.xlsx")
    bench_path = Path("docs/results/bench_gpt-oss-20b_v4.json")

    if not xlsx_path.exists() or not bench_path.exists():
        print(f"Missing evaluation files: {xlsx_path} or {bench_path}")
        return 0

    human_rows = read_xlsx_sheet(xlsx_path, "Label")
    with open(bench_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    model_results = bench_data.get("results", [])
    output_path = submission_dir / "eval_labels_vs_model.csv"

    rows_written = 0
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "row_num",
                "post_title",
                "true_fresher",
                "pred_fresher",
                "fresher_match",
                "true_role",
                "pred_role",
                "role_match",
                "true_city",
                "pred_city",
                "city_match",
            ]
        )

        for idx, (h_row, m_row) in enumerate(zip(human_rows, model_results, strict=True), start=1):
            raw_title = h_row.get("Post (title, company, location)", "").split("\n")[0].strip()
            title = raw_title or m_row.get("title", "")

            # Fresher boolean comparison
            human_fresher_raw = normalize_token(h_row.get("Fresher job?", ""))
            true_fresher = human_fresher_raw in ("yes", "y", "true")
            pred_fresher = bool(m_row.get("is_fresher", False))
            fresher_match = true_fresher == pred_fresher

            # Role comparison
            true_role = normalize_token(h_row.get("Role", ""))
            pred_role = normalize_token(m_row.get("role", ""))
            role_match = true_role == pred_role

            # City comparison
            true_city = normalize_token(h_row.get("City", ""))
            pred_city = normalize_token(m_row.get("city", ""))
            city_match = true_city == pred_city

            writer.writerow(
                [
                    idx,
                    title,
                    true_fresher,
                    pred_fresher,
                    fresher_match,
                    true_role,
                    pred_role,
                    role_match,
                    true_city,
                    pred_city,
                    city_match,
                ]
            )
            rows_written += 1

    print(f"Exported {rows_written} evaluation rows to {output_path}")
    return rows_written


def export_costs_csv(submission_dir: Path) -> None:
    costs_path = Path("docs/results/costs.json")
    if not costs_path.exists():
        print(f"Missing {costs_path}. Run scripts/cost_report.py first.")
        return

    with open(costs_path, "r", encoding="utf-8") as f:
        costs_data = json.load(f)

    output_path = submission_dir / "costs.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Section 1: Pipeline Tagging
        writer.writerow(["SECTION 1: PIPELINE TAGGING COST SCENARIOS (LLM API ONLY)"])
        writer.writerow(
            [
                "raw_posts_per_day",
                "tagged_survivors_per_day",
                "model",
                "daily_cost_usd",
                "weekly_cost_usd",
                "monthly_cost_usd",
                "annual_cost_usd",
                "cost_per_1000_raw_posts_usd",
            ]
        )
        for vol_str, s_data in costs_data.get("pipeline_scenarios", {}).items():
            for m_id, m_data in s_data.get("models", {}).items():
                writer.writerow(
                    [
                        vol_str,
                        s_data["tagged_posts_per_day"],
                        m_id,
                        m_data["daily_cost_usd"],
                        m_data["weekly_cost_usd"],
                        m_data["monthly_cost_usd"],
                        m_data["annual_cost_usd"],
                        m_data["cost_per_1000_raw_posts_usd"],
                    ]
                )

        writer.writerow([])
        # Section 2: Full-Stack Serving
        writer.writerow(
            ["SECTION 2: FULL-STACK SERVING SCENARIOS WITH CDN SENSITIVITY (LLM + DB + HOSTING)"]
        )
        writer.writerow(
            [
                "daily_active_users",
                "cdn_hit_ratio_pct",
                "monthly_searches",
                "monthly_origin_requests",
                "monthly_bandwidth_gb",
                "supabase_tier",
                "supabase_monthly_usd",
                "supabase_binding_limit",
                "vercel_tier",
                "vercel_monthly_usd",
                "vercel_binding_limit",
                "llm_monthly_usd",
                "total_weekly_usd",
                "total_monthly_usd",
                "total_annual_usd",
                "cost_per_1000_users_usd",
            ]
        )
        for dau_str, s_data in costs_data.get("serving_scenarios", {}).items():
            cases = []
            if "baseline_90_pct_cdn" in s_data and "sensitivity_50_pct_cdn" in s_data:
                cases = [s_data["baseline_90_pct_cdn"], s_data["sensitivity_50_pct_cdn"]]
            else:
                cases = [s_data]

            for c in cases:
                cdn_pct = c.get("cdn_hit_ratio_pct", 90)
                supa_m = (
                    c["supabase"]["monthly_cost_usd"]
                    if c["supabase"]["monthly_cost_usd"] is not None
                    else "contact sales"
                )
                vercel_m = (
                    c["vercel"]["monthly_cost_usd"]
                    if c["vercel"]["monthly_cost_usd"] is not None
                    else "contact sales"
                )
                w_tot = (
                    c["total_weekly_cost_usd"]
                    if c["total_weekly_cost_usd"] is not None
                    else "contact sales"
                )
                m_tot = (
                    c["total_monthly_cost_usd"]
                    if c["total_monthly_cost_usd"] is not None
                    else "contact sales"
                )
                a_tot = (
                    c["total_annual_cost_usd"]
                    if c["total_annual_cost_usd"] is not None
                    else "contact sales"
                )
                per_1k = (
                    c["cost_per_1000_users_usd"]
                    if c["cost_per_1000_users_usd"] is not None
                    else "contact sales"
                )

                origin_reqs = c.get(
                    "monthly_origin_requests",
                    round(c["monthly_searches"] * (1 - cdn_pct / 100)),
                )

                writer.writerow(
                    [
                        dau_str,
                        cdn_pct,
                        c["monthly_searches"],
                        origin_reqs,
                        c["monthly_bandwidth_gb"],
                        c["supabase"]["tier"],
                        supa_m,
                        c["supabase"].get("binding_limit", ""),
                        c["vercel"]["tier"],
                        vercel_m,
                        c["vercel"].get("binding_limit", ""),
                        c["breakdown_monthly_usd"]["llm"],
                        w_tot,
                        m_tot,
                        a_tot,
                        per_1k,
                    ]
                )

    print(f"Exported cost tables to {output_path}")


def export_prompts_markdown(submission_dir: Path) -> None:
    prompts_dir = Path("pipeline/llm/prompts")
    versions = ["tag_v1.txt", "tag_v2.txt", "tag_v3.txt", "tag_v4.txt"]

    output_path = submission_dir / "prompts.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Fresher Radar LLM Tagging Prompts Evolution\n\n")
        f.write("Evolution history and complete text of all production prompt versions.\n\n")

        f.write("## Prompt Changelog\n\n")
        f.write("| Version | Date | Changes Made | Rationale | Effect on Accuracy |\n")
        f.write("|---|---|---|---|---|\n")
        f.write(
            "| tag_v1 | 2026-11-17 | Initial tagging prompt with role and city enum names. "
            "| Baseline prompt for model evaluation. "
            "| Baseline role accuracy: 76.0% (gpt-oss-20b). |\n"
        )
        f.write(
            "| tag_v2 | 2026-11-18 | Added role descriptions to taxonomy. "
            "| Clarify boundary cases between roles. "
            "| Models hallucinated aliased role names. |\n"
        )
        f.write(
            "| tag_v3 | 2026-11-19 | Fixed alias drift back to exact canonical taxonomy enums. "
            "| Prevent invalid enum generation. "
            "| Role accuracy improved to 82.0%; zero invalid values. |\n"
        )
        f.write(
            "| tag_v4 | 2026-11-19 | Aligned verbatim role definitions with specification. "
            "| Consistent role scope across candidate models. "
            "| Final benchmark role accuracy: 83.7% (with row 36 excluded). |\n\n"
        )

        for v in versions:
            p_file = prompts_dir / v
            if p_file.exists():
                f.write(f"## Version: {v}\n\n")
                f.write("```text\n")
                f.write(p_file.read_text(encoding="utf-8"))
                f.write("\n```\n\n")

    print(f"Exported prompt archive to {output_path}")


def export_breaks_csv(submission_dir: Path) -> int:
    breaks_file = Path("BREAKS.md")
    if not breaks_file.exists():
        print("BREAKS.md not found.")
        return 0

    content = breaks_file.read_text(encoding="utf-8")
    entries: list[dict[str, str]] = []

    pattern = re.compile(
        r"^##\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(.+?)\n"
        r"Symptom:\s*(.+?)\n"
        r"Root cause:\s*(.+?)\n"
        r"Fix:\s*(.+?)\n"
        r"Commit:\s*(.+?)\n"
        r"Next time:\s*(.+?)(?=\n##|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    for match in pattern.finditer(content):
        entries.append(
            {
                "timestamp": match.group(1).strip(),
                "title": match.group(2).strip(),
                "symptom": match.group(3).strip().replace("\n", " "),
                "root_cause": match.group(4).strip().replace("\n", " "),
                "fix": match.group(5).strip().replace("\n", " "),
                "commit": match.group(6).strip(),
                "next_time": match.group(7).strip().replace("\n", " "),
            }
        )

    output_path = submission_dir / "breaks.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["timestamp", "title", "symptom", "root_cause", "fix", "commit", "next_time"]
        )
        for e in entries:
            writer.writerow(
                [
                    e["timestamp"],
                    e["title"],
                    e["symptom"],
                    e["root_cause"],
                    e["fix"],
                    e["commit"],
                    e["next_time"],
                ]
            )

    print(f"Exported {len(entries)} breaks to {output_path}")
    return len(entries)


def main() -> None:
    submission_dir = Path("docs/submission")
    submission_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print("EXPORTING SUBMISSION ARTIFACTS TO docs/submission/")
    print("=" * 65)

    export_jobs_csv(submission_dir)
    export_eval_comparison_csv(submission_dir)
    export_costs_csv(submission_dir)
    export_prompts_markdown(submission_dir)
    export_breaks_csv(submission_dir)

    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
