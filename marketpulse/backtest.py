"""Timestamp-aware historical backtesting for MarketPulse signals.

CSV rows must contain a signal timestamp and a later entry/exit interval.
Sample values are illustrative and must not be treated as market history.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from marketpulse.engine import MarketSnapshot, evaluate_snapshot


@dataclass(frozen=True)
class TradeResult:
    date: date
    score: int
    direction: int
    gross_market_return_pct: float
    strategy_return_pct: float
    correct_direction: bool


@dataclass(frozen=True)
class BacktestReport:
    rows_seen: int
    trades_taken: int
    mixed_or_neutral: int
    insufficient_data: int
    correct_trades: int
    accuracy_pct: float | None
    average_strategy_return_pct: float | None
    compounded_strategy_return_pct: float | None
    average_buy_and_hold_return_pct: float | None
    compounded_buy_and_hold_return_pct: float | None
    average_excess_return_pct: float | None
    cost_bps_round_trip: float
    trades: tuple[TradeResult, ...]


def _optional_float(value: str | None) -> float | None:
    return float(value) if value is not None and value.strip() else None


def _optional_int(value: str | None) -> int | None:
    return int(value) if value is not None and value.strip() else None


def _timestamp(row: dict[str, str], field: str, row_number: int) -> datetime:
    raw = row.get(field, "").strip()
    if not raw:
        raise ValueError(f"CSV row {row_number}: {field} is required")
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"CSV row {row_number}: invalid {field}; use ISO 8601 with timezone") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"CSV row {row_number}: {field} must include a timezone offset")
    if value.utcoffset().total_seconds() != 5.5 * 60 * 60:
        raise ValueError(f"CSV row {row_number}: {field} must use the Asia/Kolkata UTC+05:30 offset")
    return value


def run_backtest(path: Path, cost_bps_round_trip: float = 10.0) -> BacktestReport:
    """Evaluate non-neutral signals against a later entry-to-exit price move.

    `cost_bps_round_trip` is a combined estimated cost in basis points per trade.
    It is deducted once from each trade return. This simple model does not model
    market impact, taxes, liquidity, position sizing, or portfolio drawdown.
    """
    if not math.isfinite(cost_bps_round_trip) or cost_bps_round_trip < 0:
        raise ValueError("Round-trip cost must be a finite, non-negative number of basis points")

    results: list[TradeResult] = []
    mixed = 0
    insufficient = 0
    rows_seen = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "date", "signal_time_ist", "entry_time_ist", "entry_price", "exit_time_ist", "exit_price",
            "gift_nifty_change_pct", "india_vix_previous", "india_vix_current", "advances", "declines",
            "nifty_previous_close", "nifty_open",
        }
        missing_columns = sorted(required - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError("CSV missing required columns: " + ", ".join(missing_columns))

        for row_number, row in enumerate(reader, start=2):
            rows_seen += 1
            try:
                day = date.fromisoformat(row["date"])
                signal_time = _timestamp(row, "signal_time_ist", row_number)
                entry_time = _timestamp(row, "entry_time_ist", row_number)
                exit_time = _timestamp(row, "exit_time_ist", row_number)
                entry_price = float(row["entry_price"])
                exit_price = float(row["exit_price"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"CSV row {row_number}: {exc}") from exc

            if signal_time.date() != day or entry_time.date() != day or exit_time.date() != day:
                raise ValueError(f"CSV row {row_number}: date must match all intraday timestamps")
            if entry_time <= signal_time:
                raise ValueError(f"CSV row {row_number}: entry_time_ist must be strictly after signal_time_ist (look-ahead risk)")
            if exit_time <= entry_time:
                raise ValueError(f"CSV row {row_number}: exit_time_ist must be after entry_time_ist")
            if not math.isfinite(entry_price) or not math.isfinite(exit_price) or entry_price <= 0 or exit_price <= 0:
                raise ValueError(f"CSV row {row_number}: entry_price and exit_price must be finite and greater than zero")

            snapshot = MarketSnapshot(
                date=day,
                gift_nifty_change_pct=_optional_float(row["gift_nifty_change_pct"]),
                india_vix_previous=_optional_float(row["india_vix_previous"]),
                india_vix_current=_optional_float(row["india_vix_current"]),
                advances=_optional_int(row["advances"]),
                declines=_optional_int(row["declines"]),
                nifty_previous_close=_optional_float(row["nifty_previous_close"]),
                nifty_open=_optional_float(row["nifty_open"]),
            )
            report = evaluate_snapshot(snapshot)
            if report.status != "ok":
                insufficient += 1
                continue
            assert report.score is not None
            if report.score == 0:
                mixed += 1
                continue

            direction = 1 if report.score > 0 else -1
            market_return = (exit_price - entry_price) / entry_price * 100
            strategy_return = direction * market_return - cost_bps_round_trip / 100
            results.append(TradeResult(
                date=day,
                score=report.score,
                direction=direction,
                gross_market_return_pct=market_return,
                strategy_return_pct=strategy_return,
                correct_direction=(market_return > 0 if direction > 0 else market_return < 0),
            ))

    count = len(results)
    accuracy = (sum(t.correct_direction for t in results) / count * 100) if count else None
    average = (sum(t.strategy_return_pct for t in results) / count) if count else None
    compounded = None
    average_buy_hold = None
    compounded_buy_hold = None
    average_excess = None
    if count:
        growth = 1.0
        benchmark_growth = 1.0
        for trade in results:
            growth *= 1 + trade.strategy_return_pct / 100
            benchmark_growth *= 1 + trade.gross_market_return_pct / 100
        compounded = (growth - 1) * 100
        average_buy_hold = sum(t.gross_market_return_pct for t in results) / count
        compounded_buy_hold = (benchmark_growth - 1) * 100
        average_excess = average - average_buy_hold if average is not None else None

    return BacktestReport(
        rows_seen=rows_seen,
        trades_taken=count,
        mixed_or_neutral=mixed,
        insufficient_data=insufficient,
        correct_trades=sum(t.correct_direction for t in results),
        accuracy_pct=accuracy,
        average_strategy_return_pct=average,
        compounded_strategy_return_pct=compounded,
        average_buy_and_hold_return_pct=average_buy_hold,
        compounded_buy_and_hold_return_pct=compounded_buy_hold,
        average_excess_return_pct=average_excess,
        cost_bps_round_trip=cost_bps_round_trip,
        trades=tuple(results),
    )
