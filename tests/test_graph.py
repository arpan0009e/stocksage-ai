
from unittest.mock import patch

import pandas as pd

from stocksage.fundamentals import FundamentalsResult
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


def test_invalid_request_skips_agents():
    result = research_graph.invoke(
        {"symbol": "INVALID/SYMBOL", "period": "6mo"}
    )

    assert result["report"]["status"] == "failed"
    assert result["report"]["errors"]
    assert "validate_request" in result["trace"]
    assert "market_agent" not in result["trace"]
    assert "fundamentals_agent" not in result["trace"]


@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_successful_market_and_fundamentals(
    mock_fetch, mock_fundamentals_agent
):
    dates = pd.date_range("2026-01-01", periods=60, freq="B")
    prices = pd.DataFrame(
        {"Close": [100.0 + i for i in range(60)]},
        index=dates,
    )
    prices.attrs["warnings"] = []

    mock_fetch.return_value = prices
    mock_fundamentals_agent.return_value = mock_fundamentals()

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "complete"
    assert result["report"]["symbol"] == "RELIANCE"
    assert result["report"]["errors"] == []
    assert result["metrics"]["observations"] == 60
    assert result["metrics"]["latest_close"] == 159.0
    assert result["fundamentals"]["metrics"]["revenue"] == 1000.0
    assert "market_agent" in result["trace"]
    assert "fundamentals_agent" in result["trace"]

    mock_fetch.assert_called_once_with("RELIANCE", "6mo")
    mock_fundamentals_agent.assert_called_once_with("RELIANCE")


@patch(
    "stocksage.graph.fetch_historical_prices",
    side_effect=Exception("Simulated data-source outage"),
)
def test_market_failure_returns_structured_report(mock_fetch):
    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "failed"
    assert result["report"]["errors"]
    assert "Simulated data-source outage" in str(
        result["report"]["errors"]
    )
    assert "build_failure_report" in result["trace"]
    assert "fundamentals_agent" not in result["trace"]

    mock_fetch.assert_called_once_with("RELIANCE", "6mo")


@patch("stocksage.graph.analyze_fundamentals")
@patch("stocksage.graph.fetch_historical_prices")
def test_short_history_produces_partial_report(
    mock_fetch, mock_fundamentals_agent
):
    prices = pd.DataFrame(
        {"Close": [100.0, 101.0]},
        index=pd.date_range("2026-01-01", periods=2, freq="B"),
    )
    prices.attrs["warnings"] = []

    mock_fetch.return_value = prices
    mock_fundamentals_agent.return_value = mock_fundamentals("TCS")

    result = research_graph.invoke(
        {"symbol": "TCS", "period": "1mo"}
    )

    assert result["report"]["status"] == "partial"
    assert result["report"]["errors"] == []
    assert result["metrics"]["sma_20"] is None
    assert result["metrics"]["sma_50"] is None
    assert result["report"]["warnings"]

    mock_fetch.assert_called_once_with("TCS", "1mo")
    mock_fundamentals_agent.assert_called_once_with("TCS")


@patch(
    "stocksage.graph.analyze_fundamentals",
    side_effect=RuntimeError("Fundamentals provider unavailable"),
)
@patch("stocksage.graph.fetch_historical_prices")
def test_fundamentals_failure_preserves_market_results(
    mock_fetch, mock_fundamentals_agent
):
    dates = pd.date_range("2026-01-01", periods=60, freq="B")
    prices = pd.DataFrame(
        {"Close": [100.0 + i for i in range(60)]},
        index=dates,
    )
    prices.attrs["warnings"] = []
    mock_fetch.return_value = prices

    result = research_graph.invoke(
        {"symbol": "RELIANCE", "period": "6mo"}
    )

    assert result["report"]["status"] == "partial"
    assert result["report"]["errors"] == []
    assert result["metrics"]["latest_close"] == 159.0
    assert result["fundamentals"] == {}
    assert any(
        "Fundamentals analysis was unavailable" in warning
        for warning in result["report"]["warnings"]
    )
    assert "fundamentals_agent" in result["trace"]

    mock_fetch.assert_called_once_with("RELIANCE", "6mo")
    mock_fundamentals_agent.assert_called_once_with("RELIANCE")
