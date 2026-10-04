from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.mc25_governed_lifecycle import (
    MC25Stage,
    advance_mc25_stage,
    initial_mc25_state,
)


def _initial():
    return initial_mc25_state(
        candidate_id="wp04-v3b",
        configuration_fingerprint="a" * 64,
        evidence_refs=("freeze:sealed",),
    )


def _pass(state, stage):
    return advance_mc25_stage(
        state,
        target_stage=stage,
        stage_passed=True,
        evidence_refs=(f"evidence:{stage.value}",),
    )


def test_mc25_cannot_skip_formal_stress() -> None:
    state = _pass(_initial(), MC25Stage.LINEAGE_INTEGRITY)
    state = _pass(state, MC25Stage.PERFORMANCE_STRESS)
    with pytest.raises(ValueError, match="stage skip"):
        _pass(state, MC25Stage.SHADOW)


def test_failed_stage_terminalizes_exact_configuration() -> None:
    state = _pass(_initial(), MC25Stage.LINEAGE_INTEGRITY)
    failed = advance_mc25_stage(
        state,
        target_stage=MC25Stage.PERFORMANCE_STRESS,
        stage_passed=False,
        evidence_refs=("stress:falsified",),
    )
    assert failed.stage is MC25Stage.FALSIFIED
    assert failed.terminal is True
    assert failed.promotion_allowed is False
    with pytest.raises(ValueError, match="terminal"):
        _pass(failed, MC25Stage.FORMAL_STRESS)


def test_promotion_requires_full_chain_and_owner_approval() -> None:
    state = _initial()
    for stage in (
        MC25Stage.LINEAGE_INTEGRITY,
        MC25Stage.PERFORMANCE_STRESS,
        MC25Stage.FORMAL_STRESS,
        MC25Stage.SHADOW,
        MC25Stage.CERTIFICATION,
    ):
        state = _pass(state, stage)

    with pytest.raises(ValueError, match="owner approval"):
        _pass(state, MC25Stage.PROMOTION)

    promoted = advance_mc25_stage(
        state,
        target_stage=MC25Stage.PROMOTION,
        stage_passed=True,
        evidence_refs=("promotion:sealed",),
        owner_approval_ref="owner:explicit",
    )
    assert promoted.stage is MC25Stage.PROMOTION
    assert promoted.terminal is True
    assert promoted.promotion_allowed is True
    assert promoted.productive_authority is False
