"""Synthetic causal-bar fixtures for independent stop/noise ablations."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_stop_noise_factorial_v1 import (
    Arm,
    analyze_source_geometry,
)

START = datetime(2026, 5, 4, 6, tzinfo=UTC)


def _source() -> V49Opportunity:
    return V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-05-04",
        h1_state_direction="BULLISH",
        h1_state_from=(START - timedelta(hours=1)).isoformat(),
        h1_state_until=(START + timedelta(hours=2)).isoformat(),
        h1_state_basis="H1_C2",
        m15_setup_confirmed_at=START.isoformat(),
        m15_protected_swing_price="98",
        m1_trigger_confirmed_at=(START + timedelta(minutes=30)).isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="100.5",
    )


def _bars(*, local_breathing: str, with_pivot: bool = True) -> tuple[
    CapitalizerM1Bar, ...
]:
    out = []
    half = Decimal(local_breathing) / 2
    for i in range(30):
        moment = START + timedelta(minutes=i)
        low = Decimal("100") - half
        if with_pivot and i == 5:
            low = Decimal("99")
        out.append(CapitalizerM1Bar(
            symbol="EURUSD",
            opened_at=moment,
            closed_at=moment + timedelta(minutes=1),
            open=Decimal("100"),
            high=Decimal("100") + half,
            low=low,
            close=Decimal("100"),
            volume=100,
            digits=5,
        ))
    return tuple(out)


def test_m1_pivot_outside_noise_allows_all_four_arms() -> None:
    bars = _bars(local_breathing="0.2")
    gate = analyze_source_geometry(
        _source(), bars, tuple(b.opened_at for b in bars)
    )
    assert gate.m1_anchor_available is True
    assert gate.m1_anchor_price == "99"
    assert gate.m1_stop_to_recent_m1_range == "5"
    assert gate.m1_noise_reason == "M1_EXECUTION_STOP_NOISE_4_TO_8_PASS"
    assert set(gate.eligible_arms) == {a.value for a in Arm}
    assert gate.outcome_used_for_admission is False
    assert gate.entry_authorized is False


def test_m1_pivot_inside_local_noise_cannot_veto_m15_thesis_baseline() -> None:
    bars = _bars(local_breathing="0.8")
    gate = analyze_source_geometry(
        _source(), bars, tuple(b.opened_at for b in bars)
    )
    assert gate.m1_anchor_price == "99"
    assert gate.m1_noise_reason == "M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE"
    assert set(gate.eligible_arms) == {
        Arm.M15_NOISE_OFF.value, Arm.M1_NOISE_OFF.value,
    }


def test_without_confirmed_m1_pivot_only_structural_m15_survives() -> None:
    bars = _bars(local_breathing="0.2", with_pivot=False)
    gate = analyze_source_geometry(
        _source(), bars, tuple(b.opened_at for b in bars)
    )
    assert not gate.m1_anchor_available
    assert gate.m1_noise_reason == "M1_PIVOT_UNAVAILABLE"
    assert gate.eligible_arms == (Arm.M15_NOISE_OFF.value,)


def test_unfinished_m1_bar_cannot_change_noise_or_pivot() -> None:
    bars = _bars(local_breathing="0.2")
    future = replace(
        bars[-1],
        opened_at=START + timedelta(minutes=30),
        closed_at=START + timedelta(minutes=31),
        high=Decimal("110"),
        low=Decimal("95"),
    )
    original = analyze_source_geometry(
        _source(), bars, tuple(b.opened_at for b in bars)
    )
    augmented = bars + (future,)
    after = analyze_source_geometry(
        _source(), augmented, tuple(b.opened_at for b in augmented)
    )
    assert after == original


def test_source_h1_m15_future_timestamp_blocks_admission() -> None:
    bars = _bars(local_breathing="0.2")
    source = replace(
        _source(),
        m15_setup_confirmed_at=(START + timedelta(minutes=31)).isoformat(),
    )
    with pytest.raises(ValueError, match="out of order"):
        analyze_source_geometry(
            source, bars, tuple(b.opened_at for b in bars)
        )
