from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as lab,
)


def test_loss_arms_and_win_resolves_memory() -> None:
    state = lab.FailureState()
    lab._apply_outcome(state, realized_r=Decimal("-1"), exit_reason="STOP")
    assert state.loss_streak == 1
    assert state.last_loss is True
    assert state.last_stop is True
    lab._apply_outcome(state, realized_r=Decimal("1"), exit_reason="TARGET")
    assert state.loss_streak == 0
    assert state.last_loss is False
    assert state.last_stop is False


def test_one_shot_consumption_hides_blocked_counterfactual() -> None:
    state = lab.FailureState(loss_streak=2, last_loss=True, last_stop=True)
    assert lab._should_block(semantics="LOSS2", state=state)
    lab._consume_token(state)
    assert state.loss_streak == 0
    assert state.last_loss is False
    assert state.last_stop is False


def test_stop_semantics_are_more_specific_than_loss() -> None:
    state = lab.FailureState(loss_streak=1, last_loss=True, last_stop=False)
    assert lab._should_block(semantics="LOSS1", state=state)
    assert not lab._should_block(semantics="STOP1", state=state)


def test_density_floor_and_risk_caps_are_predeclared() -> None:
    assert lab.MIN_DENSITY_RETENTION == Decimal("0.90")
    assert lab.POLICY_SPECS["LOSS1_STATE_020"][2] == Decimal("0.20")
    assert lab.POLICY_SPECS["LOSS1_STATE_035"][2] == Decimal("0.35")
