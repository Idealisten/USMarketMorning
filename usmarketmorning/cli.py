from __future__ import annotations

import argparse

from .emailer import send_report_email
from .report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="生成美股收盘晨报")
    parser.add_argument("command", choices=["generate"], help="生成并保存一篇晨报")
    parser.add_argument("--send", action="store_true", help="生成后发送邮件")
    args = parser.parse_args()

    if args.command == "generate":
        report = generate_report()
        sent = send_report_email(report) if args.send else False
        print(f"saved: {report.slug}")
        print(f"email_sent: {sent}")
        if report.errors:
            print("warnings:")
            for error in report.errors:
                print(f"- {error}")


if __name__ == "__main__":
    main()
