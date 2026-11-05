
from calendar import timegm
from datetime import datetime, timezone
from html import unescape
import re
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import feedparser
from pydantic import BaseModel, Field


class NewsDataError(Exception):
    """Raised when news retrieval fails."""


class NewsArticle(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    published_at: datetime | None = None
    summary: str | None = None


class NewsResult(BaseModel):
    symbol: str
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    articles: list[NewsArticle] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None

    # RSS summaries can contain HTML markup.
    text = re.sub(r"<[^>]+>", " ", value)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    return text or None


def _parse_published_date(entry: Any) -> datetime | None:
    parsed_date = entry.get("published_parsed")

    if parsed_date is None:
        parsed_date = entry.get("updated_parsed")

    if parsed_date is None:
        return None

    try:
        timestamp = timegm(parsed_date)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def fetch_company_news(
    symbol: str,
    max_articles: int = 10,
    timeout: int = 10,
) -> NewsResult:
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Stock symbol cannot be empty.")

    if not all(c.isalnum() or c in ".&-" for c in symbol):
        raise ValueError("Symbol contains unsupported characters.")

    if not 1 <= max_articles <= 50:
        raise ValueError("max_articles must be between 1 and 50.")

    if timeout <= 0:
        raise ValueError("timeout must be positive.")

    search_symbol = symbol.removesuffix(".NS")
    query = f"{search_symbol} NSE India company stock"

    feed_url = (
        "https://news.google.com/rss/search?"
        + urlencode(
            {
                "q": query,
                "hl": "en-IN",
                "gl": "IN",
                "ceid": "IN:en",
            }
        )
    )

    request = Request(
        feed_url,
        headers={"User-Agent": "StockSageAI/0.1"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            feed_content = response.read()

        feed = feedparser.parse(feed_content)

    except (URLError, TimeoutError, OSError) as exc:
        raise NewsDataError(
            f"News retrieval failed: {type(exc).__name__}"
        ) from exc

    if getattr(feed, "bozo", False) and not feed.entries:
        raise NewsDataError("The news provider returned an invalid RSS feed.")

    articles: list[NewsArticle] = []
    warnings: list[str] = []
    seen_urls: set[str] = set()

    for entry in feed.entries:
        title = _clean_text(entry.get("title"))
        article_url = entry.get("link")

        if not title or not article_url:
            continue

        dedupe_url = article_url.split("#", 1)[0].strip().lower()

        if dedupe_url in seen_urls:
            continue

        seen_urls.add(dedupe_url)

        source_info = entry.get("source") or {}
        publisher = _clean_text(source_info.get("title"))

        published_at = _parse_published_date(entry)

        if published_at is None:
            warnings.append(
                f"Publication date unavailable for article: {title}"
            )

        articles.append(
            NewsArticle(
                title=title,
                url=article_url,
                publisher=publisher,
                published_at=published_at,
                summary=_clean_text(entry.get("summary")),
            )
        )

        if len(articles) >= max_articles:
            break

    if not articles:
        warnings.append("No news articles were returned by the provider.")

    return NewsResult(
        symbol=search_symbol,
        articles=articles,
        warnings=warnings,
        sources=["Google News RSS"],
    )
