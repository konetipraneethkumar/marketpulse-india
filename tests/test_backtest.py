from pathlib import Path

import pytest

from marketpulse.backtest import run_backtest


HEADER = (
    "date,signal_time_ist,entry_time_ist,entry_price,exit_time_ist,exit_price,"
    "gift_nifty_change_pct,india_vix_previous,india_vix_current,advances,declines,"
    "nifty_previous_close,nifty_open\n"
)
BULLISH = (
    "2026-10-29,2026-10-29T09:20:00+05:30,2026-10-29T09:25:00+05:30,100,"
    "2026-10-29T15:20:00+05:30,102,0.4,15,16,300,100,100,101\n"
)


def write_csv(tmp_path: Path, rows: str) -> Path:
    path = tmp_path / "backtest.csv"
    path.write_text(HEADER + rows, encoding="utf-8")
    return path


def test_backtest_reports_forward_return_after_costs(tmp_path):
    result = run_backtest(write_csv(tmp_path, BULLISH), cost_bps_round_trip=10)
    assert result.rows_seen == 1
    assert result.trades_taken == 1
    assert result.correct_trades == 1
    assert result.accuracy_pct == pytest.approx(100)
    assert result.trades[0].gross_market_return_pct == pytest.approx(2)
    assert result.trades[0].strategy_return_pct == pytest.approx(1.9)
    assert result.average_strategy_return_pct == pytest.approx(1.9)
    assert result.compounded_strategy_return_pct == pytest.approx(1.9)


def test_backtest_rejects_entry_before_signal_to_prevent_lookahead(tmp_path):
    row = BULLISH.replace("2026-10-29T09:25:00+05:30", "2026-10-29T09:15:00+05:30")
    with pytest.raises(ValueError, match="look-ahead"):
        run_backtest(write_csv(tmp_path, row))


def test_backtest_requires_timezone_on_timestamps(tmp_path):
    row = BULLISH.replace("2026-10-29T09:20:00+05:30", "2026-10-29T09:20:00")
    with pytest.raises(ValueError, match="timezone offset"):
        run_backtest(write_csv(tmp_path, row))


def test_backtest_requires_india_timezone_offset(tmp_path):
    row = BULLISH.replace("+05:30", "+00:00")
    with pytest.raises(ValueError, match="Asia/Kolkata"):
        run_backtest(write_csv(tmp_path, row))


def test_backtest_rejects_exit_not_after_entry(tmp_path):
    row = BULLISH.replace("2026-10-29T15:20:00+05:30", "2026-10-29T09:25:00+05:30")
    with pytest.raises(ValueError, match="after entry"):
        run_backtest(write_csv(tmp_path, row))


@pytest.mark.parametrize("cost", [-1, float("inf"), float("nan")])
def test_backtest_rejects_invalid_cost(cost, tmp_path):
    with pytest.raises(ValueError, match="cost"):
        run_backtest(write_csv(tmp_path, BULLISH), cost_bps_round_trip=cost)


def test_empty_file_rows_returns_no_metrics(tmp_path):
    result = run_backtest(write_csv(tmp_path, ""))
    assert result.rows_seen == 0
    assert result.trades_taken == 0
    assert result.accuracy_pct is None
    assert result.compounded_strategy_return_pct is None



def test_entry_at_exact_signal_time_is_rejected(tmp_path):
    row = BULLISH.replace(
        "2026-10-29T09:25:00+05:30", "2026-10-29T09:20:00+05:30"
    )
    with pytest.raises(ValueError, match="strictly after"):
        run_backtest(write_csv(tmp_path, row))


def test_backtest_rejects_timestamp_on_wrong_date(tmp_path):
    row = BULLISH.replace(
        "2026-10-29T15:20:00+05:30", "2026-10-30T15:20:00+05:30"
    )
    with pytest.raises(ValueError, match="date must match"):
        run_backtest(write_csv(tmp_path, row))


def test_benchmark_metrics_are_reported(tmp_path):
    result = run_backtest(write_csv(tmp_path, BULLISH), cost_bps_round_trip=10)
    assert result.average_buy_and_hold_return_pct == pytest.approx(1.9)
    assert result.compounded_buy_and_hold_return_pct == pytest.approx(1.9)
    assert result.average_excess_return_pct == pytest.approx(0.0)


def test_missing_critical_signal_data_is_skipped(tmp_path):
    row = BULLISH.replace(",0.4,15,16,300,100,100,101", ",,15,16,300,100,100,101")
    result = run_backtest(write_csv(tmp_path, row))
    assert result.trades_taken == 0
    assert result.insufficient_data == 1
    assert result.accuracy_pct is None
