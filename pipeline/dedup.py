import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from rapidfuzz import fuzz

from pipeline.normalize import NormalizedJob


@dataclass
class ProcessedJob:
    job: NormalizedJob
    rule_decision: str
    rule_reason: str
    canonical_key: str
    status: str
    sources: list[str] = field(default_factory=list)
    duplicate_of: str | None = None
    city_or_remote: str = "unknown"


COMPANY_SUFFIX_REGEX = re.compile(
    r"\b(pvt\.?\s*ltd\.?|private\s+limited|llp|inc\.?|corp\.?|llc|technologies|technology|solutions|services|group|international|india)\b",
    re.IGNORECASE,
)
PUNCTUATION_REGEX = re.compile(r"[^\w\s]")
WHITESPACE_REGEX = re.compile(r"\s+")

TITLE_EXPANSIONS = {
    r"\bsr\b": "senior",
    r"\bjr\b": "junior",
    r"\bsde\b": "software development engineer",
    r"\bswe\b": "software engineer",
    r"\bqa\b": "quality assurance",
    r"\bdev\b": "developer",
    r"\bassoc\b": "associate",
    r"\bmgr\b": "manager",
}

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "source",
    "fbclid",
    "gclid",
    "trk",
    "refId",
}


def normalize_title(title: str) -> str:
    text = title.lower()
    for pattern, repl in TITLE_EXPANSIONS.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = PUNCTUATION_REGEX.sub(" ", text)
    return WHITESPACE_REGEX.sub(" ", text).strip()


def normalize_company(company: str) -> str:
    text = company.lower()
    text = COMPANY_SUFFIX_REGEX.sub(" ", text)
    text = PUNCTUATION_REGEX.sub(" ", text)
    return WHITESPACE_REGEX.sub(" ", text).strip()


def normalize_city(location_text: str) -> str:
    loc = location_text.lower().strip()
    if not loc or "remote" in loc or "anywhere" in loc:
        return "remote"
    for city in [
        "bengaluru",
        "bangalore",
        "hyderabad",
        "pune",
        "mumbai",
        "delhi",
        "noida",
        "gurgaon",
        "gurugram",
        "chennai",
        "kolkata",
        "ahmedabad",
    ]:
        if re.search(rf"\b{city}\b", loc):
            if city == "bangalore":
                return "bengaluru"
            if city in ("gurgaon", "gurugram", "noida", "delhi"):
                return "delhi_ncr"
            return city
    return "other_india"


def normalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        query_dict = parse_qs(parsed.query)
        cleaned_query = {
            k: v for k, v in query_dict.items() if k.lower() not in TRACKING_PARAMS
        }
        encoded_query = urlencode(cleaned_query, doseq=True)
        path = parsed.path.rstrip("/")
        return urlunparse(
            (parsed.scheme, parsed.netloc.lower(), path, parsed.params, encoded_query, "")
        )
    except Exception:
        return url.strip()


def shingle_jaccard(text1: str, text2: str, n: int = 2) -> float:
    """Compute n-shingle (word n-gram) Jaccard similarity."""
    tokens1 = re.findall(r"\w+", text1.lower())
    tokens2 = re.findall(r"\w+", text2.lower())

    if len(tokens1) < n or len(tokens2) < n:
        # Fallback to token unigram Jaccard
        s1 = set(tokens1)
        s2 = set(tokens2)
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

    shingles1 = {tuple(tokens1[i : i + n]) for i in range(len(tokens1) - n + 1)}
    shingles2 = {tuple(tokens2[i : i + n]) for i in range(len(tokens2) - n + 1)}

    if not shingles1 and not shingles2:
        return 1.0
    if not shingles1 or not shingles2:
        return 0.0

    return len(shingles1 & shingles2) / len(shingles1 | shingles2)


def generate_canonical_key(company_norm: str, title_norm: str, city_or_remote: str) -> str:
    seed = f"{company_norm}|{title_norm}|{city_or_remote}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def job_richness_score(job: NormalizedJob) -> int:
    """Compute richness score to pick the canonical master record."""
    score = len(job.description)
    if job.salary:
        score += 500
    if job.posted_at:
        score += 200
    if job.location_text:
        score += 100
    return score


