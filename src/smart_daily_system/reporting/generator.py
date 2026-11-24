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


class ReportGenerator:
    """Week 2 implementation boundary for deterministic report generation."""

    def generate(self, report_date: date, events: list[CollectedEvent]) -> DailyReport:
        raise NotImplementedError("Report generation is scheduled for week 2")
