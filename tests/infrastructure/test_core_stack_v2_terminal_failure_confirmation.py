from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.architecture_freeze import (
    superintelligence_freeze_contract,
)
from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    CompetingRiskBeliefState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
    PositionPathState,
)
from qore.infrastructure.core_stack_v2.recovery_failure_intelligence import (
    RecoveryChallengeState,
    RecoveryFailureAssessment,
)
from qore.infrastructure.core_stack_v2.terminal_failure_confirmation import (
    TerminalFailureState,
    assess_terminal_failure,
)

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _belief(
    *,
    stop_formation: int = 6200,
    target: int = 2800,
    uncertainty: int = 6800,
    path_available: bool = True,
) -> CompetingRiskBeliefState:
    return CompetingRiskBeliefState(
        as_of=NOW,
        stop_pressure_bps=5600,
        stop_formation_bps=stop_formation,
        target_capacity_bps=target,
        recovery_strength_bps=1200,
        uncertainty_bps=uncertainty,
        stop_hazard_proxy_bps=5600,
        target_hazard_proxy_bps=target,
        separation_margin_bps=2800,
        path_evidence_available=path_available,
    )


def _path(
    state: PositionPathState = PositionPathState.ADVERSE_DOMINANCE,
    *,
    terminal: int = 6600,
    adverse: int = 5400,
) -> PositionPathAssessment:
    return PositionPathAssessment(
        as_of=NOW,
        state=state,
        evidence_count=6,
        path_support_bps=3000,
        adverse_dominance_bps=adverse,
        adverse_persistence_bps=7000,
        recovery_persistence_bps=1000,
        winner_protection_bps=2600,
        terminal_failure_risk_bps=terminal,
        reasons=("TEST",),
    )


def _recovery(state: RecoveryChallengeState) -> RecoveryFailureAssessment:
    return RecoveryFailureAssessment(
        as_of=NOW,
        state=state,
        observations_since_formation=4,
        formation_persistence_bps=10000,
        recovery_persistence_bps=0,
        latest_stop_formation_bps=6200,
        latest_recovery_strength_bps=1200,
        latest_target_hazard_bps=2800,
        reasons=("TEST",),
    )


def test_failed_recovery_plus_terminal_path_confirms_terminal_failure() -> None:
    result = assess_terminal_failure(
        _belief(),
        _path(),
        _recovery(RecoveryChallengeState.RECOVERY_FAILED),
    )

    assert result.state is TerminalFailureState.TERMINAL_CONFIRMED
    assert "RECOVERY_FAILED" in result.reasons
    assert result.management_authority is False
    assert result.stop_mutation_authority is False


def test_recovery_active_vetoes_terminal_confirmation() -> None:
    result = assess_terminal_failure(
        _belief(),
        _path(),
        _recovery(RecoveryChallengeState.RECOVERY_ACTIVE),
    )

    assert result.state is TerminalFailureState.RECOVERY_VETO
    assert "TERMINAL_CONFIRMATION_VETOED" in result.reasons


def test_recovery_restored_vetoes_terminal_confirmation() -> None:
    result = assess_terminal_failure(
        _belief(),
        _path(),
        _recovery(RecoveryChallengeState.RECOVERY_RESTORED),
    )

    assert result.state is TerminalFailureState.RECOVERY_VETO


def test_failed_recovery_with_weak_terminal_path_remains_forming() -> None:
    result = assess_terminal_failure(
        _belief(),
        _path(terminal=5600, adverse=4400),
        _recovery(RecoveryChallengeState.RECOVERY_FAILED),
    )

    assert result.state is TerminalFailureState.TERMINAL_FORMING
    assert "FULL_TERMINAL_PATH_CONFIRMATION_NOT_YET_MET" in result.reasons


def test_high_uncertainty_prevents_terminal_confirmation() -> None:
    result = assess_terminal_failure(
        _belief(uncertainty=8200),
        _path(),
        _recovery(RecoveryChallengeState.RECOVERY_FAILED),
    )

    assert result.state is TerminalFailureState.TERMINAL_FORMING


def test_missing_trade_path_is_insufficient() -> None:
    result = assess_terminal_failure(
        _belief(path_available=False),
        _path(PositionPathState.INSUFFICIENT),
        _recovery(RecoveryChallengeState.RECOVERY_FAILED),
    )

    assert result.state is TerminalFailureState.INSUFFICIENT


def test_terminal_failure_freeze_is_shadow_only() -> None:
    contract = superintelligence_freeze_contract()
    terminal = contract["shared_essential_intelligence"]["terminal_failure_confirmation"]

    assert terminal["required"] is True
    assert terminal["phase"] == "PHASE_1_SHADOW_ONLY"
    assert terminal["recovery_failed_alone_is_not_terminal"] is True
    assert terminal["terminal_confirmation_requires_trade_path_evidence"] is True
    assert terminal["active_or_restored_recovery_vetoes_terminal_confirmation"] is True
    assert terminal["management_authority"] is False
