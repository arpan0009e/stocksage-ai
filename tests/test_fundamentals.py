
from unittest.mock import patch

import pandas as pd
import pytest

from stocksage.fundamentals import (
    FundamentalsResult,
    analyze_fundamentals,
)


def fake_ticker():
    ticker = type("FakeTicker", (), {})()

    ticker.income_stmt = pd.DataFrame(
        {
            pd.Timestamp("2025-03-31"): [1000.0, 200.0, 120.0],
        },
        index=["Total Revenue", "Operating Income", "Net Income"],
    )

    ticker.balance_sheet = pd.DataFrame(
        {
            pd.Timestamp("2025-03-31"): [
                2000.0, 300.0, 150.0, 250.0
            ],
        },
        index=[
            "Total Assets",
            "Total Debt",
            "Cash And Cash Equivalents",
            "Current Liabilities",
        ],
    )

    return ticker


@patch("stocksage.fundamentals.yf.Ticker")
def test_calculates_available_fundamentals(mock_ticker):
    mock_ticker.return_value = fake_ticker()

    result = analyze_fundamentals("RELIANCE")

    assert isinstance(result, FundamentalsResult)
    assert result.symbol == "RELIANCE.NS"
    assert result.metrics["revenue"] == 1000.0
    assert result.metrics["net_income"] == 120.0
    assert result.metrics["total_assets"] == 2000.0
    assert result.metrics["net_profit_margin"] == pytest.approx(0.12)
    assert result.warnings == []


@patch("stocksage.fundamentals.yf.Ticker")
def test_missing_metrics_are_not_invented(mock_ticker):
    ticker = type("FakeTicker", (), {})()
    ticker.income_stmt = pd.DataFrame()
    ticker.balance_sheet = pd.DataFrame()
    mock_ticker.return_value = ticker

    result = analyze_fundamentals("TCS")

    assert result.metrics["revenue"] is None
    assert result.metrics["total_assets"] is None
    assert result.metrics["net_profit_margin"] is None
    assert result.warnings


@patch("stocksage.fundamentals.yf.Ticker")
def test_statement_errors_are_reported(mock_ticker):
    ticker = type("FakeTicker", (), {})()

    def failing_statement():
        raise RuntimeError("Simulated provider failure")

    type(ticker).income_stmt = property(
        lambda self: failing_statement()
    )
    ticker.balance_sheet = pd.DataFrame()
    mock_ticker.return_value = ticker

    result = analyze_fundamentals("TCS")

    assert result.metrics["revenue"] is None
    assert any(
        "Could not retrieve income statement" in warning
        for warning in result.warnings
    )


def test_rejects_invalid_symbol():
    with pytest.raises(ValueError, match="unsupported characters"):
        analyze_fundamentals("RELIANCE/INVALID")
