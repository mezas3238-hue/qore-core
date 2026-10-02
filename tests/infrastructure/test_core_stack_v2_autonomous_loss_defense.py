from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.core_stack_v2.autonomous_loss_defense import (
    AutonomousDefenseAction,
    AutonomousLossDefenseEvidence,
    assess_autonomous_loss_defense,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import PositionPathState
from qore.infrastructure.core_stack_v2.recovery_failure_intelligence import (
    RecoveryChallengeState,
)
from qore.infrastructure.core_stack_v2.terminal_failure_confirmation import (
    TerminalFailureState,
)

NOW = datetime(2026, 9, 25, 13, 0, tzinfo=UTC)


def _evidence(
    *,
    probability_bps: int = 5_000,
    path: PositionPathState = PositionPathState.CONTESTED,
    environment: MarketEnvironmentState = MarketEnvironmentState.SUPPORTIVE,
    recovery: RecoveryChallengeState = RecoveryChallengeState.NOT_TESTED,
    terminal: TerminalFailureState = TerminalFailureState.CONTESTED,
) -> AutonomousLossDefenseEvidence:
    return AutonomousLossDefenseEvidence(
        as_of=NOW,
        data_integrity_bps=10_000,
        competing_risk_probability_bps=probability_bps,
        path_state=path,
        environment_state=environment,
        recovery_state=recovery,
        terminal_failure_state=terminal,
    )


def test_terminal_failure_caps_quarter_risk() -> None:
    result = assess_autonomous_loss_defense(
        _evidence(terminal=TerminalFailureState.TERMINAL_CONFIRMED)
    )
    assert result.action is AutonomousDefenseAction.CAP_QUARTER_RISK
    assert result.maximum_loss_r == Decimal("0.25")
    assert result.stop_widening_allowed is False
    assert result.sizing_change_allowed is False
    assert result.broker_execution_authority is False


def test_validated_contested_fragile_context_caps_quarter_risk() -> None:
    result = assess_autonomous_loss_defense(
        _evidence(
            probability_bps=9_000,
            path=PositionPathState.CONTESTED,
            environment=MarketEnvironmentState.FRAGILE,
        )
    )
    assert result.action is AutonomousDefenseAction.CAP_QUARTER_RISK
    assert result.maximum_loss_r == Decimal("0.25")


def test_adverse_path_caps_half_risk() -> None:
    result = assess_autonomous_loss_defense(
        _evidence(
            probability_bps=9_000,
            path=PositionPathState.ADVERSE_DOMINANCE,
            environment=MarketEnvironmentState.SUPPORTIVE,
            recovery=RecoveryChallengeState.RECOVERY_FAILED,
        )
    )
    assert result.action is AutonomousDefenseAction.CAP_HALF_RISK
    assert result.maximum_loss_r == Decimal("0.50")


def test_recovery_veto_prevents_moderate_defense() -> None:
    result = assess_autonomous_loss_defense(
        _evidence(
            probability_bps=9_800,
            path=PositionPathState.ADVERSE_DOMINANCE,
            recovery=RecoveryChallengeState.RECOVERY_RESTORED,
        )
    )
    assert result.action is AutonomousDefenseAction.HOLD
    assert result.maximum_loss_r is None


def test_winner_path_veto_prevents_moderate_defense() -> None:
    result = assess_autonomous_loss_defense(
        _evidence(
            probability_bps=9_800,
            path=PositionPathState.HEALTHY_PULLBACK,
            recovery=RecoveryChallengeState.RECOVERY_PENDING,
        )
    )
    assert result.action is AutonomousDefenseAction.HOLD
    assert result.maximum_loss_r is None
