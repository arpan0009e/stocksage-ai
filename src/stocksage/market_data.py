
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


class MarketDataError(Exception):
    """Raised when reliable market data cannot be retrieved."""


ALLOWED_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y"}


def clean_historical_prices(
    data: pd.DataFrame,
    symbol: str,
    max_staleness_days: int = 7,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """Validate and clean historical prices without making network calls."""

    if data.empty:
        raise MarketDataError("No historical price data returned.")

    if "Close" not in data.columns:
        raise MarketDataError("Response does not contain Close prices.")

    if max_staleness_days < 0:
        raise ValueError("max_staleness_days cannot be negative.")

    cleaned = data.copy()
    warnings: list[str] = []

    # Resolve duplicate timestamps deterministically: keep the last row.
    if cleaned.index.has_duplicates:
        warnings.append("Duplicate timestamps were removed.")
        cleaned = cleaned.loc[~cleaned.index.duplicated(keep="last")]

    cleaned = cleaned.sort_index()

    close = pd.to_numeric(cleaned["Close"], errors="coerce")
    invalid = close.isna() | (close <= 0)

    if invalid.any():
        warnings.append(
            f"{int(invalid.sum())} rows with missing or nonpositive "
            "closing prices were removed."
        )
        cleaned = cleaned.loc[~invalid].copy()

    if cleaned.empty:
        raise MarketDataError("No valid closing prices are available.")

    now = as_of or datetime.now(timezone.utc)
    latest_timestamp = pd.Timestamp(cleaned.index[-1])

    # Compare calendar dates rather than timestamp time zones.
    latest_date = latest_timestamp.date()
    current_date = now.date()
    age_days = (current_date - latest_date).days

    if age_days > max_staleness_days:
        warnings.append(
            f"Latest price is {age_days} calendar days old. "
            "Check for stale data or market holidays."
        )

    cleaned.index.name = "Date"
    cleaned.attrs["symbol"] = symbol
    cleaned.attrs["retrieved_at"] = now.isoformat()
    cleaned.attrs["warnings"] = warnings
    cleaned.attrs["latest_price_age_days"] = age_days

    return cleaned



def fetch_historical_prices(
    symbol: str,
    period: str = "6mo",
) -> pd.DataFrame:
    """Fetch and validate historical daily prices for an NSE-listed stock."""

    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Stock symbol cannot be empty.")

    if not all(c.isalnum() or c in ".&-" for c in symbol):
        raise ValueError("Symbol contains unsupported characters.")

    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    if period not in ALLOWED_PERIODS:
        raise ValueError(f"Unsupported period: {period}")

    try:
        data = yf.Ticker(symbol).history(
            period=period,
            interval="1d",
            auto_adjust=True,
        )
    except Exception as exc:
        raise MarketDataError(
            f"Failed to retrieve data for {symbol}: {exc}"
        ) from exc

    return clean_historical_prices(data, symbol)
