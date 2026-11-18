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

logger = logging.getLogger(__name__)

INDIA_LOCATION_KEYWORDS = [
    "india",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "pune",
    "mumbai",
    "delhi",
    "new delhi",
    "gurgaon",
    "gurugram",
    "noida",
    "chennai",
    "kolkata",
    "ahmedabad",
]


def is_india_or_remote_open(location_text: str, title: str = "", content: str = "") -> bool:
    loc = location_text.lower()

    # Direct match for Indian city or country in location field
    for kw in INDIA_LOCATION_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", loc):
            return True

    # For remote postings, India MUST be explicitly mentioned in location, title, or content
    if "remote" in loc:
        combined = f"{loc} {title.lower()} {content.lower()}"
        return any(
            re.search(rf"\b{re.escape(kw)}\b", combined)
            for kw in INDIA_LOCATION_KEYWORDS
        )

    return False


class GreenhouseAdapter(BaseSourceAdapter):
    """Adapter for Greenhouse Public Job Boards API."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base_url = config.get(
            "base_url", "https://boards-api.greenhouse.io/v1/boards"
        ).rstrip("/")
        self.companies = config.get("companies", [])
        self.cache_dir = Path(config.get("cache_dir", "data/cache/greenhouse"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.contact_email = os.environ.get("CONTACT_EMAIL", "garvd2005@gmail.com")
        self.user_agent = config.get(
            "user_agent", "fresher-radar/0.1 ({contact_email})"
        ).format(contact_email=self.contact_email)
        self.polite_delay = float(
            config.get("rate_limit", {}).get("polite_delay_seconds", 0.2)
        )

    @property
    def name(self) -> str:
        return "greenhouse"

    def _get_cache_path(self, token: str) -> Path:
        return self.cache_dir / f"{token}.json"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def _execute_board_request(
        self, client: httpx.Client, token: str
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{token}/jobs"
        params = {"content": "true"}
        headers = {"User-Agent": self.user_agent}

        response = client.get(url, params=params, headers=headers, timeout=20.0)
        response.raise_for_status()
        return response.json()

    def fetch_company(
        self,
        token: str,
        cache_mode: str = "read-through",
        use_cache: bool | None = None,
        client: httpx.Client | None = None,
    ) -> list[RawPost]:
        posts, _, _, _ = self.fetch_company_details(
            token, cache_mode=cache_mode, use_cache=use_cache, client=client
        )
        return posts

    def fetch_company_details(
        self,
        token: str,
        cache_mode: str = "read-through",
        use_cache: bool | None = None,
        client: httpx.Client | None = None,
    ) -> tuple[list[RawPost], str, int, int]:
        if use_cache is not None:
            cache_mode = "cache-only" if use_cache else "bypass"

        cache_path = self._get_cache_path(token)

        data = None
        status = "miss"
        if cache_mode in ("read-through", "cache-only"):
            if cache_path.exists():
                try:
                    data = json.loads(cache_path.read_text(encoding="utf-8"))
                    status = "hit"
                    logger.info("Greenhouse cache HIT for %s: %s", token, cache_path.name)
                except Exception as exc:
                    logger.warning("Failed reading cache for Greenhouse %s: %s", token, exc)
            elif cache_mode == "cache-only":
                logger.info("Greenhouse cache MISS for %s", token)
                return [], "miss", 0, 0

        if data is None:
            owns_client = client is None
            http_client = client or httpx.Client()
            try:
                data = self._execute_board_request(http_client, token)
                # Write to disk cache immediately before any other processing
                cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                status = "live"
                logger.info("Greenhouse live fetch for %s cached to %s", token, cache_path.name)
                time.sleep(self.polite_delay)
            finally:
                if owns_client:
                    http_client.close()

        if not data:
            return [], status, 0, 0

        jobs = data.get("jobs", [])
        total_before = len(jobs)
        india_posts: list[RawPost] = []
        for job in jobs:
            job_id = str(job.get("id", ""))
            location_name = job.get("location", {}).get("name", "") or ""
            title = job.get("title", "") or ""
            content = job.get("content", "") or ""

            if is_india_or_remote_open(location_name, title, content):
                payload = dict(job)
                payload["company_token"] = token
                india_posts.append(
                    RawPost(
                        source=self.name,
                        source_id=f"{token}_{job_id}",
                        payload=payload,
                    )
                )

        total_after = len(india_posts)
        return india_posts, status, total_before, total_after

    def fetch(
        self,
        mode: str = "dev",
        cache_mode: str = "read-through",
        use_cache: bool | None = None,
        companies_override: list[str] | None = None,
    ) -> tuple[list[RawPost], dict[str, dict[str, Any]]]:
        if use_cache is not None:
            cache_mode = "cache-only" if use_cache else "bypass"

        companies = (
            companies_override
            if companies_override is not None
            else self.companies
        )
        all_posts: list[RawPost] = []
        stats: dict[str, dict[str, Any]] = {}
        seen_ids: set[str] = set()

        with httpx.Client() as client:
            for token in companies:
                try:
                    posts, status, total_before, total_after = (
                        self.fetch_company_details(
                            token=token,
                            cache_mode=cache_mode,
                            client=client,
                        )
                    )
                    new_unique_count = 0
                    for post in posts:
                        if post.source_id not in seen_ids:
                            seen_ids.add(post.source_id)
                            all_posts.append(post)
                            new_unique_count += 1

                    stats[token] = {
                        "status": status,
                        "total_before_filter": total_before,
                        "after_filter": total_after,
                        "new_unique": new_unique_count,
                    }
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Greenhouse board %s returned HTTP %d",
                        token,
                        exc.response.status_code,
                    )
                    stats[token] = {
                        "status": f"http_{exc.response.status_code}",
                        "total_before_filter": 0,
                        "after_filter": 0,
                        "new_unique": 0,
                    }
                except Exception as exc:
                    logger.warning("Error fetching Greenhouse board %s: %s", token, exc)
                    stats[token] = {
                        "status": f"error: {exc}",
                        "total_before_filter": 0,
                        "after_filter": 0,
                        "new_unique": 0,
                    }

        return all_posts, stats
