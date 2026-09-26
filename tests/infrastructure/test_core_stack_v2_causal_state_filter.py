from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.causal_state_filter import (
    CausalStateEmission,
    filter_causal_state_sequence,
)

STATES = ("STOP", "TERMINAL", "RECOVERY", "TARGET", "NO_EVENT")

TRANSITIONS = {
    state: {
        target: 6_000 if target == state else 1_000
        for target in STATES
    }
    for state in STATES
}


def _frame(
    minute: int,
    *,
    stop: int,
    terminal: int,
    recovery: int,
    target: int,
    no_event: int,
    uncertainty: int = 1_500,
) -> CausalStateEmission:
    return CausalStateEmission(
        as_of=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        + timedelta(minutes=minute),
        probabilities_bps=(
            ("STOP", stop),
            ("TERMINAL", terminal),
            ("RECOVERY", recovery),
            ("TARGET", target),
            ("NO_EVENT", no_event),
        ),
        uncertainty_bps=uncertainty,
    )


def test_persistent_terminal_emissions_accumulate() -> None:
    beliefs = filter_causal_state_sequence(
        (
            _frame(
                0,
                stop=4_000,
                terminal=3_000,
                recovery=1_000,
                target=500,
                no_event=1_500,
            ),
            _frame(
                1,
                stop=4_500,
                terminal=3_000,
                recovery=800,
                target=400,
                no_event=1_300,
            ),
            _frame(
                2,
                stop=5_000,
                terminal=3_000,
                recovery=700,
                target=300,
                no_event=1_000,
            ),
        ),
        transition_bps=TRANSITIONS,
    )

    assert beliefs[-1].dominant_state in {"STOP", "TERMINAL"}
    assert beliefs[-1].probability_bps("STOP") > beliefs[0].probability_bps("STOP")
    assert beliefs[-1].outcome_used is False
    assert beliefs[-1].pnl_used is False
    assert beliefs[-1].future_market_used is False
    assert beliefs[-1].risk_authority is False
    assert beliefs[-1].execution_authority is False


def test_recovery_sequence_can_overturn_old_adverse_prior() -> None:
    beliefs = filter_causal_state_sequence(
        (
            _frame(
                0,
                stop=5_000,
                terminal=2_500,
                recovery=800,
                target=500,
                no_event=1_200,
            ),
            _frame(
                1,
                stop=4_000,
                terminal=2_000,
                recovery=2_000,
                target=800,
                no_event=1_200,
            ),
            _frame(
                2,
                stop=1_000,
                terminal=500,
                recovery=5_000,
                target=2_000,
                no_event=1_500,
            ),
            _frame(
                3,
                stop=700,
                terminal=300,
                recovery=5_200,
                target=2_500,
                no_event=1_300,
            ),
        ),
        transition_bps=TRANSITIONS,
    )

    final = beliefs[-1]
    assert final.dominant_state == "RECOVERY"
    assert final.probability_bps("RECOVERY") > final.probability_bps("STOP")


def test_high_uncertainty_tempers_current_emission() -> None:
    low_uncertainty = filter_causal_state_sequence(
        (
            _frame(
                0,
                stop=2_000,
                terminal=1_000,
                recovery=2_000,
                target=2_000,
                no_event=3_000,
            ),
            _frame(
                1,
                stop=8_000,
                terminal=1_000,
                recovery=300,
                target=200,
                no_event=500,
                uncertainty=500,
            ),
        ),
        transition_bps=TRANSITIONS,
    )[-1]
    high_uncertainty = filter_causal_state_sequence(
        (
            _frame(
                0,
                stop=2_000,
                terminal=1_000,
                recovery=2_000,
                target=2_000,
                no_event=3_000,
            ),
            _frame(
                1,
                stop=8_000,
                terminal=1_000,
                recovery=300,
                target=200,
                no_event=500,
                uncertainty=9_000,
            ),
        ),
        transition_bps=TRANSITIONS,
    )[-1]

    assert low_uncertainty.probability_bps("STOP") > high_uncertainty.probability_bps(
        "STOP"
    )


def test_noncausal_order_fails_closed() -> None:
    with pytest.raises(ValueError):
        filter_causal_state_sequence(
            (
                _frame(
                    1,
                    stop=2_000,
                    terminal=1_000,
                    recovery=2_000,
                    target=2_000,
                    no_event=3_000,
                ),
                _frame(
                    0,
                    stop=2_000,
                    terminal=1_000,
                    recovery=2_000,
                    target=2_000,
                    no_event=3_000,
                ),
            ),
            transition_bps=TRANSITIONS,
        )
