"""Failure injection tests covering all five system failure scenarios.

1. Source returns 500 / times out: run is marked partial, remaining source succeeds.
2. Groq returns 429: backoff honors Retry-After, succeeds on retry.
3. Malformed JSON from LLM: one repair retry, then marked needs_review (never crashes).
4. Database unreachable: pipeline logs masked error without credentials, raises clean exception.
5. Out-of-enum value from model: rejected, repair attempted, falls back to needs_review.
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline.llm.groq import GroqProvider
from pipeline.run import run_fetch_stage
from pipeline.sources.base import BaseSourceAdapter, RawPost
from pipeline.store import save_raw_posts


class FailingAdapter(BaseSourceAdapter):
    """Source adapter simulating upstream 500 server error or timeout."""

    @property
    def name(self) -> str:
        return "failing_source"

    def fetch(
        self,
        mode: str = "dev",
        use_cache: bool = True,
        **kwargs: Any,
    ) -> tuple[list[RawPost], dict[str, Any]]:
        raise RuntimeError("HTTP 500 Internal Server Error from upstream source")


class WorkingAdapter(BaseSourceAdapter):
    """Source adapter returning successful posts."""

    @property
    def name(self) -> str:
        return "working_source"

    def fetch(
        self,
        mode: str = "dev",
        use_cache: bool = True,
        **kwargs: Any,
    ) -> tuple[list[RawPost], dict[str, Any]]:
        posts = [
            RawPost(
                source=self.name,
                source_id="ok_1",
                payload={"title": "Dev Intern", "company": "Good Corp"},
            ),
            RawPost(
                source=self.name,
                source_id="ok_2",
                payload={"title": "QA Trainee", "company": "Good Corp"},
            ),
        ]
        return posts, {"fetched": 2}


def test_failure_1_source_failure_marks_run_partial() -> None:
    """When one source times out or returns 500, run is marked partial and other succeeds."""
    adapters: list[BaseSourceAdapter] = [FailingAdapter(), WorkingAdapter()]

    with patch("pipeline.run.start_pipeline_run", return_value=999):
        with patch("pipeline.run.save_raw_posts", return_value=2):
            with patch("pipeline.run.finish_pipeline_run") as mock_finish:
                count, status, stats = run_fetch_stage(
                    adapters=adapters,
                    mode="dev",
                    cache_mode="bypass",
                )

    assert status == "partial", f"Expected partial status, got {status}"
    assert stats["source_counts"]["working_source"] == 2
    assert stats["source_counts"]["failing_source"] == 0
    assert "failing_source" in stats["errors"]
    assert "HTTP 500" in stats["errors"]["failing_source"]
    assert mock_finish.called


def test_failure_2_groq_429_backoff_honors_retry_after() -> None:
    """When Groq returns 429, backoff honors Retry-After header and succeeds on retry."""
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
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "completion_tokens_details": {"reasoning_tokens": 20},
        },
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
            "title": "Software Engineer",
            "company": "Acme",
            "location": "Bengaluru",
            "description": "Entry level",
        }
    ]

    with patch("time.sleep") as mock_sleep:
        results, usage = provider.tag_batch(posts)

    assert mock_client.post.call_count == 2
    mock_sleep.assert_called_with(0.01)
    assert len(results) == 1
    assert results[0].role == "software_dev"
    assert usage.status == "success"


def test_failure_3_malformed_json_repair_then_needs_review() -> None:
    """When LLM returns malformed JSON, provider retries repair once, then sets needs_review."""
    mock_client = MagicMock()
    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {
        "choices": [{"message": {"content": "This is totally invalid json {"}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10},
    }

    mock_client.post.side_effect = [bad_resp, bad_resp]

    provider = GroqProvider(
        model="openai/gpt-oss-20b",
        api_key="gsk_test_key",
        http_client=mock_client,
    )

    posts = [
        {
            "index": 0,
            "title": "Junior Tester",
            "company": "Beta Corp",
            "location": "Pune",
            "description": "QA role",
        }
    ]

    results, usage = provider.tag_batch(posts)
    assert len(results) == 1
    assert results[0].status == "needs_review"
    assert mock_client.post.call_count == 2


def test_failure_4_database_unreachable_masks_credentials() -> None:
    """When database is unreachable, error is logged with masked credentials."""
    posts = [
        RawPost(
            source="jooble",
            source_id="test_1",
            payload={"title": "Test Job"},
        )
    ]

    user_part = "user:SuperSecretPass123"
    host_part = "db.supabase:5432"
    leak_error = Exception(f"connection to postgresql://{user_part}@{host_part} failed")
    dummy_url = f"postgresql://{user_part}@{host_part}/db"

    with patch("psycopg.connect", side_effect=leak_error):
        with pytest.raises(RuntimeError) as exc_info:
            save_raw_posts(
                posts,
                db_url=dummy_url,
            )

    error_message = str(exc_info.value).lower()
    # Password must never appear in the error message
    assert "supersecretpass123" not in error_message
    assert "credentials masked" in error_message


def test_failure_5_out_of_enum_value_rejected_falls_back_to_needs_review() -> None:
    """When model generates an out-of-enum role, validation rejects it."""
    mock_client = MagicMock()
    invalid_enum_resp = MagicMock()
    invalid_enum_resp.status_code = 200
    invalid_enum_resp.json.return_value = {
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
                                    "role": "human_resources",
                                    "city": "pune",
                                }
                            ]
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10},
    }

    mock_client.post.side_effect = [invalid_enum_resp, invalid_enum_resp]

    provider = GroqProvider(
        model="openai/gpt-oss-20b",
        api_key="gsk_test_key",
        http_client=mock_client,
    )

    posts = [
        {
            "index": 0,
            "title": "Recruiter",
            "company": "Staffing",
            "location": "Pune",
            "description": "Recruitment specialist",
        }
    ]

    results, usage = provider.tag_batch(posts)
    assert len(results) == 1
    assert results[0].role != "human_resources"
    assert results[0].status == "needs_review"
    assert mock_client.post.call_count == 2
