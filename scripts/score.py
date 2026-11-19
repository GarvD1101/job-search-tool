"""Evaluation and scoring script for fresher-radar LLM tagging benchmark.

Compares human labels from Excel against model predictions in bench JSON.
Calculates:
- Headline Strict Numbers:
  - Role accuracy (with row 36 excluded from role only)
  - City accuracy
  - is_fresher agreement (excluding Unsure)
  - Precision and Recall on the No class (detecting non-freshers)
  - Top 5 role confusion pairs
- Secondary Metrics:
  - Role accuracy excluding rows whose human label is 'other' (with n and excluded row numbers)
  - Role-family accuracy using families defined in config/taxonomy.yaml
  - Error counts: wrong city, false accept, false reject, invalid enum values

Outputs:
- Console report table with sample size (n) for each metric
- Disagreements-only CSV: docs/results/disagreements_<model>_<version>.csv
- Disagreements-only HTML: docs/results/disagreements_<model>_<version>.html
- Model score reports: docs/results/score_<model>_<version>.txt
- Summary comparison table across models
"""

import argparse
import csv
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from pipeline.llm.base import City, PostType, Role

logger = logging.getLogger(__name__)

OPENXML_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OPENXML_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OPENXML_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def load_role_families(taxonomy_path: Path | str = "config/taxonomy.yaml") -> dict[str, str]:
    """Map each role to its role family defined in config/taxonomy.yaml."""
    path = Path(taxonomy_path)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            families = data.get("role_families", {})
            role_to_family = {}
            for fam, roles in families.items():
                for r in roles:
                    role_to_family[normalize_token(r)] = fam
            if role_to_family:
                return role_to_family
        except Exception as exc:
            logger.warning("Could not load role families from %s: %s", path, exc)

    return {
        "software_dev": "tech",
        "data_analytics": "tech",
        "ml_ai": "tech",
        "ai_ml": "tech",
        "it_devops_security": "tech",
        "devops_cloud": "tech",
        "cybersecurity": "tech",
        "qa_testing": "tech",
        "teaching_education": "education_research",
        "teaching_academics": "education_research",
        "research": "education_research",
        "research_science": "education_research",
        "core_engineering": "engineering_health",
        "healthcare": "engineering_health",
        "healthcare_pharma": "engineering_health",
        "sales_bd": "business",
        "marketing": "business",
        "marketing_growth": "business",
        "content_writing": "business",
        "design": "business",
        "design_creative": "business",
        "product_management": "business",
        "customer_support": "operations_support",
        "admin_back_office": "operations_support",
        "operations_logistics": "operations_support",
        "hospitality_retail": "operations_support",
        "bpo_kpo": "operations_support",
        "hospitality_travel": "operations_support",
        "hr_recruitment": "people_finance_legal",
        "finance_banking": "people_finance_legal",
        "legal_compliance": "people_finance_legal",
        "other": "other",
    }


