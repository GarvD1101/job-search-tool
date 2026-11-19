from datetime import datetime, timezone

import pytest

from pipeline.dedup import (
    Deduplicator,
    normalize_url,
    shingle_jaccard,
)
from pipeline.filters import FilterRuleEngine, load_filters_config
from pipeline.normalize import NormalizedJob, clean_text


@pytest.fixture
def filter_engine() -> FilterRuleEngine:
    return FilterRuleEngine()


def make_job(
    title: str,
    company: str = "Acme Corp",
    location: str = "Bengaluru, India",
    description: str = "",
    url: str = "https://example.com/job/1",
    source: str = "jooble",
    source_id: str = "job_1",
    posted_at: datetime | None = None,
) -> NormalizedJob:
    return NormalizedJob(
        source=source,
        source_id=source_id,
        origin_site=source,
        title=title,
        company=company,
        location_text=location,
        description=description,
        url=url,
        posted_at=posted_at or datetime.now(timezone.utc),
    )


# -------------------------------------------------------------
# 20 TRICKY FIXTURES FROM PLAN.md SECTION 3
# -------------------------------------------------------------

def test_fixture_01_software_engineer_intern(filter_engine: FilterRuleEngine):
    job = make_job(title="Software Engineer Intern")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_02_graduate_engineer_trainee(filter_engine: FilterRuleEngine):
    job = make_job(title="Graduate Engineer Trainee")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_03_management_trainee(filter_engine: FilterRuleEngine):
    job = make_job(title="Management Trainee")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_04_senior_backend_engineer_5plus_years(filter_engine: FilterRuleEngine):
    job = make_job(title="Senior Backend Engineer, 5+ years")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason in ("seniority", "experience_required")


def test_fixture_05_sde_1_0_to_2_years(filter_engine: FilterRuleEngine):
    job = make_job(title="SDE-1 (0-2 years)")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_06_data_analyst_2_to_4_years(filter_engine: FilterRuleEngine):
    job = make_job(title="Data Analyst, 2-4 years")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason == "experience_required"


def test_fixture_07_associate_1_to_3_years(filter_engine: FilterRuleEngine):
    job = make_job(title="Associate, 1-3 years")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "ambiguous"


def test_fixture_08_product_fellowship_with_fee(filter_engine: FilterRuleEngine):
    job = make_job(
        title="12-week Product Fellowship",
        description="cohort starts Dec, fee Rs 15,000",
    )
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason in ("pay_to_join", "not_a_job_post")


def test_fixture_09_product_fellowship_with_stipend(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Product Fellowship at StartupX",
        description="full-time, monthly stipend 40,000",
    )
    dec, reason = filter_engine.evaluate(job)
    assert dec == "ambiguous"
    assert reason == "fellowship_with_stipend"


def test_fixture_10_free_python_workshop(filter_engine: FilterRuleEngine):
    job = make_job(title="Free Python workshop this Sunday")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason == "not_a_job_post"


def test_fixture_11_hiring_2026_batch_passouts(filter_engine: FilterRuleEngine):
    job = make_job(title="Hiring 2026 batch pass-outs")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_12_placement_guaranteed_course(filter_engine: FilterRuleEngine):
    job = make_job(title="Placement guaranteed data science course")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason in ("pay_to_join", "not_a_job_post")


def test_fixture_13_internship_with_registration_fee(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Internship",
        description="registration fee Rs 999",
    )
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason == "pay_to_join"


def test_fixture_14_internal_audit_manager_word_boundary(filter_engine: FilterRuleEngine):
    # 'internal' must not match 'intern'; 'manager' triggers seniority
    job = make_job(title="Internal Audit Manager")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason == "seniority"


def test_fixture_15_lead_generation_intern_override(filter_engine: FilterRuleEngine):
    # 'intern' overrides 'lead'
    job = make_job(title="Lead Generation Intern")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_16_apprentice_technician(filter_engine: FilterRuleEngine):
    job = make_job(title="Apprentice Technician")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    assert reason == "fresher_signal_matched"


