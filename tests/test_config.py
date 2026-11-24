import unittest
from pathlib import Path

from smart_daily_system.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_match_local_development_convention(self) -> None:
        settings = Settings.from_environment({})

        self.assertEqual(settings.database_path, Path("data/daily_reports.sqlite3"))
        self.assertEqual(settings.timezone, "Asia/Shanghai")

    def test_environment_overrides_are_applied(self) -> None:
        settings = Settings.from_environment(
            {
                "SMART_DAILY_DATABASE_PATH": "tmp/test.sqlite3",
                "SMART_DAILY_TIMEZONE": "UTC",
            }
        )

        self.assertEqual(settings.database_path, Path("tmp/test.sqlite3"))
        self.assertEqual(settings.timezone, "UTC")

    def test_empty_timezone_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "TIMEZONE"):
            Settings.from_environment({"SMART_DAILY_TIMEZONE": "  "})


if __name__ == "__main__":
    unittest.main()
