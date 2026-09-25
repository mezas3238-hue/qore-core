from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.causal_path_representation import (
    CausalPathPhase,
    CausalPathPoint,
    PathDirection,
    represent_causal_path,
)


def _point(
    *,
    stop: int,
    target: int,
    recovery: int,
    support: int,
    adverse: int,
    terminal: int,
    deterioration: int,
) -> CausalPathPoint:
    return CausalPathPoint(
        stop_pressure_bps=stop,
        target_capacity_bps=target,
        recovery_strength_bps=recovery,
        uncertainty_bps=3_000,
        path_support_bps=support,
        path_adverse_bps=adverse,
        path_recovery_bps=recovery,
        path_terminal_risk_bps=terminal,
        trajectory_support_bps=support,
        trajectory_adversity_bps=adverse,
        trajectory_deterioration_bps=deterioration,
        trajectory_recovery_bps=recovery,
        environment_support_bps=support,
        environment_adverse_bps=adverse,
        futures_terminal_bps=terminal,
        futures_recovery_bps=recovery,
    )


def test_terminal_acceleration_preserves_relations() -> None:
    points = (
        _point(
            stop=4_000,
            target=5_500,
            recovery=5_000,
            support=5_500,
            adverse=4_000,
            terminal=4_000,
            deterioration=4_000,
        ),
        _point(
            stop=5_500,
            target=5_000,
            recovery=4_500,
            support=5_000,
            adverse=5_500,
            terminal=5_500,
            deterioration=5_500,
        ),
        _point(
            stop=7_000,
            target=4_000,
            recovery=3_500,
            support=4_000,
            adverse=7_000,
            terminal=7_000,
            deterioration=7_000,
        ),
    )

    result = represent_causal_path(points)

    assert result.phase is CausalPathPhase.TERMINAL_ACCELERATION
    assert result.stop_direction is PathDirection.RISING
    assert result.target_direction is PathDirection.FALLING
    assert result.recovery_direction is PathDirection.FALLING
    assert result.stop_target_gap_bps == 3_000
    assert result.terminal_recovery_gap_bps == 3_500
    assert "TERMINAL_ACCELERATION" in result.motif_token()
    assert result.outcome_input_used is False
    assert result.future_market_used is False
    assert result.sizing_used is False
    assert result.risk_authority is False
    assert result.execution_authority is False


def test_recovery_reassertion_is_not_terminal() -> None:
    points = (
        _point(
            stop=5_500,
            target=4_500,
            recovery=3_500,
            support=4_000,
            adverse=6_000,
            terminal=5_500,
            deterioration=6_000,
        ),
        _point(
            stop=5_000,
            target=4_800,
            recovery=4_500,
            support=4_500,
            adverse=5_500,
            terminal=5_000,
            deterioration=5_000,
        ),
        _point(
            stop=4_500,
            target=5_200,
            recovery=5_500,
            support=5_500,
            adverse=4_500,
            terminal=5_000,
            deterioration=4_500,
        ),
    )

    result = represent_causal_path(points)

    assert result.phase is CausalPathPhase.RECOVERY_REASSERTION
    assert result.recovery_direction is PathDirection.RISING
    assert result.support_direction is PathDirection.RISING
    assert result.stop_direction is PathDirection.FALLING


def test_one_point_is_insufficient_but_valid() -> None:
    result = represent_causal_path(
        (
            _point(
                stop=5_000,
                target=5_000,
                recovery=5_000,
                support=5_000,
                adverse=5_000,
                terminal=5_000,
                deterioration=5_000,
            ),
        )
    )

    assert result.phase is CausalPathPhase.INSUFFICIENT
    assert result.evidence_count == 1


def test_bps_contract_is_fail_closed() -> None:
    with pytest.raises(ValueError):
        CausalPathPoint(
            stop_pressure_bps=10_001,
            target_capacity_bps=0,
            recovery_strength_bps=0,
            uncertainty_bps=0,
            path_support_bps=0,
            path_adverse_bps=0,
            path_recovery_bps=0,
            path_terminal_risk_bps=0,
            trajectory_support_bps=0,
            trajectory_adversity_bps=0,
            trajectory_deterioration_bps=0,
            trajectory_recovery_bps=0,
            environment_support_bps=0,
            environment_adverse_bps=0,
            futures_terminal_bps=0,
            futures_recovery_bps=0,
        )