def test_fixture_17_dedup_cross_source_consolidation():
    dedup = Deduplicator()
    # Job from Jooble
    j1 = make_job(
        title="Software Engineer Trainee",
        company="Infosys Limited",
        location="Bengaluru, Karnataka",
        description="Great fresher opportunity with 3 months training in python.",
        source="jooble",
        source_id="jb_101",
    )
    # Job from Greenhouse with slight company/title variation
    j2 = make_job(
        title="Software Engineer Trainee (Fresher)",
        company="Infosys",
        location="Bengaluru",
        description="Great fresher opportunity with 3 months training in python and java.",
        source="greenhouse",
        source_id="gh_202",
    )

    items = [(j1, "accept", "fresher_signal_matched"), (j2, "accept", "fresher_signal_matched")]
    processed, stats = dedup.deduplicate(items)

    survivors = [p for p in processed if p.status == "pending_tag"]
    duplicates = [p for p in processed if p.status == "duplicate"]

    assert len(survivors) == 1
    assert len(duplicates) == 1
    # Check that both sources are recorded on the surviving master
    assert "jooble" in survivors[0].sources
    assert "greenhouse" in survivors[0].sources
    assert stats["cross_source_duplicates"] >= 1


def test_fixture_18_singapore_location_rejected(filter_engine: FilterRuleEngine):
    job = make_job(title="Software Engineer Intern", location="Singapore")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason == "not_india"


