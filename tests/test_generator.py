import unittest
from datetime import UTC, date, datetime, timedelta

from smart_daily_system.collectors.base import CollectedEvent
from smart_daily_system.reporting.generator import ReportGenerator
from smart_daily_system.reporting.renderer import render_report, report_fingerprint


class ReportGeneratorTests(unittest.TestCase):
    def test_events_are_deduplicated_grouped_and_sorted(self) -> None:
        base = datetime(2026, 11, 24, 1, tzinfo=UTC)
        events = [
            CollectedEvent("github", "bob", base + timedelta(hours=2), "提交 B", "gh-b"),
            CollectedEvent("github", "alice", base, "提交 A", "gh-a"),
            CollectedEvent("github", "alice", base, "提交 A", "gh-a"),
            CollectedEvent("feishu_task", "alice", base + timedelta(hours=1), "任务 A", "task-a"),
        ]

        report = ReportGenerator().generate(date(2026, 11, 24), events)

        self.assertEqual([entry.actor for entry in report.entries], ["alice", "bob"])
        self.assertEqual(len(report.entries[0].highlights), 2)
        self.assertEqual(report.entries[0].source_event_ids, ("gh-a", "task-a"))
        self.assertTrue(all(entry.source_event_ids for entry in report.entries))

    def test_rendering_and_fingerprint_are_deterministic(self) -> None:
        event = CollectedEvent(
            "github",
            "alice",
            datetime(2026, 11, 24, 2, tzinfo=UTC),
            "完成采集器",
            "gh-1",
        )
        generator = ReportGenerator()

        first = generator.generate(date(2026, 11, 24), [event])
        second = generator.generate(date(2026, 11, 24), [event])

        self.assertEqual(report_fingerprint(first), report_fingerprint(second))
        self.assertIn("## alice", render_report(first))
        self.assertIn("[GitHub] 完成采集器", render_report(first))
