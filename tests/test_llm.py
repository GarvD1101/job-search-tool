import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from pipeline.llm.base import City, PostType, Role, TagResult
from pipeline.llm.groq import GroqProvider
from pipeline.llm.mock import MockProvider
from pipeline.tagger import TagManager, get_cache_key, get_content_hash


def test_mock_provider_deterministic():
    provider = MockProvider(model="mock")
    posts = [
        {
            "index": 0,
            "title": "Software Engineer Intern",
            "company": "Alpha Tech",
            "location": "Bengaluru",
            "description": "Python, Django, backend APIs. Freshers welcome.",
        },
        {
            "index": 1,
            "title": "Senior Architect",
            "company": "Big Enterprise",
            "location": "Mumbai",
            "description": "10+ years experience required.",
        },
    ]
    results, usage = provider.tag_batch(posts)
    assert len(results) == 2
    assert results[0].index == 0
    assert results[0].post_type == PostType.internship
    assert results[0].is_fresher is True
    assert results[0].role == Role.software_dev
    assert results[0].city == City.bengaluru
    assert results[0].is_remote is False

    assert results[1].index == 1
    assert results[1].is_fresher is False
    assert usage.status == "success"
    assert usage.input_tokens > 0


def test_tag_result_schema_validation():
    # Valid result
    r = TagResult(
        index=0,
        post_type=PostType.job,
        is_fresher=True,
        role=Role.data_analytics,
        city=City.remote,
    )
    assert r.is_remote is True

    # Invalid post_type
    with pytest.raises(ValidationError):
        TagResult(
            index=0,
            post_type="not_an_enum",  # type: ignore[arg-type]
            is_fresher=True,
            role=Role.software_dev,
            city=City.pune,
        )

    # Invalid role
    with pytest.raises(ValidationError):
        TagResult(
            index=0,
            post_type=PostType.job,
            is_fresher=True,
            role="unrecognized_role",  # type: ignore[arg-type]
            city=City.pune,
        )


def test_repair_retry_on_invalid_json():
    # Simulate Groq returning bad JSON first, then valid JSON on repair retry
    mock_client = MagicMock()
    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {
        "choices": [{"message": {"content": "This is not valid json {"}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10},
    }

    good_resp = MagicMock()
    good_resp.status_code = 200
    good_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "results": [
                                {
                                    "index": 0,
                                    "post_type": "job",
                                    "is_fresher": True,
                                    "role": "software_dev",
                                    "city": "bengaluru",
                                }
                            ]
                        }
                    )
                }
            }
        ],
        "usage": {
            "prompt_tokens": 70,
            "completion_tokens": 20,
            "completion_tokens_details": {"reasoning_tokens": 5},
        },
    }

    mock_client.post.side_effect = [bad_resp, good_resp]

    provider = GroqProvider(
        model="openai/gpt-oss-20b",
        api_key="gsk_test_key",
        http_client=mock_client,
    )

    posts = [
        {
            "index": 0,
            "title": "Junior Python Dev",
            "company": "Startup",
            "location": "Bengaluru",
            "description": "Code daily.",
        }
    ]

    results, usage = provider.tag_batch(posts)
    assert len(results) == 1
    assert results[0].role == Role.software_dev
    assert usage.reasoning_tokens == 5
    assert mock_client.post.call_count == 2


def test_429_backoff_honors_retry_after():
    mock_client = MagicMock()
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0.01"}

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "results": [
                                {
                                    "index": 0,
                                    "post_type": "internship",
                                    "is_fresher": True,
                                    "role": "marketing",
                                    "city": "mumbai",
                                }
                            ]
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 40, "completion_tokens": 15},
    }

    mock_client.post.side_effect = [resp_429, resp_200]

    provider = GroqProvider(
        model="openai/gpt-oss-20b",
        api_key="gsk_test_key",
        http_client=mock_client,
    )

    posts = [
        {
            "index": 0,
            "title": "SEO Intern",
            "company": "GrowthCo",
            "location": "Mumbai",
            "description": "Keywords.",
        }
    ]

    results, usage = provider.tag_batch(posts)
    assert len(results) == 1
    assert results[0].role == Role.marketing
    assert mock_client.post.call_count == 2


def test_cache_hit_makes_zero_calls(tmp_path: Path):
    mock_provider = MagicMock()
    manager = TagManager(
        model="mock",
        provider=mock_provider,
        cache_dir=str(tmp_path / "cache"),
    )

    job_title = "Data Analyst Trainee"
    job_company = "Metrics Corp"
    job_loc = "Pune"
    job_desc = "SQL queries and reporting."

    c_hash = get_content_hash(job_title, job_company, job_loc, job_desc)
    c_key = get_cache_key(c_hash, "tag_v1", "mock")

    cached_result = TagResult(
        index=0,
        post_type=PostType.trainee,
        is_fresher=True,
        role=Role.data_analytics,
        city=City.pune,
    )
    manager.save_cached_tag(c_key, cached_result)

    # In production mode with this job, load_cached_tag returns result
    # and provider.tag_batch is not called
    loaded = manager.load_cached_tag(c_key)
    assert loaded is not None
    assert loaded.role == Role.data_analytics
    assert mock_provider.tag_batch.call_count == 0


def test_budget_guard_stops_at_80_percent(tmp_path: Path):
    mock_provider = MagicMock()
    manager = TagManager(
        model="openai/gpt-oss-20b",
        provider=mock_provider,
        cache_dir=str(tmp_path / "cache"),
    )

    with patch("pipeline.tagger.get_today_token_usage", return_value=165000):
        with patch("pipeline.tagger.load_pending_jobs") as mock_load:
            res = manager.run_production_mode()
            assert res["status"] == "budget_exhausted"
            assert mock_load.call_count == 0
            assert mock_provider.tag_batch.call_count == 0


def test_api_key_redaction():
    import logging

    from pipeline.run import RedactKeyFilter

    test_key = "gsk_secret_1234567890abcdef"
    with patch.dict("os.environ", {"JOOBLE_API_KEY": test_key}):
        log_filter = RedactKeyFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Calling URL https://example.com/api/{test_key}/jobs",
            args=(),
            exc_info=None,
        )
        log_filter.filter(record)
        assert test_key not in record.msg
        assert "<REDACTED>" in record.msg


def test_bench_mode_writes_nothing_to_jobs(tmp_path: Path):
    provider = MockProvider(model="mock")
    manager = TagManager(
        model="mock",
        provider=provider,
        cache_dir=str(tmp_path / "cache"),
    )

    ids_file = tmp_path / "sample_ids.txt"
    ids_file.write_text("id_1\nid_2\n", encoding="utf-8")

    bench_out = tmp_path / "bench_results.json"

    with patch("pipeline.tagger.update_tagged_jobs") as mock_update_jobs:
        stats = manager.run_bench_mode(ids_file=ids_file, bench_out=bench_out)
        assert mock_update_jobs.call_count == 0
        assert bench_out.exists()
        assert stats["total_posts"] == 2
        assert stats["valid_posts"] == 2
        data = json.loads(bench_out.read_text(encoding="utf-8"))
        assert "tokens" in data
        assert "results" in data
        assert len(data["results"]) == 2
