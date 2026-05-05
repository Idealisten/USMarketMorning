from __future__ import annotations

import json
import re
from pathlib import Path

from .config import settings
from .models import Report

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ensure_storage() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
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


def subscribers_path() -> Path:
    return settings.data_dir / "subscribers.json"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(normalize_email(email)))


def list_subscribers() -> list[str]:
    ensure_storage()
    path = subscribers_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return sorted({normalize_email(item) for item in data if isinstance(item, str) and is_valid_email(item)})


def add_subscriber(email: str) -> tuple[bool, str]:
    normalized = normalize_email(email)
    if not is_valid_email(normalized):
        return False, "请输入有效的邮箱地址。"

    subscribers = list_subscribers()
    if normalized not in subscribers:
        subscribers.append(normalized)
        subscribers.sort()
        subscribers_path().write_text(json.dumps(subscribers, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, "订阅成功，下一封晨报会发送到你的邮箱。"
