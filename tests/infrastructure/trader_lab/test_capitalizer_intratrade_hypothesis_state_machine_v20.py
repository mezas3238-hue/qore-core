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
    capitalizer_intratrade_hypothesis_state_machine_v20 as lab,
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


def test_invalidating_state_can_recover_without_dead_exit() -> None:
    state = lab._State(period="DEV", trade=_trade())
    bars = (
        _bar(0, open_="100", high="100.10", low="99.90", close="100.00"),
        _bar(1, open_="100", high="100.05", low="99.80", close="99.95"),
        _bar(2, open_="100.00", high="100.02", low="99.55", close="99.60"),
        _bar(3, open_="99.60", high="99.90", low="99.58", close="99.85"),
    )
    triggers: tuple[v18.TriggerEvent, ...] = ()
    transitions: tuple[lab.TransitionEvent, ...] = ()
    for bar in bars:
        triggers, transitions = lab._process_bar(state, bar)

    assert triggers == ()
    assert any(
        row.spec == "HSM_BASE"
        and row.to_phase == lab.Phase.RECOVERED.value
        and row.reason == "CAUSAL_RECLAIM"
        for row in transitions
    )
    assert state.tracks is not None
    assert state.tracks["HSM_BASE"].phase is lab.Phase.RECOVERED


def test_persistent_structural_failure_reaches_dead() -> None:
    state = lab._State(period="DEV", trade=_trade())
    bars = (
        _bar(0, open_="100", high="100.10", low="99.90", close="100.00"),
        _bar(1, open_="100", high="100.05", low="99.80", close="99.95"),
        _bar(2, open_="100.00", high="100.02", low="99.55", close="99.60"),
        _bar(3, open_="99.60", high="99.72", low="99.40", close="99.50"),
        _bar(4, open_="99.50", high="99.60", low="99.30", close="99.40"),
    )
    all_triggers: list[v18.TriggerEvent] = []
    all_transitions: list[lab.TransitionEvent] = []
    for bar in bars:
        triggers, transitions = lab._process_bar(state, bar)
        all_triggers.extend(triggers)
        all_transitions.extend(transitions)

    assert any(row.trigger == "HSM_BASE" for row in all_triggers)
    assert any(
        row.spec == "HSM_BASE"
        and row.to_phase == lab.Phase.INVALIDATING.value
        for row in all_transitions
    )
    assert any(
        row.spec == "HSM_BASE"
        and row.to_phase == lab.Phase.DEAD.value
        and row.reason == "PERSISTENT_INVALIDATION_WITH_EXTENSION"
        for row in all_transitions
    )
    assert state.dead is not None
    assert "HSM_BASE" in state.dead
    assert all(row.current_outcome_visible is False for row in all_transitions)
    assert all(row.future_bars_visible is False for row in all_transitions)


def test_departure_terminates_failure_state_evaluation() -> None:
    state = lab._State(period="DEV", trade=_trade())
    departure = _bar(
        0,
        open_="100.00",
        high="100.30",
        low="99.98",
        close="100.20",
    )
    triggers, transitions = lab._process_bar(state, departure)
    assert triggers == ()
    assert transitions == ()
    assert state.departed is True


def test_v20_has_recovery_hysteresis_and_keeps_holdout_sealed() -> None:
    assert lab.Phase.RECOVERED.value == "RECOVERED"
    assert lab.Phase.DEAD.value == "DEAD"
    assert set(lab.STATE_SPECS) == {"HSM_FAST", "HSM_BASE", "HSM_STRICT"}
    assert set(lab.POLICY_SPECS) == {
        "GLOBAL_HSM_FAST",
        "GLOBAL_HSM_BASE",
        "DD2_HSM_BASE",
        "DEFENSIVE_HSM_BASE",
        "GLOBAL_HSM_STRICT",
        "DD2_HSM_STRICT",
        "DEFENSIVE_HSM_STRICT",
    }
    assert "2018-09-17_TO_2020-09-17" not in lab.POLICY_SPECS
