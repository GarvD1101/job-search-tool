import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from pipeline.llm.base import (
    BaseLLMProvider,
    City,
    PostType,
    Role,
    TagResult,
    Usage,
)

logger = logging.getLogger(__name__)


def load_prompt_template(version: str = "tag_v1") -> str:
    prompt_file = Path(f"pipeline/llm/prompts/{version}.txt")
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template {version} not found at {prompt_file}")
    return prompt_file.read_text(encoding="utf-8")


class GroqProvider(BaseLLMProvider):
    """Groq API provider using plain httpx calls against OpenAI-compatible endpoint."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        max_tpm: int = 8000,
        timeout_seconds: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(model=model)
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.max_tpm = max_tpm
        self.timeout_seconds = timeout_seconds
        self.client = http_client
        self._token_window: list[tuple[float, int]] = []

    def _throttle(self, estimated_tokens: int = 1500) -> None:
        """Throttle requests to stay within 8,000 tokens per minute free-tier limit."""
        now = time.time()
        # Keep calls within last 60 seconds
        self._token_window = [(t, tok) for t, tok in self._token_window if now - t < 60.0]
        used_tokens = sum(tok for _, tok in self._token_window)

        if used_tokens + estimated_tokens > (self.max_tpm - 500):
            oldest_time = self._token_window[0][0]
            sleep_duration = max(0.5, 60.0 - (now - oldest_time) + 0.5)
            logger.info(
                "Approaching token limit (%d/%d TPM). Throttling for %.2fs",
                used_tokens,
                self.max_tpm,
                sleep_duration,
            )
            time.sleep(sleep_duration)
            self._token_window = [
                (t, tok) for t, tok in self._token_window if time.time() - t < 60.0
            ]

    def _record_tokens(self, tokens: int) -> None:
        self._token_window.append((time.time(), tokens))

    def _format_posts_prompt(self, posts: list[dict[str, Any]]) -> str:
        lines: list[str] = ["Here is the batch of job posts to classify:\n"]
        for p in posts:
            idx = p.get("index", 0)
            title = p.get("title", "").strip()
            company = p.get("company", "").strip()
            loc = p.get("location", "").strip()
            desc = p.get("description", "").strip()[:600]
            lines.append(
                f"Post: [{idx}] Title: {title} | Company: {company} | Location: {loc} | "
                f"Description: {desc}"
            )
        lines.append("\nReturn JSON classifying all posts by their index.")
        return "\n".join(lines)

    def _call_api_with_retry(
        self,
        messages: list[dict[str, str]],
        max_retries: int = 3,
    ) -> tuple[dict[str, Any], int]:
        contact = os.environ.get("CONTACT_EMAIL") or "https://github.com/GarvD1101/job-search-tool"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"fresher-radar/0.1 (contact: {contact})",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        # Model-specific parameters
        if "gpt-oss" in self.model:
            payload["reasoning_effort"] = "low"
        elif "qwen" in self.model:
            payload["reasoning_effort"] = "none"

        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        should_close = self.client is None

        for attempt in range(max_retries + 1):
            self._throttle()
            start_t = time.time()
            try:
                resp = client.post(self.BASE_URL, headers=headers, json=payload)
                latency_ms = int((time.time() - start_t) * 1000)

                if resp.status_code == 429:
                    retry_hdr = resp.headers.get("Retry-After")
                    sleep_time = float(retry_hdr) if retry_hdr else (2.0 ** attempt + 1.0)
                    logger.warning(
                        "Groq rate limit hit (429). Backing off for %.2fs (attempt %d/%d)",
                        sleep_time,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(sleep_time)
                    continue

                resp.raise_for_status()
                data = resp.json()
                if should_close:
                    client.close()
                return data, latency_ms

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < max_retries:
                    sleep_time = 2.0 ** attempt + 1.0
                    time.sleep(sleep_time)
                    continue
                if should_close:
                    client.close()
                raise RuntimeError(
                    f"Groq API error ({exc.response.status_code}): {exc.response.text}"
                ) from exc
            except Exception:
                if attempt < max_retries:
                    time.sleep(2.0 ** attempt + 1.0)
                    continue
                if should_close:
                    client.close()
                raise

        if should_close:
            client.close()
        raise RuntimeError("Groq API call exceeded maximum retries")

    def tag_batch(
        self,
        posts: list[dict[str, Any]],
        prompt_version: str = "tag_v1",
    ) -> tuple[list[TagResult], Usage]:
        if not posts:
            return [], Usage(model=self.model)

        system_prompt = load_prompt_template(prompt_version)
        user_prompt = self._format_posts_prompt(posts)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        data, latency_ms = self._call_api_with_retry(messages)

        usage_block = data.get("usage", {})
        prompt_tokens = int(usage_block.get("prompt_tokens", 0))
        completion_tokens = int(usage_block.get("completion_tokens", 0))
        reasoning_tokens = int(
            usage_block.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        )
        total_tokens = int(usage_block.get("total_tokens", prompt_tokens + completion_tokens))
        self._record_tokens(total_tokens)

        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse and validate JSON output
        parsed_results: list[TagResult] = []
        try:
            content_json = json.loads(raw_content)
            items = content_json.get("results", [])
            for item in items:
                parsed_results.append(TagResult(**item))
        except (json.JSONDecodeError, ValidationError, TypeError) as parse_err:
            logger.warning(
                "Initial JSON validation failed: %s. Initiating one repair retry.", parse_err
            )
            # Attempt one repair retry restating the allowed enum lists
            allowed_roles = ", ".join([r.value for r in Role])
            allowed_cities = ", ".join([c.value for c in City])
            allowed_post_types = ", ".join([p.value for p in PostType])
            repair_prompt = (
                f"Your output failed validation: {parse_err}\n"
                "You must use ONLY the following allowed enum values:\n"
                f"- role: {allowed_roles}\n"
                f"- city: {allowed_cities}\n"
                f"- post_type: {allowed_post_types}\n"
                "Return ONLY valid JSON matching the exact schema with key 'results'."
            )
            repair_messages = list(messages)
            repair_messages.append({"role": "assistant", "content": raw_content})
            repair_messages.append({"role": "user", "content": repair_prompt})
            repair_data, repair_lat = self._call_api_with_retry(repair_messages)
            latency_ms += repair_lat

            r_usage = repair_data.get("usage", {})
            r_prompt = int(r_usage.get("prompt_tokens", 0))
            r_comp = int(r_usage.get("completion_tokens", 0))
            r_reas = int(
                r_usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            )
            prompt_tokens += r_prompt
            completion_tokens += r_comp
            reasoning_tokens += r_reas
            self._record_tokens(r_prompt + r_comp)

            repair_content = (
                repair_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            try:
                repaired_json = json.loads(repair_content)
                parsed_results = [
                    TagResult(**item) for item in repaired_json.get("results", [])
                ]
            except Exception as final_err:
                logger.error("Repair retry also failed validation: %s", final_err)
                raise ValidationError.from_exception_data(
                    title="TagResult", line_errors=[]
                ) from final_err

        usage = Usage(
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            latency_ms=latency_ms,
            model=self.model,
            status="success",
        )
        return parsed_results, usage
