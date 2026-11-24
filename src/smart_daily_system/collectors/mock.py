from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from smart_daily_system.collectors.base import CollectedEvent


class MockCollector:
    def __init__(self, source: str, events: list[CollectedEvent]) -> None:
        self.source = source
        self.events = tuple(events)

    def collect(
        self,
        *,
        actor_ids: tuple[str, ...],
        start_at: datetime,
        end_at: datetime,
    ) -> list[CollectedEvent]:
        requested = set(actor_ids)
        return [
            event
            for event in self.events
            if event.source == self.source
            and (not requested or event.actor in requested)
            and start_at <= event.occurred_at < end_at
        ]


def load_mock_events(path: Path | str) -> list[CollectedEvent]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("Mock event file must contain a JSON array")
    events: list[CollectedEvent] = []
    for item in payload:
        if not isinstance(item, dict):
            raise TypeError("Each mock event must be a JSON object")
        events.append(
            CollectedEvent(
                source=str(item["source"]),
                actor=str(item["actor"]),
                occurred_at=datetime.fromisoformat(str(item["occurred_at"])),
                summary=str(item["summary"]),
                external_id=str(item["external_id"]),
                url=str(item["url"]) if item.get("url") else None,
            )
        )
    return events
