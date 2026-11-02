
import numpy as np
import pandas as pd


def calculate_market_metrics(
    prices: pd.DataFrame,
    price_column: str = "Close",
) -> dict[str, float | int | None]:
    """Calculate deterministic metrics from historical closing prices."""

    if price_column not in prices.columns:
        raise ValueError(f"Missing required column: {price_column}")

    close = pd.to_numeric(prices[price_column], errors="coerce")
    close = close.replace([np.inf, -np.inf], np.nan)

    if (close.dropna() <= 0).any():
        raise ValueError("Closing prices must be positive.")

    close = close.dropna()

    if close.empty:
        raise ValueError("No valid closing prices available.")

    daily_returns = close.pct_change().dropna()

    period_return = (
        float(close.iloc[-1] / close.iloc[0] - 1)
        if len(close) >= 2
        else None
    )

    volatility = (
        float(daily_returns.std(ddof=1) * np.sqrt(252))
        if len(daily_returns) >= 2
        else None
    )

    return {
        "observations": int(len(close)),
        "latest_close": float(close.iloc[-1]),
        "period_return": period_return,
        "annualized_volatility": volatility,
        "sma_20": (
            float(close.tail(20).mean())
            if len(close) >= 20
            else None
        ),
        "sma_50": (
            float(close.tail(50).mean())
            if len(close) >= 50
            else None
        ),
    }
