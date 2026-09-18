"""Position Intelligence and Structural Rearm for VT31_NAS100.

The mechanics implement the Turtle Soup architectural lessons without copying
XAUUSD policy parameters.

- initial stop remains VT31 methodological invalidation;
- a stop may only stay or improve, never widen;
- a structural observation becomes actionable only after confirmation;
- conquered DOLs can be represented as protection candidates;
- contextual trailing thresholds are configuration learned from NAS100, not
  hard-coded from Turtle Soup;
- after a protected/trailing exit, re-entry requires a genuinely new VT31
  market event rather than an arbitrary time cooldown.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ManagementContext(StrEnum):
    SUPPORTIVE = "SUPPORTIVE"
    MIXED = "MIXED"
    CAUTIOUS = "CAUTIOUS"
    UNRESOLVED = "UNRESOLVED"


class PositionAction(StrEnum):
    HOLD = "HOLD"
    TRAIL = "TRAIL"
    DOL_LOCK = "DOL_LOCK"
    BANK = "BANK"
    EXTEND = "EXTEND"
    EXIT = "EXIT"
    REARM_REQUIRED = "REARM_REQUIRED"


@dataclass(frozen=True, slots=True)
class ContextualTrailingPolicy:
    """NAS100-learned parameters; None means policy not yet calibrated."""

    supportive_swing_confirmations: int | None
    mixed_swing_confirmations: int | None
    cautious_swing_confirmations: int | None
    dol_lock_enabled: bool

    def __post_init__(self) -> None:
        for value in (
            self.supportive_swing_confirmations,
            self.mixed_swing_confirmations,
            self.cautious_swing_confirmations,
        ):
            if value is not None and value < 1:
                raise ValueError("swing confirmations must be >=1 or None")

    def confirmations_for(self, state: ManagementContext) -> int | None:
        if state is ManagementContext.SUPPORTIVE:
            return self.supportive_swing_confirmations
        if state is ManagementContext.MIXED:
            return self.mixed_swing_confirmations
        if state is ManagementContext.CAUTIOUS:
            return self.cautious_swing_confirmations
        return None


RESEARCH_UNCALIBRATED_POLICY = ContextualTrailingPolicy(
    supportive_swing_confirmations=None,
    mixed_swing_confirmations=None,
    cautious_swing_confirmations=None,
    dol_lock_enabled=False,
)


@dataclass(frozen=True, slots=True)
class StructuralProtectionCandidate:
    level: Decimal
    confirmations: int
    source: str

    def __post_init__(self) -> None:
        if not self.level.is_finite() or self.level <= 0:
            raise ValueError("protection level must be positive finite")
        if self.confirmations < 1:
            raise ValueError("protection candidate requires confirmation")


@dataclass(frozen=True, slots=True)
class PositionManagementDecision:
    action: PositionAction
    next_stop: Decimal | None
    reason: str
    policy_calibrated: bool


def improves_stop(
    *,
    side: str,
    current_stop: Decimal,
    candidate_stop: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return current_stop < candidate_stop < target
    if side == "short":
        return target < candidate_stop < current_stop
    raise ValueError(f"unsupported side: {side}")


def decide_structural_protection(
    *,
    side: str,
    current_stop: Decimal,
    target: Decimal,
    context: ManagementContext,
    swing: StructuralProtectionCandidate | None,
    conquered_dol: Decimal | None,
    policy: ContextualTrailingPolicy = RESEARCH_UNCALIBRATED_POLICY,
) -> PositionManagementDecision:
    """Choose protection without ever widening or copying XAUUSD thresholds."""
    required = policy.confirmations_for(context)

    # A conquered DOL is supported mechanically, but it is not activated until
    # NAS100 position-management research explicitly enables it.
    if (
        policy.dol_lock_enabled
        and conquered_dol is not None
        and improves_stop(
            side=side,
            current_stop=current_stop,
            candidate_stop=conquered_dol,
            target=target,
        )
    ):
        return PositionManagementDecision(
            action=PositionAction.DOL_LOCK,
            next_stop=conquered_dol,
            reason="CONQUERED_DOL_STRUCTURAL_PROTECTION",
            policy_calibrated=True,
        )

    if required is None:
        return PositionManagementDecision(
            action=PositionAction.HOLD,
            next_stop=None,
            reason="VT31_CONTEXTUAL_TRAILING_NOT_YET_CALIBRATED",
            policy_calibrated=False,
        )

    if swing is None or swing.confirmations < required:
        return PositionManagementDecision(
            action=PositionAction.HOLD,
            next_stop=None,
            reason="ADDITIONAL_STRUCTURAL_CONFIRMATION_REQUIRED",
            policy_calibrated=True,
        )

    if not improves_stop(
        side=side,
        current_stop=current_stop,
        candidate_stop=swing.level,
        target=target,
    ):
        return PositionManagementDecision(
            action=PositionAction.HOLD,
            next_stop=None,
            reason="CANDIDATE_DOES_NOT_IMPROVE_STOP",
            policy_calibrated=True,
        )

    return PositionManagementDecision(
        action=PositionAction.TRAIL,
        next_stop=swing.level,
        reason=f"{context.value}_CONFIRMED_STRUCTURAL_PROTECTION",
        policy_calibrated=True,
    )


def structurally_rearmed(
    *,
    protected_exit_at_epoch: int | None,
    new_raid_at_epoch: int,
    new_confirmation_at_epoch: int,
    new_decision_at_epoch: int,
) -> bool:
    """VT31 rearm: require a new raid + confirmation + decision after exit."""
    if protected_exit_at_epoch is None:
        return True
    return bool(
        new_raid_at_epoch > protected_exit_at_epoch
        and new_confirmation_at_epoch > protected_exit_at_epoch
        and new_decision_at_epoch > protected_exit_at_epoch
    )
