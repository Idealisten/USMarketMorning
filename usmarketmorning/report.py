from __future__ import annotations

from datetime import datetime

import pytz

from .analysis import ai_analysis, heuristic_analysis, infer_market_reason, infer_stock_reason, summarize_trump_comments
from .config import settings
from .market import fetch_market_moves, fetch_nasdaq100_constituents, fetch_sp500_constituents, fetch_stock_movers
from .models import Report, StockMove
from .news import fetch_news
from .storage import save_report


def generate_report() -> Report:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    slug = now.strftime("%Y-%m-%d")
    report = Report(
        slug=slug,
        title=f"{now.strftime('%Y年%m月%d日')} 美股收盘晨报",
        date=now.strftime("%Y-%m-%d"),
        generated_at=now.isoformat(),
    )

    facts, news_errors = fetch_news()
    report.facts = facts
    report.trump_summary = summarize_trump_comments(facts)
    report.errors.extend(news_errors)

    try:
        report.market_moves = fetch_market_moves()
        for move in report.market_moves:
            move.reason = infer_market_reason(move, facts)
    except Exception as exc:
        report.errors.append(f"市场指数/商品/美债数据获取失败：{exc}")

    try:
        report.nasdaq_gainers, report.nasdaq_losers, errors = fetch_stock_movers(
            "纳斯达克100", fetch_nasdaq100_constituents()
        )
        report.errors.extend(errors)
    except Exception as exc:
        report.errors.append(f"纳斯达克100 个股涨跌筛选失败：{exc}")

    try:
        report.sp500_gainers, report.sp500_losers, errors = fetch_stock_movers(
            "标普500", fetch_sp500_constituents()
        )
        report.errors.extend(errors)
    except Exception as exc:
        report.errors.append(f"标普500 个股涨跌筛选失败：{exc}")

    all_movers: list[StockMove] = (
        report.nasdaq_gainers
        + report.nasdaq_losers
        + report.sp500_gainers
        + report.sp500_losers
    )
    for stock in all_movers:
        stock.reason = infer_stock_reason(stock, facts)

    ai_result = ai_analysis(report.market_moves, facts, all_movers)
    if ai_result:
        report.analysis, report.individual_stock_notes = ai_result
    else:
        report.analysis, report.individual_stock_notes = heuristic_analysis(report.market_moves, facts, all_movers)

    save_report(report)
    return report
