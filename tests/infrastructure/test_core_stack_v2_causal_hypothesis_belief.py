from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.causal_hypothesis_belief import (
    CausalBeliefDisposition,
    CausalHypothesisEvidence,
    accumulate_causal_hypotheses,
)


def _frame(
    minute: int,
    *,
    terminal: int,
    recovery: int,
    target: int,
    no_event: int,
    uncertainty: int = 2_000,
) -> CausalHypothesisEvidence:
    return CausalHypothesisEvidence(
        as_of=datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(minutes=minute),
        terminal_bps=terminal,
        recovery_bps=recovery,
        target_bps=target,
        no_event_bps=no_event,
        uncertainty_bps=uncertainty,
    )


def test_persistent_terminal_evidence_becomes_dominant() -> None:
    result = accumulate_causal_hypotheses(
        (
            _frame(0, terminal=7_000, recovery=1_000, target=500, no_event=1_500),
            _frame(1, terminal=7_500, recovery=800, target=400, no_event=1_300),
            _frame(2, terminal=8_000, recovery=700, target=300, no_event=1_000),
        )
    )

    assert result.disposition is CausalBeliefDisposition.TERMINAL_DOMINANT
    assert result.terminal_bps > result.favorable_bps
    assert result.outcome_used is False
    assert result.pnl_used is False
    assert result.future_market_used is False
    assert result.sizing_authority is False
    assert result.risk_authority is False
    assert result.order_authority is False
    assert result.stop_authority is False
    assert result.target_authority is False
    assert result.execution_authority is False


def test_recent_recovery_can_overturn_old_adversity_without_future_data() -> None:
    result = accumulate_causal_hypotheses(
        (
            _frame(0, terminal=7_500, recovery=500, target=500, no_event=1_500),
            _frame(1, terminal=6_500, recovery=1_000, target=1_000, no_event=1_500),
            _frame(2, terminal=1_000, recovery=5_500, target=2_000, no_event=1_500),
            _frame(3, terminal=800, recovery=5_800, target=2_200, no_event=1_200),
        ),
        decay_bps=5_000,
    )

    assert result.disposition is CausalBeliefDisposition.FAVORABLE_DOMINANT
    assert result.favorable_bps > result.terminal_bps


def test_single_frame_is_insufficient_but_preserves_probability_mass() -> None:
    result = accumulate_causal_hypotheses(
        (
            _frame(0, terminal=4_000, recovery=2_000, target=1_000, no_event=3_000),
        )
    )

    assert result.disposition is CausalBeliefDisposition.INSUFFICIENT
    assert (
        result.terminal_bps
        + result.recovery_bps
        + result.target_bps
        + result.no_event_bps
        == 10_000
    )


def test_noncausal_time_order_fails_closed() -> None:
    with pytest.raises(ValueError):
        accumulate_causal_hypotheses(
            (
                _frame(1, terminal=4_000, recovery=2_000, target=1_000, no_event=3_000),
                _frame(0, terminal=4_000, recovery=2_000, target=1_000, no_event=3_000),
            )
        )
