from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

from .config import settings
from .models import MarketMove, StockMove


SYMBOL_NAMES = {
    "^NDX": "纳斯达克100",
    "^GSPC": "标普500",
    "^KS11": "韩国KOSPI",
    "^KQ11": "韩国KOSDAQ",
    "^N225": "日经225",
    "^TOPX": "日本TOPIX",
    "HSTECH.HK": "香港恒生科技",
    "^HSTECH": "香港恒生科技",
    "159699.SZ": "恒生消费ETF代理",
    "^HSCGSI": "恒生消费品及服务",
    "GC=F": "国际黄金",
    "SI=F": "白银",
    "PL=F": "铂金",
    "HG=F": "铜",
    "CL=F": "WTI原油",
    "BZ=F": "布伦特原油",
    "^IRX": "短期美债收益率(13周)",
    "^FVX": "中期美债收益率(5年)",
    "^TNX": "中期美债收益率(10年)",
    "^TYX": "长期美债收益率(30年)",
}

YIELD_SYMBOLS = {"^IRX", "^FVX", "^TNX", "^TYX"}
HTTP_HEADERS = {"User-Agent": "USMarketMorning/1.0 (+https://github.com/)"}
warnings.filterwarnings("ignore", category=FutureWarning, module="yfinance")


@dataclass(frozen=True)
class Quote:
    symbol: str
    name: str
    price: float | None
    previous_close: float | None
    change: float | None
    change_pct: float | None


def yahoo_symbol(symbol: str) -> str:
    return symbol.replace(".", "-")


