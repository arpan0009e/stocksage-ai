
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from stocksage.market_data import MarketDataError, fetch_historical_prices
from stocksage.market_metrics import calculate_market_metrics
from stocksage.schemas import ResearchReport, ResearchRequest


class ResearchState(TypedDict, total=False):
    # User input
    symbol: str
    period: str

    # Shared workflow data
    request: dict[str, Any]
    metrics: dict[str, Any]
    warnings: list[str]
    errors: list[str]
    sources: list[str]
    trace: list[str]

    # Final output
    report: dict[str, Any]


def validate_request(state: ResearchState) -> dict[str, Any]:
    """Validate raw user input before running financial tools."""
    trace = [*state.get("trace", []), "validate_request"]

    try:
        request = ResearchRequest(
            symbol=state.get("symbol", ""),
            period=state.get("period", "6mo"),
        )
        return {
            "request": request.model_dump(),
            "symbol": request.symbol,
            "period": request.period,
            "errors": [],
            "warnings": [],
            "trace": trace,
        }
    except (ValidationError, TypeError, ValueError) as exc:
        return {
            "errors": [f"Invalid research request: {exc}"],
            "trace": trace,
        }


def route_after_validation(state: ResearchState) -> str:
    """Route invalid requests directly to failure reporting."""
    return "failure" if state.get("errors") else "market"


def market_agent(state: ResearchState) -> dict[str, Any]:
    """Run deterministic market-data retrieval and analysis."""
    trace = [*state.get("trace", []), "market_agent"]
    symbol = state["symbol"]
    period = state["period"]

    try:
        prices = fetch_historical_prices(symbol, period)
        metrics = calculate_market_metrics(prices)

        warnings = list(prices.attrs.get("warnings", []))
        if metrics["sma_20"] is None:
            warnings.append("Insufficient observations for SMA-20.")
        if metrics["sma_50"] is None:
            warnings.append("Insufficient observations for SMA-50.")

        return {
            "metrics": metrics,
            "warnings": warnings,
            "sources": ["Yahoo Finance via yfinance"],
            "errors": [],
            "trace": trace,
        }
    except (MarketDataError, ValueError) as exc:
        return {
            "errors": [f"Market analysis failed: {exc}"],
            "trace": trace,
        }
    except Exception as exc:
        # Keep unexpected tool failures visible in the report.
        return {
            "errors": [
                f"Unexpected market-tool error: {type(exc).__name__}: {exc}"
            ],
            "trace": trace,
        }


def route_after_market(state: ResearchState) -> str:
    """Choose a success or failure path based on tool results."""
    return "failure" if state.get("errors") else "success"


def build_success_report(state: ResearchState) -> dict[str, Any]:
    """Create a validated report from the market-agent results."""
    trace = [*state.get("trace", []), "build_success_report"]
    warnings = state.get("warnings", [])

    report = ResearchReport(
        symbol=state["symbol"],
        status="partial" if warnings else "complete",
        summary="Market metrics calculated successfully.",
        warnings=warnings,
        sources=state.get("sources", []),
    )

    return {"report": report.model_dump(mode="json"), "trace": trace}


def build_failure_report(state: ResearchState) -> dict[str, Any]:
    """Return a structured failure instead of crashing the workflow."""
    trace = [*state.get("trace", []), "build_failure_report"]
    errors = state.get("errors", ["Unknown workflow failure."])

    report = ResearchReport(
        symbol=state.get("symbol", "UNKNOWN"),
        status="failed",
        summary="Market research could not be completed.",
        warnings=state.get("warnings", []),
        errors=errors,
        sources=state.get("sources", []),
    )

    return {"report": report.model_dump(mode="json"), "trace": trace}


def build_graph():
    """Build and compile the StockSage AI market-research graph."""
    builder = StateGraph(ResearchState)

    builder.add_node("validate_request", validate_request)
    builder.add_node("market_agent", market_agent)
    builder.add_node("build_success_report", build_success_report)
    builder.add_node("build_failure_report", build_failure_report)

    builder.add_edge(START, "validate_request")
    builder.add_conditional_edges(
        "validate_request",
        route_after_validation,
        {
            "market": "market_agent",
            "failure": "build_failure_report",
        },
    )
    builder.add_conditional_edges(
        "market_agent",
        route_after_market,
        {
            "success": "build_success_report",
            "failure": "build_failure_report",
        },
    )
    builder.add_edge("build_success_report", END)
    builder.add_edge("build_failure_report", END)

    return builder.compile()


research_graph = build_graph()
