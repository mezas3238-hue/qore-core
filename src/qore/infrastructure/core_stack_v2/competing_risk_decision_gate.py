"""Temporal decision gate for the Shared Competing-Risk Path Core.

A single bar may form a hypothesis but cannot confirm a destination. Confirmed
STOP/TARGET states require persistent separation across multiple causal belief
states. Recovery is an explicit veto against premature terminal classification.

Phase one is shadow-only and carries no trading authority.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    CompetingRiskBeliefState,
)


class CompetingRiskDecision(StrEnum):
    STOP_FORMING = "STOP_FORMING"
    STOP_LIKELY = "STOP_LIKELY"
    TARGET_FORMING = "TARGET_FORMING"
    TARGET_LIKELY = "TARGET_LIKELY"
    RECOVERABLE = "RECOVERABLE"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class CompetingRiskDecisionPolicy:
    confirmation_observations: int = 3
    hazard_threshold_bps: int = 6_500
    formation_threshold_bps: int = 5_000
    minimum_margin_bps: int = 1_800
    persistence_bps: int = 10_000
    maximum_uncertainty_bps: int = 6_500
    recovery_veto_bps: int = 6_500
    recovery_stop_cap_bps: int = 5_000

    def __post_init__(self) -> None:
        if self.confirmation_observations < 2:
            raise ValueError("confirmation_observations must be at least 2")
        for name in (
            "hazard_threshold_bps",
            "formation_threshold_bps",
            "minimum_margin_bps",
            "persistence_bps",
            "maximum_uncertainty_bps",
            "recovery_veto_bps",
            "recovery_stop_cap_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class CompetingRiskDecisionState:
    as_of: datetime
    decision: CompetingRiskDecision
    evidence_count: int
    stop_persistence_bps: int
    stop_formation_persistence_bps: int
    target_persistence_bps: int
    recovery_persistence_bps: int
    latest_stop_hazard_bps: int
    latest_stop_formation_bps: int
    latest_target_hazard_bps: int
    latest_recovery_strength_bps: int
    latest_uncertainty_bps: int
    latest_separation_margin_bps: int
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
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        for name in (
            "stop_persistence_bps",
            "stop_formation_persistence_bps",
            "target_persistence_bps",
            "recovery_persistence_bps",
            "latest_stop_hazard_bps",
            "latest_stop_formation_bps",
            "latest_target_hazard_bps",
            "latest_recovery_strength_bps",
            "latest_uncertainty_bps",
            "latest_separation_margin_bps",
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
            raise ValueError("phase-one competing-risk decision gate is shadow-only")


def _ratio(count: int, total: int) -> int:
    if total <= 0:
        return 0
    return count * 10_000 // total


def _stop_formation_qualifies(
    item: CompetingRiskBeliefState,
    policy: CompetingRiskDecisionPolicy,
) -> bool:
    return (
        item.path_evidence_available
        and item.stop_formation_bps >= policy.formation_threshold_bps
        and item.stop_formation_bps > item.target_hazard_proxy_bps
        and item.recovery_strength_bps < policy.recovery_veto_bps
    )


def _stop_qualifies(
    item: CompetingRiskBeliefState,
    policy: CompetingRiskDecisionPolicy,
) -> bool:
    return (
        item.path_evidence_available
        and item.stop_hazard_proxy_bps >= policy.hazard_threshold_bps
        and item.stop_hazard_proxy_bps > item.target_hazard_proxy_bps
        and item.separation_margin_bps >= policy.minimum_margin_bps
        and item.uncertainty_bps <= policy.maximum_uncertainty_bps
        and item.recovery_strength_bps < policy.recovery_veto_bps
    )


def _target_qualifies(
    item: CompetingRiskBeliefState,
    policy: CompetingRiskDecisionPolicy,
) -> bool:
    return (
        item.path_evidence_available
        and item.target_hazard_proxy_bps >= policy.hazard_threshold_bps
        and item.target_hazard_proxy_bps > item.stop_hazard_proxy_bps
        and item.separation_margin_bps >= policy.minimum_margin_bps
        and item.uncertainty_bps <= policy.maximum_uncertainty_bps
        and item.recovery_strength_bps < policy.recovery_veto_bps
    )


def _recovery_qualifies(
    item: CompetingRiskBeliefState,
    policy: CompetingRiskDecisionPolicy,
) -> bool:
    return (
        item.path_evidence_available
        and item.recovery_strength_bps >= policy.recovery_veto_bps
        and item.stop_hazard_proxy_bps <= policy.recovery_stop_cap_bps
    )


def assess_competing_risk_decision(
    beliefs: Sequence[CompetingRiskBeliefState],
    *,
    policy: CompetingRiskDecisionPolicy | None = None,
) -> CompetingRiskDecisionState:
    """Require temporal persistence before confirming STOP or TARGET."""
    if not beliefs:
        raise ValueError("at least one competing-risk belief is required")
    effective = policy or CompetingRiskDecisionPolicy()

    for left, right in zip(beliefs, beliefs[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError("belief states must be strictly increasing and causal")

    window = tuple(beliefs[-effective.confirmation_observations :])
    latest = window[-1]
    stop_count = sum(_stop_qualifies(item, effective) for item in window)
    stop_formation_count = sum(
        _stop_formation_qualifies(item, effective) for item in window
    )
    target_count = sum(_target_qualifies(item, effective) for item in window)
    recovery_count = sum(_recovery_qualifies(item, effective) for item in window)
    stop_persistence = _ratio(stop_count, len(window))
    stop_formation_persistence = _ratio(stop_formation_count, len(window))
    target_persistence = _ratio(target_count, len(window))
    recovery_persistence = _ratio(recovery_count, len(window))

    latest_stop = _stop_qualifies(latest, effective)
    latest_stop_formation = _stop_formation_qualifies(latest, effective)
    latest_target = _target_qualifies(latest, effective)
    latest_recovery = _recovery_qualifies(latest, effective)
    enough_history = len(window) >= effective.confirmation_observations

    reasons: list[str] = []
    if not latest.path_evidence_available:
        decision = CompetingRiskDecision.INSUFFICIENT
        reasons.append("TRADE_PATH_EVIDENCE_NOT_ESTABLISHED")
    elif latest_recovery:
        decision = CompetingRiskDecision.RECOVERABLE
        reasons.extend(
            (
                "RECOVERY_STRENGTH_HIGH",
                "STOP_HAZARD_CAPPED_DURING_RECOVERY",
            )
        )
    elif (
        latest_stop
        and enough_history
        and stop_persistence >= effective.persistence_bps
    ):
        decision = CompetingRiskDecision.STOP_LIKELY
        reasons.extend(
            (
                "STOP_HAZARD_SEPARATED",
                "STOP_HAZARD_PERSISTENT",
                "RECOVERY_VETO_ABSENT",
            )
        )
    elif latest_stop:
        decision = CompetingRiskDecision.STOP_FORMING
        reasons.extend(
            (
                "STOP_HAZARD_SEPARATED",
                "STOP_PERSISTENCE_NOT_YET_CONFIRMED",
            )
        )
    elif latest_stop_formation:
        decision = CompetingRiskDecision.STOP_FORMING
        reasons.extend(
            (
                "EARLY_STOP_FORMATION_PRESSURE_PRESENT",
                "CONFIRMED_STOP_HAZARD_NOT_YET_ESTABLISHED",
            )
        )
    elif (
        latest_target
        and enough_history
        and target_persistence >= effective.persistence_bps
    ):
        decision = CompetingRiskDecision.TARGET_LIKELY
        reasons.extend(
            (
                "TARGET_HAZARD_SEPARATED",
                "TARGET_HAZARD_PERSISTENT",
                "FAVORABLE_PATH_EVIDENCE_PRESENT",
            )
        )
    elif latest_target:
        decision = CompetingRiskDecision.TARGET_FORMING
        reasons.extend(
            (
                "TARGET_HAZARD_SEPARATED",
                "TARGET_PERSISTENCE_NOT_YET_CONFIRMED",
            )
        )
    else:
        decision = CompetingRiskDecision.CONTESTED
        if latest.uncertainty_bps > effective.maximum_uncertainty_bps:
            reasons.append("UNCERTAINTY_TOO_HIGH_FOR_DECISION")
        if latest.separation_margin_bps < effective.minimum_margin_bps:
            reasons.append("STOP_TARGET_MARGIN_TOO_SMALL")
        if latest.recovery_strength_bps >= effective.recovery_veto_bps:
            reasons.append("RECOVERY_EVIDENCE_CONTRADICTS_TERMINAL_DECISION")
        if not reasons:
            reasons.append("NO_PERSISTENT_COMPETING_RISK_SEPARATION")

    return CompetingRiskDecisionState(
        as_of=latest.as_of,
        decision=decision,
        evidence_count=len(window),
        stop_persistence_bps=stop_persistence,
        stop_formation_persistence_bps=stop_formation_persistence,
        target_persistence_bps=target_persistence,
        recovery_persistence_bps=recovery_persistence,
        latest_stop_hazard_bps=latest.stop_hazard_proxy_bps,
        latest_stop_formation_bps=latest.stop_formation_bps,
        latest_target_hazard_bps=latest.target_hazard_proxy_bps,
        latest_recovery_strength_bps=latest.recovery_strength_bps,
        latest_uncertainty_bps=latest.uncertainty_bps,
        latest_separation_margin_bps=latest.separation_margin_bps,
        reasons=tuple(dict.fromkeys(reasons)),
    )
