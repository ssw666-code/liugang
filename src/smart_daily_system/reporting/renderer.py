from __future__ import annotations

import hashlib
import json

from smart_daily_system.reporting.generator import DailyReport


def report_fingerprint(report: DailyReport) -> str:
    canonical = {
        "report_date": report.report_date.isoformat(),
        "entries": [
            {
                "actor": entry.actor,
                "highlights": list(entry.highlights),
                "source_event_ids": list(entry.source_event_ids),
            }
            for entry in report.entries
        ],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def render_report(report: DailyReport) -> str:
    lines = [f"团队日报 {report.report_date.isoformat()}", ""]
    if not report.entries:
        lines.append("今日暂无已采集的工作事件。")
        return "\n".join(lines)
    for entry in report.entries:
        lines.append(f"## {entry.actor}")
        lines.extend(f"- {highlight}" for highlight in entry.highlights)
        lines.append("")
    return "\n".join(lines).rstrip()
