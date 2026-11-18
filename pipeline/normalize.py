import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class NormalizedJob:
    source: str
    source_id: str
    origin_site: str
    title: str
    company: str
    location_text: str
    description: str
    url: str
    posted_at: datetime | None
    salary: str | None = None
    job_type: str | None = None


EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_REGEX = re.compile(
    r"(?:(?:\+?91[\s.-]?)?[6-9]\d{9}\b)|(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b)"
)
SCRIPT_STYLE_REGEX = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
HTML_COMMENT_REGEX = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG_REGEX = re.compile(r"<[^>]+>")
WHITESPACE_REGEX = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Strip HTML, unescape entities, handle double-encoding, remove contacts, and normalize."""
    if not text:
        return ""

    # Unescape HTML entities first (up to 3 passes to handle double-encoded entities like &amp;lt;)
    cleaned = text
    for _ in range(3):
        unescaped = html.unescape(cleaned)
        if unescaped == cleaned:
            break
        cleaned = unescaped

    # Remove script and style tags with content
    cleaned = SCRIPT_STYLE_REGEX.sub(" ", cleaned)
    # Remove HTML comments
    cleaned = HTML_COMMENT_REGEX.sub(" ", cleaned)
    # Strip HTML tags
    cleaned = HTML_TAG_REGEX.sub(" ", cleaned)
    # Final unescape pass in case any entities were uncovered
    cleaned = html.unescape(cleaned)

    # Replace non-breaking spaces and other special spaces
    cleaned = cleaned.replace("\xa0", " ").replace("\u200b", " ")

    # Strip emails and phone numbers
    cleaned = EMAIL_REGEX.sub(" ", cleaned)
    cleaned = PHONE_REGEX.sub(" ", cleaned)

    # Collapse multiple whitespaces
    cleaned = WHITESPACE_REGEX.sub(" ", cleaned).strip()
    return cleaned


def parse_datetime(dt_val: Any) -> datetime | None:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val

    s = str(dt_val).strip()
    # Handle ISO formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            parsed = datetime.strptime(s, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass

    # Try standard fromisoformat
    try:
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def normalize_post(source: str, source_id: str, payload: dict[str, Any]) -> NormalizedJob:
    """Normalize a raw job post from Jooble or Greenhouse into a NormalizedJob."""
    if source == "jooble":
        title = clean_text(str(payload.get("title", "")))
        company = clean_text(str(payload.get("company", "")))
        location = clean_text(str(payload.get("location", "")))

        # Jooble snippet is short description text
        snippet = str(payload.get("snippet", ""))
        desc = clean_text(snippet)[:4000]

        origin_site = str(payload.get("source", "")).strip() or "jooble"
        url = str(payload.get("link", "")).strip()
        salary = clean_text(str(payload.get("salary", ""))) or None
        job_type = str(payload.get("type", "")).strip() or None
        posted_at = parse_datetime(payload.get("updated"))

        return NormalizedJob(
            source="jooble",
            source_id=str(source_id),
            origin_site=origin_site,
            title=title,
            company=company,
            location_text=location,
            description=desc,
            url=url,
            posted_at=posted_at,
            salary=salary,
            job_type=job_type,
        )

    elif source == "greenhouse":
        title = clean_text(str(payload.get("title", "")))
        company_token = str(payload.get("company_token", "")).strip()
        company = clean_text(company_token.capitalize())
        loc_data = payload.get("location", {})
        location_raw = loc_data.get("name", "") if isinstance(loc_data, dict) else str(loc_data)
        location = clean_text(str(location_raw))

        content_html = str(payload.get("content", ""))
        desc = clean_text(content_html)[:4000]

        url = str(payload.get("absolute_url") or payload.get("url") or "").strip()
        posted_at = parse_datetime(payload.get("updated_at"))

        return NormalizedJob(
            source="greenhouse",
            source_id=str(source_id),
            origin_site="greenhouse",
            title=title,
            company=company,
            location_text=location,
            description=desc,
            url=url,
            posted_at=posted_at,
            salary=None,
            job_type=None,
        )

    else:
        # Generic fallback
        title = clean_text(str(payload.get("title", "")))
        company = clean_text(str(payload.get("company", "")))
        location = clean_text(str(payload.get("location", "")))
        desc = clean_text(str(payload.get("description", "")))[:4000]
        url = str(payload.get("url", "")).strip()
        posted_at = parse_datetime(payload.get("posted_at") or payload.get("updated_at"))

        return NormalizedJob(
            source=source,
            source_id=str(source_id),
            origin_site=source,
            title=title,
            company=company,
            location_text=location,
            description=desc,
            url=url,
            posted_at=posted_at,
        )
