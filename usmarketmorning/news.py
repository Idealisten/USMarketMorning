from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import settings
from .models import NewsItem


DEFAULT_QUERIES = [
    '("stock market" OR "Wall Street" OR "Nasdaq" OR "S&P 500") when:1d',
    '("Federal Reserve" OR inflation OR Treasury OR yields OR dollar) when:1d',
    '(oil OR OPEC OR energy OR "Middle East" OR war OR sanctions) when:1d',
    '("artificial intelligence" OR OpenAI OR Nvidia OR semiconductor OR chips) when:1d',
    '(Trump OR "Truth Social" OR "Trump X" OR "Trump tweet") when:1d',
    '("South Korea stocks" OR KOSPI OR Nikkei OR Hang Seng Tech) when:1d',
]


def google_news_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"


def default_feeds() -> list[str]:
    feeds = [google_news_url(query) for query in DEFAULT_QUERIES]
    if settings.trump_source_url:
        feeds.append(settings.trump_source_url)
    return feeds


def _entry_datetime(entry) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def categorize(title: str, summary: str = "") -> str:
    text = f"{title} {summary}".lower()
    if any(word in text for word in ["war", "missile", "sanction", "geopolitical", "gaza", "ukraine", "iran"]):
        return "战争/地缘"
    if any(word in text for word in ["oil", "opec", "energy", "crude", "gas"]):
        return "能源"
    if any(word in text for word in ["ai", "artificial intelligence", "openai", "nvidia", "chip", "semiconductor"]):
        return "科技/AI"
    if any(word in text for word in ["fed", "inflation", "treasury", "yield", "dollar", "rate"]):
        return "利率/宏观"
    if any(word in text for word in ["trump", "truth social", "tweet", " x "]):
        return "特朗普言论"
    return "市场/公司"


def fetch_news(limit: int = 36) -> tuple[list[NewsItem], list[str]]:
    urls = list(settings.news_rss_urls) or default_feeds()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    seen: set[str] = set()
    items: list[NewsItem] = []
    errors: list[str] = []

    for url in urls:
        try:
            if url.startswith("http"):
                response = requests.get(url, timeout=20, headers={"User-Agent": "USMarketMorning/1.0"})
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            else:
                feed = feedparser.parse(url)
        except Exception as exc:
            errors.append(f"新闻源读取失败 {url}: {exc}")
            continue

        for entry in feed.entries[:20]:
            published_dt = _entry_datetime(entry)
            if published_dt and published_dt < cutoff:
                continue
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            source = ""
            if entry.get("source"):
                source = entry.source.get("title", "")
            source = source or feed.feed.get("title", "RSS")
            summary = BeautifulSummary.clean(entry.get("summary", ""))
            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    url=link,
                    published=published_dt.isoformat() if published_dt else "",
                    category=categorize(title, summary),
                    summary=summary,
                )
            )
            if len(items) >= limit:
                break
        if len(items) >= limit:
            break
    return items, errors


class BeautifulSummary:
    @staticmethod
    def clean(value: str) -> str:
        return " ".join(BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True).split())[:260]
