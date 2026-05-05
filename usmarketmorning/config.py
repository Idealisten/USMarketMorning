from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _int_env("PORT", 8000)
    run_scheduler: bool = os.getenv("RUN_SCHEDULER", "true").lower() == "true"
    timezone: str = os.getenv("REPORT_TIMEZONE", "Asia/Shanghai")
    report_hour: int = _int_env("REPORT_HOUR", 6)
    report_minute: int = _int_env("REPORT_MINUTE", 0)
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))

    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = _int_env("SMTP_PORT", 587)
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    email_to: str = os.getenv("EMAIL_TO", "prometheus.mr.cy@gmail.com")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    nasdaq100_symbol: str = os.getenv("NASDAQ100_SYMBOL", "^NDX")
    sp500_symbol: str = os.getenv("SP500_SYMBOL", "^GSPC")
    korea_symbols: tuple[str, ...] = tuple(_csv_env("KOREA_INDEX_SYMBOLS", "^KS11,^KQ11"))
    japan_symbols: tuple[str, ...] = tuple(_csv_env("JAPAN_INDEX_SYMBOLS", "^N225"))
    hk_symbols: tuple[str, ...] = tuple(_csv_env("HK_INDEX_SYMBOLS", "HSTECH.HK,159699.SZ"))
    commodity_symbols: tuple[str, ...] = tuple(_csv_env("COMMODITY_SYMBOLS", "GC=F,SI=F,PL=F,HG=F,CL=F,BZ=F"))
    bond_symbols: tuple[str, ...] = tuple(_csv_env("BOND_SYMBOLS", "^IRX,^FVX,^TNX,^TYX"))
    news_rss_urls: tuple[str, ...] = tuple(_csv_env("NEWS_RSS_URLS", ""))
    trump_source_url: str = os.getenv("TRUMP_SOURCE_URL", "")

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    def all_market_symbols(self) -> Iterable[str]:
        yield self.nasdaq100_symbol
        yield self.sp500_symbol
        yield from self.korea_symbols
        yield from self.japan_symbols
        yield from self.hk_symbols
        yield from self.commodity_symbols
        yield from self.bond_symbols


settings = Settings()
