import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path

from smart_daily_system.collectors.base import CollectedEvent
from smart_daily_system.reporting.generator import ReportGenerator
from smart_daily_system.storage.sqlite import SQLiteReportRepository


class RepositoryTests(unittest.TestCase):
    def test_save_report_is_idempotent_and_links_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteReportRepository(Path(directory) / "reports.sqlite3")
            event = CollectedEvent(
                "github",
                "alice",
                datetime(2026, 11, 24, 1, tzinfo=UTC),
                "提交",
                "gh-1",
            )
            report = ReportGenerator().generate(date(2026, 11, 24), [event])

            first = repository.save_report(report, [event])
            second = repository.save_report(report, [event])

            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertEqual(repository.count_reports(), 1)
            self.assertEqual(repository.count_report_event_links(), 1)

    def test_successful_delivery_requires_same_fingerprint_and_recipients(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteReportRepository(Path(directory) / "reports.sqlite3")
            event = CollectedEvent(
                "github",
                "alice",
                datetime(2026, 11, 24, 1, tzinfo=UTC),
                "提交",
                "gh-1",
            )
            report = ReportGenerator().generate(date(2026, 11, 24), [event])
            stored = repository.save_report(report, [event])
            recipients = ("a@example.com", "b@example.com")

            repository.record_delivery(
                stored.report_id, stored.fingerprint, recipients, "sent", None
            )

            self.assertTrue(
                repository.has_successful_delivery(
                    stored.report_id,
                    stored.fingerprint,
                    ("b@example.com", "a@example.com"),
                )
            )
            self.assertFalse(
                repository.has_successful_delivery(
                    stored.report_id,
                    stored.fingerprint,
                    ("other@example.com",),
                )
            )


if __name__ == "__main__":
    unittest.main()
