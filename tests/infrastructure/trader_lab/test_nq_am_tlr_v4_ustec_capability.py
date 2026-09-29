from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import nq_am_temporal_liquidity_reversal_v2 as v2
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar
from qore.infrastructure.trader_lab.nq_am_tlr_v4_ustec_capability import (
    PRIMARY_VARIANT,
    OpeningSignature,
    ReferenceModel,
    _adjudicate_primary,
    _nearest_prior_daily_low,
    _opening_signature_passes,
    variant_name,
)


def _bar(minute: int, high: str, close: str) -> Bar:
    opened = datetime(2025, 1, 8, 14, 30, tzinfo=UTC) + timedelta(minutes=minute)
    return Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal("90"),
        close=Decimal(close),
    )


def _eth(day: date, low: str) -> v2.EthDailySession:
    opened, closed = v2._eth_bounds(day)
    return v2.EthDailySession(
        trade_day=day,
        opened_at=opened,
        closed_at=closed,
        high=Decimal("120"),
        low=Decimal(low),
        close=Decimal("110"),
        bars=(),
    )


def test_primary_variant_is_frozen_rolling_am_low_m2() -> None:
    assert PRIMARY_VARIANT == "ROLLING_AM_LOW_M2"
    assert (
        variant_name(ReferenceModel.ROLLING_AM_LOW, OpeningSignature.M2)
        == PRIMARY_VARIANT
    )


def test_opening_signature_m2_requires_two_completed_weak_bars() -> None:
    bars = (
        _bar(0, "100.5", "99.5"),
        _bar(1, "100.8", "99.0"),
        _bar(2, "103", "102"),
    )
    assert _opening_signature_passes(
        bars,
        signature=OpeningSignature.M2,
        lower_octant=Decimal("100"),
        lower_quadrant=Decimal("101"),
    )
    assert not _opening_signature_passes(
        bars,
        signature=OpeningSignature.M5,
        lower_octant=Decimal("100"),
        lower_quadrant=Decimal("101"),
    )


def test_nearest_prior_daily_low_is_causal_and_not_2sd_ranked() -> None:
    sessions = (
        _eth(date(2025, 1, 3), "80"),
        _eth(date(2025, 1, 6), "91"),
        _eth(date(2025, 1, 7), "95"),
    )
    selected = _nearest_prior_daily_low(
        sessions,
        current_day=date(2025, 1, 8),
        current_open=Decimal("100"),
    )
    assert selected == (date(2025, 1, 7), Decimal("95"))


def test_primary_gate_supports_only_when_all_requirements_pass() -> None:
    metrics = {
        "trade_count": 30,
        "primary_total_r": "12",
        "primary_pf": "1.40",
        "primary_max_drawdown_r": "5",
        "by_fold": {
            "Y1": {"total_r": "4"},
            "Y2": {"total_r": "-1"},
            "Y3": {"total_r": "9"},
        },
    }
    result = _adjudicate_primary(metrics)
    assert result["label"] == "USTEC_CAPABILITY_SUPPORTED"
    assert result["supported"] is True


def test_primary_gate_reports_insufficient_sample_before_economics() -> None:
    metrics = {
        "trade_count": 12,
        "primary_total_r": "50",
        "primary_pf": "3",
        "primary_max_drawdown_r": "1",
        "by_fold": {
            "Y1": {"total_r": "10"},
            "Y2": {"total_r": "20"},
            "Y3": {"total_r": "20"},
        },
    }
    result = _adjudicate_primary(metrics)
    assert result["label"] == "INSUFFICIENT_SAMPLE"
    assert result["supported"] is False
