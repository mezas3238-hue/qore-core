from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as lab,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _trade(*, exit_minute: int = 20) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at=f"2026-01-05T10:{exit_minute:02d}:00+00:00",
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
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 10, minute, tzinfo=UTC)
    close_d = Decimal(close)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=close_d,
        volume=1,
        digits=5,
    )


def test_sustained_adverse_acceptance_triggers_without_departure() -> None:
    state = lab._PathState(period="DEV", trade=_trade())
    events = []
    for minute, close in enumerate(
        ("100", "100", "99.9", "99.7", "99.7", "99.7")
    ):
        events.extend(
            lab._process_bar(
                state,
                _bar(
                    minute,
                    high="100.10",
                    low=str(Decimal(close) - Decimal("0.05")),
                    close=close,
                ),
            )
        )
    by_name = {event.trigger: event for event in events}
    assert "STALL5_A025" in by_name
    assert by_name["STALL5_A025"].trigger_r <= "-0.25"
    assert Decimal(by_name["STALL5_A025"].max_favorable_r_before_trigger) < (
        lab.DEPARTURE_R
    )


def test_favorable_departure_disables_invalidation() -> None:
    state = lab._PathState(period="DEV", trade=_trade())
    lab._process_bar(
        state,
        _bar(0, high="100.30", low="99.95", close="100.05"),
    )
    assert state.departed is True
    events = []
    for minute in range(1, 10):
        events.extend(
            lab._process_bar(
                state,
                _bar(minute, high="100.05", low="99.50", close="99.50"),
            )
        )
    assert not events


def test_original_exit_bar_is_excluded() -> None:
    state = lab._PathState(period="DEV", trade=_trade(exit_minute=5))
    for minute in range(4):
        lab._process_bar(
            state,
            _bar(minute, high="100.05", low="99.70", close="99.70"),
        )
    events = lab._process_bar(
        state,
        _bar(4, high="100.05", low="99.60", close="99.60"),
    )
    assert not events


def test_activation_uses_only_current_dd_and_surface_multiplier() -> None:
    trigger, allowed = lab._activation(
        policy="DD2_STALL5_A040",
        current_dd=Decimal("2.1"),
        base_multiplier=Decimal("1"),
    )
    assert trigger == "STALL5_A040"
    assert allowed is True

    _trigger, defensive = lab._activation(
        policy="DEFENSIVE_STALL5_A040",
        current_dd=Decimal("0"),
        base_multiplier=Decimal("0.55"),
    )
    assert defensive is True

    _trigger, not_defensive = lab._activation(
        policy="DEFENSIVE_STALL5_A040",
        current_dd=Decimal("5"),
        base_multiplier=Decimal("0.75"),
    )
    assert not_defensive is False


def test_v18_contract_has_no_market_specific_thresholds() -> None:
    assert lab.DEPARTURE_R == Decimal("0.25")
    assert lab.CONSECUTIVE_CLOSES == 2
    assert all(minimum >= 3 for minimum, _adverse in lab.TRIGGER_SPECS.values())
    assert "DD3_STALL5_A040" in lab.POLICY_SPECS
