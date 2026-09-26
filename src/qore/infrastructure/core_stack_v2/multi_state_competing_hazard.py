"""Generic multi-state competing-hazard decision gate for Shared Core.

Shared receives already-causal, point-in-time probabilities for mutually
exclusive near-term path events. This gate keeps STOP/TARGET/RECOVERY/CONTESTED
separate and gives winner protection an independent veto. It owns no strategy,
risk, sizing, order, stop, target or broker authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CompetingHazardDecision(StrEnum):
    STOP_LIKELY = "STOP_LIKELY"
    TARGET_LIKELY = "TARGET_LIKELY"
    RECOVERABLE = "RECOVERABLE"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class CompetingHazardPolicy:
    minimum_integrity_bps: int = 7_500
    adverse_threshold_bps: int = 5_500
    target_threshold_bps: int = 5_000
    recovery_threshold_bps: int = 5_000
    minimum_margin_bps: int = 1_200
    minimum_persistence_bps: int = 5_500
    winner_veto_threshold_bps: int = 6_500
    maximum_uncertainty_bps: int = 7_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class CompetingHazardEvidence:
    as_of: datetime
    data_integrity_bps: int
    stop_hazard_bps: int
    terminal_hazard_bps: int
    target_hazard_bps: int
    recovery_hazard_bps: int
    no_event_bps: int
    adverse_persistence_bps: int
    target_persistence_bps: int
    recovery_persistence_bps: int
    winner_veto_bps: int
    uncertainty_bps: int

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in self.__dataclass_fields__:
            if name == "as_of":
                continue
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class CompetingHazardAssessment:
    as_of: datetime
    decision: CompetingHazardDecision
    adverse_hazard_bps: int
    favorable_hazard_bps: int
    separation_margin_bps: int
    winner_veto_active: bool
    reasons: tuple[str, ...]
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_mutation_authority: bool = False
    target_mutation_authority: bool = False
    execution_authority: bool = False


def assess_competing_hazards(
    evidence: CompetingHazardEvidence,
    *,
    policy: CompetingHazardPolicy | None = None,
) -> CompetingHazardAssessment:
    p = policy or CompetingHazardPolicy()
    adverse = min(10_000, evidence.stop_hazard_bps + evidence.terminal_hazard_bps)
    favorable = min(10_000, evidence.target_hazard_bps + evidence.recovery_hazard_bps)
    margin = abs(adverse - favorable)
    veto = evidence.winner_veto_bps >= p.winner_veto_threshold_bps
    reasons: tuple[str, ...]

    if evidence.data_integrity_bps < p.minimum_integrity_bps:
        decision = CompetingHazardDecision.INSUFFICIENT
        reasons = ("DATA_INTEGRITY_INSUFFICIENT",)
    elif evidence.uncertainty_bps > p.maximum_uncertainty_bps:
        decision = CompetingHazardDecision.CONTESTED
        reasons = ("UNCERTAINTY_TOO_HIGH",)
    elif (
        adverse >= p.adverse_threshold_bps
        and adverse - favorable >= p.minimum_margin_bps
        and evidence.adverse_persistence_bps >= p.minimum_persistence_bps
        and not veto
    ):
        decision = CompetingHazardDecision.STOP_LIKELY
        reasons = ("ADVERSE_HAZARD_DOMINANT", "ADVERSE_PERSISTENT")
    elif (
        evidence.recovery_hazard_bps >= p.recovery_threshold_bps
        and evidence.recovery_hazard_bps - adverse >= p.minimum_margin_bps
        and evidence.recovery_persistence_bps >= p.minimum_persistence_bps
    ):
        decision = CompetingHazardDecision.RECOVERABLE
        reasons = ("RECOVERY_HAZARD_DOMINANT",)
    elif (
        evidence.target_hazard_bps >= p.target_threshold_bps
        and evidence.target_hazard_bps - adverse >= p.minimum_margin_bps
        and evidence.target_persistence_bps >= p.minimum_persistence_bps
    ):
        decision = CompetingHazardDecision.TARGET_LIKELY
        reasons = ("TARGET_HAZARD_DOMINANT",)
    else:
        decision = CompetingHazardDecision.CONTESTED
        reasons = (
            "WINNER_VETO_ACTIVE"
            if veto and adverse > favorable
            else "HAZARDS_NOT_SEPARATED",
        )

    return CompetingHazardAssessment(
        as_of=evidence.as_of,
        decision=decision,
        adverse_hazard_bps=adverse,
        favorable_hazard_bps=favorable,
        separation_margin_bps=margin,
        winner_veto_active=veto,
        reasons=reasons,
    )
