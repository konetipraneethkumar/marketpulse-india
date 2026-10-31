"""Command-line interface for MarketPulse India."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from marketpulse.engine import MarketSnapshot, evaluate_snapshot

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "sample_market.csv"


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
    args = parser.parse_args()

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
