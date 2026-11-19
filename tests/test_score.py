"""Unit tests for scripts/score.py using synthetic mock data."""

import csv
from pathlib import Path

from scripts.score import (
    evaluate_benchmark,
    normalize_token,
    read_key_csv,
    write_disagreements_csv,
    write_disagreements_html,
)


def test_normalize_token():
    assert normalize_token("Software Dev") == "software_dev"
    assert normalize_token("  Delhi_NCR  ") == "delhi_ncr"
    assert normalize_token("Admin / Back Office") == "admin_back_office"


def test_read_key_csv(tmp_path: Path):
    key_file = tmp_path / "test_key.csv"
    key_file.write_text("#,id\n1,job_101\n2,job_102\n3,job_103\n", encoding="utf-8")

    mapping = read_key_csv(key_file)
    assert mapping == {"1": "job_101", "2": "job_102", "3": "job_103"}


def test_evaluate_benchmark_synthetic():
    labels = [
        {
            "#": "1",
            "Post": "Python Dev",
            "Role": "software_dev",
            "City": "bengaluru",
            "Fresher job?": "Yes",
        },
        {
            "#": "2",
            "Post": "Data Analyst",
            "Role": "data_analytics",
            "City": "pune",
            "Fresher job?": "No",
        },
        {
            "#": "3",
            "Post": "HR Intern",
            "Role": "human_resources",
            "City": "mumbai",
            "Fresher job?": "Unsure",
        },
        {
            "#": "4",
            "Post": "Senior Manager",
            "Role": "product_management",
            "City": "hyderabad",
            "Fresher job?": "No",
        },
    ]

    key_map = {
        "1": "id_1",
        "2": "id_2",
        "3": "id_3",
        "4": "id_4",
    }

    bench_data = {
        "model": "test-model",
        "results": [
            {
                "id": "id_1",
                "title": "Python Dev",
                "role": "software_dev",
                "city": "bengaluru",
                "is_fresher": True,
            },
            {
                "id": "id_2",
                "title": "Data Analyst",
                "role": "data_analytics",
                "city": "mumbai",  # city mismatch
                "is_fresher": False,  # matches
            },
            {
                "id": "id_3",
                "title": "HR Intern",
                "role": "admin_back_office",  # role mismatch
                "city": "mumbai",
                "is_fresher": True,  # Unsure excluded from fresher metrics
            },
            {
                "id": "id_4",
                "title": "Senior Manager",
                "role": "product_management",
                "city": "hyderabad",
                "is_fresher": True,  # fresher mismatch: human No, model True (FN for No class)
            },
        ],
    }

    metrics = evaluate_benchmark(labels, key_map, bench_data)

    assert metrics["total_evaluated"] == 4
    # Role: id_1 (match), id_2 (match), id_3 (mismatch), id_4 (match) -> 3/4 = 75%
    assert metrics["role_matches"] == 3
    assert metrics["role_accuracy_pct"] == 75.0

    # City: id_1 (match), id_2 (mismatch), id_3 (match), id_4 (match) -> 3/4 = 75%
    assert metrics["city_matches"] == 3
    assert metrics["city_accuracy_pct"] == 75.0

    # Fresher evaluated: id_1 (Yes), id_2 (No), id_4 (No) -> 3 (id_3 is Unsure, excluded)
    assert metrics["fresher_evaluated"] == 3
    # Matches: id_1 (Yes/True), id_2 (No/False) -> 2/3 = 66.67%
    assert metrics["fresher_matches"] == 2
    assert round(metrics["fresher_agreement_pct"], 1) == 66.7

    # No class metrics:
    # TP: id_2 (human No, model False) -> 1
    # FP: 0
    # FN: id_4 (human No, model True) -> 1
    # Precision: 1 / (1 + 0) = 100%
    # Recall: 1 / (1 + 1) = 50%
    assert metrics["no_class_metrics"]["tp"] == 1
    assert metrics["no_class_metrics"]["fn"] == 1
    assert metrics["no_class_metrics"]["precision_pct"] == 100.0
    assert metrics["no_class_metrics"]["recall_pct"] == 50.0

    # Disagreements:
    # id_2: city mismatch
    # id_3: role mismatch
    # id_4: fresher mismatch
    assert len(metrics["disagreements"]) == 3


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

    html_content = html_out.read_text(encoding="utf-8")
    assert "Disagreements Report: test-model" in html_content
    assert "class=\"diff\"" in html_content
