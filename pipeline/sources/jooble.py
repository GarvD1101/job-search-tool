import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pipeline.sources.base import BaseSourceAdapter, RawPost
from pipeline.sources.usage_counter import QuotaExceededError, UsageCounter

logger = logging.getLogger(__name__)


def _get_api_key() -> str | None:
    return os.environ.get("JOOBLE_API_KEY")


class JoobleAdapter(BaseSourceAdapter):
    """Adapter for Jooble Partner REST API."""

    def __init__(
        self,
        config: dict[str, Any],
        usage_counter: UsageCounter | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = config
        self.base_url = config.get("base_url", "https://in.jooble.org/api").rstrip("/")
        self.daily_budget_total = int(config.get("daily_budget_total", 100))
        self.daily_budget_cron = int(config.get("daily_budget_cron", 60))
        self.daily_budget_dev = int(config.get("daily_budget_dev", 40))
        self.cache_dir = Path(config.get("cache_dir", "data/cache/jooble"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.contact_email = os.environ.get("CONTACT_EMAIL", "garvd2005@gmail.com")
        self.user_agent = config.get(
            "user_agent", "fresher-radar/0.1 ({contact_email})"
        ).format(contact_email=self.contact_email)
        self.polite_delay = float(
            config.get("rate_limit", {}).get("polite_delay_seconds", 0.5)
        )
        self.usage_counter = usage_counter or UsageCounter(
            config.get("usage_counter_file", "data/usage_counter.json")
        )
        self.api_key = api_key or _get_api_key()

    @property
    def name(self) -> str:
        return "jooble"

    def _redact(self, message: str) -> str:
        if self.api_key and self.api_key in message:
            return message.replace(self.api_key, "<REDACTED>")
        return message

    def _get_cache_path(self, keywords: str, location: str, page: int) -> Path:
        query_key = f"{keywords.lower().strip()}_{location.lower().strip()}_{page}"
        query_hash = hashlib.sha256(query_key.encode("utf-8")).hexdigest()[:12]
        clean_kw = re.sub(r"[^a-z0-9]+", "_", keywords.lower().strip()).strip("_")
        clean_loc = re.sub(r"[^a-z0-9]+", "_", location.lower().strip()).strip("_")
        return self.cache_dir / f"jooble_{clean_kw}_{clean_loc}_p{page}_{query_hash}.json"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def _execute_live_request(
        self, client: httpx.Client, keywords: str, location: str, page: int
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("JOOBLE_API_KEY is not configured.")

        url = f"{self.base_url}/{self.api_key}"
        payload = {"keywords": keywords, "location": location, "page": page}
        headers = {"Content-Type": "application/json", "User-Agent": self.user_agent}

        try:
            response = client.post(url, json=payload, headers=headers, timeout=15.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            safe_msg = self._redact(str(exc))
            logger.error("Jooble API HTTP error: %s", safe_msg)
            raise httpx.HTTPStatusError(
                message=safe_msg,
                request=exc.request,
                response=exc.response,
            ) from None
        except Exception as exc:
            safe_msg = self._redact(str(exc))
            logger.error("Jooble API request error: %s", safe_msg)
            raise RuntimeError(safe_msg) from None

    def fetch_query(
        self,
        keywords: str,
        location: str,
        page: int = 1,
        mode: str = "dev",
        cache_mode: str = "read-through",
        use_cache: bool | None = None,
        client: httpx.Client | None = None,
    ) -> tuple[list[RawPost], str]:
        if use_cache is not None:
            cache_mode = "cache-only" if use_cache else "bypass"

        cache_path = self._get_cache_path(keywords, location, page)

        if cache_mode in ("read-through", "cache-only"):
            if cache_path.exists():
                logger.info(
                    "Jooble cache HIT for (%s | %s | page %d): %s",
                    keywords,
                    location,
                    page,
                    cache_path.name,
                )
                try:
                    data = json.loads(cache_path.read_text(encoding="utf-8"))
                    return self._parse_jobs(data), "hit"
                except Exception as exc:
                    logger.warning(
                        "Failed reading cache file %s: %s", cache_path.name, exc
                    )
            elif cache_mode == "cache-only":
                logger.info(
                    "Jooble cache MISS for (%s | %s | page %d)",
                    keywords,
                    location,
                    page,
                )
                return [], "miss"

        # Live request path (for read-through on cache miss, or bypass mode)
        mode_limit = (
            self.daily_budget_cron if mode == "cron" else self.daily_budget_dev
        )
        if not self.usage_counter.can_request(
            "jooble", mode, mode_limit, self.daily_budget_total
        ):
            logger.warning(
                "Jooble daily budget reached for mode=%s (%d limit)",
                mode,
                mode_limit,
            )
            raise QuotaExceededError(
                f"Jooble daily quota reached for mode={mode}. Aborting live call."
            )

        owns_client = client is None
        http_client = client or httpx.Client()
        try:
            data = self._execute_live_request(
                http_client, keywords, location, page
            )
            # Write response to disk cache immediately before any other operation
            cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("Cached live Jooble response to %s", cache_path.name)

            # Record request in usage counter
            self.usage_counter.record_request(
                "jooble", mode, 1, mode_limit, self.daily_budget_total
            )

            time.sleep(self.polite_delay)
            return self._parse_jobs(data), "live"
        finally:
            if owns_client:
                http_client.close()

    def _parse_jobs(self, data: dict[str, Any]) -> list[RawPost]:
        jobs = data.get("jobs", [])
        posts = []
        for job in jobs:
            job_id = str(job.get("id", ""))
            if not job_id:
                continue
            posts.append(
                RawPost(
                    source=self.name,
                    source_id=job_id,
                    payload=job,
                )
            )
        return posts

    def fetch(
        self,
        mode: str = "dev",
        cache_mode: str = "read-through",
        use_cache: bool | None = None,
        queries_override: list[tuple[str, str]] | None = None,
    ) -> tuple[list[RawPost], dict[str, dict[str, Any]]]:
        if use_cache is not None:
            cache_mode = "cache-only" if use_cache else "bypass"

        if queries_override is not None:
            query_pairs = queries_override
        else:
            terms = self.config.get("search_queries", {}).get("terms", ["fresher"])
            locations = self.config.get("search_queries", {}).get(
                "locations", ["India"]
            )
            query_pairs = [(term, loc) for term in terms for loc in locations]

        all_posts: list[RawPost] = []
        stats: dict[str, dict[str, Any]] = {}
        seen_ids: set[str] = set()

        with httpx.Client() as client:
            for term, loc in query_pairs:
                query_name = f"{term} | {loc}"
                cache_path = self._get_cache_path(term, loc, 1)
                try:
                    posts, status = self.fetch_query(
                        keywords=term,
                        location=loc,
                        page=1,
                        mode=mode,
                        cache_mode=cache_mode,
                        client=client,
                    )
                    new_unique_count = 0
                    for post in posts:
                        if post.source_id not in seen_ids:
                            seen_ids.add(post.source_id)
                            all_posts.append(post)
                            new_unique_count += 1

                    stats[query_name] = {
                        "status": status,
                        "returned": len(posts),
                        "new_unique": new_unique_count,
                        "cache_file": cache_path.name if cache_path.exists() else None,
                    }
                except QuotaExceededError as qe:
                    logger.warning("Jooble budget limit: %s", qe)
                    stats[query_name] = {
                        "status": "quota_exceeded",
                        "returned": 0,
                        "new_unique": 0,
                        "cache_file": None,
                    }
                    break
                except Exception as exc:
                    safe_msg = self._redact(str(exc))
                    logger.error(
                        "Jooble error on query %s: %s", query_name, safe_msg
                    )
                    stats[query_name] = {
                        "status": f"error: {safe_msg}",
                        "returned": 0,
                        "new_unique": 0,
                        "cache_file": None,
                    }

                if not self.usage_counter.can_request(
                    "jooble",
                    mode,
                    self.daily_budget_cron
                    if mode == "cron"
                    else self.daily_budget_dev,
                    self.daily_budget_total,
                ):
                    break

        return all_posts, stats
