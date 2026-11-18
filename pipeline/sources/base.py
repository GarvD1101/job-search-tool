from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RawPost(BaseModel):
    source: str
    source_id: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any]


class BaseSourceAdapter(ABC):
    """Abstract base class for all source adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique source identifier (e.g. jooble, greenhouse)."""
        pass

    @abstractmethod
    def fetch(
        self,
        mode: str = "dev",
        use_cache: bool = True,
    ) -> tuple[list[RawPost], dict[str, int]]:
        """Fetch raw posts from source.

        Returns:
            Tuple of (posts list, query/board counts dictionary).
        """
        pass
