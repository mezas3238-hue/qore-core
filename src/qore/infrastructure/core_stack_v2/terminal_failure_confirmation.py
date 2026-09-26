"""Shadow-only terminal-failure confirmation for Shared CCRPC.

This layer closes a specific phase-one gap:

    stop formation -> recovery challenge -> failed recovery -> terminal failure

Recovery failure alone is not enough to call a terminal stop. Confirmation
requires the trade-specific path to show materially adverse dominance and
terminal-failure pressure while target capacity is weak and uncertainty is
bounded.

The result is diagnostic only. It carries no stop, sizing, risk, order, or
execution authority.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

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


class TerminalFailureState(StrEnum):
    TERMINAL_CONFIRMED = "TERMINAL_CONFIRMED"
    EXTREME_ADVERSE_AMBIGUITY = "EXTREME_ADVERSE_AMBIGUITY"
    TERMINAL_FORMING = "TERMINAL_FORMING"
    RECOVERY_VETO = "RECOVERY_VETO"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class TerminalFailurePolicy:
    minimum_stop_formation_bps: int = 5_750
    minimum_terminal_failure_bps: int = 6_200
    minimum_adverse_dominance_bps: int = 5_000
    maximum_target_hazard_bps: int = 3_500
    maximum_uncertainty_bps: int = 7_000
    extreme_stop_formation_bps: int = 7_000

    def __post_init__(self) -> None:
        for name in (
            "minimum_stop_formation_bps",
            "minimum_terminal_failure_bps",
            "minimum_adverse_dominance_bps",
            "maximum_target_hazard_bps",
            "maximum_uncertainty_bps",
            "extreme_stop_formation_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class TerminalFailureAssessment:
    as_of: datetime
    state: TerminalFailureState
    stop_formation_bps: int
    terminal_failure_bps: int
    adverse_dominance_bps: int
    target_hazard_bps: int
    uncertainty_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    management_authority: bool = False
    stop_mutation_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "stop_formation_bps",
            "terminal_failure_bps",
            "adverse_dominance_bps",
            "target_hazard_bps",
            "uncertainty_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.management_authority
            or self.stop_mutation_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("terminal-failure confirmation is shadow-only")


def assess_terminal_failure(
    belief: CompetingRiskBeliefState,
    path: PositionPathAssessment,
    recovery: RecoveryFailureAssessment,
    *,
    policy: TerminalFailurePolicy | None = None,
) -> TerminalFailureAssessment:
    """Confirm terminal failure only after failed recovery plus path evidence."""
    effective = policy or TerminalFailurePolicy()
    if path.as_of != belief.as_of or recovery.as_of != belief.as_of:
        raise ValueError("belief, path, and recovery assessment must share as_of")

    reasons: list[str] = []
    if (
        not belief.path_evidence_available
        or path.state is PositionPathState.INSUFFICIENT
        or recovery.state is RecoveryChallengeState.INSUFFICIENT
    ):
        state = TerminalFailureState.INSUFFICIENT
        reasons.append("TRADE_PATH_OR_RECOVERY_EVIDENCE_INSUFFICIENT")
    elif recovery.state in {
        RecoveryChallengeState.RECOVERY_ACTIVE,
        RecoveryChallengeState.RECOVERY_RESTORED,
    }:
        state = TerminalFailureState.RECOVERY_VETO
        reasons.extend(
            (
                "RECOVERY_EVIDENCE_ACTIVE",
                "TERMINAL_CONFIRMATION_VETOED",
            )
        )
    elif recovery.state is not RecoveryChallengeState.RECOVERY_FAILED:
        state = TerminalFailureState.CONTESTED
        reasons.append("RECOVERY_FAILURE_NOT_ESTABLISHED")
    else:
        confirmed = (
            belief.stop_formation_bps >= effective.minimum_stop_formation_bps
            and path.terminal_failure_risk_bps
            >= effective.minimum_terminal_failure_bps
            and path.adverse_dominance_bps
            >= effective.minimum_adverse_dominance_bps
            and belief.target_hazard_proxy_bps
            <= effective.maximum_target_hazard_bps
            and belief.uncertainty_bps <= effective.maximum_uncertainty_bps
        )
        extreme_contested_adversity = (
            confirmed
            and path.state is PositionPathState.CONTESTED
            and belief.stop_formation_bps > effective.extreme_stop_formation_bps
        )
        if extreme_contested_adversity:
            state = TerminalFailureState.EXTREME_ADVERSE_AMBIGUITY
            reasons.extend(
                (
                    "RECOVERY_FAILED",
                    "EXTREME_ADVERSE_PRESSURE_PRESENT",
                    "TRADE_PATH_STILL_CONTESTED",
                    "EXTREME_PRESSURE_MAY_BE_EXHAUSTION_OR_LIQUIDITY_SWEEP",
                    "TERMINAL_CONFIRMATION_DEFERRED",
                )
            )
        elif confirmed:
            state = TerminalFailureState.TERMINAL_CONFIRMED
            reasons.extend(
                (
                    "RECOVERY_FAILED",
                    "STOP_FORMATION_PERSISTED",
                    "TRADE_PATH_TERMINAL_PRESSURE_HIGH",
                    "ADVERSE_DOMINANCE_HIGH",
                    "TARGET_CAPACITY_WEAK",
                    "UNCERTAINTY_BOUNDED",
                )
            )
        elif (
            belief.stop_formation_bps >= effective.minimum_stop_formation_bps
            and belief.target_hazard_proxy_bps
            <= effective.maximum_target_hazard_bps
        ):
            state = TerminalFailureState.TERMINAL_FORMING
            reasons.extend(
                (
                    "RECOVERY_FAILED",
                    "STOP_FORMATION_PERSISTS",
                    "FULL_TERMINAL_PATH_CONFIRMATION_NOT_YET_MET",
                )
            )
        else:
            state = TerminalFailureState.CONTESTED
            reasons.append("FAILED_RECOVERY_WITHOUT_TERMINAL_PATH_SEPARATION")

    return TerminalFailureAssessment(
        as_of=belief.as_of,
        state=state,
        stop_formation_bps=belief.stop_formation_bps,
        terminal_failure_bps=path.terminal_failure_risk_bps,
        adverse_dominance_bps=path.adverse_dominance_bps,
        target_hazard_bps=belief.target_hazard_proxy_bps,
        uncertainty_bps=belief.uncertainty_bps,
        reasons=tuple(dict.fromkeys(reasons)),
    )

def resolve_terminal_failure_sequence(
    assessments: Sequence[TerminalFailureAssessment],
    *,
    ambiguity_confirmations: int = 2,
) -> TerminalFailureAssessment:
    """Promote only persistent extreme ambiguity using causal history."""
    if not assessments:
        raise ValueError("at least one terminal-failure assessment is required")
    if ambiguity_confirmations < 2:
        raise ValueError("ambiguity_confirmations must be at least 2")

    for left, right in zip(assessments, assessments[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError(
                "terminal-failure assessments must be strictly increasing and causal"
            )

    latest = assessments[-1]
    if latest.state is not TerminalFailureState.EXTREME_ADVERSE_AMBIGUITY:
        return latest

    tail = tuple(assessments[-ambiguity_confirmations:])
    persistent = (
        len(tail) == ambiguity_confirmations
        and all(
            item.state is TerminalFailureState.EXTREME_ADVERSE_AMBIGUITY
            for item in tail
        )
    )
    if not persistent:
        return latest

    return replace(
        latest,
        state=TerminalFailureState.TERMINAL_CONFIRMED,
        reasons=tuple(
            dict.fromkeys(
                (
                    *latest.reasons,
                    "EXTREME_ADVERSE_AMBIGUITY_PERSISTED",
                    "TERMINAL_CONFIRMATION_PROMOTED_BY_CAUSAL_PERSISTENCE",
                )
            )
        ),
    )

