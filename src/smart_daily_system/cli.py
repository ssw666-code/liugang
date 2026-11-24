from __future__ import annotations

import argparse
import platform
import sqlite3
import sys
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from smart_daily_system import __version__
from smart_daily_system.application import DailyReportApplication, RunResult
from smart_daily_system.collectors.feishu import (
    FeishuApiClient,
    FeishuMessageCollector,
    FeishuTaskCollector,
)
from smart_daily_system.collectors.github import GitHubCollector
from smart_daily_system.collectors.mock import MockCollector, load_mock_events
from smart_daily_system.config import Settings
from smart_daily_system.delivery.email import OutboxEmailSender, SmtpEmailSender
from smart_daily_system.http import JsonHttpClient
from smart_daily_system.reporting.generator import ReportGenerator
from smart_daily_system.storage.sqlite import SQLiteReportRepository, initialize_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smart-daily",
        description="Smart Daily System command line entry point.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Show the application version.")
    subparsers.add_parser("doctor", help="Check runtime and credential readiness.")

    init_db = subparsers.add_parser("init-db", help="Create or update the local SQLite database.")
    init_db.add_argument("--path", type=Path, help="Override SMART_DAILY_DATABASE_PATH.")

    run = subparsers.add_parser("run", help="Collect events, generate and send the daily report.")
    run.add_argument("--date", type=date_type.fromisoformat, help="Report date, YYYY-MM-DD.")
    run.add_argument("--mock", action="store_true", help="Use the deterministic local fixture.")
    run.add_argument("--fixture", type=Path, default=Path("fixtures/mock_events.json"))
    run.add_argument("--actor", action="append", default=[], help="Mock canonical actor ID.")
    run.add_argument("--outbox", type=Path, default=Path("data/outbox"))
    run.add_argument("--no-send", action="store_true", help="Generate and store without sending.")

    query = subparsers.add_parser("query", help="Print a stored report.")
    query.add_argument("--date", required=True, type=date_type.fromisoformat)
    return parser


def _run_doctor(settings: Settings) -> int:
    project_root = Path(__file__).resolve().parents[2]
    checks = [
        ("Python >= 3.12", sys.version_info >= (3, 12), platform.python_version()),
        ("SQLite", True, sqlite3.sqlite_version),
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
    for label, ready in settings.credential_status().items():
        print(f"[{'READY' if ready else 'EMPTY'}] {label}")
    missing = settings.missing_real_configuration()
    print(f"Real-mode missing fields: {', '.join(missing) if missing else 'none'}")
    return 0 if all(check[1] for check in checks) else 1


def _build_application(
    settings: Settings,
    args: argparse.Namespace,
) -> tuple[DailyReportApplication, dict[str, tuple[str, ...]]]:
    if args.mock:
        events = load_mock_events(args.fixture)
        actors = (
            tuple(args.actor)
            or settings.mock_actors
            or tuple(sorted({event.actor for event in events}))
        )
        collectors = [
            MockCollector(source, events) for source in ("github", "feishu_task", "feishu_message")
        ]
        actors_by_source = {collector.source: actors for collector in collectors}
        sender = OutboxEmailSender(args.outbox)
        recipients = () if args.no_send else settings.recipients or ("demo@example.com",)
    else:
        missing = settings.missing_real_configuration(include_delivery=not args.no_send)
        if missing:
            raise ValueError(f"Missing real-mode configuration: {', '.join(missing)}")
        transport = JsonHttpClient()
        github = GitHubCollector(
            owner=settings.github_owner,
            repository=settings.github_repo,
            actor_map=settings.github_actor_map,
            token=settings.github_token,
            transport=transport,
        )
        feishu_client = FeishuApiClient(
            app_id=settings.feishu_app_id,
            app_secret=settings.feishu_app_secret,
            transport=transport,
        )
        tasks = FeishuTaskCollector(
            client=feishu_client,
            actor_map=settings.feishu_actor_map,
        )
        messages = FeishuMessageCollector(
            client=feishu_client,
            actor_map=settings.feishu_actor_map,
            chat_id=settings.feishu_chat_id,
        )
        collectors = [github, tasks, messages]
        github_actors = tuple(settings.github_actor_map)
        feishu_actors = tuple(settings.feishu_actor_map)
        actors_by_source = {
            "github": github_actors,
            "feishu_task": feishu_actors,
            "feishu_message": feishu_actors,
        }
        recipients = () if args.no_send else settings.recipients
        sender = SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            sender=settings.smtp_from,
        )

    return (
        DailyReportApplication(
            collectors=collectors,
            generator=ReportGenerator(),
            repository=SQLiteReportRepository(settings.database_path),
            sender=sender,
            recipients=recipients,
            timezone_name=settings.timezone,
        ),
        actors_by_source,
    )


def _print_run_result(result: RunResult) -> None:
    print(f"Report date: {result.report.report_date.isoformat()}")
    print(f"Report ID: {result.report_id}")
    print(f"Actors: {', '.join(entry.actor for entry in result.report.entries) or 'none'}")
    print(f"Fingerprint: {result.fingerprint}")
    print(f"Delivery: {result.delivery_status}")
    for source, count in sorted(result.collector_counts.items()):
        print(f"Source {source}: {count} events")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning.source}/{warning.code}: {warning.message}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.load()
    except ValueError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

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
    if args.command == "run":
        report_date = args.date or datetime.now(ZoneInfo(settings.timezone)).date()
        try:
            application, actors_by_source = _build_application(settings, args)
        except (OSError, ValueError) as error:
            print(f"Run configuration error: {error}", file=sys.stderr)
            return 2
        result = application.run(report_date, actors_by_source=actors_by_source)
        _print_run_result(result)
        return 0 if result.successful else 1
    if args.command == "query":
        repository = SQLiteReportRepository(settings.database_path)
        content = repository.get_report_text(args.date.isoformat())
        if content is None:
            print(f"No report found for {args.date.isoformat()}", file=sys.stderr)
            return 1
        print(content)
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
