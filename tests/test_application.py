import tempfile
import time
import unittest
from datetime import UTC, date, datetime
from pathlib import Path

from smart_daily_system.application import DailyReportApplication
from smart_daily_system.collectors.base import CollectedEvent
from smart_daily_system.collectors.mock import MockCollector
from smart_daily_system.delivery.email import OutboxEmailSender
from smart_daily_system.errors import CollectorError, DeliveryError
from smart_daily_system.reporting.generator import ReportGenerator
from smart_daily_system.storage.sqlite import SQLiteReportRepository


class FailingCollector:
    source = "feishu_message"

    def collect(self, **_: object) -> list[CollectedEvent]:
        raise CollectorError("feishu_message", "SIMULATED_FAILURE", "simulated source failure")


class FailingSender:
    def send(self, report: object, recipients: tuple[str, ...]) -> None:
        raise DeliveryError("SIMULATED_SMTP", "simulated delivery failure")


def _events() -> list[CollectedEvent]:
    base = datetime(2026, 11, 24, 1, tzinfo=UTC)
    return [
        CollectedEvent("github", "alice", base, "提交 A", "gh-a"),
        CollectedEvent("feishu_task", "bob", base, "任务 B", "task-b"),
        CollectedEvent("feishu_message", "carol", base, "消息 C", "msg-c"),
    ]


class ApplicationTests(unittest.TestCase):
    def test_end_to_end_is_idempotent_and_fast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = SQLiteReportRepository(root / "reports.sqlite3")
            application = DailyReportApplication(
                collectors=[
                    MockCollector("github", _events()),
                    MockCollector("feishu_task", _events()),
                    MockCollector("feishu_message", _events()),
                ],
                generator=ReportGenerator(),
                repository=repository,
                sender=OutboxEmailSender(root / "outbox"),
                recipients=("team@example.com",),
                timezone_name="Asia/Shanghai",
            )

            started = time.monotonic()
            first = application.run(date(2026, 11, 24), default_actors=("alice", "bob", "carol"))
            elapsed = time.monotonic() - started
            second = application.run(date(2026, 11, 24), default_actors=("alice", "bob", "carol"))

            self.assertEqual(first.delivery_status, "sent")
            self.assertEqual(second.delivery_status, "skipped")
            self.assertEqual(repository.count_reports(), 1)
            self.assertEqual(repository.count_delivery_attempts(), 1)
            self.assertEqual(len(first.report.entries), 3)
            self.assertLess(elapsed, 60)

    def test_single_source_failure_does_not_stop_other_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application = DailyReportApplication(
                collectors=[
                    MockCollector("github", _events()),
                    FailingCollector(),
                ],
                generator=ReportGenerator(),
                repository=SQLiteReportRepository(root / "reports.sqlite3"),
                sender=OutboxEmailSender(root / "outbox"),
                recipients=("team@example.com",),
            )

            result = application.run(date(2026, 11, 24), default_actors=("alice",))

            self.assertEqual(result.delivery_status, "sent")
            self.assertEqual(len(result.report.entries), 1)
            self.assertEqual(result.warnings[0].code, "SIMULATED_FAILURE")

    def test_delivery_failure_is_recorded_and_retried(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteReportRepository(Path(directory) / "reports.sqlite3")
            application = DailyReportApplication(
                collectors=[MockCollector("github", _events())],
                generator=ReportGenerator(),
                repository=repository,
                sender=FailingSender(),
                recipients=("team@example.com",),
            )

            first = application.run(date(2026, 11, 24), default_actors=("alice",))
            second = application.run(date(2026, 11, 24), default_actors=("alice",))

            self.assertEqual(first.delivery_status, "failed")
            self.assertEqual(second.delivery_status, "failed")
            self.assertEqual(repository.count_delivery_attempts(), 2)


if __name__ == "__main__":
    unittest.main()
