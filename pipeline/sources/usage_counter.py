import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Raised when daily source request budget is exceeded."""

    pass


class UsageCounter:
    """Tracks daily request counts per source.

    Uses PostgreSQL source_usage table when available so local development and
    GitHub Actions cron share the real quota. Falls back to a local JSON file.
    """

    def __init__(
        self,
        counter_file: str | Path = "data/usage_counter.json",
        db_url: str | None = None,
        use_db: bool | None = None,
    ) -> None:
        self.counter_file = Path(counter_file)
        self.counter_file.parent.mkdir(parents=True, exist_ok=True)
        if use_db is False:
            self.db_url = None
        elif db_url is not None:
            self.db_url = db_url if db_url else None
        else:
            self.db_url = os.environ.get("SUPABASE_DB_URL")

    def _today_date(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # File-based fallback methods
    def _load_file(self) -> dict[str, Any]:
        if not self.counter_file.exists():
            return {}
        try:
            return json.loads(self.counter_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_file(self, data: dict[str, Any]) -> None:
        tmp_file = self.counter_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_file.replace(self.counter_file)

    def get_count(
        self,
        source: str,
        mode: str | None = None,
        date_str: str | None = None,
    ) -> int:
        day = date_str or self._today_date()

        if self.db_url:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        if mode:
                            cur.execute(
                                """
                                SELECT COALESCE(SUM(count), 0)
                                FROM source_usage
                                WHERE day = %s AND source = %s AND mode = %s;
                                """,
                                (day, source, mode),
                            )
                        else:
                            cur.execute(
                                """
                                SELECT COALESCE(SUM(count), 0)
                                FROM source_usage
                                WHERE day = %s AND source = %s;
                                """,
                                (day, source),
                            )
                        row = cur.fetchone()
                        return int(row[0]) if row else 0
            except Exception as exc:
                logger.warning(
                    "Failed querying source_usage from DB, falling back to file: %s", exc
                )

        data = self._load_file()
        day_stats = data.get(day, {}).get(source, {})
        if mode:
            return int(day_stats.get(mode, 0))
        return int(day_stats.get("total", 0))

    def can_request(
        self,
        source: str,
        mode: str = "dev",
        mode_limit: int = 40,
        total_limit: int = 100,
    ) -> bool:
        current_total = self.get_count(source)
        current_mode = self.get_count(source, mode=mode)

        if current_total >= total_limit:
            return False
        if current_mode >= mode_limit:
            return False
        return True

    def record_request(
        self,
        source: str,
        mode: str = "dev",
        count: int = 1,
        mode_limit: int = 40,
        total_limit: int = 100,
    ) -> int:
        day = self._today_date()
        current_total = self.get_count(source)
        current_mode = self.get_count(source, mode=mode)

        if current_total + count > total_limit:
            raise QuotaExceededError(
                f"Source {source} total daily quota exceeded: "
                f"{current_total} + {count} > {total_limit}"
            )

        if current_mode + count > mode_limit:
            raise QuotaExceededError(
                f"Source {source} {mode} daily quota exceeded: "
                f"{current_mode} + {count} > {mode_limit}"
            )

        if self.db_url:
            try:
                upsert_sql = """
                INSERT INTO source_usage (day, source, mode, count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (day, source, mode)
                DO UPDATE SET count = source_usage.count + EXCLUDED.count;
                """
                with psycopg.connect(self.db_url, autocommit=True) as conn:
                    with conn.cursor() as cur:
                        cur.execute(upsert_sql, (day, source, mode, count))
                return current_total + count
            except Exception as exc:
                logger.warning("Failed saving source_usage to DB, falling back to file: %s", exc)

        data = self._load_file()
        if day not in data:
            data[day] = {}
        if source not in data[day]:
            data[day][source] = {"total": 0, "dev": 0, "cron": 0}

        data[day][source]["total"] = current_total + count
        data[day][source][mode] = current_mode + count
        self._save_file(data)
        return current_total + count
