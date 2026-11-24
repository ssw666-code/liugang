from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings that do not expose credential values."""

    database_path: Path
    timezone: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environment is None else environment
        database_path = Path(
            values.get("SMART_DAILY_DATABASE_PATH", "data/daily_reports.sqlite3")
        )
        timezone = values.get("SMART_DAILY_TIMEZONE", "Asia/Shanghai").strip()
        if not timezone:
            raise ValueError("SMART_DAILY_TIMEZONE must not be empty")
        return cls(database_path=database_path, timezone=timezone)
