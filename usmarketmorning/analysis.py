from __future__ import annotations

import json
from collections import Counter

from openai import OpenAI

from .config import settings
from .models import MarketMove, NewsItem, StockMove


def format_pct(value: float | None) -> str:
    if value is None:
        return "暂无数据"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def direction(value: float | None) -> str:
    if value is None:
        return "暂无报价"
    if value > 0:
        return "上涨"
    if value < 0:
        return "下跌"
    return "持平"


def infer_market_reason(move: MarketMove, facts: list[NewsItem]) -> str:
    titles = "；".join(item.title for item in facts[:18])
    category_counts = Counter(item.category for item in facts)
    macro = category_counts.most_common(2)
    leading = "、".join(name for name, _ in macro) or "市场消息"
    move_dir = direction(move.change_pct)

    if "美债" in move.category:
        return f"{move_dir}主要参考利率/宏观新闻脉络；过去24小时相关主题集中在{leading}。收益率上行通常压制估值，下行通常利好成长股。"
    if any(word in move.name for word in ["黄金", "白银", "铂", "铜"]):
        return f"{move_dir}与避险、美元和实际利率预期有关；新闻面主要线索为{leading}。"
    if "原油" in move.name:
        return f"{move_dir}通常受供需、OPEC、库存和地缘风险影响；过去24小时新闻线索偏向{leading}。"
    if any(word in move.name for word in ["纳斯达克", "恒生科技"]):
        return f"{move_dir}更多受科技/AI、半导体、利率预期和风险偏好影响；相关新闻线索包括{titles[:90]}。"
    return f"{move_dir}反映本地市场风险偏好与全球宏观联动；过去24小时新闻主题集中在{leading}。"


def infer_stock_reason(stock: StockMove, facts: list[NewsItem]) -> str:
    text = " ".join(item.title.lower() for item in facts)
    company = stock.name.lower()
    symbol = stock.symbol.lower()
    related = [item.title for item in facts if symbol in item.title.lower() or company[:10] in item.title.lower()]
    if related:
        return f"相关新闻：{related[0][:100]}"
    if any(word in text for word in ["ai", "nvidia", "semiconductor", "chip"]):
        return "受科技/AI与半导体主线情绪影响。"
    if any(word in text for word in ["yield", "fed", "rate", "inflation"]):
        return "受利率与估值环境变化影响，成长/周期股弹性可能被放大。"
    return "暂无明确公司级新闻，可能来自板块轮动、财报预期或技术性交易。"


def _field(item: NewsItem | dict, name: str) -> str:
    if isinstance(item, dict):
        return str(item.get(name, "") or "")
    return str(getattr(item, name, "") or "")


def summarize_trump_comments(facts: list[NewsItem] | list[dict]) -> str:
    related = [
        item
        for item in facts
        if _field(item, "category") == "特朗普言论"
        or "trump" in _field(item, "title").lower()
        or "truth social" in _field(item, "title").lower()
    ]
    if not related:
        return "过去24小时公开新闻源中没有抓取到明确的特朗普新发言。若需要更完整覆盖，可在环境变量 TRUMP_SOURCE_URL 中配置稳定的 X 或 Truth Social RSS 源。"

    titles = [_field(item, "title") for item in related[:8]]
    text = " ".join(titles).lower()
    themes: list[str] = []
    if any(word in text for word in ["fed", "federal reserve", "powell", "rate", "inflation"]):
        themes.append("美联储、利率或通胀")
    if any(word in text for word in ["tariff", "trade", "china", "import", "export"]):
        themes.append("关税与贸易政策")
    if any(word in text for word in ["oil", "energy", "iran", "middle east", "war", "ceasefire"]):
        themes.append("能源与地缘风险")
    if any(word in text for word in ["ai", "chip", "semiconductor", "tech", "nvidia"]):
        themes.append("科技与半导体")
    if not themes:
        themes.append("美国政策与市场预期")

    joined_titles = "；".join(titles[:3])
    return (
        f"过去24小时抓取到的特朗普相关消息主要围绕{'、'.join(themes)}。"
        f"核心线索包括：{joined_titles}。"
        "这些表态或相关政治动向通常会通过利率预期、贸易风险、能源价格和风险偏好传导到股市。"
    )


def heuristic_analysis(
    market_moves: list[MarketMove],
    facts: list[NewsItem],
    movers: list[StockMove],
) -> tuple[str, list[str]]:
    category_counts = Counter(item.category for item in facts)
    fact_line = "、".join(f"{name}{count}条" for name, count in category_counts.most_common())
    strongest = sorted(
        [move for move in market_moves if move.change_pct is not None],
        key=lambda item: abs(item.change_pct or 0),
        reverse=True,
    )[:5]
    market_line = "；".join(f"{item.name}{format_pct(item.change_pct)}" for item in strongest)
    analysis = (
        f"过去24小时的事实线索主要集中在：{fact_line or '暂无足够新闻'}。"
        f"从资产表现看，波动较明显的品类包括：{market_line or '暂无足够行情'}。"
        "若美债收益率上行同时科技指数承压，通常说明估值折现压力上升；若黄金与原油同步走强，需重点观察地缘与通胀预期；"
        "若纳斯达克100或恒生科技跑赢，则市场可能更偏好AI、半导体与高成长资产。"
    )
    notes = []
    for stock in movers[:12]:
        notes.append(f"{stock.index} {stock.name}({stock.symbol}) {format_pct(stock.change_pct)}：{stock.reason}")
    return analysis, notes


def ai_analysis(
    market_moves: list[MarketMove],
    facts: list[NewsItem],
    movers: list[StockMove],
) -> tuple[str, list[str]] | None:
    if not settings.openai_api_key:
        return None
    client = OpenAI(api_key=settings.openai_api_key)
    payload = {
        "markets": [item.__dict__ for item in market_moves],
        "facts": [item.__dict__ for item in facts[:30]],
        "movers": [item.__dict__ for item in movers[:40]],
    }
    prompt = (
        "你是严谨的中文美股晨报分析师。根据 JSON 数据写两部分：\n"
        "1. 分析总结：逐一解释每个资产品类的涨跌原因，必须把事实新闻与行情联系起来，避免编造未给出的事实。\n"
        "2. 大幅波动个股：挑出最值得关注的个股，解释可能原因，并标注若只是推断。\n"
        "输出 JSON，字段为 analysis (string) 和 stock_notes (string array)。"
    )
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)[:45000]},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return parsed.get("analysis", ""), parsed.get("stock_notes", [])
    except Exception:
        return None
