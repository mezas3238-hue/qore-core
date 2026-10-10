"""Preregistered H1 bias null: source-episode membership + deterministic random."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_direction_random_baseline_v1 import (
    DRAWS,
    DirectionNullRow,
    _future_label,
    _runs,
    _seed,
    eligible_h1_state_times,
)

START = datetime(2026, 5, 4, 10, tzinfo=UTC)


def _bar(i: int, *, close: str = "100") -> CapitalizerM1Bar:
    at = START + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal("100"), high=Decimal("101"),
        low=Decimal("99"), close=Decimal(close),
        volume=100, digits=5,
    )


def _source() -> V49Opportunity:
    return V49Opportunity(
        symbol="EURUSD", session="LONDON",
        operating_date="2026-05-04",
        h1_state_direction="BULLISH",
        h1_state_from=START.isoformat(),
        h1_state_until=(START + timedelta(minutes=55)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:SWING_LOW",
        m15_setup_confirmed_at=(START + timedelta(minutes=5)).isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=(START + timedelta(minutes=20)).isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )


def test_asof_episode_does_not_read_future_state_expiration() -> None:
    source = _source()
    bars = tuple(_bar(i) for i in range(52))
    opposite = (START + timedelta(minutes=32),)
    eligible = eligible_h1_state_times(source,bars,opposite)
    assert all(b.closed_at <= opposite[0] for b in eligible)
    assert all(b.closed_at != START + timedelta(minutes=20) for b in eligible)
    assert any(b.closed_at == START + timedelta(minutes=12) for b in eligible)
    assert len(eligible) == 30
    altered = replace(source, h1_state_until=(START + timedelta(days=30)).isoformat())
    assert eligible_h1_state_times(altered,bars,opposite) == eligible
    assert eligible_h1_state_times(
        source,bars,(START + timedelta(hours=2),)
    )[-1].closed_at > opposite[0]


def test_forward_labels_only_on_full_consecutive_native_m1() -> None:
    bars = tuple(_bar(i, close=str(100+i/100)) for i in range(61))
    stamps = tuple(b.opened_at for b in bars)
    r = _future_label(
        bars, stamps, _runs(bars), START, Decimal("100"), 1, "LONDON",
    )
    assert r == (Decimal("0.14"), Decimal("0.29"), Decimal("0.59"))
    missing = bars[:7] + bars[8:]
    assert _future_label(
        missing,tuple(b.opened_at for b in missing),_runs(missing),
        START,Decimal("100"),1,"LONDON",
    ) == (None,None,None)


def test_null_seed_is_stable_and_different_for_independent_models() -> None:
    assert _seed("fixed-id","UNIFORM_H1_STATE")==_seed(
        "fixed-id","UNIFORM_H1_STATE"
    )
    assert _seed("fixed-id","UNIFORM_H1_STATE")!=_seed(
        "fixed-id","MATCHED_H1_CLOCK_THIRD"
    )
    assert DRAWS == 32


def test_all_samples_are_research_and_no_trade_can_be_changed() -> None:
    # Rows store source IDs and original economics as immutable historical
    # joins; a method that mutates them would violate the contract.
    fields = DirectionNullRow.__dataclass_fields__
    assert "h1_state_from" in fields
    assert "original_realized_gross_r" in fields
    assert fields["draw_uses_forward_outcomes"].default is False
    assert fields["changed_original_trade"].default is False
    assert fields["null_used_future_bias_expiry"].default is False


def test_session_membership_bound_to_new_york_operating_date() -> None:
    source = _source()
    bars = tuple(_bar(i) for i in range(80))
    eligible = eligible_h1_state_times(source,bars,())
    # London cutoff 8:30 NY = 12:30 UTC in May (150m after START)
    assert len(eligible)>70
    assert all(b.opened_at >= START for b in eligible)
