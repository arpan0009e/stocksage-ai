
import math

import pandas as pd
import pytest

from stocksage.market_metrics import calculate_market_metrics


def test_calculates_return_from_fixed_prices():
    prices = pd.DataFrame({"Close": [100.0, 110.0, 99.0]})

    result = calculate_market_metrics(prices)

    assert result["observations"] == 3
    assert result["latest_close"] == pytest.approx(99.0)
    assert result["period_return"] == pytest.approx(-0.01)


def test_calculates_annualized_volatility():
    prices = pd.DataFrame({"Close": [100.0, 110.0, 99.0]})

    result = calculate_market_metrics(prices)

    daily_returns = pd.Series([0.10, -0.10])
    expected = daily_returns.std(ddof=1) * math.sqrt(252)

    assert result["annualized_volatility"] == pytest.approx(expected)


def test_calculates_moving_averages():
    prices = pd.DataFrame({"Close": list(range(1, 51))})

    result = calculate_market_metrics(prices)

    assert result["sma_20"] == pytest.approx(40.5)
    assert result["sma_50"] == pytest.approx(25.5)


def test_short_history_returns_none_for_unavailable_metrics():
    prices = pd.DataFrame({"Close": [100.0]})

    result = calculate_market_metrics(prices)

    assert result["period_return"] is None
    assert result["annualized_volatility"] is None
    assert result["sma_20"] is None
    assert result["sma_50"] is None


def test_rejects_missing_close_column():
    prices = pd.DataFrame({"Open": [100.0]})

    with pytest.raises(ValueError, match="Missing required column"):
        calculate_market_metrics(prices)


def test_rejects_nonpositive_prices():
    prices = pd.DataFrame({"Close": [100.0, 0.0]})

    with pytest.raises(ValueError, match="must be positive"):
        calculate_market_metrics(prices)


def test_rejects_empty_valid_price_data():
    prices = pd.DataFrame({"Close": [float("nan")]})

    with pytest.raises(ValueError, match="No valid closing prices"):
        calculate_market_metrics(prices)
