import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from pipeline.llm.base import BaseLLMProvider, TagResult
from pipeline.llm.groq import GroqProvider
from pipeline.llm.mock import MockProvider
from pipeline.store import (
    get_today_token_usage,
    load_pending_jobs,
    record_llm_call,
    update_tagged_jobs,
)

logger = logging.getLogger(__name__)


def load_pricing_config(config_path: str = "config/pricing.yaml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_provider(model: str, **kwargs: Any) -> BaseLLMProvider:
    if model.lower() == "mock":
        return MockProvider(model=model, **kwargs)
    return GroqProvider(model=model, **kwargs)


def get_content_hash(title: str, company: str, location: str, description: str) -> str:
    raw = f"{title.strip()}|{company.strip()}|{location.strip()}|{description.strip()[:600]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cache_key(content_hash: str, prompt_version: str, model: str) -> str:
    token = f"{content_hash}_{prompt_version}_{model}"
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TagManager:
    """Orchestrates job post tagging, caching, and token budget guard."""

    def __init__(
        self,
        model: str,
        provider: BaseLLMProvider | None = None,
        prompt_version: str = "tag_v1",
        cache_dir: str = "data/cache/llm",
        batch_size: int = 10,
    ) -> None:
        self.model = model
        self.provider = provider or build_provider(model)
        self.prompt_version = prompt_version
        self.batch_size = batch_size
        self.cache_dir = Path(cache_dir) / model.replace("/", "_")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.pricing_config = load_pricing_config()
        model_cfg = self.pricing_config.get("models", {}).get(model, {})
        rl = model_cfg.get("rate_limits", {})
        self.daily_budget_tokens = int(
            rl.get("daily_token_budget_stop_tokens", 160000)
        )

    def load_cached_tag(self, cache_key: str) -> TagResult | None:
        file_path = self.cache_dir / f"{cache_key}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                return TagResult(**data)
            except Exception:
                return None
        return None

    def save_cached_tag(self, cache_key: str, result: TagResult) -> None:
        file_path = self.cache_dir / f"{cache_key}.json"
        try:
            file_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed saving tag cache for %s: %s", cache_key, exc)

    def run_bench_mode(
        self,
        ids_file: str | Path,
        bench_out: str | Path,
        run_id: int | None = None,
    ) -> dict[str, Any]:
        """Run benchmark on explicit IDs and write output only to a JSON file."""
        ids_path = Path(ids_file)
        if not ids_path.exists():
            raise FileNotFoundError(f"IDs file not found at {ids_path}")

        target_ids = [
            line.strip()
            for line in ids_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        logger.info("Loaded %d target IDs from %s for benchmark", len(target_ids), ids_path)

        # Load posts from eval/sample_50.csv if available
        posts_map: dict[str, dict[str, Any]] = {}
        sample_csv = Path("eval/sample_50.csv")
        if sample_csv.exists():
            with open(sample_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    posts_map[str(row["id"])] = {
                        "id": str(row["id"]),
                        "title": row.get("title", ""),
                        "company": row.get("company", ""),
                        "location": row.get("location_text", ""),
                        "description": row.get("description_snippet", ""),
                    }

        target_posts: list[dict[str, Any]] = []
        for tid in target_ids:
            if tid in posts_map:
                target_posts.append(posts_map[tid])
            else:
                target_posts.append(
                    {"id": tid, "title": "", "company": "", "location": "", "description": ""}
                )

        tagged_results: list[dict[str, Any]] = []
        call_logs: list[dict[str, Any]] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_reasoning_tokens = 0
        total_latency_ms = 0
        valid_items_count = 0
        total_items_count = len(target_posts)

        # Batch in groups of batch_size
        for i in range(0, len(target_posts), self.batch_size):
            chunk = target_posts[i : i + self.batch_size]
            batch_posts = [
                {
                    "index": j,
                    "id": p["id"],
                    "title": p["title"],
                    "company": p["company"],
                    "location": p["location"],
                    "description": p["description"][:600],
                }
                for j, p in enumerate(chunk)
            ]

            logger.info("Tagging bench batch %d-%d of %d", i + 1, i + len(chunk), len(target_posts))
            try:
                results, usage = self.provider.tag_batch(batch_posts, self.prompt_version)
                total_input_tokens += usage.input_tokens
                total_output_tokens += usage.output_tokens
                total_reasoning_tokens += usage.reasoning_tokens
                total_latency_ms += usage.latency_ms

                call_logs.append(
                    {
                        "batch_start": i,
                        "batch_size": len(chunk),
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "reasoning_tokens": usage.reasoning_tokens,
                        "latency_ms": usage.latency_ms,
                        "status": "success",
                    }
                )

                # Log call to llm_calls table
                record_llm_call(
                    model=self.model,
                    prompt_version=self.prompt_version,
                    batch_size=len(chunk),
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    reasoning_tokens=usage.reasoning_tokens,
                    latency_ms=usage.latency_ms,
                    status="success",
                    run_id=run_id,
                )

                # Map results back to post IDs
                results_by_idx = {r.index: r for r in results}
                for j, p in enumerate(chunk):
                    if j in results_by_idx:
                        r = results_by_idx[j]
                        valid_items_count += 1
                        tagged_results.append(
                            {
                                "index": i + j,
                                "id": p["id"],
                                "title": p["title"],
                                "company": p["company"],
                                "post_type": r.post_type.value,
                                "is_fresher": r.is_fresher,
                                "role": r.role.value,
                                "city": r.city.value,
                                "is_remote": r.is_remote,
                            }
                        )
                    else:
                        tagged_results.append(
                            {
                                "index": i + j,
                                "id": p["id"],
                                "error": "Missing from model response",
                            }
                        )

            except Exception as exc:
                logger.error("Bench batch %d-%d failed: %s", i + 1, i + len(chunk), exc)
                call_logs.append(
                    {
                        "batch_start": i,
                        "batch_size": len(chunk),
                        "error": str(exc),
                        "status": "failed",
                    }
                )

        validity_rate = (
            round((valid_items_count / total_items_count) * 100, 2)
            if total_items_count > 0
            else 0.0
        )
        total_tokens = total_input_tokens + total_output_tokens
        num_posts = len(tagged_results)
        inp_per_post = round(total_input_tokens / num_posts, 2) if num_posts > 0 else 0
        out_per_post = round(total_output_tokens / num_posts, 2) if num_posts > 0 else 0
        reas_per_post = round(total_reasoning_tokens / num_posts, 2) if num_posts > 0 else 0
        reasoning_share = (
            round((total_reasoning_tokens / total_output_tokens) * 100, 2)
            if total_output_tokens > 0
            else 0.0
        )

        bench_payload = {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "total_posts": total_items_count,
            "valid_posts": valid_items_count,
            "validity_rate_pct": validity_rate,
            "calls_made": len(call_logs),
            "tokens": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "reasoning_tokens": total_reasoning_tokens,
                "total_tokens": total_tokens,
                "input_per_post": inp_per_post,
                "output_per_post": out_per_post,
                "reasoning_per_post": reas_per_post,
                "reasoning_share_of_output_pct": reasoning_share,
            },
            "latency": {
                "total_latency_ms": total_latency_ms,
                "avg_latency_ms": round(total_latency_ms / len(call_logs), 2) if call_logs else 0,
            },
            "results": tagged_results,
            "calls": call_logs,
        }

        out_path = Path(bench_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(bench_payload, indent=2), encoding="utf-8")
        logger.info("Saved benchmark output to %s", out_path)
        return bench_payload

    def run_production_mode(
        self,
        limit: int | None = None,
        run_id: int | None = None,
    ) -> dict[str, Any]:
        """Tag jobs with status pending_tag up to token budget guard limit."""
        today_used = get_today_token_usage(self.model)
        if today_used >= self.daily_budget_tokens:
            logger.warning(
                "Daily token budget guard: already used %d / %d tokens. Stopping.",
                today_used,
                self.daily_budget_tokens,
            )
            return {"status": "budget_exhausted", "tokens_used": today_used, "tagged": 0}

        pending = load_pending_jobs(limit=limit)
        logger.info("Loaded %d pending_tag jobs for tagging", len(pending))
        if not pending:
            return {"status": "no_pending_jobs", "tagged": 0}

        tagged_records: list[dict[str, Any]] = []
        cache_hits = 0
        live_calls = 0
        tokens_accumulated = today_used

        uncached_batch: list[tuple[dict[str, Any], str]] = []

        def flush_batch() -> None:
            nonlocal live_calls, tokens_accumulated
            if not uncached_batch:
                return

            posts_for_call = [
                {
                    "index": idx,
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location_text"],
                    "description": job["description"][:600],
                }
                for idx, (job, _) in enumerate(uncached_batch)
            ]

            try:
                results, usage = self.provider.tag_batch(posts_for_call, self.prompt_version)
                live_calls += 1
                tokens_accumulated += (usage.input_tokens + usage.output_tokens)

                record_llm_call(
                    model=self.model,
                    prompt_version=self.prompt_version,
                    batch_size=len(uncached_batch),
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    reasoning_tokens=usage.reasoning_tokens,
                    latency_ms=usage.latency_ms,
                    status="success",
                    run_id=run_id,
                )

                res_map = {r.index: r for r in results}
                for idx, (job, c_key) in enumerate(uncached_batch):
                    if idx in res_map:
                        res = res_map[idx]
                        self.save_cached_tag(c_key, res)
                        is_active = (
                            res.post_type.value in ("job", "internship", "trainee")
                            and res.is_fresher
                        )
                        status = "active" if is_active else "rejected"
                        rule_reason = (
                            None
                            if is_active
                            else ("llm_not_fresher" if not res.is_fresher else "llm_not_a_job")
                        )
                        tagged_records.append(
                            {
                                "canonical_key": job["canonical_key"],
                                "status": status,
                                "role": res.role.value,
                                "city": res.city.value,
                                "post_type": res.post_type.value,
                                "is_fresher": res.is_fresher,
                                "is_remote": res.is_remote,
                                "rule_reason": rule_reason,
                                "tag_source": "llm",
                                "tagger_model": self.model,
                                "prompt_version": self.prompt_version,
                            }
                        )
                    else:
                        tagged_records.append(
                            {
                                "canonical_key": job["canonical_key"],
                                "status": "needs_review",
                                "rule_reason": "missing_from_llm_batch",
                                "tag_source": "llm",
                                "tagger_model": self.model,
                                "prompt_version": self.prompt_version,
                            }
                        )
            except ValidationError:
                for job, _ in uncached_batch:
                    tagged_records.append(
                        {
                            "canonical_key": job["canonical_key"],
                            "status": "needs_review",
                            "rule_reason": "invalid_llm_json",
                            "tag_source": "llm",
                            "tagger_model": self.model,
                            "prompt_version": self.prompt_version,
                        }
                    )
            finally:
                uncached_batch.clear()

        for job in pending:
            if tokens_accumulated >= self.daily_budget_tokens:
                logger.warning(
                    "Token budget stop reached (%d >= %d). Halting production tagging.",
                    tokens_accumulated,
                    self.daily_budget_tokens,
                )
                break

            c_hash = get_content_hash(
                job["title"], job["company"], job["location_text"], job["description"]
            )
            cache_key = get_cache_key(c_hash, self.prompt_version, self.model)
            cached_res = self.load_cached_tag(cache_key)

            if cached_res is not None:
                cache_hits += 1
                is_active = (
                    cached_res.post_type.value in ("job", "internship", "trainee")
                    and cached_res.is_fresher
                )
                status = "active" if is_active else "rejected"
                rule_reason = (
                    None
                    if is_active
                    else ("llm_not_fresher" if not cached_res.is_fresher else "llm_not_a_job")
                )
                tagged_records.append(
                    {
                        "canonical_key": job["canonical_key"],
                        "status": status,
                        "role": cached_res.role.value,
                        "city": cached_res.city.value,
                        "post_type": cached_res.post_type.value,
                        "is_fresher": cached_res.is_fresher,
                        "is_remote": cached_res.is_remote,
                        "rule_reason": rule_reason,
                        "tag_source": "llm",
                        "tagger_model": self.model,
                        "prompt_version": self.prompt_version,
                    }
                )
            else:
                uncached_batch.append((job, cache_key))
                if len(uncached_batch) >= self.batch_size:
                    flush_batch()

        # Flush any remaining uncached jobs
        if uncached_batch:
            flush_batch()

        if tagged_records:
            updated_count = update_tagged_jobs(tagged_records)
            logger.info("Updated %d jobs in database with LLM tags", updated_count)

        return {
            "status": "success",
            "total_processed": len(tagged_records),
            "cache_hits": cache_hits,
            "live_calls": live_calls,
            "tokens_used_today": tokens_accumulated,
        }
