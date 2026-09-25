from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    CompetingRiskBeliefState,
)
from qore.infrastructure.core_stack_v2.recovery_failure_intelligence import (
    RecoveryChallengeState,
    assess_recovery_failure,
)


def _belief(
    minute: int,
    *,
    formation: int,
    stop: int = 4500,
    target: int = 2500,
    recovery: int = 2000,
    path: bool = True,
) -> CompetingRiskBeliefState:
    return CompetingRiskBeliefState(
        as_of=datetime(2026, 9, 25, 12, 0, tzinfo=UTC) + timedelta(minutes=minute),
        stop_pressure_bps=stop,
        stop_formation_bps=formation,
        target_capacity_bps=target,
        recovery_strength_bps=recovery,
        uncertainty_bps=6500,
        stop_hazard_proxy_bps=stop,
        target_hazard_proxy_bps=target,
        separation_margin_bps=abs(stop - target),
        path_evidence_available=path,
    )


def test_single_formation_stays_pending() -> None:
    result = assess_recovery_failure(
        (_belief(1, formation=6200),)
    )

    assert result.state is RecoveryChallengeState.RECOVERY_PENDING
    assert result.observations_since_formation == 1


def test_persistent_formation_without_recovery_becomes_recovery_failed() -> None:
    result = assess_recovery_failure(
        (
            _belief(1, formation=6000, recovery=1800, target=2500),
            _belief(2, formation=6300, recovery=1700, target=2300),
            _belief(3, formation=6600, recovery=1600, target=2200),
        )
    )

    assert result.state is RecoveryChallengeState.RECOVERY_FAILED
    assert result.formation_persistence_bps == 10000
    assert result.recovery_persistence_bps == 0
    assert "RECOVERY_NEVER_CONFIRMED" in result.reasons


def test_recovery_strength_without_relaxed_formation_is_active_not_restored() -> None:
    result = assess_recovery_failure(
        (
            _belief(1, formation=6200, recovery=1800),
            _belief(2, formation=6100, recovery=7200, target=4200),
        )
    )

    assert result.state is RecoveryChallengeState.RECOVERY_ACTIVE


def test_recovery_reclaim_restores_path_after_formation() -> None:
    result = assess_recovery_failure(
        (
            _belief(1, formation=6200, recovery=1800, target=2500),
            _belief(2, formation=5800, recovery=5000, target=4200),
            _belief(3, formation=4200, recovery=7600, target=6500),
        )
    )

    assert result.state is RecoveryChallengeState.RECOVERY_RESTORED
    assert "STOP_FORMATION_RELAXED_OR_TARGET_CAPACITY_RECLAIMED" in result.reasons


def test_no_formation_is_not_tested() -> None:
    result = assess_recovery_failure(
        (
            _belief(1, formation=2500, recovery=1800),
            _belief(2, formation=3000, recovery=2000),
        )
    )

    assert result.state is RecoveryChallengeState.NOT_TESTED


def test_missing_path_is_insufficient() -> None:
    result = assess_recovery_failure(
        (_belief(1, formation=7000, path=False),)
    )

    assert result.state is RecoveryChallengeState.INSUFFICIENT


def test_recovery_failure_has_no_management_authority() -> None:
    result = assess_recovery_failure(
        (
            _belief(1, formation=6000),
            _belief(2, formation=6200),
            _belief(3, formation=6400),
        )
    )

    assert result.outcome_used is False
    assert result.future_market_used is False
    assert result.management_authority is False
    assert result.sizing_authority is False
    assert result.execution_authority is False