def read_xlsx_sheet(file_path: Path | str, sheet_name: str = "Label") -> list[dict[str, str]]:
    """Read rows from an xlsx sheet using standard library zipfile and xml.etree."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found at {file_path}")

    with zipfile.ZipFile(file_path, "r") as z:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            si_elements = tree.findall(f".//{{{OPENXML_SHEET_NS}}}si")
            if not si_elements:
                si_elements = tree.findall(".//si")
            for si in si_elements:
                t_elements = si.findall(f".//{{{OPENXML_SHEET_NS}}}t")
                if not t_elements:
                    t_elements = si.findall(".//t")
                text_parts = [t.text or "" for t in t_elements]
                shared_strings.append("".join(text_parts))

        sheet_path = None
        if "xl/workbook.xml" in z.namelist() and "xl/_rels/workbook.xml.rels" in z.namelist():
            wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
            rels_tree = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))

            rel_ns = {"rel": OPENXML_REL_NS}
            rid_map: dict[str, str] = {}
            rels = rels_tree.findall(".//rel:Relationship", rel_ns)
            if not rels:
                rels = rels_tree.findall(".//Relationship")
            for rel in rels:
                r_id = rel.attrib.get("Id")
                target = rel.attrib.get("Target")
                if r_id and target:
                    rid_map[r_id] = target

            wb_ns = {"ns": OPENXML_SHEET_NS, "r": OPENXML_DOC_REL_NS}
            sheets = wb_tree.findall(".//ns:sheet", wb_ns)
            if not sheets:
                sheets = wb_tree.findall(".//sheet")
            for sheet in sheets:
                s_name = sheet.attrib.get("name")
                r_id = sheet.attrib.get(f"{{{wb_ns['r']}}}id") or sheet.attrib.get("r:id")
                if s_name and s_name.strip().lower() == sheet_name.strip().lower() and r_id:
                    target = rid_map.get(r_id, "")
                    if target:
                        if not target.startswith("xl/"):
                            target = "xl/" + target.lstrip("/")
                        sheet_path = target
                    break

        if not sheet_path or sheet_path not in z.namelist():
            candidates = [
                n for n in z.namelist()
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            ]
            if candidates:
                sheet_path = candidates[0]
            else:
                raise ValueError(f"No worksheet found in {file_path}")

        sheet_tree = ET.fromstring(z.read(sheet_path))
        rows_data: list[dict[str, str]] = []

        row_elements = sheet_tree.findall(f".//{{{OPENXML_SHEET_NS}}}row")
        if not row_elements:
            row_elements = sheet_tree.findall(".//row")

        for row in row_elements:
            cell_map: dict[str, str] = {}
            cells = row.findall(f".//{{{OPENXML_SHEET_NS}}}c")
            if not cells:
                cells = row.findall(".//c")

            for cell in cells:
                ref = cell.attrib.get("r", "")
                col_letters = "".join(filter(str.isalpha, ref))
                cell_type = cell.attrib.get("t")
                v_elem = cell.find(f".//{{{OPENXML_SHEET_NS}}}v")
                if v_elem is None:
                    v_elem = cell.find(".//v")

                val = ""
                if cell_type == "s" and v_elem is not None and v_elem.text is not None:
                    try:
                        idx = int(v_elem.text)
                        if 0 <= idx < len(shared_strings):
                            val = shared_strings[idx]
                    except ValueError:
                        val = v_elem.text
                elif cell_type == "inlineStr":
                    is_elem = cell.find(f".//{{{OPENXML_SHEET_NS}}}is")
                    if is_elem is None:
                        is_elem = cell.find(".//is")
                    if is_elem is not None:
                        t_elem = is_elem.find(f".//{{{OPENXML_SHEET_NS}}}t")
                        if t_elem is None:
                            t_elem = is_elem.find(".//t")
                        if t_elem is not None and t_elem.text:
                            val = t_elem.text
                elif v_elem is not None and v_elem.text is not None:
                    val = v_elem.text

                if col_letters:
                    cell_map[col_letters] = val.strip()

            if cell_map:
                rows_data.append(cell_map)

        if not rows_data:
            return []

        header_row = rows_data[0]
        sorted_cols = sorted(header_row.keys(), key=lambda c: (len(c), c))
        headers = {col: header_row[col].strip() for col in sorted_cols if header_row[col].strip()}

        records: list[dict[str, str]] = []
        for r in rows_data[1:]:
            record = {h: r.get(col, "").strip() for col, h in headers.items()}
            if any(record.values()):
                records.append(record)

        return records


def read_key_csv(file_path: Path | str) -> dict[str, str]:
    """Read sample_50_key.csv mapping row_no to id."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Key file not found at {path}")

    mapping: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return mapping

        row_idx = 0
        id_idx = 1
        for i, col in enumerate(header):
            col_clean = col.strip().lower()
            if col_clean in ("#", "row_no", "row", "index"):
                row_idx = i
            elif col_clean in ("id", "job_id", "source_id"):
                id_idx = i

        for parts in reader:
            if len(parts) > max(row_idx, id_idx):
                row_val = parts[row_idx].strip()
                id_val = parts[id_idx].strip()
                if row_val and id_val:
                    mapping[row_val] = id_val

    return mapping


def normalize_token(token: str) -> str:
    """Normalize string tokens for comparison."""
    t = token.strip().lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")


