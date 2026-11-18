import json
from pathlib import Path
from typing import Any

import pytest

from pipeline.run import run_fetch_stage
from pipeline.sources.base import BaseSourceAdapter, RawPost
from pipeline.sources.greenhouse import GreenhouseAdapter, is_india_or_remote_open
from pipeline.sources.jooble import JoobleAdapter
from pipeline.sources.usage_counter import QuotaExceededError, UsageCounter


@pytest.fixture
def fixtures_data() -> dict[str, Any]:
    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "synthetic_fixtures.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_usage_counter_budget_enforcement(tmp_path: Path):
    counter_file = tmp_path / "test_usage.json"
    counter = UsageCounter(counter_file, use_db=False)

    # Initially allowed
    assert counter.can_request("jooble", mode="dev", mode_limit=2, total_limit=5)

    # Record 2 requests (reaching dev limit)
    counter.record_request("jooble", mode="dev", count=2, mode_limit=2, total_limit=5)
    assert not counter.can_request("jooble", mode="dev", mode_limit=2, total_limit=5)

    # Next attempt raises QuotaExceededError
    with pytest.raises(QuotaExceededError):
        counter.record_request("jooble", mode="dev", count=1, mode_limit=2, total_limit=5)


def test_jooble_redaction(tmp_path: Path):
    config = {
        "base_url": "https://in.jooble.org/api",
        "cache_dir": str(tmp_path / "cache"),
        "daily_budget_total": 100,
        "daily_budget_dev": 40,
        "daily_budget_cron": 60,
    }
    secret_key = "super_secret_test_key_123"
    adapter = JoobleAdapter(config=config, api_key=secret_key)

    msg = f"Request to https://in.jooble.org/api/{secret_key} failed"
    redacted = adapter._redact(msg)
    assert secret_key not in redacted
    assert "<REDACTED>" in redacted


def test_jooble_parse_fixtures(tmp_path: Path, fixtures_data: dict[str, Any]):
    config = {
        "base_url": "https://in.jooble.org/api",
        "cache_dir": str(tmp_path / "cache"),
    }
    adapter = JoobleAdapter(config=config, api_key="test_key")
    jooble_data = fixtures_data["jooble"]

    posts = adapter._parse_jobs(jooble_data)
    assert len(posts) == 2
    assert posts[0].source == "jooble"
    assert posts[0].source_id == "100001"
    assert posts[0].payload["title"] == "Software Engineer Trainee"
    assert posts[1].source_id == "100002"


def test_greenhouse_india_location_filter():
    # India locations
    assert is_india_or_remote_open("Bengaluru, India")
    assert is_india_or_remote_open("Pune, Maharashtra")
    assert is_india_or_remote_open("Remote, India")
    assert is_india_or_remote_open("Gurugram")
    assert is_india_or_remote_open("Remote", title="Software Engineer - India")

    # Non-India locations (remote without India mentioned must be rejected)
    assert not is_india_or_remote_open("Remote - Worldwide")
    assert not is_india_or_remote_open("Remote - US Only")
    assert not is_india_or_remote_open("San Francisco, CA")
    assert not is_india_or_remote_open("London, United Kingdom")
    assert not is_india_or_remote_open("Singapore")


def test_greenhouse_fetch_company_from_cache(
    tmp_path: Path, fixtures_data: dict[str, Any]
):
    cache_dir = tmp_path / "greenhouse_cache"
    cache_dir.mkdir(parents=True)

    company_token = "acme"
    cache_file = cache_dir / f"{company_token}.json"
    cache_file.write_text(
        json.dumps(fixtures_data["greenhouse"]), encoding="utf-8"
    )

    config = {
        "base_url": "https://boards-api.greenhouse.io/v1/boards",
        "cache_dir": str(cache_dir),
        "companies": [company_token],
    }
    adapter = GreenhouseAdapter(config=config)
    posts = adapter.fetch_company(company_token, use_cache=True)

    # Out of 2 synthetic jobs (one in Bengaluru, one in SF), only India job must be kept
    assert len(posts) == 1
    assert posts[0].source == "greenhouse"
    assert posts[0].source_id == f"{company_token}_200001"
    assert "Bengaluru" in posts[0].payload["location"]["name"]


