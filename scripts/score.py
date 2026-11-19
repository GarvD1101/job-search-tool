"""Evaluation and scoring script for fresher-radar LLM tagging benchmark.

Compares human labels from Excel against model predictions in bench JSON.
Calculates:
- Role accuracy
- City accuracy
- is_fresher agreement (excluding Unsure)
- Precision and Recall on the No class (detecting non-freshers)
- Top 5 role confusion pairs

Outputs:
- Console report table
- Disagreements-only CSV: docs/results/disagreements_<model>.csv
- Disagreements-only HTML: docs/results/disagreements_<model>.html
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

logger = logging.getLogger(__name__)

OPENXML_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OPENXML_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OPENXML_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_xlsx_sheet(file_path: Path | str, sheet_name: str = "Label") -> list[dict[str, str]]:
    """Read rows from an xlsx sheet using standard library zipfile and xml.etree."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found at {file_path}")

    with zipfile.ZipFile(file_path, "r") as z:
        # 1. Parse shared strings if present
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ns = {"ns": OPENXML_SHEET_NS}
            si_elements = tree.findall(".//ns:si", ns) or tree.findall(".//si")
            for si in si_elements:
                t_elements = si.findall(".//ns:t", ns) or si.findall(".//t")
                text_parts = [t.text or "" for t in t_elements]
                shared_strings.append("".join(text_parts))

        # 2. Locate target worksheet XML from workbook metadata
        sheet_path = "xl/worksheets/sheet1.xml"
        if "xl/workbook.xml" in z.namelist() and "xl/_rels/workbook.xml.rels" in z.namelist():
            wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
            rels_tree = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))

            rel_ns = {"rel": OPENXML_REL_NS}
            rid_map: dict[str, str] = {}
            for rel in (
                rels_tree.findall(".//rel:Relationship", rel_ns)
                or rels_tree.findall(".//Relationship")
            ):
                r_id = rel.attrib.get("Id")
                target = rel.attrib.get("Target")
                if r_id and target:
                    rid_map[r_id] = target

            wb_ns = {"ns": OPENXML_SHEET_NS, "r": OPENXML_DOC_REL_NS}
            sheets = wb_tree.findall(".//ns:sheet", wb_ns) or wb_tree.findall(".//sheet")
            for sheet in sheets:
                s_name = sheet.attrib.get("name")
                r_id = sheet.attrib.get(f"{{{wb_ns['r']}}}id") or sheet.attrib.get("r:id")
                if s_name and s_name.strip().lower() == sheet_name.strip().lower() and r_id:
                    target = rid_map.get(r_id, "worksheets/sheet1.xml")
                    if not target.startswith("xl/"):
                        target = "xl/" + target.lstrip("/")
                    sheet_path = target
                    break

        if sheet_path not in z.namelist():
            candidates = [
                n for n in z.namelist()
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            ]
            if candidates:
                sheet_path = candidates[0]
            else:
                raise ValueError(f"No worksheet found in {file_path}")

        # 3. Parse cell records from sheet XML
        sheet_tree = ET.fromstring(z.read(sheet_path))
        rows_data: list[dict[str, str]] = []

        row_elements = (
            sheet_tree.findall(f".//{{{OPENXML_SHEET_NS}}}row")
            or sheet_tree.findall(".//row")
        )
        for row in row_elements:
            cell_map: dict[str, str] = {}
            cells = (
                row.findall(f".//{{{OPENXML_SHEET_NS}}}c")
                or row.findall(".//c")
            )
            for cell in cells:
                ref = cell.attrib.get("r", "")
                col_letters = "".join(filter(str.isalpha, ref))
                cell_type = cell.attrib.get("t")
                v_elem = (
                    cell.find(f".//{{{OPENXML_SHEET_NS}}}v")
                    or cell.find(".//v")
                )

                val = ""
                if cell_type == "s" and v_elem is not None and v_elem.text is not None:
                    try:
                        idx = int(v_elem.text)
                        if 0 <= idx < len(shared_strings):
                            val = shared_strings[idx]
                    except ValueError:
                        val = v_elem.text
                elif cell_type == "inlineStr":
                    is_elem = (
                        cell.find(f".//{{{OPENXML_SHEET_NS}}}is")
                        or cell.find(".//is")
                    )
                    if is_elem is not None:
                        t_elem = (
                            is_elem.find(f".//{{{OPENXML_SHEET_NS}}}t")
                            or is_elem.find(".//t")
                        )
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

        # First row is assumed to be header
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
) -> dict[str, Any]:
    """Compute benchmark comparison metrics."""
    bench_results = bench_data.get("results", [])
    model_by_id: dict[str, dict[str, Any]] = {}
    model_by_idx: dict[str, dict[str, Any]] = {}

    for res in bench_results:
        if "id" in res:
            model_by_id[str(res["id"]).strip()] = res
        if "index" in res:
            model_by_idx[str(res["index"]).strip()] = res

    total_evaluated = 0
    role_matches = 0
    city_matches = 0

    fresher_evaluated = 0
    fresher_matches = 0

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
        human_role = normalize_token(row.get("Role", ""))
        model_role = normalize_token(str(model_res.get("role", "")))

        human_city = normalize_token(row.get("City", ""))
        model_city = normalize_token(str(model_res.get("city", "")))

        human_fresher_raw = row.get("Fresher job?", "").strip()
        model_fresher = bool(model_res.get("is_fresher"))

        # Role check
        role_matched = (human_role == model_role)
        if role_matched:
            role_matches += 1
        else:
            role_confusions.append((human_role, model_role))

        # City check
        city_matched = (human_city == model_city)
        if city_matched:
            city_matches += 1

        # Fresher check (Exclude Unsure)
        fresher_evaluable = False
        fresher_matched = False
        human_fresher_bool: bool | None = None

        if human_fresher_raw.lower() in ("yes", "y", "true", "1"):
            human_fresher_bool = True
        elif human_fresher_raw.lower() in ("no", "n", "false", "0"):
            human_fresher_bool = False

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
            elif human_fresher_bool is False and model_fresher is True:
                fn_no += 1
            elif human_fresher_bool is True and model_fresher is True:
                tn_no += 1

        # Check disagreement
        is_disagreement = False
        if not role_matched or not city_matched:
            is_disagreement = True
        if fresher_evaluable and not fresher_matched:
            is_disagreement = True

        if is_disagreement:
            disagreements.append({
                "row #": row_no,
                "title": title,
                "my role": row.get("Role", ""),
                "model role": model_res.get("role", ""),
                "my city": row.get("City", ""),
                "model city": model_res.get("city", ""),
                "my fresher label": human_fresher_raw,
                "model is_fresher": model_fresher,
            })

    role_acc = (role_matches / total_evaluated * 100.0) if total_evaluated > 0 else 0.0
    city_acc = (city_matches / total_evaluated * 100.0) if total_evaluated > 0 else 0.0
    fresher_acc = (
        (fresher_matches / fresher_evaluated * 100.0)
        if fresher_evaluated > 0
        else 0.0
    )

    no_precision = (tp_no / (tp_no + fp_no) * 100.0) if (tp_no + fp_no) > 0 else 0.0
    no_recall = (tp_no / (tp_no + fn_no) * 100.0) if (tp_no + fn_no) > 0 else 0.0

    top_5_confusions = Counter(role_confusions).most_common(5)

    return {
        "total_evaluated": total_evaluated,
        "role_matches": role_matches,
        "role_accuracy_pct": role_acc,
        "city_matches": city_matches,
        "city_accuracy_pct": city_acc,
        "fresher_evaluated": fresher_evaluated,
        "fresher_matches": fresher_matches,
        "fresher_agreement_pct": fresher_acc,
        "no_class_metrics": {
            "tp": tp_no,
            "fp": fp_no,
            "fn": fn_no,
            "tn": tn_no,
            "precision_pct": no_precision,
            "recall_pct": no_recall,
        },
        "top_5_role_confusions": top_5_confusions,
        "disagreements": disagreements,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score LLM tagging benchmark against human labels."
    )
    parser.add_argument(
        "--labeled", default="eval/sample_50_labeled.xlsx", help="Path to labeled Excel file"
    )
    parser.add_argument("--sheet", default="Label", help="Sheet name in Excel file")
    parser.add_argument("--key", default="eval/sample_50_key.csv", help="Path to key CSV file")
    parser.add_argument("--bench-json", required=True, help="Path to model bench JSON results")
    parser.add_argument("--model-name", default=None, help="Model display name")
    parser.add_argument(
        "--output-dir", default="docs/results", help="Directory to save disagreement reports"
    )

    args = parser.parse_args()

    bench_path = Path(args.bench_json)
    if not bench_path.exists():
        logger.error("Bench JSON not found at %s", bench_path)
        sys.exit(1)

    with open(bench_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    model_name = args.model_name or bench_data.get("model", bench_path.stem.replace("bench_", ""))

    labels = read_xlsx_sheet(args.labeled, sheet_name=args.sheet)
    key_map = read_key_csv(args.key)

    metrics = evaluate_benchmark(labels, key_map, bench_data)

    clean_model_id = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", model_name)
    out_dir = Path(args.output_dir)

    csv_path = out_dir / f"disagreements_{clean_model_id}.csv"
    html_path = out_dir / f"disagreements_{clean_model_id}.html"

    write_disagreements_csv(csv_path, metrics["disagreements"])
    write_disagreements_html(html_path, metrics["disagreements"], model_name)

    tot = metrics["total_evaluated"]
    r_acc = metrics["role_accuracy_pct"]
    r_m = metrics["role_matches"]
    c_acc = metrics["city_accuracy_pct"]
    c_m = metrics["city_matches"]
    f_acc = metrics["fresher_agreement_pct"]
    f_m = metrics["fresher_matches"]
    f_tot = metrics["fresher_evaluated"]

    print("\n" + "=" * 60)
    print(f"BENCHMARK EVALUATION REPORT: {model_name}")
    print("=" * 60)
    print(f"Total Evaluated: {tot}")
    print(f"Role Accuracy:   {r_acc:.1f}% ({r_m}/{tot})")
    print(f"City Accuracy:   {c_acc:.1f}% ({c_m}/{tot})")
    print(f"Fresher Agree:   {f_acc:.1f}% ({f_m}/{f_tot}) [Yes/No rows only]")
    print(f"No-Class Prec:   {metrics['no_class_metrics']['precision_pct']:.1f}%")
    print(f"No-Class Recall: {metrics['no_class_metrics']['recall_pct']:.1f}%")
    print("\nTop 5 Role Confusion Pairs (Human -> Model):")
    for (h_role, m_role), count in metrics["top_5_role_confusions"]:
        print(f"  - {h_role} -> {m_role}: {count}")
    print(f"\nDisagreements:   {len(metrics['disagreements'])} rows")
    print(f"Saved CSV:       {csv_path}")
    print(f"Saved HTML:      {html_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