def evaluate_benchmark(
    labels: list[dict[str, str]],
    key_map: dict[str, str],
    bench_data: dict[str, Any],
    exclude_role_rows: set[str] | None = None,
    role_to_family: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute benchmark comparison metrics with headline strict and secondary metrics."""
    bench_results = bench_data.get("results", [])
    model_by_id: dict[str, dict[str, Any]] = {}
    model_by_idx: dict[str, dict[str, Any]] = {}

    allowed_roles = {r.value for r in Role}
    allowed_cities = {c.value for c in City}
    allowed_post_types = {p.value for p in PostType}

    invalid_enum_count = 0
    for res in bench_results:
        if "id" in res:
            model_by_id[str(res["id"]).strip()] = res
        if "index" in res:
            model_by_idx[str(res["index"]).strip()] = res

        r_val = str(res.get("role", ""))
        c_val = str(res.get("city", ""))
        p_val = str(res.get("post_type", ""))
        if (
            r_val not in allowed_roles
            or c_val not in allowed_cities
            or p_val not in allowed_post_types
        ):
            invalid_enum_count += 1

    families_map = role_to_family or load_role_families()
    exclude_role_set = exclude_role_rows or set()

    total_evaluated = 0
    role_evaluated = 0
    role_matches = 0
    city_matches = 0

    # Secondary: Role accuracy excluding 'other'
    role_excl_other_evaluated = 0
    role_excl_other_matches = 0
    other_excluded_rows: list[str] = []

    # Secondary: Role-family accuracy
    role_family_matches = 0

    fresher_evaluated = 0
    fresher_matches = 0
    unsure_fresher_count = 0

    # Error counters
    false_accept_count = 0  # model True where human No
    false_reject_count = 0  # model False where human Yes
    wrong_city_count = 0

    tp_no = 0
    fp_no = 0
    fn_no = 0
    tn_no = 0

    role_confusions: list[tuple[str, str]] = []
    disagreements: list[dict[str, Any]] = []

    for i, row in enumerate(labels):
        row_no = str(row.get("#", str(i + 1))).strip()
        job_id = key_map.get(row_no, "")

        model_res = model_by_id.get(job_id)
        if not model_res:
            model_res = model_by_idx.get(str(i))
        if not model_res:
            continue

        total_evaluated += 1

        title = row.get("Post") or row.get("title") or model_res.get("title", "")
        raw_human_role = row.get("Role", "")
        human_role = normalize_token(raw_human_role)
        model_role = normalize_token(str(model_res.get("role", "")))

        human_city = normalize_token(row.get("City", ""))
        model_city = normalize_token(str(model_res.get("city", "")))

        human_fresher_raw = row.get("Fresher job?", "").strip()
        model_fresher = bool(model_res.get("is_fresher"))

        # Role evaluation (headline strict: row 36 excluded)
        skip_role = (row_no in exclude_role_set)
        role_matched = False
        if not skip_role:
            role_evaluated += 1
            role_matched = (human_role == model_role)
            if role_matched:
                role_matches += 1
            else:
                role_confusions.append((human_role, model_role))

            # Secondary a: Exclude human 'other'
            if human_role == "other":
                other_excluded_rows.append(row_no)
            else:
                role_excl_other_evaluated += 1
                if role_matched:
                    role_excl_other_matches += 1

            # Secondary b: Role-family evaluation
            human_fam = families_map.get(human_role, "other")
            model_fam = families_map.get(model_role, "other")
            if human_fam == model_fam:
                role_family_matches += 1

        # City check (always evaluated)
        city_matched = (human_city == model_city)
        if city_matched:
            city_matches += 1
        else:
            wrong_city_count += 1

        # Fresher check (Exclude Unsure)
        fresher_evaluable = False
        fresher_matched = False
        human_fresher_bool: bool | None = None

        if human_fresher_raw.lower() in ("yes", "y", "true", "1"):
            human_fresher_bool = True
        elif human_fresher_raw.lower() in ("no", "n", "false", "0"):
            human_fresher_bool = False
        else:
            unsure_fresher_count += 1

        if human_fresher_bool is not None:
            fresher_evaluable = True
            fresher_evaluated += 1
            fresher_matched = (human_fresher_bool == model_fresher)
            if fresher_matched:
                fresher_matches += 1

            if human_fresher_bool is False and model_fresher is False:
                tp_no += 1
            elif human_fresher_bool is True and model_fresher is False:
                fp_no += 1
                false_reject_count += 1
            elif human_fresher_bool is False and model_fresher is True:
                fn_no += 1
                false_accept_count += 1
            elif human_fresher_bool is True and model_fresher is True:
                tn_no += 1

        is_disagreement = False
        if not skip_role and not role_matched:
            is_disagreement = True
        if not city_matched:
            is_disagreement = True
        if fresher_evaluable and not fresher_matched:
            is_disagreement = True

        if is_disagreement:
            disagreements.append({
                "row #": row_no,
                "title": title,
                "my role": raw_human_role,
                "model role": model_res.get("role", ""),
                "my city": row.get("City", ""),
                "model city": model_res.get("city", ""),
                "my fresher label": human_fresher_raw,
                "model is_fresher": model_fresher,
            })

    role_acc = (role_matches / role_evaluated * 100.0) if role_evaluated > 0 else 0.0
    city_acc = (city_matches / total_evaluated * 100.0) if total_evaluated > 0 else 0.0
    fresher_acc = (
        (fresher_matches / fresher_evaluated * 100.0)
        if fresher_evaluated > 0
        else 0.0
    )

    role_excl_other_acc = (
        (role_excl_other_matches / role_excl_other_evaluated * 100.0)
        if role_excl_other_evaluated > 0
        else 0.0
    )
    role_family_acc = (
        (role_family_matches / role_evaluated * 100.0)
        if role_evaluated > 0
        else 0.0
    )

    no_precision = (tp_no / (tp_no + fp_no) * 100.0) if (tp_no + fp_no) > 0 else 0.0
    no_recall = (tp_no / (tp_no + fn_no) * 100.0) if (tp_no + fn_no) > 0 else 0.0

    top_5_confusions = Counter(role_confusions).most_common(5)

    return {
        "total_evaluated": total_evaluated,
        "role_evaluated": role_evaluated,
        "role_matches": role_matches,
        "role_accuracy_pct": role_acc,
        "city_matches": city_matches,
        "city_accuracy_pct": city_acc,
        "fresher_evaluated": fresher_evaluated,
        "fresher_matches": fresher_matches,
        "fresher_agreement_pct": fresher_acc,
        "unsure_fresher_count": unsure_fresher_count,
        "no_class_metrics": {
            "tp": tp_no,
            "fp": fp_no,
            "fn": fn_no,
            "tn": tn_no,
            "n_precision": tp_no + fp_no,
            "n_recall": tp_no + fn_no,
            "precision_pct": no_precision,
            "recall_pct": no_recall,
        },
        "top_5_role_confusions": top_5_confusions,
        "disagreements": disagreements,
        "excluded_role_rows": sorted(exclude_role_set),
        "secondary_metrics": {
            "role_excl_other_accuracy_pct": role_excl_other_acc,
            "role_excl_other_matches": role_excl_other_matches,
            "role_excl_other_evaluated": role_excl_other_evaluated,
            "other_excluded_rows": other_excluded_rows,
            "role_family_accuracy_pct": role_family_acc,
            "role_family_matches": role_family_matches,
            "role_family_evaluated": role_evaluated,
            "error_counts": {
                "wrong_city": wrong_city_count,
                "false_accept": false_accept_count,
                "false_reject": false_reject_count,
                "invalid_enum_values": invalid_enum_count,
            },
        },
    }


def write_disagreements_csv(path: Path | str, disagreements: list[dict[str, Any]]) -> None:
    """Write disagreements to RFC-4180 CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "row #",
        "title",
        "my role",
        "model role",
        "my city",
        "model city",
        "my fresher label",
        "model is_fresher",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in disagreements:
            writer.writerow({k: d.get(k, "") for k in fieldnames})


def write_disagreements_html(
    path: Path | str,
    disagreements: list[dict[str, Any]],
    model_name: str,
) -> None:
    """Write disagreements to a standalone HTML file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows_html: list[str] = []
    for d in disagreements:
        role_diff = normalize_token(str(d["my role"])) != normalize_token(str(d["model role"]))
        city_diff = normalize_token(str(d["my city"])) != normalize_token(str(d["model city"]))

        my_f = str(d["my fresher label"]).strip().lower()
        m_f = bool(d["model is_fresher"])
        fresher_diff = (my_f == "yes" and not m_f) or (my_f == "no" and m_f)

        r_class = ' class="diff"' if role_diff else ""
        c_class = ' class="diff"' if city_diff else ""
        f_class = ' class="diff"' if fresher_diff else ""

        rows_html.append(
            f"<tr>"
            f"<td>{d['row #']}</td>"
            f"<td>{d['title']}</td>"
            f"<td>{d['my role']}</td>"
            f"<td{r_class}>{d['model role']}</td>"
            f"<td>{d['my city']}</td>"
            f"<td{c_class}>{d['model city']}</td>"
            f"<td>{d['my fresher label']}</td>"
            f"<td{f_class}>{d['model is_fresher']}</td>"
            f"</tr>"
        )

    css_style = (
        "body { font-family: -apple-system, sans-serif; margin: 24px; color: #24292f; }\n"
        "table { border-collapse: collapse; width: 100%; border: 1px solid #d0d7de; }\n"
        "th, td { padding: 8px 12px; text-align: left; font-size: 13px; "
        "border-bottom: 1px solid #d0d7de; }\n"
        "th { background: #f6f8fa; font-weight: 600; }\n"
        "tr:hover { background: #f3f4f6; }\n"
        "td.diff { background: #ffebe9; color: #cf222e; font-weight: 600; }\n"
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Tagging Disagreements: {model_name}</title>
<style>
{css_style}
</style>
</head>
<body>
  <h1>Disagreements Report: {model_name}</h1>
  <p>Total Disagreements: {len(disagreements)}</p>
  <table>
    <thead>
      <tr>
        <th>Row #</th>
        <th>Title</th>
        <th>My Role</th>
        <th>Model Role</th>
        <th>My City</th>
        <th>Model City</th>
        <th>My Fresher Label</th>
        <th>Model is_fresher</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows_html)}
    </tbody>
  </table>
</body>
</html>
"""
    path.write_text(html_content, encoding="utf-8")


def format_report(metrics: dict[str, Any], model_name: str, csv_path: Path, html_path: Path) -> str:
    """Format evaluation metrics into readable text report with secondary metrics."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"BENCHMARK EVALUATION REPORT: {model_name}")
    lines.append("=" * 60)

    tot = metrics["total_evaluated"]
    r_n = metrics["role_evaluated"]
    r_acc = metrics["role_accuracy_pct"]
    r_m = metrics["role_matches"]
    c_acc = metrics["city_accuracy_pct"]
    c_m = metrics["city_matches"]
    f_n = metrics["fresher_evaluated"]
    f_acc = metrics["fresher_agreement_pct"]
    f_m = metrics["fresher_matches"]
    u_n = metrics["unsure_fresher_count"]

    no_prec = metrics["no_class_metrics"]["precision_pct"]
    no_rec = metrics["no_class_metrics"]["recall_pct"]
    n_p = metrics["no_class_metrics"]["n_precision"]
    n_r = metrics["no_class_metrics"]["n_recall"]

    sec = metrics["secondary_metrics"]
    sec_r_acc = sec["role_excl_other_accuracy_pct"]
    sec_r_m = sec["role_excl_other_matches"]
    sec_r_n = sec["role_excl_other_evaluated"]
    sec_ex_rows = sec["other_excluded_rows"]

    sec_fam_acc = sec["role_family_accuracy_pct"]
    sec_fam_m = sec["role_family_matches"]
    sec_fam_n = sec["role_family_evaluated"]

    err = sec["error_counts"]

    lines.append("Headline Strict Metrics:")
    if metrics.get("excluded_role_rows"):
        lines.append(
            f"  Role Excluded Row: {metrics['excluded_role_rows']} (dropped from role only)"
        )
    lines.append(f"  Total Evaluated:   {tot}")
    lines.append(f"  Role Accuracy:     {r_acc:.1f}% ({r_m}/{r_n}, n={r_n})")
    lines.append(f"  City Accuracy:     {c_acc:.1f}% ({c_m}/{tot}, n={tot})")
    lines.append(f"  Unsure Excluded:   {u_n} rows dropped from fresher metrics")
    lines.append(f"  Fresher Agree:     {f_acc:.1f}% ({f_m}/{f_n}, n={f_n}) [Yes/No rows only]")
    lines.append(f"  No-Class Prec:     {no_prec:.1f}% (n={n_p})")
    lines.append(f"  No-Class Recall:   {no_rec:.1f}% (n={n_r})")
    lines.append("")
    lines.append("Secondary Metrics:")
    lines.append(
        f"  Role Acc (excl 'other'): {sec_r_acc:.1f}% ({sec_r_m}/{sec_r_n}, n={sec_r_n}) "
        f"[excluded row(s): {sec_ex_rows}]"
    )
    lines.append(
        f"  Role-Family Accuracy:    {sec_fam_acc:.1f}% ({sec_fam_m}/{sec_fam_n}, n={sec_fam_n})"
    )
    lines.append("")
    lines.append("Error Counts (Secondary):")
    lines.append(f"  - Wrong City:            {err['wrong_city']}")
    lines.append(
        f"  - False Accept (FN):     {err['false_accept']} (model fresher True where human No)"
    )
    lines.append(
        f"  - False Reject (FP):     {err['false_reject']} (model fresher False where human Yes)"
    )
    lines.append(f"  - Invalid Enum Values:   {err['invalid_enum_values']}")
    lines.append("")
    lines.append("Top 5 Role Confusion Pairs (Human -> Model):")
    for (h_role, m_role), count in metrics["top_5_role_confusions"]:
        lines.append(f"  - {h_role} -> {m_role}: {count}")
    lines.append("")
    lines.append(f"Disagreements:   {len(metrics['disagreements'])} rows")
    lines.append(f"Saved CSV:       {csv_path}")
    lines.append(f"Saved HTML:      {html_path}")
    lines.append("=" * 60)
    return "\n".join(lines)


def score_single_model(
    bench_json_path: Path | str,
    labeled_path: Path | str = "eval/sample_50_labeled.xlsx",
    sheet_name: str = "Label",
    key_path: Path | str = "eval/sample_50_key.csv",
    output_dir: Path | str = "docs/results",
    exclude_role_rows: str = "36",
    version_suffix: str = "v3",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Score a single model bench result."""
    bench_path = Path(bench_json_path)
    with open(bench_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    model_name = bench_data.get("model", bench_path.stem.replace("bench_", ""))
    model_slug = model_name.split("/")[-1]

    exclude_set = {
        r.strip() for r in exclude_role_rows.split(",") if r.strip()
    }

    labels = read_xlsx_sheet(labeled_path, sheet_name=sheet_name)
    key_map = read_key_csv(key_path)

    metrics = evaluate_benchmark(
        labels,
        key_map,
        bench_data,
        exclude_role_rows=exclude_set,
    )

    clean_model_id = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", model_slug)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"disagreements_{clean_model_id}_{version_suffix}.csv"
    html_path = out_dir / f"disagreements_{clean_model_id}_{version_suffix}.html"

    write_disagreements_csv(csv_path, metrics["disagreements"])
    write_disagreements_html(html_path, metrics["disagreements"], model_name)

    report_text = format_report(metrics, model_name, csv_path, html_path)

    score_file = out_dir / f"score_{clean_model_id}_{version_suffix}.txt"
    score_file.write_text(report_text, encoding="utf-8")

    return metrics, bench_data, report_text


def compute_cost_per_1k(
    inp_tok_per_post: float,
    out_tok_per_post: float,
    model_id: str,
    pricing_path: Path | str = "config/pricing.yaml",
) -> float:
    """Calculate list-price cost for 1,000 posts based on pricing.yaml."""
    p_path = Path(pricing_path)
    prices = {
        "openai/gpt-oss-20b": (0.075, 0.30),
        "openai/gpt-oss-120b": (0.15, 0.60),
        "qwen/qwen3.8-27b": (0.80, 4.00),
    }
    if p_path.exists():
        try:
            with open(p_path, "r", encoding="utf-8") as f:
                p_data = yaml.safe_load(f) or {}
            m_data = p_data.get("models", {}).get(model_id, {})
            if m_data:
                prices[model_id] = (
                    float(m_data.get("input_price_per_1m", 0.0)),
                    float(m_data.get("output_price_per_1m", 0.0)),
                )
        except Exception:
            pass

    inp_price, out_price = prices.get(model_id, (0.0, 0.0))
    inp_cost = (inp_tok_per_post * 1000.0 * inp_price) / 1_000_000.0
    out_cost = (out_tok_per_post * 1000.0 * out_price) / 1_000_000.0
    return round(inp_cost + out_cost, 4)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score LLM tagging benchmark against human labels."
    )
    parser.add_argument(
        "--labeled", default="eval/sample_50_labeled.xlsx", help="Path to labeled Excel file"
    )
    parser.add_argument("--sheet", default="Label", help="Sheet name in Excel file")
    parser.add_argument("--key", default="eval/sample_50_key.csv", help="Path to key CSV file")
    parser.add_argument("--bench-json", default=None, help="Path to single model bench JSON")
    parser.add_argument(
        "--compare",
        nargs="+",
        default=None,
        help="List of bench JSON files to evaluate and produce comparison table",
    )
    parser.add_argument(
        "--output-dir", default="docs/results", help="Directory to save reports"
    )
    parser.add_argument(
        "--exclude-role-rows",
        default="36",
        help="Comma-separated row numbers to exclude from role accuracy only (e.g. '36')",
    )
    parser.add_argument(
        "--version-suffix", default="v3", help="Version suffix for output files (default: v3)"
    )

    args = parser.parse_args()

    bench_files = []
    if args.compare:
        bench_files = [Path(p) for p in args.compare]
    elif args.bench_json:
        bench_files = [Path(args.bench_json)]
    else:
        logger.error("Must specify either --bench-json or --compare")
        sys.exit(1)

    all_results: list[dict[str, Any]] = []

    for b_file in bench_files:
        metrics, bench_data, rep_text = score_single_model(
            bench_json_path=b_file,
            labeled_path=args.labeled,
            sheet_name=args.sheet,
            key_path=args.key,
            output_dir=args.output_dir,
            exclude_role_rows=args.exclude_role_rows,
            version_suffix=args.version_suffix,
        )
        print("\n" + rep_text + "\n")

        model_name = bench_data.get("model", b_file.stem)
        tok = bench_data.get("tokens", {})
        inp_p = tok.get("input_per_post", 0.0)
        out_p = tok.get("output_per_post", 0.0)
        reas_p = tok.get("reasoning_per_post", 0.0)
        cost_1k = compute_cost_per_1k(inp_p, out_p, model_name)

        all_results.append({
            "model": model_name,
            "json_validity": bench_data.get("validity_rate_pct", 100.0),
            "role_acc": metrics["role_accuracy_pct"],
            "role_n": metrics["role_evaluated"],
            "role_excl_other_acc": metrics["secondary_metrics"]["role_excl_other_accuracy_pct"],
            "role_excl_other_n": metrics["secondary_metrics"]["role_excl_other_evaluated"],
            "role_fam_acc": metrics["secondary_metrics"]["role_family_accuracy_pct"],
            "city_acc": metrics["city_accuracy_pct"],
            "city_n": metrics["total_evaluated"],
            "fresher_agree": metrics["fresher_agreement_pct"],
            "fresher_n": metrics["fresher_evaluated"],
            "no_prec": metrics["no_class_metrics"]["precision_pct"],
            "no_rec": metrics["no_class_metrics"]["recall_pct"],
            "inp_per_post": inp_p,
            "out_per_post": out_p,
            "reas_per_post": reas_p,
            "cost_per_1k": cost_1k,
        })

    if len(all_results) > 1:
        tbl_lines = []
        tbl_lines.append("=" * 110)
        tbl_lines.append(
            f"THREE-MODEL BENCHMARK COMPARISON TABLE (Prompt tag_{args.version_suffix})"
        )
        tbl_lines.append("=" * 110)
        header = (
            f"{'Model':<20} | {'Validity':<8} | {'Role (n=49)':<11} | "
            f"{'Role-NoOth':<10} | {'Role-Fam':<9} | {'City':<8} | "
            f"{'Fresh(n=48)':<11} | {'No-Prec':<7} | {'No-Rec':<7} | "
            f"{'In/Post':<7} | {'Out/Post':<8} | {'Cost/1k':<7}"
        )
        tbl_lines.append(header)
        tbl_lines.append("-" * 110)

        for r in all_results:
            row_str = (
                f"{r['model']:<20} | {r['json_validity']:>7.1f}% | {r['role_acc']:>10.1f}% | "
                f"{r['role_excl_other_acc']:>9.1f}% | {r['role_fam_acc']:>8.1f}% | "
                f"{r['city_acc']:>7.1f}% | "
                f"{r['fresher_agree']:>10.1f}% | {r['no_prec']:>6.1f}% | {r['no_rec']:>6.1f}% | "
                f"{r['inp_per_post']:>7.1f} | {r['out_per_post']:>8.1f} | ${r['cost_per_1k']:>6.4f}"
            )
            tbl_lines.append(row_str)
        tbl_lines.append("=" * 110)

        table_output = "\n".join(tbl_lines)
        print("\n" + table_output + "\n")

        tbl_file = Path(args.output_dir) / f"comparison_{args.version_suffix}.txt"
        tbl_file.write_text(table_output, encoding="utf-8")


if __name__ == "__main__":
    main()
