import contextlib
import io
import unittest

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


if __name__ == "__main__":
    unittest.main()
