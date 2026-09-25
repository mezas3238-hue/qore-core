"""Failure-of-recovery intelligence for Shared CCRPC.

Early adverse formation is not terminal by itself. This layer tracks what
happens after stop-formation pressure appears and separates:
- recovery still pending,
- recovery actively building,
- recovery restored,
- recovery failed persistently.

It is point-in-time, sequence-based, shadow-only, and carries no trade authority.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    CompetingRiskBeliefState,
)


class RecoveryChallengeState(StrEnum):
    NOT_TESTED = "NOT_TESTED"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RECOVERY_ACTIVE = "RECOVERY_ACTIVE"
    RECOVERY_RESTORED = "RECOVERY_RESTORED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class RecoveryFailurePolicy:
    lookback_observations: int = 5
    minimum_failure_observations: int = 3
    stop_formation_threshold_bps: int = 5_000
    recovery_confirm_bps: int = 6_500
    target_reclaim_bps: int = 6_000
    restored_stop_formation_cap_bps: int = 4_500

    def __post_init__(self) -> None:
        if self.lookback_observations < 3:
            raise ValueError("lookback_observations must be at least 3")
        if self.minimum_failure_observations < 2:
            raise ValueError("minimum_failure_observations must be at least 2")
        if self.minimum_failure_observations > self.lookback_observations:
            raise ValueError("minimum_failure_observations cannot exceed lookback")
        for name in (
            "stop_formation_threshold_bps",
            "recovery_confirm_bps",
            "target_reclaim_bps",
            "restored_stop_formation_cap_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class RecoveryFailureAssessment:
    as_of: datetime
    state: RecoveryChallengeState
    observations_since_formation: int
    formation_persistence_bps: int
    recovery_persistence_bps: int
    latest_stop_formation_bps: int
    latest_recovery_strength_bps: int
    latest_target_hazard_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    management_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.observations_since_formation < 0:
            raise ValueError("observations_since_formation cannot be negative")
        for name in (
            "formation_persistence_bps",
            "recovery_persistence_bps",
            "latest_stop_formation_bps",
            "latest_recovery_strength_bps",
            "latest_target_hazard_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.management_authority
            or self.sizing_authority
            or self.execution_authority
        ):
            raise ValueError("recovery-failure intelligence is shadow-only")


def _ratio(count: int, total: int) -> int:
    if total <= 0:
        return 0
    return count * 10_000 // total


def assess_recovery_failure(
    beliefs: Sequence[CompetingRiskBeliefState],
    *,
    policy: RecoveryFailurePolicy | None = None,
) -> RecoveryFailureAssessment:
    """Track whether recovery succeeds after causal stop formation begins."""
    if not beliefs:
        raise ValueError("at least one competing-risk belief is required")
    effective = policy or RecoveryFailurePolicy()
    for left, right in zip(beliefs, beliefs[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError("belief states must be strictly increasing and causal")

    latest = beliefs[-1]
    if not latest.path_evidence_available:
        return RecoveryFailureAssessment(
            as_of=latest.as_of,
            state=RecoveryChallengeState.INSUFFICIENT,
            observations_since_formation=0,
            formation_persistence_bps=0,
            recovery_persistence_bps=0,
            latest_stop_formation_bps=latest.stop_formation_bps,
            latest_recovery_strength_bps=latest.recovery_strength_bps,
            latest_target_hazard_bps=latest.target_hazard_proxy_bps,
            reasons=("TRADE_PATH_EVIDENCE_NOT_ESTABLISHED",),
        )

    search = tuple(beliefs[-effective.lookback_observations :])
    formation_indexes = [
        idx
        for idx, item in enumerate(search)
        if (
            item.path_evidence_available
            and item.stop_formation_bps >= effective.stop_formation_threshold_bps
            and item.recovery_strength_bps < effective.recovery_confirm_bps
        )
    ]
    if not formation_indexes:
        state = (
            RecoveryChallengeState.RECOVERY_ACTIVE
            if latest.recovery_strength_bps >= effective.recovery_confirm_bps
            else RecoveryChallengeState.NOT_TESTED
        )
        reasons = (
            ("RECOVERY_PRESENT_WITHOUT_ACTIVE_STOP_FORMATION",)
            if state is RecoveryChallengeState.RECOVERY_ACTIVE
            else ("NO_STOP_FORMATION_CHALLENGE_PRESENT",)
        )
        return RecoveryFailureAssessment(
            as_of=latest.as_of,
            state=state,
            observations_since_formation=0,
            formation_persistence_bps=0,
            recovery_persistence_bps=10_000 if state is RecoveryChallengeState.RECOVERY_ACTIVE else 0,
            latest_stop_formation_bps=latest.stop_formation_bps,
            latest_recovery_strength_bps=latest.recovery_strength_bps,
            latest_target_hazard_bps=latest.target_hazard_proxy_bps,
            reasons=reasons,
        )

    start = formation_indexes[0]
    challenge = search[start:]
    formation_count = sum(
        item.stop_formation_bps >= effective.stop_formation_threshold_bps
        for item in challenge
    )
    recovery_count = sum(
        item.recovery_strength_bps >= effective.recovery_confirm_bps
        for item in challenge
    )
    formation_persistence = _ratio(formation_count, len(challenge))
    recovery_persistence = _ratio(recovery_count, len(challenge))

    recovery_reclaimed = (
        latest.recovery_strength_bps >= effective.recovery_confirm_bps
        and (
            latest.stop_formation_bps <= effective.restored_stop_formation_cap_bps
            or latest.target_hazard_proxy_bps >= effective.target_reclaim_bps
        )
    )
    if recovery_reclaimed:
        state = RecoveryChallengeState.RECOVERY_RESTORED
        reasons = (
            "RECOVERY_STRENGTH_CONFIRMED",
            "STOP_FORMATION_RELAXED_OR_TARGET_CAPACITY_RECLAIMED",
        )
    elif latest.recovery_strength_bps >= effective.recovery_confirm_bps:
        state = RecoveryChallengeState.RECOVERY_ACTIVE
        reasons = (
            "RECOVERY_STRENGTH_RISING",
            "RECOVERY_NOT_YET_PROVEN_RESTORED",
        )
    elif (
        len(challenge) >= effective.minimum_failure_observations
        and formation_persistence == 10_000
        and recovery_persistence == 0
        and latest.target_hazard_proxy_bps < effective.target_reclaim_bps
    ):
        state = RecoveryChallengeState.RECOVERY_FAILED
        reasons = (
            "STOP_FORMATION_PERSISTED",
            "RECOVERY_NEVER_CONFIRMED",
            "TARGET_CAPACITY_NOT_RECLAIMED",
        )
    else:
        state = RecoveryChallengeState.RECOVERY_PENDING
        reasons = (
            "STOP_FORMATION_PRESENT",
            "WAITING_FOR_RECOVERY_OR_FAILURE_RESOLUTION",
        )

    return RecoveryFailureAssessment(
        as_of=latest.as_of,
        state=state,
        observations_since_formation=len(challenge),
        formation_persistence_bps=formation_persistence,
        recovery_persistence_bps=recovery_persistence,
        latest_stop_formation_bps=latest.stop_formation_bps,
        latest_recovery_strength_bps=latest.recovery_strength_bps,
        latest_target_hazard_bps=latest.target_hazard_proxy_bps,
        reasons=reasons,
    )
