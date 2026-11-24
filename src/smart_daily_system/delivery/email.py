from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from smart_daily_system.errors import DeliveryError
from smart_daily_system.reporting.generator import DailyReport
from smart_daily_system.reporting.renderer import render_report


class ReportSender(Protocol):
    """Boundary implemented by email and future delivery channels."""

    def send(self, report: DailyReport, recipients: tuple[str, ...]) -> None:
        """Deliver one completed report to the configured recipients."""
        ...


class OutboxEmailSender:
    """Write standards-compliant emails to a local directory for demos/tests."""

    def __init__(self, outbox_directory: Path | str) -> None:
        self.outbox_directory = Path(outbox_directory)

    def send(self, report: DailyReport, recipients: tuple[str, ...]) -> None:
        message = _build_message(
            report,
            recipients,
            sender="smart-daily@example.invalid",
        )
        try:
            self.outbox_directory.mkdir(parents=True, exist_ok=True)
            target = self.outbox_directory / f"daily-report-{report.report_date.isoformat()}.eml"
            target.write_bytes(message.as_bytes())
        except OSError as error:
            raise DeliveryError("OUTBOX_WRITE", "Could not write the local outbox") from error


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self._password = password
        self.sender = sender
        self.timeout_seconds = timeout_seconds

    def send(self, report: DailyReport, recipients: tuple[str, ...]) -> None:
        message = _build_message(report, recipients, sender=self.sender)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as client:
                client.ehlo()
                client.starttls()
                client.ehlo()
                if self.username:
                    client.login(self.username, self._password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            raise DeliveryError("SMTP_SEND", "SMTP delivery failed") from error


def _build_message(
    report: DailyReport,
    recipients: tuple[str, ...],
    *,
    sender: str,
) -> EmailMessage:
    if not recipients:
        raise DeliveryError("NO_RECIPIENTS", "At least one recipient is required")
    message = EmailMessage()
    message["Subject"] = f"团队日报 {report.report_date.isoformat()}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(render_report(report))
    return message
