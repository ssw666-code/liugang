from __future__ import annotations

import argparse
import platform
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from smart_daily_system import __version__
from smart_daily_system.config import Settings
from smart_daily_system.storage.sqlite import initialize_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smart-daily",
        description="Smart Daily System command line entry point.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Show the application version.")
    subparsers.add_parser("doctor", help="Check the local runtime and project paths.")

    init_db = subparsers.add_parser("init-db", help="Create or update the local SQLite database.")
    init_db.add_argument(
        "--path",
        type=Path,
        help="Override SMART_DAILY_DATABASE_PATH.",
    )
    return parser


def _run_doctor(settings: Settings) -> int:
    project_root = Path(__file__).resolve().parents[2]
    sqlite_version = sqlite3.sqlite_version
    checks = [
        ("Python >= 3.12", sys.version_info >= (3, 12), platform.python_version()),
        ("SQLite", True, sqlite_version),
        ("specs directory", (project_root / "specs").is_dir(), str(project_root / "specs")),
        ("src directory", (project_root / "src").is_dir(), str(project_root / "src")),
    ]

    print(f"Smart Daily System {__version__}")
    print(f"Platform: {platform.platform()}")
    print(f"Timezone: {settings.timezone}")
    print(f"Database: {settings.database_path}")
    for label, passed, detail in checks:
        marker = "PASS" if passed else "FAIL"
        print(f"[{marker}] {label}: {detail}")

    return 0 if all(check[1] for check in checks) else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_environment()

    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "doctor":
        return _run_doctor(settings)
    if args.command == "init-db":
        database_path = args.path or settings.database_path
        initialize_database(database_path)
        print(f"Database ready: {database_path}")
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