def _clean_number(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def _normalize_yield(symbol: str, value: float | None) -> float | None:
    if value is None:
        return None
    if symbol in YIELD_SYMBOLS and abs(value) > 20:
        return value / 10
    return value


def fetch_quote(symbol: str, name: str | None = None) -> Quote:
    chart_quote = fetch_quote_from_yahoo_chart(symbol, name)
    if chart_quote.price is not None and chart_quote.previous_close is not None:
        return chart_quote

    ticker = yf.Ticker(symbol)
    price = previous = None
    try:
        history = ticker.history(period="7d", interval="1d", auto_adjust=False)
        closes = history["Close"].dropna()
        if len(closes) >= 2:
            price = _clean_number(closes.iloc[-1])
            previous = _clean_number(closes.iloc[-2])
        elif len(closes) == 1:
            price = _clean_number(closes.iloc[-1])
    except Exception:
        pass

    if price is None or previous is None:
        try:
            info = ticker.fast_info
            price = price if price is not None else _clean_number(info.get("last_price"))
            previous = previous if previous is not None else _clean_number(info.get("previous_close"))
        except Exception:
            pass

    price = _normalize_yield(symbol, price)
    previous = _normalize_yield(symbol, previous)
    change = None if price is None or previous is None else price - previous
    change_pct = None if change is None or not previous else change / previous * 100
    return Quote(
        symbol=symbol,
        name=name or SYMBOL_NAMES.get(symbol, symbol),
        price=price,
        previous_close=previous,
        change=change,
        change_pct=change_pct,
    )


def fetch_quote_from_yahoo_chart(symbol: str, name: str | None = None) -> Quote:
    encoded = requests.utils.quote(symbol, safe="")
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{encoded}"
    price = previous = None
    try:
        response = requests.get(
            url,
            params={"range": "7d", "interval": "1d"},
            timeout=15,
            headers=HTTP_HEADERS,
        )
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        meta = result.get("meta", {})
        closes = [
            _clean_number(value)
            for value in result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        ]
        closes = [value for value in closes if value is not None]
        if len(closes) >= 2:
            price = closes[-1]
            previous = closes[-2]
        else:
            price = _clean_number(meta.get("regularMarketPrice"))
            previous = _clean_number(meta.get("chartPreviousClose") or meta.get("previousClose"))
    except Exception:
        pass

    price = _normalize_yield(symbol, price)
    previous = _normalize_yield(symbol, previous)
    change = None if price is None or previous is None else price - previous
    change_pct = None if change is None or not previous else change / previous * 100
    return Quote(
        symbol=symbol,
        name=name or SYMBOL_NAMES.get(symbol, symbol),
        price=price,
        previous_close=previous,
        change=change,
        change_pct=change_pct,
    )


def market_categories() -> list[tuple[str, Iterable[str]]]:
    return [
        ("美股指数", [settings.nasdaq100_symbol, settings.sp500_symbol]),
        ("韩国股市指数", settings.korea_symbols),
        ("日本股市指数", settings.japan_symbols),
        ("香港指数", settings.hk_symbols),
        ("国际黄金/原油/贵金属", settings.commodity_symbols),
        ("美债收益率", settings.bond_symbols),
    ]


def fetch_market_moves() -> list[MarketMove]:
    moves: list[MarketMove] = []
    for category, symbols in market_categories():
        for symbol in symbols:
            quote = fetch_quote(symbol)
            moves.append(
                MarketMove(
                    symbol=symbol,
                    name=quote.name,
                    category=category,
                    price=quote.price,
                    previous_close=quote.previous_close,
                    change=quote.change,
                    change_pct=quote.change_pct,
                )
            )
    return moves


@lru_cache(maxsize=4)
def fetch_sp500_constituents() -> list[tuple[str, str]]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    response = requests.get(url, timeout=20, headers=HTTP_HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", id="constituents")
    rows: list[tuple[str, str]] = []
    if not table:
        return rows
    for tr in table.select("tbody tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
        if len(cells) >= 2 and cells[0] != "Symbol":
            rows.append((yahoo_symbol(cells[0]), cells[1]))
    return rows


@lru_cache(maxsize=4)
def fetch_nasdaq100_constituents() -> list[tuple[str, str]]:
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    response = requests.get(url, timeout=20, headers=HTTP_HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows: list[tuple[str, str]] = []
    for table in soup.find_all("table", class_="wikitable"):
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        if not any("ticker" in header for header in headers):
            continue
        for tr in table.select("tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            symbol = cells[0]
            company = cells[1]
            if symbol and symbol.lower() != "ticker":
                rows.append((yahoo_symbol(symbol), company))
        if rows:
            break
    return rows


def _close_pair_from_download(data: pd.DataFrame, symbol: str) -> tuple[float | None, float | None]:
    if data.empty:
        return None, None
    try:
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"][symbol].dropna()
        else:
            closes = data["Close"].dropna()
        if len(closes) >= 2:
            return _clean_number(closes.iloc[-1]), _clean_number(closes.iloc[-2])
    except Exception:
        return None, None
    return None, None


def fetch_stock_movers(index_name: str, constituents: list[tuple[str, str]], limit: int = 10) -> tuple[list[StockMove], list[StockMove], list[str]]:
    errors: list[str] = []
    if not constituents:
        return [], [], [f"{index_name} 成分股列表为空，无法筛选个股涨跌。"]

    symbols = [symbol for symbol, _ in constituents]
    names = dict(constituents)
    moves: list[StockMove] = []
    try:
        data = yf.download(
            tickers=symbols,
            period="7d",
            interval="1d",
            auto_adjust=False,
            group_by="column",
            progress=False,
            threads=True,
        )
    except Exception as exc:
        return [], [], [f"{index_name} 个股批量行情获取失败：{exc}"]

    for symbol in symbols:
        price, previous = _close_pair_from_download(data, symbol)
        if price is None or previous in (None, 0):
            continue
        change = price - previous
        moves.append(
            StockMove(
                symbol=symbol,
                name=names.get(symbol, symbol),
                index=index_name,
                price=price,
                change=change,
                change_pct=change / previous * 100,
            )
        )

    if not moves:
        errors.append(f"{index_name} 没有可用个股涨跌数据。")
        return [], [], errors

    gainers = sorted(moves, key=lambda item: item.change_pct or 0, reverse=True)[:limit]
    losers = sorted(moves, key=lambda item: item.change_pct or 0)[:limit]
    return gainers, losers, errors
