from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from smart_daily_system.collectors.base import CollectedEvent
from smart_daily_system.reporting.generator import DailyReport
from smart_daily_system.reporting.renderer import render_report, report_fingerprint

SCHEMA_VERSION = 2


def initialize_database(database_path: Path | str) -> None:
    """Create the local database and apply the idempotent schema."""

    path = Path(database_path)
    if path != Path(":memory:"):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS source_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                url TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(source, external_id)
            );

            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT NOT NULL UNIQUE,
                fingerprint TEXT NOT NULL,
                content_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS report_events (
                report_id INTEGER NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
                event_id INTEGER NOT NULL REFERENCES source_events(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                PRIMARY KEY (report_id, event_id)
            );

            CREATE TABLE IF NOT EXISTS delivery_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
                fingerprint TEXT NOT NULL,
                recipients_hash TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('sent', 'failed')),
                error_code TEXT,
                attempted_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_source_events_actor
                ON source_events(actor, occurred_at);
            CREATE INDEX IF NOT EXISTS idx_delivery_success
                ON delivery_attempts(report_id, fingerprint, recipients_hash, status);
            """
        )
        connection.execute(
            """
            INSERT INTO schema_meta (key, value)
            VALUES ('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(SCHEMA_VERSION),),
        )
        connection.commit()
    finally:
        connection.close()


@dataclass(frozen=True, slots=True)
class StoredReport:
    report_id: int
    fingerprint: str
    created: bool


class SQLiteReportRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        initialize_database(self.database_path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_report(self, report: DailyReport, events: list[CollectedEvent]) -> StoredReport:
        fingerprint = report_fingerprint(report)
        content_text = render_report(report)
        now = _utc_now()
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT id FROM daily_reports WHERE report_date = ?",
                (report.report_date.isoformat(),),
            ).fetchone()
            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO daily_reports
                        (report_date, fingerprint, content_text, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (report.report_date.isoformat(), fingerprint, content_text, now, now),
                )
                report_id = int(cursor.lastrowid)
                created = True
            else:
                report_id = int(existing["id"])
                connection.execute(
                    """
                    UPDATE daily_reports
                    SET fingerprint = ?, content_text = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (fingerprint, content_text, now, report_id),
                )
                created = False

            event_ids: list[int] = []
            for event in events:
                connection.execute(
                    """
                    INSERT INTO source_events
                        (source, external_id, actor, occurred_at, summary, url, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source, external_id) DO UPDATE SET
                        actor = excluded.actor,
                        occurred_at = excluded.occurred_at,
                        summary = excluded.summary,
                        url = excluded.url
                    """,
                    (
                        event.source,
                        event.external_id,
                        event.actor,
                        event.occurred_at.isoformat(),
                        event.summary,
                        event.url,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT id FROM source_events WHERE source = ? AND external_id = ?",
                    (event.source, event.external_id),
                ).fetchone()
                if row is not None:
                    event_ids.append(int(row["id"]))

            connection.execute("DELETE FROM report_events WHERE report_id = ?", (report_id,))
            connection.executemany(
                "INSERT INTO report_events (report_id, event_id, position) VALUES (?, ?, ?)",
                [(report_id, event_id, position) for position, event_id in enumerate(event_ids)],
            )
        return StoredReport(report_id=report_id, fingerprint=fingerprint, created=created)

    def has_successful_delivery(
        self,
        report_id: int,
        fingerprint: str,
        recipients: tuple[str, ...],
    ) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM delivery_attempts
                WHERE report_id = ? AND fingerprint = ?
                  AND recipients_hash = ? AND status = 'sent'
                LIMIT 1
                """,
                (report_id, fingerprint, _recipients_hash(recipients)),
            ).fetchone()
        return row is not None

    def record_delivery(
        self,
        report_id: int,
        fingerprint: str,
        recipients: tuple[str, ...],
        status: str,
        error_code: str | None,
    ) -> None:
        if status not in {"sent", "failed"}:
            raise ValueError("delivery status must be sent or failed")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO delivery_attempts
                    (report_id, fingerprint, recipients_hash, status, error_code, attempted_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    fingerprint,
                    _recipients_hash(recipients),
                    status,
                    error_code,
                    _utc_now(),
                ),
            )

    def get_report_text(self, report_date: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT content_text FROM daily_reports WHERE report_date = ?",
                (report_date,),
            ).fetchone()
        return str(row["content_text"]) if row is not None else None

    def count_reports(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM daily_reports").fetchone()
        return int(row["count"])

    def count_delivery_attempts(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM delivery_attempts").fetchone()
        return int(row["count"])

    def count_report_event_links(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM report_events").fetchone()
        return int(row["count"])


def _recipients_hash(recipients: tuple[str, ...]) -> str:
    normalized = "\n".join(sorted(set(recipients))).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
