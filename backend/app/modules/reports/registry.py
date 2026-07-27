from __future__ import annotations

from app.modules.reports.contract import ReportDef

REPORTS: dict[str, ReportDef] = {}


def register(report: ReportDef) -> ReportDef:
    if report.key in REPORTS:
        raise ValueError(f"Duplicate report key: {report.key}")
    REPORTS[report.key] = report
    return report
