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
                "GITHUB_ACTOR_MAP": "octocat=alice,mona=bob",
                "FEISHU_ACTOR_MAP": "ou_1=alice,ou_2=bob",
                "SMART_DAILY_RECIPIENTS": "a@example.com,b@example.com",
            }
        )

        self.assertEqual(settings.database_path, Path("tmp/test.sqlite3"))
        self.assertEqual(settings.timezone, "UTC")
        self.assertEqual(settings.github_actor_map, {"octocat": "alice", "mona": "bob"})
        self.assertEqual(settings.feishu_actor_map, {"ou_1": "alice", "ou_2": "bob"})
        self.assertEqual(settings.recipients, ("a@example.com", "b@example.com"))

    def test_empty_timezone_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "TIMEZONE"):
            Settings.from_environment({"SMART_DAILY_TIMEZONE": "  "})

    def test_secret_values_are_not_in_repr(self) -> None:
        settings = Settings.from_environment(
            {
                "GITHUB_TOKEN": "github-secret-value",
                "FEISHU_APP_SECRET": "feishu-secret-value",
                "SMTP_PASSWORD": "smtp-secret-value",
            }
        )

        rendered = repr(settings)

        self.assertNotIn("github-secret-value", rendered)
        self.assertNotIn("feishu-secret-value", rendered)
        self.assertNotIn("smtp-secret-value", rendered)

    def test_invalid_actor_map_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "external_id=canonical_id"):
            Settings.from_environment({"GITHUB_ACTOR_MAP": "missing-separator"})

    def test_no_send_mode_does_not_require_delivery_configuration(self) -> None:
        settings = Settings.from_environment(
            {
                "GITHUB_OWNER": "example",
                "GITHUB_REPO": "repo",
                "GITHUB_ACTOR_MAP": "octocat=alice",
                "FEISHU_APP_ID": "app",
                "FEISHU_APP_SECRET": "secret",
                "FEISHU_CHAT_ID": "chat",
                "FEISHU_ACTOR_MAP": "ou_1=alice",
            }
        )

        self.assertEqual(settings.missing_real_configuration(include_delivery=False), ())
        self.assertIn("SMTP_HOST", settings.missing_real_configuration())


if __name__ == "__main__":
    unittest.main()
