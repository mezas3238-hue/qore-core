from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.causal_state_filter import (
    FilteredCausalStateBelief,
)
from qore.infrastructure.core_stack_v2.factorized_causal_state import (
    factorize_causal_state,
)

ADVERSE = frozenset({"STOP", "TERMINAL"})
FAVORABLE = frozenset({"RECOVERY", "TARGET"})


def _belief(
    *,
    stop: int,
    terminal: int,
    recovery: int,
    target: int,
    no_event: int,
) -> FilteredCausalStateBelief:
    values = (
        ("STOP", stop),
        ("TERMINAL", terminal),
        ("RECOVERY", recovery),
        ("TARGET", target),
        ("NO_EVENT", no_event),
    )
    ranked = sorted(values, key=lambda item: item[1], reverse=True)
    return FilteredCausalStateBelief(
        as_of=datetime(2026, 9, 25, 20, 30, tzinfo=UTC),
        evidence_count=4,
        posterior_bps=values,
        dominant_state=ranked[0][0],
        dominance_margin_bps=ranked[0][1] - ranked[1][1],
        entropy_bps=7_500,
        confidence_bps=1_500,
        reasons=("TEST",),
    )


def test_no_event_dominance_does_not_erase_adverse_direction() -> None:
    result = factorize_causal_state(
        _belief(
            stop=2_500,
            terminal=1_500,
            recovery=800,
            target=700,
            no_event=4_500,
        ),
        adverse_states=ADVERSE,
        favorable_states=FAVORABLE,
        no_event_state="NO_EVENT",
    )

    assert result.no_event_bps == 4_500
    assert result.event_bps == 5_500
    assert result.dominant_direction == "ADVERSE"
    assert result.directional_margin_bps > 0


def test_no_event_dominance_does_not_erase_favorable_direction() -> None:
    result = factorize_causal_state(
        _belief(
            stop=500,
            terminal=500,
            recovery=2_500,
            target=2_000,
            no_event=4_500,
        ),
        adverse_states=ADVERSE,
        favorable_states=FAVORABLE,
        no_event_state="NO_EVENT",
    )

    assert result.dominant_direction == "FAVORABLE"
    assert result.directional_margin_bps < 0
    assert result.favorable_conditional_bps > result.adverse_conditional_bps


def test_zero_directional_mass_is_contested() -> None:
    result = factorize_causal_state(
        _belief(
            stop=0,
            terminal=0,
            recovery=0,
            target=0,
            no_event=10_000,
        ),
        adverse_states=ADVERSE,
        favorable_states=FAVORABLE,
        no_event_state="NO_EVENT",
    )

    assert result.dominant_direction == "CONTESTED"
    assert result.adverse_conditional_bps == 5_000
    assert result.favorable_conditional_bps == 5_000


def test_overlapping_direction_sets_fail_closed() -> None:
    with pytest.raises(ValueError):
        factorize_causal_state(
            _belief(
                stop=2_000,
                terminal=2_000,
                recovery=2_000,
                target=2_000,
                no_event=2_000,
            ),
            adverse_states=frozenset({"STOP", "TARGET"}),
            favorable_states=FAVORABLE,
            no_event_state="NO_EVENT",
        )
