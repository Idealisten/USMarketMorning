from __future__ import annotations

import socket

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, abort, render_template

from .config import settings
from .emailer import send_report_email
from .report import generate_report
from .storage import latest_report, list_reports, load_report


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    @app.route("/")
    def home():
        reports = list_reports()
        return render_template("index.html", latest=reports[0] if reports else None, reports=reports)

    @app.route("/articles/<slug>")
    def article(slug: str):
        try:
            report = load_report(slug)
        except FileNotFoundError:
            abort(404)
        return render_template("article.html", report=report, reports=list_reports())

    @app.route("/health")
    def health():
        return {"ok": True, "latest": (latest_report() or {}).get("slug")}

    return app


def run_daily_job() -> None:
    report = generate_report()
    send_report_email(report)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=pytz.timezone(settings.timezone))
    scheduler.add_job(
        run_daily_job,
        trigger=CronTrigger(
            hour=settings.report_hour,
            minute=settings.report_minute,
            timezone=pytz.timezone(settings.timezone),
        ),
        id="daily_market_report",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler


def find_available_port(start: int, host: str) -> int:
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    port = start
    while port < start + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((probe_host, port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"未找到可用端口，起始端口：{start}")


def main() -> None:
    app = create_app()
    scheduler = None
    if settings.run_scheduler:
        scheduler = start_scheduler()
    port = find_available_port(settings.port, settings.host)
    try:
        app.run(host=settings.host, port=port)
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
