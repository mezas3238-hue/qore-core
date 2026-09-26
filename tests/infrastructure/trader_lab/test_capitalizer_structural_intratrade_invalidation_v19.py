from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_structural_intratrade_invalidation_v19 as lab,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _trade() -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at="2026-01-05T10:30:00+00:00",
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r="-1",
        exit_reason="STOP",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 10, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=5,
    )


def test_adverse_displacement_requires_body_and_prior_extreme_break() -> None:
    trade = _trade()
    prior = (
        _bar(0, open_="100", high="100.10", low="99.90", close="100.00"),
        _bar(1, open_="100", high="100.05", low="99.80", close="99.95"),
    )
    strong = _bar(
        2,
        open_="100.00",
        high="100.02",
        low="99.55",
        close="99.60",
    )
    assert lab._displacement_qualifies(
        bar=strong,
        prior=prior,
        trade=trade,
        minimum_body_r=Decimal("0.20"),
        minimum_adverse_close_r=Decimal("0.15"),
    )

    weak = _bar(
        2,
        open_="99.82",
        high="99.84",
        low="99.55",
        close="99.70",
    )
    assert not lab._displacement_qualifies(
        bar=weak,
        prior=prior,
        trade=trade,
        minimum_body_r=Decimal("0.20"),
        minimum_adverse_close_r=Decimal("0.15"),
    )


def test_structural_trigger_requires_acceptance_extension_and_failed_reclaim() -> None:
    state = lab._StructuralState(period="DEV", trade=_trade())
    bars = (
        _bar(0, open_="100", high="100.10", low="99.90", close="100.00"),
        _bar(1, open_="100", high="100.05", low="99.80", close="99.95"),
        _bar(2, open_="100.00", high="100.02", low="99.55", close="99.60"),
        _bar(3, open_="99.60", high="99.72", low="99.40", close="99.50"),
        _bar(4, open_="99.50", high="99.60", low="99.30", close="99.40"),
    )
    first: tuple[v18.TriggerEvent, ...] = ()
    second: tuple[v18.TriggerEvent, ...] = ()
    for index, bar in enumerate(bars):
        events = lab._process_bar(state, bar)
        if index == 3:
            first = events
        if index == 4:
            second = events

    assert any(
        event.trigger == "STRUCT3_B015_C010_A1"
        for event in first
    )
    assert not any(
        event.trigger == "STRUCT3_B020_C015_A2"
        for event in first
    )
    assert any(
        event.trigger == "STRUCT3_B020_C015_A2"
        for event in second
    )
    assert all(event.current_outcome_visible_to_trigger is False for event in second)
    assert all(event.original_exit_bar_used_for_trigger is False for event in second)


def test_midpoint_reclaim_cancels_pending_structure() -> None:
    trade = _trade()
    pending = lab._Pending(
        midpoint=Decimal("99.80"),
        adverse_extreme=Decimal("99.55"),
    )
    reclaim = _bar(
        3,
        open_="99.60",
        high="99.90",
        low="99.58",
        close="99.85",
    )
    assert lab._reclaimed(reclaim, pending=pending, trade=trade)


def test_v19_preserves_sealed_holdout_and_no_market_filters() -> None:
    assert "2018-09-17_TO_2020-09-17" not in lab.POLICY_SPECS
    assert set(lab.POLICY_SPECS) == {
        "GLOBAL_STRUCT3_B020_A2",
        "DD2_STRUCT3_B020_A2",
        "DEFENSIVE_STRUCT3_B020_A2",
        "GLOBAL_STRUCT5_B020_A2",
        "DD2_STRUCT5_B020_A2",
        "DEFENSIVE_STRUCT5_B020_A2",
        "GLOBAL_STRUCT5_B025_A2",
    }
