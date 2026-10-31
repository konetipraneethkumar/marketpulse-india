"""Pure, deterministic rules for a MarketPulse opening snapshot."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class MarketSnapshot:
    date: date
    gift_nifty_change_pct: Optional[float]
    india_vix_previous: Optional[float]
    india_vix_current: Optional[float]
    advances: Optional[int]
    declines: Optional[int]
    nifty_previous_close: Optional[float]
    nifty_open: Optional[float]


@dataclass(frozen=True)
class SignalReport:
    date: date
    status: str
    label: str
    score: Optional[int]
    components: dict[str, Optional[int]]
    breadth_ratio: Optional[float]
    opening_gap_pct: Optional[float]
    vix_change_pct: Optional[float]
    explanations: tuple[str, ...]


def _validate_snapshot(snapshot: MarketSnapshot) -> None:
    """Reject invalid values even when another critical input is missing."""
    numeric_fields = (
        ("GIFT Nifty change", snapshot.gift_nifty_change_pct),
        ("previous India VIX", snapshot.india_vix_previous),
        ("current India VIX", snapshot.india_vix_current),
        ("previous NIFTY close", snapshot.nifty_previous_close),
        ("NIFTY open", snapshot.nifty_open),
    )
    for name, value in numeric_fields:
        if value is not None and not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    for name, value in (
        ("advances", snapshot.advances),
        ("declines", snapshot.declines),
    ):
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
    if snapshot.nifty_previous_close is not None and snapshot.nifty_previous_close <= 0:
        raise ValueError("Previous NIFTY close must be greater than zero")
    for name, value in (
        ("Previous India VIX", snapshot.india_vix_previous),
        ("Current India VIX", snapshot.india_vix_current),
    ):
        if value is not None and value <= 0:
            raise ValueError(f"{name} must be greater than zero when provided")


def _sign(value: float, deadband: float = 0.0) -> int:
    if value > deadband:
        return 1
    if value < -deadband:
        return -1
    return 0


def evaluate_snapshot(snapshot: MarketSnapshot) -> SignalReport:
    """Evaluate a snapshot without guessing when a critical input is missing.

    GIFT Nifty, advances/declines breadth, and NIFTY opening gap each contribute
    -1, 0, or +1. India VIX is reported separately as volatility context.
    These are illustrative research rules, not a validated trading strategy.
    """
    _validate_snapshot(snapshot)

    critical = {
        "GIFT Nifty change": snapshot.gift_nifty_change_pct,
        "advances": snapshot.advances,
        "declines": snapshot.declines,
        "previous NIFTY close": snapshot.nifty_previous_close,
        "NIFTY open": snapshot.nifty_open,
    }
    missing = [name for name, value in critical.items() if value is None]
    if missing:
        return SignalReport(
            date=snapshot.date,
            status="insufficient_data",
            label="Insufficient data",
            score=None,
            components={"gift_nifty": None, "breadth": None, "opening_gap": None},
            breadth_ratio=None,
            opening_gap_pct=None,
            vix_change_pct=_vix_change(snapshot),
            explanations=("Missing critical inputs: " + ", ".join(missing) + ".",),
        )

    # The missing-data check above makes these values non-optional here.
    gift_change = snapshot.gift_nifty_change_pct
    advances, declines = snapshot.advances, snapshot.declines
    previous_close, opening = snapshot.nifty_previous_close, snapshot.nifty_open
    assert gift_change is not None and advances is not None and declines is not None
    assert previous_close is not None and opening is not None

    gift = _sign(gift_change, deadband=0.05)
    breadth_total = advances + declines
    breadth_ratio = (
        advances / declines if declines > 0
        else (float("inf") if advances > 0 else None)
    )
    if breadth_total == 0:
        breadth = 0
    else:
        breadth = _sign((advances - declines) / breadth_total, deadband=0.05)

    opening_gap_pct = (opening - previous_close) / previous_close * 100
    gap = _sign(opening_gap_pct, deadband=0.05)
    components = {"gift_nifty": gift, "breadth": breadth, "opening_gap": gap}
    score = sum(components.values())

    if score >= 2:
        label = "Bullish"
    elif score == 1:
        label = "Weak bullish"
    elif score == 0:
        label = "Mixed"
    elif score == -1:
        label = "Weak bearish"
    else:
        label = "Bearish"

    explanations = [
        f"GIFT Nifty: {gift_change:+.2f}% ({_direction(gift)}).",
        f"Market breadth: {advances} advances vs {declines} declines ({_direction(breadth)}).",
        f"NIFTY opening gap: {opening_gap_pct:+.2f}% ({_direction(gap)}).",
    ]
    vix_change = _vix_change(snapshot)
    if vix_change is None:
        explanations.append("India VIX context unavailable; no volatility conclusion drawn.")
    else:
        explanations.append(
            f"India VIX changed {vix_change:+.2f}%; this is volatility context, not a directional vote."
        )

    return SignalReport(
        date=snapshot.date,
        status="ok",
        label=label,
        score=score,
        components=components,
        breadth_ratio=breadth_ratio,
        opening_gap_pct=opening_gap_pct,
        vix_change_pct=vix_change,
        explanations=tuple(explanations),
    )


def _vix_change(snapshot: MarketSnapshot) -> Optional[float]:
    previous, current = snapshot.india_vix_previous, snapshot.india_vix_current
    if previous is None or current is None:
        return None
    # Positivity and finiteness are validated before this helper is called.
    return (current - previous) / previous * 100


def _direction(score: int) -> str:
    return {1: "positive", 0: "neutral", -1: "negative"}[score]
