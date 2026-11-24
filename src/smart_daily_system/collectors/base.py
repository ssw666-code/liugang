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


class Collector(Protocol):
    """Boundary implemented by each external data-source adapter."""

    def collect(
        self,
        *,
        actor_ids: tuple[str, ...],
        start_at: datetime,
        end_at: datetime,
    ) -> list[CollectedEvent]:
        """Collect normalized events for the requested actors and time window."""
        ...
