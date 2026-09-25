from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeObservation,
    AdversityChallengeState,
    assess_adversity_challenge,
)


BASE = datetime(2026, 9, 25, 15, 0, tzinfo=UTC)


def _row(
    index: int,
    *,
    path_support: int = 7000,
    path_adverse: int = 2500,
    path_terminal: int = 2000,
    winner: int = 6500,
    trajectory_support: int = 7000,
    trajectory_adverse: int = 2500,
    environment_support: int = 7500,
    environment_adverse: int = 2000,
    recovery: int = 6500,
    target: int = 6500,
    futures_terminal: int = 2000,
    futures_recovery: int = 6500,
    uncertainty: int = 2000,
) -> AdversityChallengeObservation:
    return AdversityChallengeObservation(
        as_of=BASE + timedelta(minutes=index),
        data_integrity_bps=10_000,
        path_support_bps=path_support,
        path_adverse_bps=path_adverse,
        path_terminal_bps=path_terminal,
        winner_protection_bps=winner,
        trajectory_support_bps=trajectory_support,
        trajectory_adverse_bps=trajectory_adverse,
        environment_support_bps=environment_support,
        environment_adverse_bps=environment_adverse,
        recovery_strength_bps=recovery,
        target_capacity_bps=target,
        futures_terminal_bps=futures_terminal,
        futures_recovery_bps=futures_recovery,
        uncertainty_bps=uncertainty,
    )


def test_local_collapse_with_broad_support_is_not_terminal() -> None:
    rows = [
        _row(0),
        _row(1),
        _row(2),
        _row(
            3,
            path_support=2500,
            path_adverse=8000,
            path_terminal=7500,
            winner=2500,
            trajectory_support=3000,
            trajectory_adverse=7800,
            futures_terminal=7800,
            recovery=2500,
            target=2500,
            futures_recovery=2500,
        ),
    ]
    result = assess_adversity_challenge(rows)
    assert result.state is AdversityChallengeState.LOCAL_COLLAPSE_BROAD_SUPPORT_INTACT
    assert result.broad_support_reserve_bps > 0


def test_local_and_broad_deterioration_is_separate_state() -> None:
    rows = [
        _row(0),
        _row(1, environment_support=6500, environment_adverse=3000),
        _row(2, environment_support=5000, environment_adverse=4500),
        _row(
            3,
            path_support=2500,
            path_adverse=8500,
            path_terminal=8000,
            winner=2000,
            trajectory_support=2500,
            trajectory_adverse=8200,
            environment_support=3000,
            environment_adverse=7500,
            recovery=1800,
            target=1800,
            futures_terminal=8200,
            futures_recovery=1800,
        ),
    ]
    result = assess_adversity_challenge(rows)
    assert result.state in {
        AdversityChallengeState.LOCAL_AND_BROAD_DETERIORATION,
        AdversityChallengeState.TERMINAL_CONVERGENCE,
    }
    assert result.broad_support_velocity_bps < 0


def test_recovery_reassertion_has_priority_over_stale_adversity() -> None:
    rows = [
        _row(
            0,
            path_support=2500,
            path_adverse=7500,
            path_terminal=7000,
            recovery=2000,
            target=2500,
            futures_terminal=7500,
            futures_recovery=2000,
        ),
        _row(
            1,
            path_support=3000,
            path_adverse=7000,
            path_terminal=6500,
            recovery=3000,
            target=3500,
            futures_terminal=6500,
            futures_recovery=3000,
        ),
        _row(
            2,
            path_support=4500,
            path_adverse=5500,
            path_terminal=5000,
            recovery=5000,
            target=5200,
            futures_terminal=5000,
            futures_recovery=5200,
        ),
        _row(
            3,
            path_support=6500,
            path_adverse=3500,
            path_terminal=3000,
            recovery=7500,
            target=7200,
            futures_terminal=3000,
            futures_recovery=7600,
        ),
    ]
    result = assess_adversity_challenge(rows)
    assert result.state is AdversityChallengeState.RECOVERY_REASSERTING
    assert result.recovery_velocity_bps > 0


def test_high_uncertainty_forces_contested() -> None:
    rows = [_row(i) for i in range(3)]
    rows.append(
        _row(
            3,
            path_support=2000,
            path_adverse=8500,
            path_terminal=8500,
            uncertainty=9000,
        )
    )
    result = assess_adversity_challenge(rows)
    assert result.state is AdversityChallengeState.CONTESTED


def test_module_carries_no_authority() -> None:
    result = assess_adversity_challenge([_row(i) for i in range(4)])
    assert result.outcome_used is False
    assert result.pnl_used is False
    assert result.sizing_authority is False
    assert result.risk_authority is False
    assert result.order_authority is False
    assert result.execution_authority is False
