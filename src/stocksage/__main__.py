
import argparse
import json

from stocksage.graph import research_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="StockSage AI — NSE market research MVP"
    )
    parser.add_argument(
        "symbol",
        help="NSE stock symbol, for example RELIANCE or TCS",
    )
    parser.add_argument(
        "--period",
        default="6mo",
        choices=["1mo", "3mo", "6mo", "1y", "2y"],
        help="Historical data period (default: 6mo)",
    )
    args = parser.parse_args()

    result = research_graph.invoke(
        {"symbol": args.symbol, "period": args.period}
    )

  
    
    print(
        json.dumps(
            {
                "report": result.get("report"),
                "metrics": result.get("metrics"),
                "fundamentals": result.get("fundamentals"),
                "news": result.get("news"),
                "trace": result.get("trace"),
            },
            indent=2,
            default=str,
        )
    )




if __name__ == "__main__":
    main()