class FakeFailingAdapter(BaseSourceAdapter):

    @property
    def name(self) -> str:
        return "fake_failing"

    def fetch(
        self, mode: str = "dev", use_cache: bool = True
    ) -> tuple[list[RawPost], dict[str, int]]:
        raise ConnectionError("Simulated upstream network timeout")


class FakeWorkingAdapter(BaseSourceAdapter):

    @property
    def name(self) -> str:
        return "fake_working"

    def fetch(
        self, mode: str = "dev", use_cache: bool = True
    ) -> tuple[list[RawPost], dict[str, int]]:
        post = RawPost(
            source="fake_working",
            source_id="job_999",
            payload={"title": "Data Intern"},
        )
        return [post], {"board_1": 1}


def test_partial_failure_handling(monkeypatch: pytest.MonkeyPatch):
    # Prevent real database writes during unit test
    monkeypatch.setattr("pipeline.run.save_raw_posts", lambda posts: len(posts))
    monkeypatch.setattr("pipeline.run.start_pipeline_run", lambda trigger: None)
    monkeypatch.setattr(
        "pipeline.run.finish_pipeline_run", lambda run_id, status, stats: None
    )

    adapters = [FakeWorkingAdapter(), FakeFailingAdapter()]
    _, status, stats = run_fetch_stage(
        adapters=adapters, mode="dev", use_cache=True
    )

    assert status == "partial"
    assert stats["source_counts"]["fake_working"] == 1
    assert stats["source_counts"]["fake_failing"] == 0
    assert "fake_failing" in stats["errors"]


def test_jooble_cache_miss_returns_empty_and_does_not_use_sample(tmp_path: Path):
    cache_dir = tmp_path / "jooble_cache"
    cache_dir.mkdir(parents=True)
    config = {
        "base_url": "https://in.jooble.org/api",
        "cache_dir": str(cache_dir),
        "daily_budget_total": 100,
        "daily_budget_dev": 40,
        "daily_budget_cron": 60,
    }
    adapter = JoobleAdapter(config=config, api_key="dummy_key")

    # In use_cache=True mode, missing cache file must return 0 posts and "miss"
    posts, status = adapter.fetch_query(
        keywords="fresher", location="Pune", page=1, mode="dev", use_cache=True
    )
    assert len(posts) == 0
    assert status == "miss"


def test_greenhouse_cache_miss_returns_empty(tmp_path: Path):
    cache_dir = tmp_path / "gh_cache"
    cache_dir.mkdir(parents=True)
    config = {
        "base_url": "https://boards-api.greenhouse.io/v1/boards",
        "cache_dir": str(cache_dir),
        "companies": ["nonexistent_company"],
    }
    adapter = GreenhouseAdapter(config=config)

    posts, status, tb, ta = adapter.fetch_company_details(
        "nonexistent_company", use_cache=True
    )
    assert len(posts) == 0
    assert status == "miss"
    assert tb == 0
    assert ta == 0


def test_usage_counter_not_incremented_on_cache_hit(tmp_path: Path):
    counter_file = tmp_path / "usage.json"
    counter = UsageCounter(counter_file=counter_file, use_db=False)
    cache_dir = tmp_path / "jooble_cache"
    cache_dir.mkdir(parents=True)

    config = {
        "base_url": "https://in.jooble.org/api",
        "cache_dir": str(cache_dir),
        "daily_budget_total": 100,
        "daily_budget_dev": 40,
        "daily_budget_cron": 60,
    }
    adapter = JoobleAdapter(
        config=config, usage_counter=counter, api_key="dummy_key"
    )

    # Pre-populate a query cache file
    cache_file = adapter._get_cache_path("fresher", "Pune", 1)
    cache_file.write_text(
        json.dumps({"jobs": [{"id": "999", "title": "Test Fresher"}]}),
        encoding="utf-8",
    )

    # Fetch with read-through cache
    posts, status = adapter.fetch_query(
        keywords="fresher",
        location="Pune",
        page=1,
        mode="dev",
        cache_mode="read-through",
    )
    assert status == "hit"
    assert len(posts) == 1
    # Quota must be untouched (0 recorded requests)
    assert counter.get_count("jooble", mode="dev") == 0
    assert counter.get_count("jooble") == 0
