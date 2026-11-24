from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from smart_daily_system.collectors.base import CollectedEvent


@dataclass(frozen=True, slots=True)
class ReportEntry:
    actor: str
    highlights: tuple[str, ...]
    source_event_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DailyReport:
    report_date: date
    entries: tuple[ReportEntry, ...]


SOURCE_LABELS = {
    "github": "GitHub",
    "feishu_task": "飞书任务",
    "feishu_message": "飞书消息",
}


class ReportGenerator:
    """Build deterministic, traceable daily reports from normalized events."""

    def generate(self, report_date: date, events: list[CollectedEvent]) -> DailyReport:
        unique_events: dict[tuple[str, str], CollectedEvent] = {}
        for event in events:
            key = (event.source, event.external_id)
            unique_events.setdefault(key, event)

        grouped: dict[str, list[CollectedEvent]] = {}
        for event in unique_events.values():
            grouped.setdefault(event.actor, []).append(event)

        entries: list[ReportEntry] = []
        for actor in sorted(grouped):
            actor_events = sorted(
                grouped[actor],
                key=lambda event: (event.occurred_at, event.source, event.external_id),
            )
            highlights = tuple(
                f"[{SOURCE_LABELS.get(event.source, event.source)}] {event.summary.strip()}"
                for event in actor_events
            )
            source_ids = tuple(event.external_id for event in actor_events)
            entries.append(
                ReportEntry(
                    actor=actor,
                    highlights=highlights,
                    source_event_ids=source_ids,
                )
            )
        return DailyReport(report_date=report_date, entries=tuple(entries))