def test_fixture_19_remote_open_to_india_accepted(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Software Engineer Intern",
        location="Remote",
        description="Role is remote and open to candidates in India.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"


def test_fixture_20_email_and_phone_sanitized():
    raw_text = "Apply now at jobs@example.com or call +91-9876543210 for details."
    cleaned = clean_text(raw_text)
    assert "jobs@example.com" not in cleaned
    assert "+91-9876543210" not in cleaned
    assert "9876543210" not in cleaned
    assert "Apply now at or call for details." == cleaned


# -------------------------------------------------------------
# DEDUPLICATION & CONFIG TESTS
# -------------------------------------------------------------

def test_filters_config_loader():
    cfg = load_filters_config("config/filters.yaml")
    assert cfg["recency"]["max_age_days"] == 45
    assert "singapore" in cfg["location"]["known_non_india"]
    assert "fresher" in cfg["positive_signals"]["title_keywords"]


def test_shingle_jaccard_similarity():
    t1 = "software engineer trainee python django sql"
    t2 = "software engineer trainee python django postgres"
    sim = shingle_jaccard(t1, t2)
    assert 0.5 <= sim <= 1.0

    t3 = "unrelated marketing sales lead manager"
    assert shingle_jaccard(t1, t3) == 0.0


def test_url_normalization_strips_tracking():
    raw_url = "https://jobs.example.com/view/123?utm_source=linkedin&utm_medium=cpc&ref=aggregator"
    norm = normalize_url(raw_url)
    assert "utm_source" not in norm
    assert "ref" not in norm
    assert norm == "https://jobs.example.com/view/123"


def test_dedup_and_filter_idempotency():
    dedup = Deduplicator()
    engine = FilterRuleEngine()

    jobs = [
        make_job("SDE-1 (0-2 years)", company="TechCorp", source_id="j1"),
        make_job("SDE-1 (0-2 years)", company="TechCorp", source_id="j2"),
        make_job("Senior Architect", company="BigCo", source_id="j3"),
        make_job("Data Analyst Trainee", company="Alpha Analytics", source_id="j4"),
    ]

    def run_pipeline_eval(job_list):
        survivors = []
        rejects = []
        for j in job_list:
            dec, reason = engine.evaluate(j)
            if dec in ("accept", "ambiguous"):
                survivors.append((j, dec, reason))
            else:
                rejects.append((j, dec, reason))
        processed, stats = dedup.deduplicate(survivors)
        return processed, rejects, stats

    p1, r1, s1 = run_pipeline_eval(jobs)
    p2, r2, s2 = run_pipeline_eval(jobs)

    # Identical counts
    assert s1 == s2
    assert len(p1) == len(p2)
    assert len(r1) == len(r2)

    # Identical canonical keys and statuses
    keys1 = [(p.canonical_key, p.status, p.duplicate_of) for p in p1]
    keys2 = [(p.canonical_key, p.status, p.duplicate_of) for p in p2]
    assert keys1 == keys2


# -------------------------------------------------------------
# PHASE 2 FIXES FIXTURES & TESTS
# -------------------------------------------------------------

def test_accept_path_generic_desc_words_become_ambiguous(filter_engine: FilterRuleEngine):
    # Description has generic 'fresher' or 'graduate', but title has no entry signal
    job = make_job(
        title="Python Developer",
        description="We are seeking talented freshers and graduates for our expanding team.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert dec == "ambiguous"
    assert reason == "unclear_fresher_fit"


def test_accept_path_title_signal_accepts(filter_engine: FilterRuleEngine):
    job = make_job(title="Software Engineer Intern")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    sig = filter_engine.get_accept_signal(job)
    assert sig is not None
    assert sig[0] == "intern"


def test_accept_path_jooble_type_internship_accepts(filter_engine: FilterRuleEngine):
    job = make_job(title="Backend Engineer")
    job.job_type = "Internship"
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    sig = filter_engine.get_accept_signal(job)
    assert sig is not None
    assert sig[1] == "type: Internship"


def test_accept_path_explicit_experience_pattern_accepts(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Web Developer",
        description="Candidate must have 0-1 yrs experience in HTML and CSS.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert dec == "accept"
    sig = filter_engine.get_accept_signal(job)
    assert sig is not None
    assert "0-1" in sig[0]


def test_not_a_job_post_exempt_article_trainee(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Article Trainee",
        company="Rahul Agarwal Chartered Accountants",
        description="Hiring article trainee pursuing CA course for audit assignments.",
    )
    dec, reason = filter_engine.evaluate(job)
    # Article trainee is an ICAI trainee role; title has 'trainee', must accept
    assert dec == "accept"
    assert reason != "not_a_job_post"


def test_not_a_job_post_exempt_admission_counsellor(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Admission Counsellor",
        company="Global Business School",
        description="Handling student queries and campus admissions.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert reason != "not_a_job_post"


def test_not_a_job_post_exempt_associate_customer_success(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Associate Customer Success Manager",
        company="SaaS Corp",
        description="Drive user retention, perform cohort analysis, and support clients.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert reason != "not_a_job_post"


def test_not_a_job_post_exempt_junior_associate_ar(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Junior Associate AR",
        company="Healthcare BPO",
        description="Accounts receivable processing and patient hospital admission billing.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert reason != "not_a_job_post"


def test_not_a_job_post_exempt_marine_engineer(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Marine Engineer",
        company="Maritime Shipping",
        description="Vessel maintenance after completing pre-sea training course.",
    )
    dec, reason = filter_engine.evaluate(job)
    assert reason != "not_a_job_post"


def test_seniority_lead_generation_exempted(filter_engine: FilterRuleEngine):
    job = make_job(title="Lead Generation Specialist")
    dec, reason = filter_engine.evaluate(job)
    # Should not be rejected as seniority
    assert reason != "seniority"


def test_seniority_team_lead_rejected(filter_engine: FilterRuleEngine):
    job = make_job(title="Process Team Lead")
    dec, reason = filter_engine.evaluate(job)
    assert dec == "reject"
    assert reason == "seniority"


def test_pay_to_join_anti_fraud_disclaimer_exempted(filter_engine: FilterRuleEngine):
    job = make_job(
        title="Customer Support Associate",
        description=(
            "Note: Our company and vendors will never charge a candidate a registration fee."
        ),
    )
    dec, reason = filter_engine.evaluate(job)
    assert reason != "pay_to_join"


def test_save_jobs_preserves_already_tagged_job():
    from unittest.mock import MagicMock, patch

    from pipeline.dedup import ProcessedJob
    from pipeline.store import save_jobs

    job = make_job(title="Software Engineer Intern", company="Acme")
    pj = ProcessedJob(
        job=job,
        rule_decision="accept",
        rule_reason="fresher_signal_matched",
        canonical_key="test_canonical_key_123",
        status="pending_tag",
        sources=["jooble"],
        duplicate_of=None,
        city_or_remote="bengaluru",
    )

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn

    with patch("psycopg.connect", return_value=mock_conn):
        count = save_jobs([pj], db_url="postgresql://localhost:5432/testdb")
        assert count == 1
        executed_sql = mock_cursor.executemany.call_args[0][0]
        # Verify that already tagged jobs are preserved and status is not blindly overwritten
        assert "WHEN jobs.tag_source = 'llm'" in executed_sql
        assert "WHEN jobs.status IN ('active', 'expired', 'needs_review')" in executed_sql
        # Verify tagged fields (role, city, post_type, tag_source) are not overwritten
        assert "role = EXCLUDED.role" not in executed_sql
        assert "city = EXCLUDED.city" not in executed_sql
        assert "post_type = EXCLUDED.post_type" not in executed_sql


def test_html_cleaning_double_encoded_entities():
    raw_html = (
        "&amp;lt;h3&amp;gt;Company Info&amp;lt;/h3&amp;gt;"
        "&lt;p&gt;Some description &amp;amp; details.&lt;/p&gt;"
    )
    cleaned = clean_text(raw_html)
    assert "<h3>" not in cleaned
    assert "&lt;" not in cleaned
    assert "<p>" not in cleaned
    assert "Company Info Some description & details." == cleaned
