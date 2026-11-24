from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEZONE = "Asia/Shanghai"


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_actor_map(value: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in _split_csv(value):
        external_id, separator, canonical_id = item.partition("=")
        if not separator or not external_id.strip() or not canonical_id.strip():
            raise ValueError("Actor map entries must use external_id=canonical_id")
        mapping[external_id.strip()] = canonical_id.strip()
    return mapping


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE lines without overwriting process variables."""

    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            os.environ.setdefault(key, value)


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings; secret values are excluded from repr output."""

    database_path: Path
    timezone: str
    github_owner: str = ""
    github_repo: str = ""
    github_token: str = field(default="", repr=False)
    github_actor_map: dict[str, str] = field(default_factory=dict)
    feishu_app_id: str = ""
    feishu_app_secret: str = field(default="", repr=False)
    feishu_chat_id: str = ""
    feishu_actor_map: dict[str, str] = field(default_factory=dict)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = field(default="", repr=False)
    smtp_from: str = ""
    recipients: tuple[str, ...] = ()
    mock_actors: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environment is None else environment
        database_path_value = values.get(
            "SMART_DAILY_DATABASE_PATH", "data/daily_reports.sqlite3"
        ).strip()
        if not database_path_value:
            raise ValueError("SMART_DAILY_DATABASE_PATH must not be empty")
        timezone = values.get("SMART_DAILY_TIMEZONE", DEFAULT_TIMEZONE).strip()
        if not timezone:
            raise ValueError("SMART_DAILY_TIMEZONE must not be empty")
        try:
            smtp_port = int(values.get("SMTP_PORT", "587"))
        except ValueError as error:
            raise ValueError("SMTP_PORT must be an integer") from error
        return cls(
            database_path=Path(database_path_value),
            timezone=timezone,
            github_owner=values.get("GITHUB_OWNER", "").strip(),
            github_repo=values.get("GITHUB_REPO", "").strip(),
            github_token=values.get("GITHUB_TOKEN", "").strip(),
            github_actor_map=_parse_actor_map(values.get("GITHUB_ACTOR_MAP", "")),
            feishu_app_id=values.get("FEISHU_APP_ID", "").strip(),
            feishu_app_secret=values.get("FEISHU_APP_SECRET", "").strip(),
            feishu_chat_id=values.get("FEISHU_CHAT_ID", "").strip(),
            feishu_actor_map=_parse_actor_map(values.get("FEISHU_ACTOR_MAP", "")),
            smtp_host=values.get("SMTP_HOST", "").strip(),
            smtp_port=smtp_port,
            smtp_username=values.get("SMTP_USERNAME", "").strip(),
            smtp_password=values.get("SMTP_PASSWORD", "").strip(),
            smtp_from=values.get("SMTP_FROM", values.get("SMTP_USERNAME", "")).strip(),
            recipients=_split_csv(values.get("SMART_DAILY_RECIPIENTS", "")),
            mock_actors=_split_csv(values.get("SMART_DAILY_MOCK_ACTORS", "alice,bob,carol")),
        )

    @classmethod
    def load(cls, environment: Mapping[str, str] | None = None) -> Settings:
        if environment is None:
            load_dotenv(Path.cwd() / ".env")
        return cls.from_environment(environment)

    def missing_real_configuration(self, *, include_delivery: bool = True) -> tuple[str, ...]:
        required = {
            "GITHUB_OWNER": self.github_owner,
            "GITHUB_REPO": self.github_repo,
            "GITHUB_ACTOR_MAP": self.github_actor_map,
            "FEISHU_APP_ID": self.feishu_app_id,
            "FEISHU_APP_SECRET": self.feishu_app_secret,
            "FEISHU_CHAT_ID": self.feishu_chat_id,
            "FEISHU_ACTOR_MAP": self.feishu_actor_map,
        }
        if include_delivery:
            required.update(
                {
                    "SMTP_HOST": self.smtp_host,
                    "SMTP_FROM": self.smtp_from,
                    "SMART_DAILY_RECIPIENTS": self.recipients,
                }
            )
        return tuple(name for name, value in required.items() if not value)

    def credential_status(self) -> dict[str, bool]:
        return {
            "GitHub token": bool(self.github_token),
            "Feishu app": bool(self.feishu_app_id and self.feishu_app_secret),
            "SMTP account": bool(self.smtp_host and self.smtp_from),
        }
