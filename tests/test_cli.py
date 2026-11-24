import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from smart_daily_system import __version__
from smart_daily_system.cli import main


class CliTests(unittest.TestCase):
    def test_version_command_prints_package_version(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["version"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), __version__)

    def test_doctor_reports_required_project_directories(self) -> None:
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["doctor"])

        self.assertEqual(exit_code, 0)
        self.assertIn("[PASS] specs directory", output.getvalue())
        self.assertIn("[PASS] src directory", output.getvalue())

    def test_mock_run_creates_report_and_outbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database_path = root / "reports.sqlite3"
            outbox = root / "outbox"
            output = io.StringIO()
            environment = {
                "SMART_DAILY_DATABASE_PATH": str(database_path),
                "SMART_DAILY_RECIPIENTS": "team@example.com",
                "SMART_DAILY_MOCK_ACTORS": "alice,bob,carol",
            }

            with (
                patch.dict(os.environ, environment, clear=True),
                contextlib.redirect_stdout(output),
            ):
                exit_code = main(
                    [
                        "run",
                        "--mock",
                        "--date",
                        "2026-11-24",
                        "--fixture",
                        "fixtures/mock_events.json",
                        "--outbox",
                        str(outbox),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Delivery: sent", output.getvalue())
            self.assertTrue(database_path.is_file())
            self.assertTrue((outbox / "daily-report-2026-11-24.eml").is_file())


if __name__ == "__main__":
    unittest.main()
