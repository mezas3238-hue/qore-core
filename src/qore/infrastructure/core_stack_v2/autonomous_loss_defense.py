"""Autonomous loss-defense intelligence for Shared Core.

This module converts already-causal Shared resident state into a monotonic
loss-defense directive. It is intentionally independent from any trader,
methodology, symbol, order type or account.

The policy may only improve a stop-equivalent loss boundary or hold it. It
cannot widen risk, change sizing, allocate capital, authorize an order or send
anything to a broker. Offline research may score the directive on historical
paths, but runtime inference never consumes realized outcome or future market
information.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathState,
)
from qore.infrastructure.core_stack_v2.recovery_failure_intelligence import (
    RecoveryChallengeState,
)
from qore.infrastructure.core_stack_v2.terminal_failure_confirmation import (
    TerminalFailureState,
)

ZERO = Decimal("0")
ONE = Decimal("1")


class AutonomousDefenseAction(StrEnum):
    HOLD = "HOLD"
    CAP_HALF_RISK = "CAP_HALF_RISK"
    CAP_QUARTER_RISK = "CAP_QUARTER_RISK"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class AutonomousLossDefensePolicy:
    minimum_integrity_bps: int = 7_500
    high_confidence_probability_bps: int = 9_000
    moderate_probability_bps: int = 9_000
    half_risk_cap_r: Decimal = Decimal("0.50")
    quarter_risk_cap_r: Decimal = Decimal("0.25")

    def __post_init__(self) -> None:
        for name in (
            "minimum_integrity_bps",
            "high_confidence_probability_bps",
            "moderate_probability_bps",
        ):
            bps_value = int(getattr(self, name))
            if not 0 <= bps_value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        for name in ("half_risk_cap_r", "quarter_risk_cap_r"):
            risk_value = Decimal(getattr(self, name))
            if not ZERO < risk_value <= ONE:
                raise ValueError(f"{name} must be within (0, 1]")
        if self.quarter_risk_cap_r > self.half_risk_cap_r:
            raise ValueError("quarter-risk cap cannot be looser than half-risk cap")


@dataclass(frozen=True, slots=True)
class AutonomousLossDefenseEvidence:
    as_of: datetime
    data_integrity_bps: int
    competing_risk_probability_bps: int
    path_state: PositionPathState
    environment_state: MarketEnvironmentState
    recovery_state: RecoveryChallengeState
    terminal_failure_state: TerminalFailureState

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "data_integrity_bps",
            "competing_risk_probability_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class AutonomousLossDefenseDirective:
    as_of: datetime
    action: AutonomousDefenseAction
    maximum_loss_r: Decimal | None
    reasons: tuple[str, ...]
    stop_widening_allowed: bool = False
    sizing_change_allowed: bool = False
    risk_budget_authority: bool = False
    order_authority: bool = False
    broker_execution_authority: bool = False
    realized_outcome_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.maximum_loss_r is not None and not ZERO < self.maximum_loss_r <= ONE:
            raise ValueError("maximum_loss_r must be within (0, 1]")
        if (
            self.stop_widening_allowed
            or self.sizing_change_allowed
            or self.risk_budget_authority
            or self.order_authority
            or self.broker_execution_authority
            or self.realized_outcome_used
            or self.future_market_used
        ):
            raise ValueError("Shared autonomous defense cannot carry trading authority")


def assess_autonomous_loss_defense(
    evidence: AutonomousLossDefenseEvidence,
    *,
    policy: AutonomousLossDefensePolicy | None = None,
) -> AutonomousLossDefenseDirective:
    """Select a monotonic loss-defense boundary from causal Shared state."""

    effective = policy or AutonomousLossDefensePolicy()
    if evidence.data_integrity_bps < effective.minimum_integrity_bps:
        return AutonomousLossDefenseDirective(
            as_of=evidence.as_of,
            action=AutonomousDefenseAction.INSUFFICIENT,
            maximum_loss_r=None,
            reasons=("DATA_INTEGRITY_INSUFFICIENT",),
        )

    if evidence.terminal_failure_state is TerminalFailureState.TERMINAL_CONFIRMED:
        return AutonomousLossDefenseDirective(
            as_of=evidence.as_of,
            action=AutonomousDefenseAction.CAP_QUARTER_RISK,
            maximum_loss_r=effective.quarter_risk_cap_r,
            reasons=("TERMINAL_FAILURE_CONFIRMED",),
        )

    validated_context = (
        evidence.competing_risk_probability_bps
        >= effective.high_confidence_probability_bps
        and evidence.path_state is PositionPathState.CONTESTED
        and evidence.environment_state is MarketEnvironmentState.FRAGILE
    )
    if validated_context:
        return AutonomousLossDefenseDirective(
            as_of=evidence.as_of,
            action=AutonomousDefenseAction.CAP_QUARTER_RISK,
            maximum_loss_r=effective.quarter_risk_cap_r,
            reasons=(
                "HIGH_CONFIDENCE_COMPETING_RISK",
                "CONTESTED_PATH_IN_FRAGILE_ENVIRONMENT",
            ),
        )

    recovery_veto = evidence.recovery_state in {
        RecoveryChallengeState.RECOVERY_ACTIVE,
        RecoveryChallengeState.RECOVERY_RESTORED,
    } or evidence.path_state in {
        PositionPathState.RECOVERING,
        PositionPathState.HEALTHY_PULLBACK,
        PositionPathState.FAVORABLE_EXPANSION,
    }
    if recovery_veto:
        return AutonomousLossDefenseDirective(
            as_of=evidence.as_of,
            action=AutonomousDefenseAction.HOLD,
            maximum_loss_r=None,
            reasons=("RECOVERY_OR_WINNER_PATH_VETO",),
        )

    moderate_adversity = (
        evidence.competing_risk_probability_bps
        >= effective.moderate_probability_bps
        and evidence.path_state
        in {
            PositionPathState.ADVERSE_DOMINANCE,
            PositionPathState.FAILURE_RISK,
        }
    )
    if moderate_adversity:
        return AutonomousLossDefenseDirective(
            as_of=evidence.as_of,
            action=AutonomousDefenseAction.CAP_HALF_RISK,
            maximum_loss_r=effective.half_risk_cap_r,
            reasons=(
                "HIGH_COMPETING_RISK_PROBABILITY",
                "PATH_ADVERSITY_CONFIRMED",
            ),
        )

    return AutonomousLossDefenseDirective(
        as_of=evidence.as_of,
        action=AutonomousDefenseAction.HOLD,
        maximum_loss_r=None,
        reasons=("NO_AUTONOMOUS_DEFENSE_TRIGGER",),
    )
