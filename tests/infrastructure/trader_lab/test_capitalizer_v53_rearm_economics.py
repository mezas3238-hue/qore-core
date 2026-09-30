from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.capitalizer_v50_m1_rearm_capacity import (
    V50RearmAttempt,
)
from qore.infrastructure.trader_lab.capitalizer_v53_rearm_economics import (
    _direction,
    _selected_attempts,
)


def _attempt(
    *,
    minute: int,
    attempt_index: int,
    geometry_ready: bool,
    cognitive_ready: bool,
    setup_minute: int = 0,
) -> V50RearmAttempt:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    return V50RearmAttempt(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="TEST",
        m15_setup_confirmed_at=(at + timedelta(minutes=setup_minute)).isoformat(),
        m15_protected_swing_price="99",
        trigger_confirmed_at=(at + timedelta(minutes=minute)).isoformat(),
        trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="102",
        attempt_index=attempt_index,
        geometry_decision="READY" if geometry_ready else "WAIT_STOP_BREATHING",
        cognitive_disposition=(
            "PASS_TO_COMPETITION" if cognitive_ready else "WAIT_REFRESH_H1"
        ),
        geometry_ready=geometry_ready,
        cognitive_geometry_ready=cognitive_ready,
    )


def test_v53_geometry_and_cognitive_choose_different_rearm_attempts() -> None:
    first = _attempt(
        minute=5,
        attempt_index=1,
        geometry_ready=True,
        cognitive_ready=False,
    )
    second = _attempt(
        minute=9,
        attempt_index=2,
        geometry_ready=True,
        cognitive_ready=True,
    )

    geometry = _selected_attempts((first, second), policy="GEOMETRY_REARM")
    cognitive = _selected_attempts((first, second), policy="COGNITIVE_REARM")

    assert geometry == ((first, first.trigger_confirmed_at),)
    assert cognitive == ((second, first.trigger_confirmed_at),)


def test_v53_rearm_groups_attempts_by_parent_m15_setup() -> None:
    first_setup = _attempt(
        minute=5,
        attempt_index=1,
        geometry_ready=True,
        cognitive_ready=True,
        setup_minute=0,
    )
    second_setup = _attempt(
        minute=8,
        attempt_index=1,
        geometry_ready=True,
        cognitive_ready=True,
        setup_minute=1,
    )
    chosen = _selected_attempts(
        (first_setup, second_setup),
        policy="COGNITIVE_REARM",
    )
    assert len(chosen) == 2


def test_v53_direction_is_inferred_from_thesis_stop_geometry() -> None:
    bullish = _attempt(
        minute=5,
        attempt_index=1,
        geometry_ready=True,
        cognitive_ready=True,
    )
    assert _direction(bullish) == "BULLISH"

    bearish = V50RearmAttempt(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_from=bullish.h1_state_from,
        h1_state_until=bullish.h1_state_until,
        h1_state_basis="TEST",
        m15_setup_confirmed_at=bullish.m15_setup_confirmed_at,
        m15_protected_swing_price="101",
        trigger_confirmed_at=bullish.trigger_confirmed_at,
        trigger_family=bullish.trigger_family,
        decision_reference_price="100",
        structural_target_witness_price="98",
        attempt_index=1,
        geometry_decision="READY",
        cognitive_disposition="PASS_TO_COMPETITION",
        geometry_ready=True,
        cognitive_geometry_ready=True,
    )
    assert _direction(bearish) == "BEARISH"
