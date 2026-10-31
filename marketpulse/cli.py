"""Command-line interface for MarketPulse India."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from marketpulse.backtest import run_backtest
from marketpulse.engine import MarketSnapshot, evaluate_snapshot

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "sample_market.csv"
DEFAULT_BACKTEST_DATA = ROOT / "data" / "sample_backtest.csv"


def _optional_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def _optional_int(value: str) -> int | None:
    return int(value) if value.strip() else None


def load_snapshot(path: Path, target_date: date) -> MarketSnapshot:
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if date.fromisoformat(row["date"]) == target_date:
                return MarketSnapshot(
                    date=target_date,
                    gift_nifty_change_pct=_optional_float(row["gift_nifty_change_pct"]),
                    india_vix_previous=_optional_float(row["india_vix_previous"]),
                    india_vix_current=_optional_float(row["india_vix_current"]),
                    advances=_optional_int(row["advances"]),
                    declines=_optional_int(row["declines"]),
                    nifty_previous_close=_optional_float(row["nifty_previous_close"]),
                    nifty_open=_optional_float(row["nifty_open"]),
                )
    raise ValueError(f"No market snapshot found for {target_date} in {path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="marketpulse", description="Explainable Indian market-opening signal report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    report_parser = subparsers.add_parser("report", help="Generate a report for a date in the input CSV")
    report_parser.add_argument("--date", required=True, type=date.fromisoformat, help="Trading date in YYYY-MM-DD format")
    report_parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help=f"Input CSV (default: {DEFAULT_DATA})")
    backtest_parser = subparsers.add_parser("backtest", help="Backtest timestamped historical snapshots against later prices")
    backtest_parser.add_argument("--data", type=Path, default=DEFAULT_BACKTEST_DATA, help=f"Timestamped backtest CSV (default: {DEFAULT_BACKTEST_DATA})")
    backtest_parser.add_argument("--cost-bps", type=float, default=10.0, help="Estimated round-trip costs in basis points per trade (default: 10)")
    args = parser.parse_args()

    if args.command == "backtest":
        try:
            result = run_backtest(args.data, cost_bps_round_trip=args.cost_bps)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print("MarketPulse India — historical backtest")
        print(f"Rows read: {result.rows_seen}")
        print(f"Trades taken: {result.trades_taken}")
        print(f"Mixed/neutral skipped: {result.mixed_or_neutral}")
        print(f"Insufficient-data rows skipped: {result.insufficient_data}")
        print(f"Estimated round-trip cost: {result.cost_bps_round_trip:.2f} bps per trade")
        print(f"Directional accuracy: {result.accuracy_pct:.2f}%" if result.accuracy_pct is not None else "Directional accuracy: N/A")
        print(f"Average net strategy return per trade: {result.average_strategy_return_pct:+.4f}%" if result.average_strategy_return_pct is not None else "Average net strategy return per trade: N/A")
        print(f"Compounded net strategy return: {result.compounded_strategy_return_pct:+.4f}%" if result.compounded_strategy_return_pct is not None else "Compounded net strategy return: N/A")
        print("\nResearch only. Results from sample data are illustrative, not evidence of a real trading edge.")
        return

    try:
        report = evaluate_snapshot(load_snapshot(args.data, args.date))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(f"MarketPulse India — {report.date}")
    print(f"Assessment: {report.label}")
    print(f"Status: {report.status}")
    print(f"Score: {report.score if report.score is not None else 'N/A'}")
    if report.breadth_ratio is not None:
        ratio = "infinite (zero declines)" if report.breadth_ratio == float("inf") else f"{report.breadth_ratio:.2f}"
        print(f"Advance/decline ratio: {ratio}")
    if report.vix_change_pct is not None:
        print(f"India VIX change: {report.vix_change_pct:+.2f}%")
    print("\nExplanation:")
    for item in report.explanations:
        print(f"- {item}")
    print("\nResearch output only — not financial advice.")


if __name__ == "__main__":
    main()
