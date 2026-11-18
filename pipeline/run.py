import argparse
import csv
import hashlib
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from pipeline.dedup import Deduplicator, ProcessedJob, normalize_city
from pipeline.filters import FilterRuleEngine
from pipeline.normalize import NormalizedJob, normalize_post
from pipeline.sources.base import BaseSourceAdapter, RawPost
from pipeline.sources.greenhouse import GreenhouseAdapter
from pipeline.sources.jooble import JoobleAdapter
from pipeline.store import (
    finish_pipeline_run,
    load_raw_posts,
    save_jobs,
    save_raw_posts,
    start_pipeline_run,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

jooble_key = os.environ.get("JOOBLE_API_KEY")


class RedactKeyFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        key = os.environ.get("JOOBLE_API_KEY")
        if key and isinstance(record.msg, str):
            record.msg = record.msg.replace(key, "<REDACTED>")
        return True


root_logger = logging.getLogger()
root_logger.addFilter(RedactKeyFilter())

logger = logging.getLogger("pipeline.run")


def load_sources_config(config_path: str = "config/sources.yaml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Source configuration file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_adapters(config: dict[str, Any]) -> list[BaseSourceAdapter]:
    adapters: list[BaseSourceAdapter] = []
    sources_data = config.get("sources", {})

    jooble_cfg = sources_data.get("jooble", {})
    if jooble_cfg.get("enabled", False):
        adapters.append(JoobleAdapter(jooble_cfg))

    greenhouse_cfg = sources_data.get("greenhouse", {})
    if greenhouse_cfg.get("enabled", False):
        adapters.append(GreenhouseAdapter(greenhouse_cfg))

    return adapters


def run_fetch_stage(
    adapters: list[BaseSourceAdapter],
    mode: str = "dev",
    cache_mode: str = "read-through",
    use_cache: bool | None = None,
    trigger: str = "manual",
    queries_override: list[tuple[str, str]] | None = None,
    companies_override: list[str] | None = None,
) -> tuple[int, str, dict[str, Any]]:
    if use_cache is not None:
        cache_mode = "cache-only" if use_cache else "bypass"

    start_time = time.time()
    run_id = start_pipeline_run(trigger=trigger)

    all_posts: list[RawPost] = []
    source_counts: dict[str, int] = {}
    query_counts: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    for adapter in adapters:
        logger.info("Executing fetch for source: %s", adapter.name)
        try:
            kwargs: dict[str, Any] = {"cache_mode": cache_mode}
            if adapter.name == "jooble" and queries_override is not None:
                kwargs["queries_override"] = queries_override
            elif adapter.name == "greenhouse" and companies_override is not None:
                kwargs["companies_override"] = companies_override

            try:
                posts, q_stats = adapter.fetch(
                    mode=mode,
                    use_cache=(cache_mode == "cache-only"),
                    **kwargs,
                )
            except TypeError:
                posts, q_stats = adapter.fetch(
                    mode=mode,
                    use_cache=(cache_mode == "cache-only"),
                )

            source_counts[adapter.name] = len(posts)
            query_counts[adapter.name] = q_stats
            all_posts.extend(posts)
            logger.info("Source %s returned %d posts", adapter.name, len(posts))
        except Exception as exc:
            logger.error("Source %s failed: %s", adapter.name, exc)
            errors[adapter.name] = str(exc)
            source_counts[adapter.name] = 0
            query_counts[adapter.name] = {}

    # Save collected posts to database
    saved_count = 0
    if all_posts:
        try:
            saved_count = save_raw_posts(all_posts)
            logger.info("Persisted %d raw posts to database", saved_count)
        except Exception as exc:
            logger.error("Failed saving raw posts: %s", exc)
            errors["database"] = str(exc)

    duration = round(time.time() - start_time, 2)

    # Determine run status
    if errors and source_counts and any(c > 0 for c in source_counts.values()):
        status = "partial"
    elif errors and all(c == 0 for c in source_counts.values()):
        status = "failed"
    else:
        status = "success"

    stats = {
        "stage": "fetch",
        "mode": mode,
        "trigger": trigger,
        "duration_seconds": duration,
        "source_counts": source_counts,
        "query_counts": query_counts,
        "total_posts_collected": len(all_posts),
        "total_posts_persisted": saved_count,
        "errors": errors,
    }

    finish_pipeline_run(run_id, status=status, stats=stats)
    return run_id or 0, status, stats


def print_summary(status: str, stats: dict[str, Any]) -> None:
    print("\n" + "=" * 50)
    print("PIPELINE FETCH STAGE SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {status.upper()}")
    print(f"Duration: {stats.get('duration_seconds')}s")
    print(f"Total Posts Collected: {stats.get('total_posts_collected')}")
    print(f"Total Posts Persisted: {stats.get('total_posts_persisted')}")

    print("\nCounts per Source:")
    for source, count in stats.get("source_counts", {}).items():
        print(f"  - {source}: {count} posts")

    print("\nCounts per Query / Company Board:")
    for source, q_dict in stats.get("query_counts", {}).items():
        print(f"  [{source}]")
        for q_name, details in q_dict.items():
            if isinstance(details, dict):
                st = details.get("status", "unknown")
                ret = details.get("returned", 0)
                new_u = details.get("new_unique", 0)
                cf = details.get("cache_file")
                file_str = f" (cache file: {cf})" if cf else ""
                if "total_before_filter" in details:
                    tb = details.get("total_before_filter", 0)
                    af = details.get("after_filter", 0)
                    print(
                        f"    - {q_name}: before_filter={tb}, after_filter={af}, "
                        f"new_unique={new_u} [{st}]"
                    )
                else:
                    print(
                        f"    - {q_name}: returned={ret}, new_unique={new_u} "
                        f"[{st}]{file_str}"
                    )
            else:
                print(f"    - {q_name}: {details}")

    if stats.get("errors"):
        print("\nErrors Encountered:")
        for k, err in stats["errors"].items():
            print(f"  - {k}: {err}")
    print("=" * 50 + "\n")


def print_filter_summary(stats: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("PIPELINE FILTER & DEDUP STAGE SUMMARY")
    print("=" * 60)
    print(f"Duration: {stats.get('duration_seconds')}s")
    print(f"Total Raw Posts Processed: {stats.get('total_raw_posts')}")
    print(f"Total Jobs Persisted: {stats.get('total_jobs_persisted')}")

    print("\n1. Counts by Rule Decision:")
    for dec, count in stats.get("counts_by_decision", {}).items():
        print(f"  - {dec}: {count}")

    print("\n2. Counts by Rule Reason:")
    sorted_reasons = sorted(
        stats.get("counts_by_reason", {}).items(), key=lambda x: x[1], reverse=True
    )
    for reason, count in sorted_reasons:
        print(f"  - {reason}: {count}")

    print("\n3. Decisions per Source:")
    for src, d_map in stats.get("decision_by_source", {}).items():
        print(f"  [{src}]")
        for dec, count in d_map.items():
            print(f"    - {dec}: {count}")

    print("\n4. Deduplication Summary:")
    ds = stats.get("dedup_stats", {})
    print(f"  - Tier 1 exact duplicates removed: {ds.get('tier1_duplicates', 0)}")
    print(f"  - Tier 2 fuzzy duplicates removed: {ds.get('tier2_duplicates', 0)}")
    print(f"  - Cross-source duplicates removed: {ds.get('cross_source_duplicates', 0)}")
    print(f"  - Unique Survivors (pending_tag): {ds.get('total_survivors', 0)}")

    print("\n5. Survivors per Source:")
    for src, count in stats.get("survivors_by_source", {}).items():
        print(f"  - {src}: {count}")

    print("\n6. Fresher Title Keyword Analysis:")
    fts = stats.get("fresher_title_stats", {})
    print(f"  - Total posts with fresher keyword in title: {fts.get('total', 0)}")
    print(f"  - Survived (accepted or ambiguous): {fts.get('survived', 0)}")
    print("  - Top reject reasons for non-survivors:")
    for r, c in sorted(fts.get("top_reject_reasons", {}).items(), key=lambda x: x[1], reverse=True):
        print(f"      * {r}: {c}")

    print("\n7. Suspicious Posts Not Rejected (Audited):")
    susp = stats.get("suspicious_non_rejected", [])
    if susp:
        for s in susp:
            comp = s.get("company")
            tit = s.get("title")
            w = s.get("matched")
            rs = s.get("reason")
            print(f"  - [{comp}] {tit} (words: {w}) -> {rs}")
    else:
        print("  None detected.")

    print("\n8. Sample Accepted Posts with Matched Signal (25 posts):")
    acc_samples = stats.get("accepted_samples", [])
    for idx, s in enumerate(acc_samples[:25], 1):
        c = s.get("company", "Unknown")
        t = s.get("title", "")
        sig = s.get("signal", "")
        loc = s.get("location", "")
        print(f"  {idx:2d}. [{c}] \"{t}\" -> matched {sig} at {loc}")

    print("=" * 60 + "\n")


def run_filter_stage(
    filter_engine: FilterRuleEngine | None = None,
    deduplicator: Deduplicator | None = None,
    trigger: str = "manual",
    export_sample: bool = True,
    sample_size: int = 50,
    seed: int = 42,
) -> tuple[int, str, dict[str, Any]]:
    start_time = time.time()
    run_id = start_pipeline_run(trigger=trigger)

    engine = filter_engine or FilterRuleEngine()
    dedup = deduplicator or Deduplicator()

    # 1. Load all raw posts
    raw_posts = load_raw_posts()
    logger.info("Loaded %d raw posts from database for filtering", len(raw_posts))

    # 2. Normalize and filter
    survivors: list[tuple[NormalizedJob, str, str]] = []
    rejects: list[ProcessedJob] = []

    counts_by_reason: dict[str, int] = {}
    counts_by_decision: dict[str, int] = {"accept": 0, "ambiguous": 0, "reject": 0}
    decision_by_source: dict[str, dict[str, int]] = {}
    reason_by_source: dict[str, dict[str, int]] = {}
    decision_by_origin: dict[str, dict[str, int]] = {}
    reason_by_origin: dict[str, dict[str, int]] = {}

    samples_by_reason: dict[str, list[dict[str, str]]] = {}
    samples_by_decision: dict[str, list[dict[str, str]]] = {
        "accept": [],
        "ambiguous": [],
    }
    all_accepted_with_signals: list[dict[str, str]] = []

    fresher_title_regex = re.compile(
        r"\b(intern|internship|trainee|fresher|freshers|graduate)\b",
        re.IGNORECASE,
    )
    fresher_title_total = 0
    fresher_title_survived = 0
    fresher_title_reject_reasons: dict[str, int] = {}

    suspicious_non_rejected: list[dict[str, str]] = []

    for raw in raw_posts:
        norm = normalize_post(raw.source, raw.source_id, raw.payload)
        dec, reason = engine.evaluate(norm)

        # Track stats
        counts_by_decision[dec] = counts_by_decision.get(dec, 0) + 1
        counts_by_reason[reason] = counts_by_reason.get(reason, 0) + 1

        decision_by_source.setdefault(norm.source, {})
        decision_by_source[norm.source][dec] = (
            decision_by_source[norm.source].get(dec, 0) + 1
        )

        reason_by_source.setdefault(norm.source, {})
        reason_by_source[norm.source][reason] = (
            reason_by_source[norm.source].get(reason, 0) + 1
        )

        decision_by_origin.setdefault(norm.origin_site, {})
        decision_by_origin[norm.origin_site][dec] = (
            decision_by_origin[norm.origin_site].get(dec, 0) + 1
        )

        reason_by_origin.setdefault(norm.origin_site, {})
        reason_by_origin[norm.origin_site][reason] = (
            reason_by_origin[norm.origin_site].get(reason, 0) + 1
        )

        # Collect sample titles
        if dec == "reject":
            if reason not in samples_by_reason:
                samples_by_reason[reason] = []
            if len(samples_by_reason[reason]) < 10:
                samples_by_reason[reason].append(
                    {"title": norm.title, "company": norm.company}
                )
        else:
            if dec == "accept":
                sig_info = engine.get_accept_signal(norm)
                sig_val = sig_info[0] if sig_info else "fresher"
                sig_loc = sig_info[1] if sig_info else "signal"
                all_accepted_with_signals.append(
                    {
                        "title": norm.title,
                        "company": norm.company,
                        "signal": sig_val,
                        "location": sig_loc,
                    }
                )

            if len(samples_by_decision[dec]) < 15:
                samples_by_decision[dec].append(
                    {"title": norm.title, "company": norm.company}
                )

        # Track fresher keyword in title
        if fresher_title_regex.search(norm.title):
            fresher_title_total += 1
            if dec in ("accept", "ambiguous"):
                fresher_title_survived += 1
            else:
                fresher_title_reject_reasons[reason] = (
                    fresher_title_reject_reasons.get(reason, 0) + 1
                )

        # Check for pay-to-join or workshop words that survived
        if dec in ("accept", "ambiguous"):
            susp_words = [
                "fee",
                "pay",
                "course",
                "workshop",
                "admission",
                "deposit",
                "cohort",
            ]
            matched_susp = [
                w
                for w in susp_words
                if re.search(
                    rf"\b{w}\b", f"{norm.title} {norm.description}", re.I
                )
            ]
            if matched_susp and len(suspicious_non_rejected) < 10:
                suspicious_non_rejected.append(
                    {
                        "title": norm.title,
                        "company": norm.company,
                        "matched": ", ".join(matched_susp),
                        "reason": reason,
                    }
                )

        if dec in ("accept", "ambiguous"):
            survivors.append((norm, dec, reason))
        else:
            rej_key = hashlib.sha1(
                f"rej|{norm.source}|{norm.source_id}".encode("utf-8")
            ).hexdigest()
            rejects.append(
                ProcessedJob(
                    job=norm,
                    rule_decision="reject",
                    rule_reason=reason,
                    canonical_key=rej_key,
                    status="rejected",
                    sources=[norm.source],
                    duplicate_of=None,
                    city_or_remote=normalize_city(norm.location_text),
                )
            )

    # 3. Deduplicate survivors
    processed_survivors, dedup_stats = dedup.deduplicate(survivors)

    # 4. Combine all jobs
    all_jobs_to_save = processed_survivors + rejects
    saved_count = save_jobs(all_jobs_to_save)
    logger.info(
        "Persisted %d jobs to database (%d survivors, %d duplicates, %d rejected)",
        saved_count,
        dedup_stats["total_survivors"],
        dedup_stats["tier1_duplicates"] + dedup_stats["tier2_duplicates"],
        len(rejects),
    )

    # 5. Export eval/sample_50.csv from survivor masters (status == 'pending_tag')
    survivor_masters = [
        pj for pj in processed_survivors if pj.status == "pending_tag"
    ]
    survivor_masters.sort(key=lambda x: x.canonical_key)
    rnd = random.Random(seed)
    sampled = rnd.sample(
        survivor_masters, min(sample_size, len(survivor_masters))
    )

    if export_sample:
        eval_dir = Path("eval")
        eval_dir.mkdir(parents=True, exist_ok=True)
        sample_path = eval_dir / "sample_50.csv"
        if sample_path.exists():
            logger.info("eval/sample_50.csv already exists and is frozen. Skipping re-export.")
        else:
            with open(sample_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "id",
                        "title",
                        "company",
                        "location_text",
                        "description_snippet",
                        "url",
                    ]
                )
                for pj in sampled:
                    writer.writerow(
                        [
                            pj.job.source_id,
                            pj.job.title,
                            pj.job.company,
                            pj.job.location_text,
                            pj.job.description[:400],
                            pj.job.url,
                        ]
                    )
            logger.info(
                "Exported %d sampled survivor jobs to %s", len(sampled), sample_path
            )

    survivors_by_source: dict[str, int] = {}
    survivors_by_origin: dict[str, int] = {}
    for sm in survivor_masters:
        survivors_by_source[sm.job.source] = (
            survivors_by_source.get(sm.job.source, 0) + 1
        )
        survivors_by_origin[sm.job.origin_site] = (
            survivors_by_origin.get(sm.job.origin_site, 0) + 1
        )

    # Pick 25 random accepted samples for reporting
    rnd_acc = random.Random(seed)
    accepted_sample_selection = (
        rnd_acc.sample(all_accepted_with_signals, min(25, len(all_accepted_with_signals)))
        if all_accepted_with_signals
        else []
    )

    duration = round(time.time() - start_time, 2)
    stats = {
        "stage": "filter",
        "duration_seconds": duration,
        "total_raw_posts": len(raw_posts),
        "total_jobs_persisted": saved_count,
        "counts_by_decision": counts_by_decision,
        "counts_by_reason": counts_by_reason,
        "decision_by_source": decision_by_source,
        "reason_by_source": reason_by_source,
        "decision_by_origin": decision_by_origin,
        "reason_by_origin": reason_by_origin,
        "dedup_stats": dedup_stats,
        "survivors_by_source": survivors_by_source,
        "survivors_by_origin": survivors_by_origin,
        "fresher_title_stats": {
            "total": fresher_title_total,
            "survived": fresher_title_survived,
            "top_reject_reasons": fresher_title_reject_reasons,
        },
        "samples_by_reason": samples_by_reason,
        "samples_by_decision": samples_by_decision,
        "accepted_samples": accepted_sample_selection,
        "suspicious_non_rejected": suspicious_non_rejected,
    }

    finish_pipeline_run(run_id, status="success", stats=stats)
    return run_id or 0, "success", stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Fresher Job Pipeline Runner")
    parser.add_argument(
        "--stage",
        choices=["fetch", "filter"],
        default="fetch",
        help="Pipeline execution stage: fetch or filter (default: fetch)",
    )
    parser.add_argument(
        "--source",
        choices=["all", "jooble", "greenhouse"],
        default="all",
        help="Source filter (default: all)",
    )
    parser.add_argument(
        "--mode",
        choices=["dev", "cron", "prod"],
        default="dev",
        help="Execution mode for budget limits (default: dev)",
    )
    parser.add_argument(
        "--cache-mode",
        choices=["read-through", "cache-only", "bypass"],
        default="read-through",
        help="Cache behaviour: read-through, cache-only, or bypass (default: read-through)",
    )
    parser.add_argument(
        "--use-cache",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Legacy cache flag: --use-cache (cache-only) or --no-use-cache (bypass)",
    )
    parser.add_argument(
        "--queries",
        default=None,
        help="Comma-separated query pairs: term:loc,term:loc (e.g. 'fresher:Pune,intern:Mumbai')",
    )
    parser.add_argument(
        "--companies",
        default=None,
        help="Comma-separated company tokens (e.g. 'okta,twilio')",
    )
    parser.add_argument(
        "--trigger",
        default="manual",
        help="Run trigger identifier (manual, cron, dispatch)",
    )
    parser.add_argument(
        "--config",
        default="config/sources.yaml",
        help="Path to sources.yaml",
    )

    args = parser.parse_args()

    config = load_sources_config(args.config)
    adapters = build_adapters(config)

    if args.source != "all":
        adapters = [a for a in adapters if a.name == args.source]

    queries_override = None
    if args.queries:
        queries_override = [
            tuple(item.split(":", 1))
            for item in args.queries.split(",")
            if ":" in item
        ]

    companies_override = None
    if args.companies:
        companies_override = [
            item.strip() for item in args.companies.split(",") if item.strip()
        ]

    cache_mode = args.cache_mode
    if args.use_cache is not None:
        cache_mode = "cache-only" if args.use_cache else "bypass"

    if args.stage == "filter":
        _, status, stats = run_filter_stage(trigger=args.trigger)
        print_filter_summary(stats)
        return 0 if status in ("success", "partial") else 1

    _, status, stats = run_fetch_stage(
        adapters=adapters,
        mode=args.mode,
        cache_mode=cache_mode,
        trigger=args.trigger,
        queries_override=queries_override,
        companies_override=companies_override,
    )

    print_summary(status, stats)
    return 0 if status in ("success", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
