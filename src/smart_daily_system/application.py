from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from smart_daily_system.collectors.base import CollectedEvent, Collector
from smart_daily_system.delivery.email import ReportSender
from smart_daily_system.errors import CollectorError, DeliveryError
from smart_daily_system.reporting.generator import DailyReport, ReportGenerator
from smart_daily_system.reporting.renderer import report_fingerprint
from smart_daily_system.storage.sqlite import SQLiteReportRepository


@dataclass(frozen=True, slots=True)
class CollectorWarning:
    source: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class RunResult:
    report: DailyReport
    report_id: int
    fingerprint: str
    delivery_status: str
    warnings: tuple[CollectorWarning, ...]
    collector_counts: Mapping[str, int]

    @property
    def successful(self) -> bool:
        return self.delivery_status != "failed"


class DailyReportApplication:
    def __init__(
        self,
        *,
        collectors: Sequence[Collector],
        generator: ReportGenerator,
        repository: SQLiteReportRepository,
        sender: ReportSender,
        recipients: tuple[str, ...],
        timezone_name: str = "Asia/Shanghai",
    ) -> None:
        self.collectors = tuple(collectors)
        self.generator = generator
        self.repository = repository
        self.sender = sender
        self.recipients = recipients
        self.timezone_name = timezone_name

    def run(
        self,
        report_date: date,
        *,
        actors_by_source: Mapping[str, tuple[str, ...]] | None = None,
        default_actors: tuple[str, ...] = (),
    ) -> RunResult:
        zone = ZoneInfo(self.timezone_name)
        start_at = datetime.combine(report_date, time.min, tzinfo=zone)
        end_at = start_at + timedelta(days=1)
        actor_map = actors_by_source or {}

        warnings: list[CollectorWarning] = []
        counts: dict[str, int] = {}
        unique_events: dict[tuple[str, str], CollectedEvent] = {}
        for collector in self.collectors:
            actor_ids = actor_map.get(collector.source, default_actors)
            try:
                events = collector.collect(
                    actor_ids=tuple(actor_ids),
                    start_at=start_at,
                    end_at=end_at,
                )
            except CollectorError as error:
                counts[collector.source] = 0
                warnings.append(
                    CollectorWarning(
                        source=collector.source,
                        code=error.code,
                        message=str(error),
                    )
                )
                continue
            except Exception as error:  # noqa: BLE001 - isolate every collector failure.
                counts[collector.source] = 0
                warnings.append(
                    CollectorWarning(
                        source=collector.source,
                        code="COLLECTOR_UNEXPECTED",
                        message=f"Unexpected collector failure: {type(error).__name__}",
                    )
                )
                continue
            counts[collector.source] = len(events)
            for event in events:
                unique_events.setdefault((event.source, event.external_id), event)

        events = list(unique_events.values())
        report = self.generator.generate(report_date, events)
        stored = self.repository.save_report(report, events)

        if not report.entries:
            return RunResult(
                report=report,
                report_id=stored.report_id,
                fingerprint=stored.fingerprint,
                delivery_status="no_events",
                warnings=tuple(warnings),
                collector_counts=counts,
            )
        if not self.recipients:
            return RunResult(
                report=report,
                report_id=stored.report_id,
                fingerprint=stored.fingerprint,
                delivery_status="skipped",
                warnings=tuple(warnings),
                collector_counts=counts,
            )
        if self.repository.has_successful_delivery(
            stored.report_id,
            stored.fingerprint,
            self.recipients,
        ):
            return RunResult(
                report=report,
                report_id=stored.report_id,
                fingerprint=stored.fingerprint,
                delivery_status="skipped",
                warnings=tuple(warnings),
                collector_counts=counts,
            )

        try:
            self.sender.send(report, self.recipients)
        except DeliveryError as error:
            self.repository.record_delivery(
                stored.report_id,
                stored.fingerprint,
                self.recipients,
                "failed",
                error.code,
            )
            warnings.append(
                CollectorWarning(
                    source="delivery",
                    code=error.code,
                    message=str(error),
                )
            )
            delivery_status = "failed"
        except Exception as error:  # noqa: BLE001 - persist unexpected sender failures.
            self.repository.record_delivery(
                stored.report_id,
                stored.fingerprint,
                self.recipients,
                "failed",
                "DELIVERY_UNEXPECTED",
            )
            warnings.append(
                CollectorWarning(
                    source="delivery",
                    code="DELIVERY_UNEXPECTED",
                    message=f"Unexpected delivery failure: {type(error).__name__}",
                )
            )
            delivery_status = "failed"
        else:
            self.repository.record_delivery(
                stored.report_id,
                stored.fingerprint,
                self.recipients,
                "sent",
                None,
            )
            delivery_status = "sent"

        return RunResult(
            report=report,
            report_id=stored.report_id,
            fingerprint=stored.fingerprint,
            delivery_status=delivery_status,
            warnings=tuple(warnings),
            collector_counts=counts,
        )

    @staticmethod
    def fingerprint(report: DailyReport) -> str:
        return report_fingerprint(report)
