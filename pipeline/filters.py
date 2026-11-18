import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pipeline.normalize import NormalizedJob

logger = logging.getLogger(__name__)


def load_filters_config(config_path: str = "config/filters.yaml") -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Filters configuration not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class FilterRuleEngine:
    """Layered rule-based filter engine for fresher job posts."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_filters_config()

        # Recency threshold
        self.max_age_days = int(
            self.config.get("recency", {}).get("max_age_days", 45)
        )

        # Location lists
        loc_cfg = self.config.get("location", {})
        self.non_india_list = [w.lower() for w in loc_cfg.get("known_non_india", [])]
        self.india_keywords = [w.lower() for w in loc_cfg.get("india_keywords", [])]
        self.remote_india_patterns = [
            w.lower() for w in loc_cfg.get("remote_india_patterns", [])
        ]

        # Hard rejects
        hr_cfg = self.config.get("hard_rejects", {})

        # Seniority
        sen_cfg = hr_cfg.get("seniority", {})
        self.seniority_keywords = [w.lower() for w in sen_cfg.get("keywords", [])]
        self.exempt_entry_signals = [
            w.lower() for w in sen_cfg.get("exempt_entry_signals", [])
        ]
        self.sales_lead_exemptions = [
            re.compile(p, re.IGNORECASE) for p in sen_cfg.get("sales_lead_exemptions", [])
        ]

        # Experience
        exp_cfg = hr_cfg.get("experience", {})
        self.max_acceptable_years = int(exp_cfg.get("max_acceptable_years", 1))
        self.experience_patterns = [
            re.compile(p, re.IGNORECASE) for p in exp_cfg.get("patterns", [])
        ]

        # Not a job post
        naj_cfg = hr_cfg.get("not_a_job_post", {})
        self.not_job_keywords = [w.lower() for w in naj_cfg.get("keywords", [])]
        self.not_job_patterns = [
            re.compile(p, re.IGNORECASE) for p in naj_cfg.get("patterns", [])
        ]
        self.not_job_exempt_roles = [
            w.lower() for w in naj_cfg.get("exempt_roles", [])
        ]
        self.stipend_override_signals = [
            w.lower() for w in naj_cfg.get("stipend_override_signals", [])
        ]

        # Pay to join
        ptj_cfg = hr_cfg.get("pay_to_join", {})
        self.pay_to_join_keywords = [
            w.lower() for w in ptj_cfg.get("keywords", [])
        ]
        self.pay_to_join_patterns = [
            re.compile(p, re.IGNORECASE) for p in ptj_cfg.get("patterns", [])
        ]
        self.anti_fraud_disclaimers = [
            w.lower() for w in ptj_cfg.get("anti_fraud_disclaimers", [])
        ]

        # Positive signals
        pos_cfg = self.config.get("positive_signals", {})
        self.title_positive_keywords = [
            w.lower() for w in pos_cfg.get("title_keywords", [])
        ]
        self.explicit_experience_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in pos_cfg.get("explicit_experience_patterns", [])
        ]

    def _matches_word(self, pattern_word: str, text: str) -> bool:
        """Check if pattern_word matches in text using word boundaries."""
        escaped = re.escape(pattern_word)
        return bool(re.search(rf"\b{escaped}\b", text, re.IGNORECASE))

    def evaluate_location(self, location_text: str, title: str = "", description: str = "") -> bool:
        """Evaluate if location is acceptable (India, remote-open-to-India, or unknown).

        Returns:
            True if valid/acceptable, False if clearly outside India.
        """
        loc = location_text.lower().strip()
        combined = f"{loc} {title.lower()} {description.lower()}"

        # Empty location means unknown, not reject
        if not loc:
            return True

        # Check explicit remote open to India patterns
        for pattern in self.remote_india_patterns:
            if pattern in combined:
                return True

        # Check if India or Indian tech hub is mentioned
        for kw in self.india_keywords:
            if self._matches_word(kw, loc):
                return True

        # Check if clearly in known foreign country/city
        for foreign in self.non_india_list:
            if self._matches_word(foreign, loc):
                # Only reject if India is NOT mentioned anywhere
                if not any(self._matches_word(kw, combined) for kw in self.india_keywords):
                    return False

        # If location is unspecified or ambiguous (e.g. "Remote"), do not reject
        return True

    def parse_experience_years(self, text: str) -> tuple[int | None, int | None]:
        """Extract minimum and maximum years of experience from text."""
        min_years = None
        max_years = None

        for pattern in self.experience_patterns:
            for match in pattern.finditer(text):
                d = match.groupdict()
                if "min" in d and d["min"] is not None:
                    val = int(d["min"])
                    if min_years is None or val < min_years:
                        min_years = val
                if "max" in d and d["max"] is not None:
                    val = int(d["max"])
                    if max_years is None or val > max_years:
                        max_years = val

        return min_years, max_years

    def get_accept_signal(self, job: NormalizedJob) -> tuple[str, str] | None:
        """Find the matching accept signal and its location.

        Returns (signal_value, location_description) or None.
        Accepts ONLY on:
        1. Title signal
        2. Jooble type == Internship
        3. Explicit experience pattern in title or description
        """
        title = job.title
        desc = job.description

        # 1. Title entry signal
        for kw in self.title_positive_keywords:
            if self._matches_word(kw, title):
                return kw, f"title: {kw}"

        # 2. Jooble type == Internship
        if job.job_type and job.job_type.lower() == "internship":
            return "internship", "type: Internship"

        # 3. Explicit experience pattern in title or description
        for pattern in self.explicit_experience_patterns:
            m_title = pattern.search(title)
            if m_title:
                return m_title.group(0), f"title phrase: '{m_title.group(0)}'"
            m_desc = pattern.search(desc)
            if m_desc:
                return m_desc.group(0), f"description phrase: '{m_desc.group(0)}'"

        return None

    def evaluate(self, job: NormalizedJob, current_time: datetime | None = None) -> tuple[str, str]:
        """Evaluate a NormalizedJob and assign (rule_decision, rule_reason).

        Returns:
            Tuple of (decision, reason) where decision is 'accept', 'ambiguous', or 'reject'.
        """
        now = current_time or datetime.now(timezone.utc)
        title = job.title
        desc = job.description
        loc = job.location_text
        combined = f"{title} {desc}".lower()

        # 1. Recency Rule
        if job.posted_at is not None:
            age_seconds = (now - job.posted_at).total_seconds()
            if age_seconds > (self.max_age_days * 86400):
                return "reject", "stale"

        # 2. Location Check (rejects only when clearly outside India)
        if not self.evaluate_location(loc, title, desc):
            return "reject", "not_india"

        # 3. Pay-to-Join and Scams
        has_anti_fraud = any(disclaimer in combined for disclaimer in self.anti_fraud_disclaimers)
        # Anti-fraud disclaimer present: ignore pay_to_join unless title is pay-to-join
        is_pay_to_join = False
        if not has_anti_fraud:
            for ptj_kw in self.pay_to_join_keywords:
                if self._matches_word(ptj_kw, combined):
                    is_pay_to_join = True
                    break
            if not is_pay_to_join:
                for pattern in self.pay_to_join_patterns:
                    if pattern.search(combined):
                        is_pay_to_join = True
                        break
        else:
            # When anti-fraud disclaimer exists, check only title for scam patterns
            for ptj_kw in self.pay_to_join_keywords:
                if self._matches_word(ptj_kw, title):
                    is_pay_to_join = True
                    break

        if is_pay_to_join:
            return "reject", "pay_to_join"

        # 4. Not a Job Post (fellowship, bootcamp, workshop, course ad, program admission)
        # Check title against exempt real roles (e.g. CA Article Trainee, etc.)
        is_exempt_role = any(self._matches_word(role, title) for role in self.not_job_exempt_roles)

        if not is_exempt_role:
            is_not_job = False
            for naj_kw in self.not_job_keywords:
                if self._matches_word(naj_kw, combined):
                    is_not_job = True
                    break

            if not is_not_job:
                for pattern in self.not_job_patterns:
                    if pattern.search(combined):
                        is_not_job = True
                        break

            if is_not_job:
                # Check for stipend / full-time override
                has_stipend = any(
                    self._matches_word(sig, combined)
                    for sig in self.stipend_override_signals
                )
                if has_stipend:
                    return "ambiguous", "fellowship_with_stipend"
                return "reject", "not_a_job_post"

        # 5. Seniority in Title
        has_seniority_title = False
        for sen_kw in self.seniority_keywords:
            if self._matches_word(sen_kw, title):
                # If keyword is 'lead', check if it's sales lead generation
                if sen_kw == "lead" and any(p.search(title) for p in self.sales_lead_exemptions):
                    continue

                # Check if strong entry signal in title overrides seniority word
                has_override = any(
                    self._matches_word(entry_sig, title)
                    for entry_sig in self.exempt_entry_signals
                )
                if not has_override:
                    has_seniority_title = True
                    break

        if has_seniority_title:
            return "reject", "seniority"

        # 6. Experience Required
        min_years, max_years = self.parse_experience_years(combined)
        if min_years is not None and min_years >= 2:
            return "reject", "experience_required"

        is_ambiguous_exp = False
        if min_years is not None and min_years == 1 and max_years is not None and max_years >= 3:
            is_ambiguous_exp = True
        elif min_years is not None and min_years == 1 and max_years is None:
            is_ambiguous_exp = True

        # 7. Accept Path: Title signal, Jooble type == Internship, or explicit experience pattern
        accept_signal = self.get_accept_signal(job)
        if accept_signal:
            if is_ambiguous_exp:
                return "ambiguous", "experience_1_to_3_years"
            return "accept", "fresher_signal_matched"

        # 8. Ambiguous / Unclear Fit
        if is_ambiguous_exp:
            return "ambiguous", "min_1_year_experience"

        return "ambiguous", "unclear_fresher_fit"
