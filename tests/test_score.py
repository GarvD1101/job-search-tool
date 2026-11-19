"""Unit tests for scripts/score.py using synthetic mock data."""

import csv
import zipfile
from pathlib import Path

from scripts.score import (
    evaluate_benchmark,
    normalize_token,
    read_key_csv,
    read_xlsx_sheet,
    write_disagreements_csv,
    write_disagreements_html,
)


def create_synthetic_xlsx(file_path: Path) -> None:
    """Build a synthetic workbook matching real-world structure.

    Order of sheets: Guide, Label, Lists.
    Uses shared strings, 50 rows in Label sheet, and a hyperlink element.
    """
    shared_strings = [
        "#",
        "Post",
        "Snippet",
        "Fresher job?",
        "Role",
        "City",
        "Link",
        "Python Dev Intern",
        "Internship writing python code",
        "Yes",
        "software_dev",
        "bengaluru",
        "https://example.com/job1",
        "Senior Project Lead",
        "Requires 10 years experience",
        "No",
        "product_management",
        "delhi_ncr",
        "https://example.com/job2",
        "Unclear Trainee",
        "Ambiguous post",
        "Unsure",
        "other",
        "remote",
        "https://example.com/job3",
    ]

    sst_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">\n'
    )
    for s in shared_strings:
        sst_xml += f"  <si><t>{s}</t></si>\n"
    sst_xml += "</sst>"

    types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
        '  <Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
        '  <Override PartName="/xl/worksheets/sheet2.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
        '  <Override PartName="/xl/worksheets/sheet3.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
        '  <Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>\n'
        "</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>\n'
        "</Relationships>"
    )

    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>\n'
        '  <Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet2.xml"/>\n'
        '  <Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet3.xml"/>\n'
        '  <Relationship Id="rId4" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>\n'
        "</Relationships>"
    )

    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
        "  <sheets>\n"
        '    <sheet name="Guide" sheetId="1" r:id="rId1"/>\n'
        '    <sheet name="Label" sheetId="2" r:id="rId2"/>\n'
        '    <sheet name="Lists" sheetId="3" r:id="rId3"/>\n'
        "  </sheets>\n"
        "</workbook>"
    )

    # Empty Guide and Lists sheets
    empty_sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n'
        "  <sheetData/>\n"
        "</worksheet>"
    )

    # Label sheet with row 1 header, 50 data rows, and a hyperlink
    label_sheet = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n',
        "  <sheetData>\n",
        '    <row r="1">\n',
        '      <c r="A1" t="s"><v>0</v></c>\n',
        '      <c r="B1" t="s"><v>1</v></c>\n',
        '      <c r="C1" t="s"><v>2</v></c>\n',
        '      <c r="D1" t="s"><v>3</v></c>\n',
        '      <c r="E1" t="s"><v>4</v></c>\n',
        '      <c r="F1" t="s"><v>5</v></c>\n',
        '      <c r="G1" t="s"><v>6</v></c>\n',
        "    </row>\n",
    ]

    for i in range(2, 52):
        row_num = i - 1
        # Alternate between 3 types of sample rows
        if row_num % 3 == 1:
            p_idx, sn_idx, f_idx, r_idx, c_idx, l_idx = 7, 8, 9, 10, 11, 12
        elif row_num % 3 == 2:
            p_idx, sn_idx, f_idx, r_idx, c_idx, l_idx = 13, 14, 15, 16, 17, 18
        else:
            p_idx, sn_idx, f_idx, r_idx, c_idx, l_idx = 19, 20, 21, 22, 23, 24

        label_sheet.append(
            f'    <row r="{i}">\n'
            f'      <c r="A{i}"><v>{row_num}</v></c>\n'
            f'      <c r="B{i}" t="s"><v>{p_idx}</v></c>\n'
            f'      <c r="C{i}" t="s"><v>{sn_idx}</v></c>\n'
            f'      <c r="D{i}" t="s"><v>{f_idx}</v></c>\n'
            f'      <c r="E{i}" t="s"><v>{r_idx}</v></c>\n'
            f'      <c r="F{i}" t="s"><v>{c_idx}</v></c>\n'
            f'      <c r="G{i}" t="s"><v>{l_idx}</v></c>\n'
            f"    </row>\n"
        )

    label_sheet.append("  </sheetData>\n")
    # Add hyperlink cell definition
    label_sheet.append(
        "  <hyperlinks>\n"
        '    <hyperlink ref="G2" r:id="rId1" display="https://example.com/job1"/>\n'
        "  </hyperlinks>\n"
    )
    label_sheet.append("</worksheet>")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(file_path, "w") as z:
        z.writestr("[Content_Types].xml", types_xml)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", wb_xml)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/sharedStrings.xml", sst_xml)
        z.writestr("xl/worksheets/sheet1.xml", empty_sheet)
        z.writestr("xl/worksheets/sheet2.xml", "".join(label_sheet))
        z.writestr("xl/worksheets/sheet3.xml", empty_sheet)


