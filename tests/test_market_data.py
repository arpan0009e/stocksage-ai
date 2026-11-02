
from datetime import datetime, timezone

import pandas as pd
import pytest

from stocksage.market_data import (
    MarketDataError,
    clean_historical_prices,
)


def test_sorts_dates_and_removes_duplicate_timestamps():
    dates = pd.to_datetime(
        ["2026-10-28", "2026-10-27", "2026-10-28"]
    )
    prices = pd.DataFrame(
        {"Close": [120.0, 100.0, 125.0]},
        index=dates,
    )

    result = clean_historical_prices(
        prices,
        "RELIANCE.NS",
        as_of=datetime(2026, 10, 30, tzinfo=timezone.utc),
    )

    assert result.index.is_monotonic_increasing
    assert not result.index.has_duplicates
    assert result["Close"].tolist() == [100.0, 125.0]
    assert any("Duplicate" in w for w in result.attrs["warnings"])


def test_removes_missing_and_nonpositive_closes():
    prices = pd.DataFrame(
        {"Close": [100.0, float("nan"), 0.0, 110.0]},
        index=pd.date_range("2026-10-26", periods=4),
    )

    result = clean_historical_prices(
        prices,
        "RELIANCE.NS",
        as_of=datetime(2026, 10, 30, tzinfo=timezone.utc),
    )

    assert result["Close"].tolist() == [100.0, 110.0]
    assert any("2 rows" in w for w in result.attrs["warnings"])


def test_rejects_data_without_close_column():
    prices = pd.DataFrame({"Open": [100.0]})

    with pytest.raises(MarketDataError, match="Close"):
        clean_historical_prices(prices, "RELIANCE.NS")


def test_reports_potentially_stale_prices():
    prices = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.to_datetime(["2026-10-01"]),
    )

    result = clean_historical_prices(
        prices,
        "RELIANCE.NS",
        max_staleness_days=7,
        as_of=datetime(2026, 10, 20, tzinfo=timezone.utc),
    )

    assert result.attrs["latest_price_age_days"] == 19
    assert any("calendar days old" in w for w in result.attrs["warnings"])


def test_rejects_all_invalid_closes():
    prices = pd.DataFrame({"Close": [0.0, float("nan")]})

    with pytest.raises(MarketDataError, match="No valid closing"):
        clean_historical_prices(prices, "RELIANCE.NS")


def test_rejects_negative_staleness_threshold():
    prices = pd.DataFrame({"Close": [100.0]})

    with pytest.raises(ValueError, match="cannot be negative"):
        clean_historical_prices(
            prices,
            "RELIANCE.NS",
            max_staleness_days=-1,
        )
