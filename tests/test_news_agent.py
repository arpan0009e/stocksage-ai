
from unittest.mock import MagicMock, patch

import pytest

from stocksage.news_agent import (
    NewsDataError,
    fetch_company_news,
)


SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>Reliance announces business update</title>
      <link>https://example.com/article-1</link>
      <pubDate>Wed, 04 Nov 2026 10:00:00 GMT</pubDate>
      <source>Example News</source>
      <description>Company business update.</description>
    </item>
    <item>
      <title>Reliance announces business update duplicate</title>
      <link>https://example.com/article-1</link>
      <pubDate>Wed, 04 Nov 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Reliance shares in focus</title>
      <link>https://example.com/article-2</link>
      <description>Market-related article.</description>
    </item>
  </channel>
</rss>
"""


@patch("stocksage.news_agent.urlopen")
def test_fetch_company_news_parses_and_deduplicates(mock_urlopen):
    response = MagicMock()
    response.read.return_value = SAMPLE_RSS

    mock_urlopen.return_value.__enter__.return_value = response

    result = fetch_company_news("RELIANCE")

    assert result.symbol == "RELIANCE"
    assert len(result.articles) == 2

    first_article = result.articles[0]

    assert first_article.title == "Reliance announces business update"
    assert first_article.url == "https://example.com/article-1"
    assert first_article.published_at is not None
    assert first_article.publisher == "Example News"

    assert result.articles[1].published_at is None
    assert any("Publication date unavailable" in warning
               for warning in result.warnings)

    assert result.sources == ["Google News RSS"]
    mock_urlopen.assert_called_once()


@patch("stocksage.news_agent.urlopen")
def test_fetch_company_news_respects_article_limit(mock_urlopen):
    response = MagicMock()
    response.read.return_value = SAMPLE_RSS

    mock_urlopen.return_value.__enter__.return_value = response

    result = fetch_company_news("RELIANCE", max_articles=1)

    assert len(result.articles) == 1


@patch("stocksage.news_agent.urlopen")
def test_empty_feed_returns_warning(mock_urlopen):
    empty_rss = b"""<?xml version="1.0"?>
    <rss version="2.0">
      <channel><title>Google News</title></channel>
    </rss>
    """

    response = MagicMock()
    response.read.return_value = empty_rss

    mock_urlopen.return_value.__enter__.return_value = response

    result = fetch_company_news("TCS")

    assert result.articles == []
    assert any("No news articles" in warning
               for warning in result.warnings)


@patch(
    "stocksage.news_agent.urlopen",
    side_effect=TimeoutError("Simulated timeout"),
)
def test_news_provider_timeout_raises_news_data_error(mock_urlopen):
    with pytest.raises(NewsDataError, match="News retrieval failed"):
        fetch_company_news("RELIANCE")


def test_invalid_symbol_is_rejected():
    with pytest.raises(ValueError, match="unsupported characters"):
        fetch_company_news("RELIANCE/INVALID")


def test_invalid_article_limit_is_rejected():
    with pytest.raises(ValueError, match="max_articles"):
        fetch_company_news("RELIANCE", max_articles=100)