class Deduplicator:
    """Two-tier deduplication engine for job posts."""

    def __init__(
        self,
        fuzzy_title_threshold: float = 90.0,
        fuzzy_desc_threshold: float = 0.85,
    ) -> None:
        self.fuzzy_title_threshold = fuzzy_title_threshold
        self.fuzzy_desc_threshold = fuzzy_desc_threshold

    def deduplicate(
        self,
        survivor_jobs: list[tuple[NormalizedJob, str, str]],
    ) -> tuple[list[ProcessedJob], dict[str, int]]:
        """Run Tier-1 (exact key & normalized URL) and Tier-2 (fuzzy) deduplication.

        Args:
            survivor_jobs: List of tuples (NormalizedJob, rule_decision, rule_reason)

        Returns:
            Tuple of (all processed jobs with statuses, stats dict).
        """
        stats = {
            "tier1_duplicates": 0,
            "tier2_duplicates": 0,
            "total_survivors": 0,
            "cross_source_duplicates": 0,
        }

        # Cluster by Tier 1 exact match: canonical_key AND normalized_url
        tier1_buckets: dict[str, list[tuple[NormalizedJob, str, str]]] = {}
        url_to_key: dict[str, str] = {}

        for job, dec, reason in survivor_jobs:
            comp_norm = normalize_company(job.company)
            title_norm = normalize_title(job.title)
            city_norm = normalize_city(job.location_text)
            key = generate_canonical_key(comp_norm, title_norm, city_norm)

            norm_url = normalize_url(job.url)
            if norm_url and norm_url in url_to_key:
                # Same URL maps to earlier key
                key = url_to_key[norm_url]
            elif norm_url:
                url_to_key[norm_url] = key

            tier1_buckets.setdefault(key, []).append((job, dec, reason))

        # Resolve Tier 1 clusters into master candidate list
        tier1_masters: list[ProcessedJob] = []
        all_processed: list[ProcessedJob] = []

        for key, group in tier1_buckets.items():
            # Best record has highest richness score
            group.sort(key=lambda item: job_richness_score(item[0]), reverse=True)
            master_job, master_dec, master_reason = group[0]
            sources_set = {j.source for j, _, _ in group}

            master_processed = ProcessedJob(
                job=master_job,
                rule_decision=master_dec,
                rule_reason=master_reason,
                canonical_key=key,
                status="pending_tag",
                sources=sorted(sources_set),
                duplicate_of=None,
                city_or_remote=normalize_city(master_job.location_text),
            )
            tier1_masters.append(master_processed)
            all_processed.append(master_processed)

            # Record duplicates in group
            for dup_job, dup_dec, dup_reason in group[1:]:
                stats["tier1_duplicates"] += 1
                if dup_job.source != master_job.source:
                    stats["cross_source_duplicates"] += 1

                dup_comp_norm = normalize_company(dup_job.company)
                dup_title_norm = normalize_title(dup_job.title)
                dup_city_norm = normalize_city(dup_job.location_text)
                dup_key = generate_canonical_key(dup_comp_norm, dup_title_norm, dup_city_norm)

                all_processed.append(
                    ProcessedJob(
                        job=dup_job,
                        rule_decision="duplicate",
                        rule_reason=f"tier1_exact_match_of_{key[:8]}",
                        canonical_key=dup_key,
                        status="duplicate",
                        sources=[dup_job.source],
                        duplicate_of=key,
                        city_or_remote=dup_city_norm,
                    )
                )

        # Tier 2: Fuzzy matching among tier 1 masters
        # Check pairwise within the same normalized company and city/remote
        final_survivors: list[ProcessedJob] = []
        tier2_dup_map: dict[str, str] = {}  # child_key -> master_key

        for candidate in tier1_masters:
            c_comp = normalize_company(candidate.job.company)
            c_title = normalize_title(candidate.job.title)
            c_city = candidate.city_or_remote
            c_desc = candidate.job.description

            matched_master: ProcessedJob | None = None
            for master in final_survivors:
                m_comp = normalize_company(master.job.company)
                m_city = master.city_or_remote

                # Must match company and location (or both remote)
                if c_comp != m_comp:
                    continue
                if c_city != m_city and not (c_city == "remote" or m_city == "remote"):
                    continue

                m_title = normalize_title(master.job.title)
                # Rapidfuzz title similarity
                title_sim = fuzz.token_set_ratio(c_title, m_title)
                if title_sim < self.fuzzy_title_threshold:
                    continue

                m_desc = master.job.description
                desc_sim = shingle_jaccard(c_desc, m_desc)
                if desc_sim >= self.fuzzy_desc_threshold:
                    matched_master = master
                    break

            if matched_master is not None:
                # Candidate is a Tier 2 fuzzy duplicate of matched_master
                stats["tier2_duplicates"] += 1
                if candidate.job.source not in matched_master.sources:
                    matched_master.sources.append(candidate.job.source)
                    matched_master.sources.sort()
                    stats["cross_source_duplicates"] += 1

                candidate.status = "duplicate"
                candidate.rule_decision = "duplicate"
                candidate.rule_reason = f"tier2_fuzzy_match_of_{matched_master.canonical_key[:8]}"
                candidate.duplicate_of = matched_master.canonical_key
                tier2_dup_map[candidate.canonical_key] = matched_master.canonical_key
            else:
                final_survivors.append(candidate)

        # Update any Tier 1 children whose master was later marked duplicate in Tier 2
        for p in all_processed:
            if p.duplicate_of and p.duplicate_of in tier2_dup_map:
                p.duplicate_of = tier2_dup_map[p.duplicate_of]

        stats["total_survivors"] = len(final_survivors)
        return all_processed, stats
