from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MarketMove:
    symbol: str
    name: str
    category: str
    price: float | None
    previous_close: float | None
    change: float | None
    change_pct: float | None
    reason: str = ""


@dataclass
class StockMove:
    symbol: str
    name: str
    index: str
    price: float | None
    change_pct: float | None
    change: float | None
    reason: str = ""


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published: str
    category: str
    summary: str = ""


@dataclass
class Report:
    slug: str
    title: str
    date: str
    generated_at: str
    market_moves: list[MarketMove] = field(default_factory=list)
    nasdaq_gainers: list[StockMove] = field(default_factory=list)
    nasdaq_losers: list[StockMove] = field(default_factory=list)
    sp500_gainers: list[StockMove] = field(default_factory=list)
    sp500_losers: list[StockMove] = field(default_factory=list)
    facts: list[NewsItem] = field(default_factory=list)
    analysis: str = ""
    individual_stock_notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
