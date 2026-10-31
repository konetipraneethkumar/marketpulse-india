from datetime import date

import pytest

from marketpulse.engine import MarketSnapshot, evaluate_snapshot


def snapshot(**overrides):
    values = dict(
        date=date(2026, 10, 30),
        gift_nifty_change_pct=0.4,
        india_vix_previous=15.0,
        india_vix_current=16.5,
        advances=300,
        declines=200,
        nifty_previous_close=25000.0,
        nifty_open=25100.0,
    )
    values.update(overrides)
    return MarketSnapshot(**values)


def test_bullish_components_produce_bullish_assessment():
    report = evaluate_snapshot(snapshot())
    assert report.status == "ok"
    assert report.score == 3
    assert report.label == "Bullish"
    assert report.components == {"gift_nifty": 1, "breadth": 1, "opening_gap": 1}


def test_vix_change_is_context_not_directional_vote():
    report = evaluate_snapshot(snapshot())
    assert report.vix_change_pct == pytest.approx(10.0)
    assert report.score == 3
    assert any("not a directional vote" in line for line in report.explanations)


def test_zero_declines_does_not_crash():
    report = evaluate_snapshot(snapshot(advances=300, declines=0))
    assert report.status == "ok"
    assert report.breadth_ratio == float("inf")
    assert report.components["breadth"] == 1


def test_no_advances_or_declines_has_neutral_breadth():
    report = evaluate_snapshot(snapshot(advances=0, declines=0))
    assert report.components["breadth"] == 0
    assert report.breadth_ratio is None


def test_missing_critical_input_returns_insufficient_data():
    report = evaluate_snapshot(snapshot(gift_nifty_change_pct=None))
    assert report.status == "insufficient_data"
    assert report.score is None
    assert "Missing critical inputs" in report.explanations[0]


def test_opening_gap_is_calculated_from_previous_close():
    report = evaluate_snapshot(snapshot(nifty_previous_close=20000, nifty_open=20100))
    assert report.opening_gap_pct == pytest.approx(0.5)


def test_negative_breadth_counts_are_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        evaluate_snapshot(snapshot(advances=-1))


def test_zero_previous_close_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        evaluate_snapshot(snapshot(nifty_previous_close=0))
