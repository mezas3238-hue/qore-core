"""Causal fixtures for VT31 native market facts (no outcome oracle)."""
from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
    ConfirmedDestination,
    produce_market_native_facts,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    StructuralDestinationCandidate,
)

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77320000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("77320000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt31-native-facts-test"),
)
T = datetime(2026, 1, 5, 15, 0, tzinfo=UTC)


def bar(number: int, close: float, high: float, low: float) -> OhlcSnapshot:
    opened = T + timedelta(minutes=number)
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID(f"77320000-0000-0000-0000-{number+1:012d}")
        ),
        instrument=Instrument("NAS100"),
        source=_SOURCE,
        timeframe=Timeframe(60),
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=(high + low) / 2,
        high=high,
        low=low,
        close=close,
    )


def report(
    bars: tuple[OhlcSnapshot, ...],
    as_of: datetime,
    **kwargs: object,
):
    params: dict[str, object] = dict(
        bars_since_fill=bars,
        as_of=as_of,
        side="long",
        structural_invalidation_level=Decimal("99"),
        liquidity_failure_boundary=Decimal("98"),
        reference_reclaim_confirmed_at_entry=True,
        entry_regime="bullish",
        current_regime="bullish",
        regime_observed_at=T,
        primary_target=Decimal("110"),
        primary_target_reached=False,
        primary_target_accepted=False,
    )
    params.update(kwargs)
    return produce_market_native_facts(**params)


def test_producers_true_false_only_after_close_not_same_bar() -> None:
    healthy = bar(0, 102.0, 103.0, 101.0)
    breached = bar(1, 97.0, 102.0, 96.0)
    bars = (healthy, breached)
    before = report(bars, breached.opened_at)
    assert before.structure_invalidated.value is False
    assert before.liquidity_failure_confirmed.value is False
    assert before.structure_invalidated.observed_at == healthy.closed_at

    after = report(bars, breached.closed_at)
    assert after.structure_invalidated.value is True
    assert after.liquidity_failure_confirmed.value is True
    assert after.structure_invalidated.observed_at == breached.closed_at
    assert after.liquidity_failure_confirmed.observed_at == breached.closed_at


def test_unavailable_facts_are_not_false_or_invented() -> None:
    result = report(
        (bar(0, 102.0, 103.0, 101.0),), T + timedelta(minutes=1),
        structural_invalidation_level=None,
        liquidity_failure_boundary=None,
        entry_regime="unavailable",
    )
    assert result.not_evaluable_facts == (
        "structure_invalidated",
        "liquidity_failure_confirmed",
        "regime_changed_against_thesis",
    )
    for name in result.not_evaluable_facts:
        fact = getattr(result, name)
        assert fact.status == "NOT_EVALUABLE"
        assert fact.value is None


def test_regime_switch_is_as_of_and_requires_aligned_entry_thesis() -> None:
    result = report(
        (bar(0, 102.0, 103.0, 101.0),), T + timedelta(minutes=1),
        current_regime="bearish",
        regime_observed_at=T + timedelta(minutes=1),
    )
    assert result.regime_changed_against_thesis.value is True
    assert result.regime_changed_against_thesis.reason == (
        "CONFIRMED_OPPOSITE_REGIME"
    )
    with pytest.raises(ValueError, match="future regime"):
        report(
            (), T, current_regime="bearish",
            regime_observed_at=T + timedelta(minutes=1),
        )


def test_destination_is_explicit_na_before_primary_then_missing() -> None:
    base = report((), T)
    assert base.next_structural_target.status == "NOT_APPLICABLE"
    assert base.next_structural_target.reason == "PRIMARY_TARGET_NOT_REACHED"

    unaccepted = report(
        (), T, primary_target_reached=True, primary_target_accepted=False,
    )
    assert unaccepted.next_structural_target.status == "NOT_APPLICABLE"

    accepted = report(
        (), T, primary_target_reached=True, primary_target_accepted=True,
    )
    assert accepted.next_structural_target.status == "MISSING_REQUIRED"


def test_destination_only_selects_confirmed_as_of_levels() -> None:
    early = ConfirmedDestination(
        StructuralDestinationCandidate(
            level=Decimal("114"), source="confirmed-liquidity-pool",
        ), T,
    )
    future = ConfirmedDestination(
        StructuralDestinationCandidate(
            level=Decimal("112"), source="confirmed-liquidity-pool",
        ), T + timedelta(minutes=2),
    )
    before = report(
        (), T + timedelta(minutes=1),
        primary_target_reached=True,
        primary_target_accepted=True,
        confirmed_next_destinations=(early, future),
    )
    assert before.next_structural_target.status == "AVAILABLE"
    assert before.next_structural_target.candidate == early.candidate
    after = report(
        (), T + timedelta(minutes=2),
        primary_target_reached=True,
        primary_target_accepted=True,
        confirmed_next_destinations=(early, future),
    )
    assert after.next_structural_target.candidate == future.candidate


def test_short_side_breach_and_session_independent_dst() -> None:
    london = T.astimezone(ZoneInfo("Europe/London"))
    crossed = bar(0, 111.0, 112.0, 107.0)
    result = report(
        (crossed,), london + timedelta(minutes=1),
        side="short",
        structural_invalidation_level=Decimal("110"),
        liquidity_failure_boundary=Decimal("110"),
        entry_regime="bearish",
        current_regime="bullish",
        regime_observed_at=london,
    )
    assert result.structure_invalidated.value is True
    assert result.liquidity_failure_confirmed.value is True
    assert result.regime_changed_against_thesis.value is True


def test_no_sizing_or_equity_authority_in_producer_contract() -> None:
    from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
        MarketNativeProducerReport,
    )
    names = {item.name for item in fields(MarketNativeProducerReport)}
    forbidden = {"volume", "lot", "capital", "sizing", "leverage", "pnl"}
    assert names.isdisjoint(forbidden)


def test_frozen_mixed_h1_to_opposite_h1_is_observed_regime_change() -> None:
    result = report(
        (bar(0, 102.0, 103.0, 101.0),),
        T + timedelta(minutes=1),
        entry_regime="mixed",
        current_regime="bearish",
        regime_observed_at=T + timedelta(minutes=1),
    )
    assert result.regime_changed_against_thesis.status == "OBSERVED"
    assert result.regime_changed_against_thesis.value is True


def test_frozen_already_adverse_h1_does_not_fake_new_regime_change() -> None:
    result = report(
        (bar(0, 102.0, 103.0, 101.0),),
        T + timedelta(minutes=1),
        entry_regime="bearish",
        current_regime="bearish",
        regime_observed_at=T + timedelta(minutes=1),
    )
    assert result.regime_changed_against_thesis.status == "OBSERVED"
    assert result.regime_changed_against_thesis.value is False
