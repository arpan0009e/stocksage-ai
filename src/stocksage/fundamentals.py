
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from pydantic import BaseModel, Field


class FundamentalsResult(BaseModel):
    """Structured output from the fundamentals research tool."""

    symbol: str
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reporting_period: str | None = None
    metrics: dict[str, float | None] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


def _latest_value(
    statement: pd.DataFrame,
    row_names: tuple[str, ...],
) -> tuple[float | None, str | None]:
    """Return a metric from the latest available statement period."""
    if statement is None or statement.empty:
        return None, None

    available_rows = {str(row).strip().casefold(): row for row in statement.index}

    for name in row_names:
        actual_row = available_rows.get(name.casefold())
        if actual_row is None:
            continue

        values = statement.loc[actual_row].dropna()
        if values.empty:
            continue

        # Statement columns normally represent reporting periods.
        period = max(values.index)
        value = pd.to_numeric(
            pd.Series([values.loc[period]]), errors="coerce"
        ).iloc[0]

        if pd.isna(value):
            continue

        return float(value), str(period)

    return None, None


def analyze_fundamentals(symbol: str) -> FundamentalsResult:
    """Retrieve available fundamentals; missing data remains explicitly missing."""
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Stock symbol cannot be empty.")

    if not all(c.isalnum() or c in ".&-" for c in symbol):
        raise ValueError("Symbol contains unsupported characters.")

    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    warnings: list[str] = []

    try:
        ticker = yf.Ticker(symbol)
        income_stmt = ticker.income_stmt
    except Exception as exc:
        income_stmt = pd.DataFrame()
        warnings.append(
            f"Could not retrieve income statement: {type(exc).__name__}"
        )

    try:
        balance_sheet = ticker.balance_sheet
    except Exception as exc:
        balance_sheet = pd.DataFrame()
        warnings.append(
            f"Could not retrieve balance sheet: {type(exc).__name__}"
        )

    metric_rows = {
        "revenue": (income_stmt, ("Total Revenue", "Operating Revenue")),
        "operating_income": (income_stmt, ("Operating Income",)),
        "net_income": (income_stmt, ("Net Income", "Net Income Common Stockholders")),
        "total_assets": (balance_sheet, ("Total Assets",)),
        "total_debt": (balance_sheet, ("Total Debt",)),
        "cash_and_equivalents": (
            balance_sheet,
            ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
        ),
        "current_liabilities": (balance_sheet, ("Current Liabilities",)),
    }

    metrics: dict[str, float | None] = {}
    periods: list[str] = []

    for metric_name, (statement, row_names) in metric_rows.items():
        value, period = _latest_value(statement, row_names)
        metrics[metric_name] = value

        if value is None:
            warnings.append(
                f"{metric_name} is unavailable from the retrieved statements."
            )
        elif period is not None:
            periods.append(period)

    revenue = metrics["revenue"]
    net_income = metrics["net_income"]

    metrics["net_profit_margin"] = (
        net_income / revenue
        if revenue is not None and revenue > 0 and net_income is not None
        else None
    )

    if metrics["net_profit_margin"] is None:
        warnings.append(
            "Net profit margin could not be calculated from available values."
        )

    # Statement periods can differ; report them rather than implying
    # every metric comes from an identical reporting period.
    reporting_period = (
        max(periods) if periods else None
    )

    return FundamentalsResult(
        symbol=symbol,
        reporting_period=reporting_period,
        metrics=metrics,
        warnings=warnings,
        sources=["Yahoo Finance via yfinance; company statement data"],
    )
