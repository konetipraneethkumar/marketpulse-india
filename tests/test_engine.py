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


def test_bearish_components_produce_bearish_assessment():
    report = evaluate_snapshot(
        snapshot(gift_nifty_change_pct=-0.4, advances=100, declines=300, nifty_open=24900)
    )
    assert report.score == -3
    assert report.label == "Bearish"


def test_mixed_components_produce_mixed_assessment():
    report = evaluate_snapshot(snapshot(gift_nifty_change_pct=0, advances=200, declines=200, nifty_open=25000))
    assert report.score == 0
    assert report.label == "Mixed"


def test_vix_change_is_context_not_directional_vote():
    report = evaluate_snapshot(snapshot())
    assert report.vix_change_pct == pytest.approx(10.0)
    assert report.score == 3
    assert any("not a directional vote" in line for line in report.explanations)


def test_vix_falling_is_reported_as_negative_percent():
    report = evaluate_snapshot(snapshot(india_vix_previous=20.0, india_vix_current=19.0))
    assert report.vix_change_pct == pytest.approx(-5.0)


def test_vix_missing_is_context_unavailable_not_fatal():
    report = evaluate_snapshot(snapshot(india_vix_previous=None, india_vix_current=None))
    assert report.status == "ok"
    assert report.vix_change_pct is None
    assert any("context unavailable" in line for line in report.explanations)


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.05, 0), (-0.05, 0), (0.051, 1), (-0.051, -1), (0.0, 0)],
)
def test_gift_nifty_deadband_boundaries(value, expected):
    report = evaluate_snapshot(snapshot(gift_nifty_change_pct=value))
    assert report.components["gift_nifty"] == expected


def test_opening_gap_is_calculated_from_previous_close():
    report = evaluate_snapshot(snapshot(nifty_previous_close=20000, nifty_open=20100))
    assert report.opening_gap_pct == pytest.approx(0.5)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_market_values_are_rejected(bad):
    with pytest.raises(ValueError, match="finite"):
        evaluate_snapshot(snapshot(gift_nifty_change_pct=bad))


@pytest.mark.parametrize("bad", [0, -1])
def test_non_positive_previous_close_is_rejected(bad):
    with pytest.raises(ValueError, match="greater than zero"):
        evaluate_snapshot(snapshot(nifty_previous_close=bad))


@pytest.mark.parametrize("bad", [0, -1, float("inf")])
def test_invalid_vix_is_rejected_even_if_another_input_is_missing(bad):
    with pytest.raises(ValueError):
        evaluate_snapshot(snapshot(gift_nifty_change_pct=None, india_vix_current=bad))


def test_negative_breadth_counts_are_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        evaluate_snapshot(snapshot(advances=-1))


@pytest.mark.parametrize("bad", [1.5, True])
def test_non_integer_breadth_counts_are_rejected(bad):
    with pytest.raises(ValueError, match="integer"):
        evaluate_snapshot(snapshot(advances=bad))


def test_vix_only_one_value_available_is_treated_as_unavailable():
    report = evaluate_snapshot(snapshot(india_vix_current=None))
    assert report.vix_change_pct is None
    assert report.status == "ok"
