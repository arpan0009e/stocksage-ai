
from unittest.mock import patch

import pandas as pd

from stocksage.fundamentals import FundamentalsResult
from stocksage.news_agent import NewsArticle, NewsResult
from stocksage.graph import research_graph


def mock_fundamentals(symbol="RELIANCE"):
    return FundamentalsResult(
        symbol=f"{symbol}.NS",
        metrics={
            "revenue": 1000.0,
            "net_income": 120.0,
            "net_profit_margin": 0.12,
        },
        warnings=[],
        sources=["Mock fundamentals source"],
    )


def mock_news(symbol="RELIANCE"):
    return NewsResult(
        symbol=symbol,
        articles=[
            NewsArticle(
                title="Company announces business update",
                url="https://example.com/article-1",
                publisher="Example News",
            )
        ],
        warnings=[],
        sources=["Mock news source"],
    )


def mock_prices(count=60):
    dates = pd.date_range("2026-01-01", periods=count, freq="B")
    prices = pd.DataFrame(
        {"Close": [100.0 + i for i in range(count)]},
        index=dates,
    )
    prices.attrs["warnings"] = []
    return prices


@patch("stocksage.graph.fetch_company_news")
@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_successful_full_research(
    mock_fetch,
    mock_fundamentals_agent,
    mock_news_agent,
):
    mock_fetch.return_value = mock_prices()
    mock_fundamentals_agent.return_value = mock_fundamentals()
    mock_news_agent.return_value = mock_news()

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "complete"
    assert result["report"]["errors"] == []
    assert result["metrics"]["observations"] == 60
    assert result["fundamentals"]["metrics"]["revenue"] == 1000.0
    assert len(result["news"]["articles"]) == 1
    assert (
        result["news"]["articles"][0]["url"]
        == "https://example.com/article-1"
    )

    assert result["trace"] == [
        "validate_request",
        "market_agent",
        "fundamentals_agent",
        "news_agent",
        "build_success_report",
    ]

    mock_fetch.assert_called_once_with("RELIANCE", "6mo")
    mock_fundamentals_agent.assert_called_once_with("RELIANCE")
    mock_news_agent.assert_called_once_with(
        "RELIANCE", max_articles=10
    )


def test_invalid_request_skips_agents():
    result = research_graph.invoke(
        {"symbol": "INVALID/SYMBOL", "period": "6mo"}
    )

    assert result["report"]["status"] == "failed"
    assert result["report"]["errors"]
    assert "market_agent" not in result["trace"]
    assert "fundamentals_agent" not in result["trace"]
    assert "news_agent" not in result["trace"]


@patch("stocksage.graph.fetch_historical_prices")
def test_market_failure_returns_structured_report(mock_fetch):
    mock_fetch.side_effect = Exception("Simulated data-source outage")

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "failed"
    assert result["report"]["errors"]
    assert "news_agent" not in result["trace"]


@patch("stocksage.graph.fetch_company_news")
@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_fundamentals_failure_preserves_other_results(
    mock_fetch,
    mock_fundamentals_agent,
    mock_news_agent,
):
    mock_fetch.return_value = mock_prices()
    mock_fundamentals_agent.side_effect = RuntimeError(
        "Fundamentals provider unavailable"
    )
    mock_news_agent.return_value = mock_news()

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "partial"
    assert result["metrics"]["latest_close"] == 159.0
    assert result["fundamentals"] == {}
    assert len(result["news"]["articles"]) == 1
    assert any(
        "Fundamentals analysis was unavailable" in warning
        for warning in result["report"]["warnings"]
    )


@patch("stocksage.graph.fetch_company_news")
@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_news_failure_preserves_market_and_fundamentals(
    mock_fetch,
    mock_fundamentals_agent,
    mock_news_agent,
):
    mock_fetch.return_value = mock_prices()
    mock_fundamentals_agent.return_value = mock_fundamentals()
    mock_news_agent.side_effect = RuntimeError("News provider unavailable")

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "partial"
    assert result["metrics"]["latest_close"] == 159.0
    assert result["fundamentals"]["metrics"]["revenue"] == 1000.0
    assert result["news"] == {}
    assert any(
        "News retrieval was unavailable" in warning
        or "Unexpected news-tool error" in warning
        for warning in result["report"]["warnings"]
    )


@patch("stocksage.graph.fetch_company_news")
@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_empty_news_result_is_partial_not_failed(
    mock_fetch,
    mock_fundamentals_agent,
    mock_news_agent,
):
    mock_fetch.return_value = mock_prices()
    mock_fundamentals_agent.return_value = mock_fundamentals()
    mock_news_agent.return_value = NewsResult(
        symbol="RELIANCE",
        articles=[],
        warnings=["No news articles were returned by the provider."],
        sources=["Mock news source"],
    )

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "partial"
    assert result["report"]["errors"] == []
    assert result["news"]["articles"] == []
    assert result["metrics"]["observations"] == 60


@patch("stocksage.graph.fetch_company_news")
@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_short_history_produces_partial_report(
    mock_fetch,
    mock_fundamentals_agent,
    mock_news_agent,
):
    mock_fetch.return_value = mock_prices(count=2)
    mock_fundamentals_agent.return_value = mock_fundamentals()
    mock_news_agent.return_value = mock_news()

    result = research_graph.invoke(
        {"symbol": "TCS", "period": "1mo"}
    )

    assert result["report"]["status"] == "partial"
    assert result["report"]["errors"] == []
    assert result["metrics"]["sma_20"] is None
    assert result["metrics"]["sma_50"] is None
    assert result["report"]["warnings"]
