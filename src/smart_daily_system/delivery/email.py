from __future__ import annotations

from typing import Protocol

from smart_daily_system.reporting.generator import DailyReport


class ReportSender(Protocol):
    """Boundary implemented by email and future delivery channels."""

    def send(self, report: DailyReport, recipients: tuple[str, ...]) -> None:
        """Deliver one completed report to the configured recipients."""
        ...
