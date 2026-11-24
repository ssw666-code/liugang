from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CollectedEvent:
    """Provider-neutral event passed from collectors to report generation."""

    source: str
    actor: str
    occurred_at: datetime
    summary: str
    external_id: str
    url: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if not self.actor.strip():
            raise ValueError("actor must not be empty")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        if not self.summary.strip():
            raise ValueError("summary must not be empty")
        if not self.external_id.strip():
            raise ValueError("external_id must not be empty")


class Collector(Protocol):
    """Boundary implemented by each external data-source adapter."""

    source: str

    def collect(
        self,
        *,
        actor_ids: tuple[str, ...],
        start_at: datetime,
        end_at: datetime,
    ) -> list[CollectedEvent]:
        """Collect normalized events for the requested actors and time window."""
        ...
