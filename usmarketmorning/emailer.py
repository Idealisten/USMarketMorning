from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import settings
from .models import Report
from .storage import list_subscribers


def _template_env() -> Environment:
    root = Path(__file__).resolve().parent.parent / "templates"
    return Environment(loader=FileSystemLoader(root), autoescape=select_autoescape(["html", "xml"]))


def render_report_email(report: Report) -> str:
    template = _template_env().get_template("email_report.html")
    return template.render(report=report)


def send_report_email(report: Report) -> bool:
    if not settings.smtp_user or not settings.smtp_password:
        report.errors.append("未配置 SMTP_USER/SMTP_PASSWORD，跳过邮件发送。")
        return False

    recipients = sorted({email for email in [settings.email_to, *list_subscribers()] if email})
    if not recipients:
        report.errors.append("没有配置收件人，跳过邮件发送。")
        return False

    message = EmailMessage()
    sender = settings.email_from or settings.smtp_user
    message["Subject"] = report.title
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(f"{report.title}\n\n请打开网站查看完整晨报。")
    message.add_alternative(render_report_email(report), subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return True
