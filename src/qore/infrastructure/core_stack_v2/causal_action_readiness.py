"""Causal action-readiness intelligence for Shared Core.

Shared can observe adverse evidence without treating every adverse observation
as immediately actionable. This module separates cognition from action
readiness.

The disposition is authority-free:
- OBSERVE: no meaningful directional evidence yet;
- WATCH: adverse evidence exists but timing is not sufficiently imminent;
- DEFEND: adverse timing is developing but not terminally confirmed;
- EXIT_RISK_WARNING: adverse timing is both near-term and directionally
  concentrated;
- RECOVERY: favorable near-term evidence dominates;
- INSUFFICIENT: causal evidence quality is too low.

No strategy, sizing, capital, risk, stop, target, order or execution authority
is carried by this component.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ActionReadinessDisposition(StrEnum):
    OBSERVE = "OBSERVE"
    WATCH = "WATCH"
    DEFEND = "DEFEND"
    EXIT_RISK_WARNING = "EXIT_RISK_WARNING"
    RECOVERY = "RECOVERY"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class CausalActionReadinessEvidence:
    as_of: datetime
    adverse_h1_bps: int
    adverse_h3_bps: int
    favorable_h1_bps: int
    favorable_h3_bps: int
    near_directional_margin_bps: int
    adverse_velocity_bps: int
    data_integrity_bps: int = 10_000
    uncertainty_bps: int = 0

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "adverse_h1_bps",
            "adverse_h3_bps",
            "favorable_h1_bps",
            "favorable_h3_bps",
            "data_integrity_bps",
            "uncertainty_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if not -10_000 <= self.near_directional_margin_bps <= 10_000:
            raise ValueError(
                "near_directional_margin_bps must be within -10000..10000"
            )
        if not -10_000 <= self.adverse_velocity_bps <= 10_000:
            raise ValueError("adverse_velocity_bps must be within -10000..10000")


@dataclass(frozen=True, slots=True)
class CausalActionReadinessPolicy:
    minimum_data_integrity_bps: int = 7_500
    maximum_uncertainty_bps: int = 7_500
    watch_adverse_h1_bps: int = 800
    defend_adverse_h1_bps: int = 1_500
    exit_adverse_h1_bps: int = 2_500
    exit_imminence_ratio_bps: int = 5_000
    exit_near_margin_bps: int = 1_500
    exit_minimum_velocity_bps: int = -500
    recovery_near_margin_bps: int = 1_500

    def __post_init__(self) -> None:
        for name in (
            "minimum_data_integrity_bps",
            "maximum_uncertainty_bps",
            "watch_adverse_h1_bps",
            "defend_adverse_h1_bps",
            "exit_adverse_h1_bps",
            "exit_imminence_ratio_bps",
            "exit_near_margin_bps",
            "recovery_near_margin_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if not -10_000 <= self.exit_minimum_velocity_bps <= 10_000:
            raise ValueError(
                "exit_minimum_velocity_bps must be within -10000..10000"
            )
        if not (
            self.watch_adverse_h1_bps
            <= self.defend_adverse_h1_bps
            <= self.exit_adverse_h1_bps
        ):
            raise ValueError("readiness adverse thresholds must be ordered")


@dataclass(frozen=True, slots=True)
class CausalActionReadinessAssessment:
    as_of: datetime
    disposition: ActionReadinessDisposition
    imminence_ratio_bps: int
    adverse_h1_bps: int
    favorable_h1_bps: int
    near_directional_margin_bps: int
    adverse_velocity_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if not 0 <= self.imminence_ratio_bps <= 10_000:
            raise ValueError("imminence_ratio_bps must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("action readiness cannot carry trading authority")


def _imminence_ratio_bps(adverse_h1_bps: int, adverse_h3_bps: int) -> int:
    if adverse_h3_bps <= 0:
        return 0
    return max(
        0,
        min(10_000, adverse_h1_bps * 10_000 // adverse_h3_bps),
    )


def assess_causal_action_readiness(
    evidence: CausalActionReadinessEvidence,
    *,
    policy: CausalActionReadinessPolicy | None = None,
) -> CausalActionReadinessAssessment:
    """Classify timing readiness from current causal evidence only."""

    effective = policy or CausalActionReadinessPolicy()
    imminence = _imminence_ratio_bps(
        evidence.adverse_h1_bps,
        evidence.adverse_h3_bps,
    )
    reasons: list[str] = []

    if (
        evidence.data_integrity_bps < effective.minimum_data_integrity_bps
        or evidence.uncertainty_bps > effective.maximum_uncertainty_bps
    ):
        disposition = ActionReadinessDisposition.INSUFFICIENT
        reasons.append("CAUSAL_EVIDENCE_INSUFFICIENT")
    elif (
        evidence.near_directional_margin_bps
        <= -effective.recovery_near_margin_bps
        and evidence.favorable_h1_bps > evidence.adverse_h1_bps
    ):
        disposition = ActionReadinessDisposition.RECOVERY
        reasons.append("NEAR_TERM_FAVORABLE_DIRECTION_DOMINANT")
    elif (
        evidence.adverse_h1_bps >= effective.exit_adverse_h1_bps
        and imminence >= effective.exit_imminence_ratio_bps
        and evidence.near_directional_margin_bps
        >= effective.exit_near_margin_bps
        and evidence.adverse_velocity_bps
        >= effective.exit_minimum_velocity_bps
    ):
        disposition = ActionReadinessDisposition.EXIT_RISK_WARNING
        reasons.extend(
            (
                "ADVERSE_EVENT_NEAR_TERM",
                "ADVERSE_DIRECTION_DOMINANT",
                "ADVERSE_TIMING_CONFIRMED",
            )
        )
    elif (
        evidence.adverse_h1_bps >= effective.defend_adverse_h1_bps
        and evidence.near_directional_margin_bps > 0
    ):
        disposition = ActionReadinessDisposition.DEFEND
        reasons.append("ADVERSE_TIMING_DEVELOPING")
    elif (
        evidence.adverse_h1_bps >= effective.watch_adverse_h1_bps
        or evidence.near_directional_margin_bps > 0
    ):
        disposition = ActionReadinessDisposition.WATCH
        reasons.append("ADVERSE_EVIDENCE_NOT_YET_ACTION_READY")
    else:
        disposition = ActionReadinessDisposition.OBSERVE
        reasons.append("NO_ACTION_READY_CAUSAL_CONVERGENCE")

    if evidence.adverse_velocity_bps < 0:
        reasons.append("ADVERSE_IMPULSE_DECELERATING")
    if imminence < effective.exit_imminence_ratio_bps:
        reasons.append("ADVERSE_EVENT_NOT_FRONT_LOADED")

    return CausalActionReadinessAssessment(
        as_of=evidence.as_of,
        disposition=disposition,
        imminence_ratio_bps=imminence,
        adverse_h1_bps=evidence.adverse_h1_bps,
        favorable_h1_bps=evidence.favorable_h1_bps,
        near_directional_margin_bps=evidence.near_directional_margin_bps,
        adverse_velocity_bps=evidence.adverse_velocity_bps,
        reasons=tuple(dict.fromkeys(reasons)),
    )