def test_synthetic_xlsx_parser(tmp_path: Path):
    xlsx_file = tmp_path / "synthetic_test.xlsx"
    create_synthetic_xlsx(xlsx_file)

    # Must find sheet2 by name 'Label' even though Guide is sheet1
    rows = read_xlsx_sheet(xlsx_file, sheet_name="Label")
    assert len(rows) == 50

    # Header check
    assert "#" in rows[0]
    assert "Post" in rows[0]
    assert "Fresher job?" in rows[0]
    assert "Role" in rows[0]
    assert "City" in rows[0]
    assert "Link" in rows[0]

    # Row 1 values
    assert rows[0]["#"] == "1"
    assert rows[0]["Post"] == "Python Dev Intern"
    assert rows[0]["Fresher job?"] == "Yes"
    assert rows[0]["Role"] == "software_dev"
    assert rows[0]["City"] == "bengaluru"


def test_exclude_role_rows_option(tmp_path: Path):
    xlsx_file = tmp_path / "synthetic_test.xlsx"
    create_synthetic_xlsx(xlsx_file)
    rows = read_xlsx_sheet(xlsx_file, sheet_name="Label")

    key_map = {str(i): f"job_{i}" for i in range(1, 51)}

    # Model results where row 36 has a role mismatch
    bench_results = []
    for i in range(1, 51):
        bench_results.append({
            "id": f"job_{i}",
            "index": i - 1,
            "title": f"Job {i}",
            "role": "qa_testing" if i == 36 else rows[i - 1]["Role"],
            "city": rows[i - 1]["City"],
            "is_fresher": (rows[i - 1]["Fresher job?"] == "Yes"),
        })

    bench_data = {"model": "mock-model", "results": bench_results}

    # 1. Without exclusion: row 36 causes 1 mismatch
    m_no_ex = evaluate_benchmark(rows, key_map, bench_data)
    assert m_no_ex["total_evaluated"] == 50
    assert m_no_ex["role_evaluated"] == 50
    assert m_no_ex["role_matches"] == 49
    assert m_no_ex["role_accuracy_pct"] == 98.0

    # 2. With exclusion: row 36 is excluded from role evaluation
    m_ex = evaluate_benchmark(rows, key_map, bench_data, exclude_role_rows={"36"})
    assert m_ex["total_evaluated"] == 50
    assert m_ex["role_evaluated"] == 49  # Drops row 36
    assert m_ex["role_matches"] == 49
    assert m_ex["role_accuracy_pct"] == 100.0  # 49/49 = 100%
    # City and Fresher still evaluated row 36
    assert m_ex["city_matches"] == 50
    assert "36" in m_ex["excluded_role_rows"]


def test_normalize_token():
    assert normalize_token("Software Dev") == "software_dev"
    assert normalize_token("  Delhi_NCR  ") == "delhi_ncr"
    assert normalize_token("Admin / Back Office") == "admin_back_office"


def test_read_key_csv(tmp_path: Path):
    key_file = tmp_path / "test_key.csv"
    key_file.write_text("#,id\n1,job_101\n2,job_102\n3,job_103\n", encoding="utf-8")

    mapping = read_key_csv(key_file)
    assert mapping == {"1": "job_101", "2": "job_102", "3": "job_103"}


def test_write_disagreements_outputs(tmp_path: Path):
    disagreements = [
        {
            "row #": "1",
            "title": "Test Title",
            "my role": "software_dev",
            "model role": "data_analytics",
            "my city": "pune",
            "model city": "mumbai",
            "my fresher label": "No",
            "model is_fresher": True,
        }
    ]

    csv_out = tmp_path / "disagreements.csv"
    html_out = tmp_path / "disagreements.html"

    write_disagreements_csv(csv_out, disagreements)
    write_disagreements_html(html_out, disagreements, "test-model")

    assert csv_out.exists()
    assert html_out.exists()

    with open(csv_out, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert reader[0] == [
            "row #",
            "title",
            "my role",
            "model role",
            "my city",
            "model city",
            "my fresher label",
            "model is_fresher",
        ]
        assert len(reader) == 2
