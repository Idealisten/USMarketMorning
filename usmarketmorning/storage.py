from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .config import settings
from .models import Report


def ensure_storage() -> None:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)


def save_report(report: Report) -> Path:
    ensure_storage()
    path = settings.reports_dir / f"{report.slug}.json"
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_report(slug: str) -> dict:
    path = settings.reports_dir / f"{slug}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def list_reports() -> list[dict]:
    ensure_storage()
    reports: list[dict] = []
    for path in sorted(settings.reports_dir.glob("*.json"), reverse=True):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            reports.append(report)
        except json.JSONDecodeError:
            continue
    return reports


def latest_report() -> dict | None:
    reports = list_reports()
    return reports[0] if reports else None
