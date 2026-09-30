"""STI-11 source-only alert materiality and dedup cognition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityTrajectoryAssessment,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)


class SharedAlertMaterialityState(StrEnum):
    MATERIAL = "MATERIAL"
    DEDUPLICATED = "DEDUPLICATED"


@dataclass(frozen=True, slots=True)
class SharedAlertMaterialityPolicy:
    policy_id: str
    trajectory_score_delta_bps: int
    contradiction_delta_bps: int
    uncertainty_delta_bps: int
    source_only_calibration: bool
    calibration_evidence_refs: tuple[str, ...]
    calibrated_probability_claimed: bool = False
    order_priority_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "materiality policy_id must be non-empty"
            )
        for name in (
            "trajectory_score_delta_bps",
            "contradiction_delta_bps",
            "uncertainty_delta_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if not self.source_only_calibration:
            raise SharedTraderIntelligenceValidationError(
                "STI-11 materiality calibration must be source-only"
            )
        if (
            not self.calibration_evidence_refs
            or self.calibration_evidence_refs
            != tuple(sorted(set(self.calibration_evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "materiality calibration evidence must be non-empty and canonical"
            )
        if self.calibrated_probability_claimed or self.order_priority_authority:
            raise SharedTraderIntelligenceValidationError(
                "materiality is not probability or order priority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedAlertMaterialityAssessment:
    state: SharedAlertMaterialityState
    reason_codes: tuple[str, ...]
    trajectory_score_delta_bps: int
    contradiction_delta_bps: int
    uncertainty_delta_bps: int
    attention_event_only: bool = True
    trader_action_required: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "materiality assessment requires reason codes"
            )
        for name in (
            "trajectory_score_delta_bps",
            "contradiction_delta_bps",
            "uncertainty_delta_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if (
            not self.attention_event_only
            or self.trader_action_required
            or self.execution_authority
            or self.risk_authority
            or self.capital_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "materiality assessment cannot carry sovereign authority"
            )


def _dominant_score(
    assessment: SharedOpportunityTrajectoryAssessment,
) -> int:
    if assessment.dominant_mechanism is None:
        return 0
    for state in assessment.head_states:
        if state.mechanism is assessment.dominant_mechanism:
            return state.trajectory_score_bps
    return 0


def assess_alert_materiality(
    *,
    previous: SharedOpportunityTrajectoryAssessment | None,
    current: SharedOpportunityTrajectoryAssessment,
    policy: SharedAlertMaterialityPolicy,
) -> SharedAlertMaterialityAssessment:
    if previous is None:
        return SharedAlertMaterialityAssessment(
            state=SharedAlertMaterialityState.MATERIAL,
            reason_codes=("NEW_HYPOTHESIS_STATE",),
            trajectory_score_delta_bps=_dominant_score(current),
            contradiction_delta_bps=current.contradiction_bps,
            uncertainty_delta_bps=current.uncertainty_bps,
        )
    if previous.asset != current.asset:
        raise SharedTraderIntelligenceValidationError(
            "materiality comparison must use one asset"
        )

    score_delta = abs(_dominant_score(current) - _dominant_score(previous))
    contradiction_delta = abs(
        current.contradiction_bps - previous.contradiction_bps
    )
    uncertainty_delta = abs(
        current.uncertainty_bps - previous.uncertainty_bps
    )
    reasons: list[str] = []

    if current.maturity is not previous.maturity:
        reasons.append("MATURITY_STATE_CHANGED")
    if current.dominant_mechanism is not previous.dominant_mechanism:
        reasons.append("DOMINANT_MECHANISM_CHANGED")
    if (
        current.maturity is SharedOpportunityMaturity.INSUFFICIENT
        and previous.maturity is not SharedOpportunityMaturity.INSUFFICIENT
    ):
        reasons.append("DATA_BECAME_INSUFFICIENT")
    if score_delta >= policy.trajectory_score_delta_bps:
        reasons.append("TRAJECTORY_SCORE_DELTA_MATERIAL")
    if contradiction_delta >= policy.contradiction_delta_bps:
        reasons.append("CONTRADICTION_DELTA_MATERIAL")
    if uncertainty_delta >= policy.uncertainty_delta_bps:
        reasons.append("UNCERTAINTY_DELTA_MATERIAL")

    if reasons:
        state = SharedAlertMaterialityState.MATERIAL
    else:
        state = SharedAlertMaterialityState.DEDUPLICATED
        reasons.append("NO_MATERIAL_COGNITIVE_CHANGE")

    return SharedAlertMaterialityAssessment(
        state=state,
        reason_codes=tuple(sorted(set(reasons))),
        trajectory_score_delta_bps=score_delta,
        contradiction_delta_bps=contradiction_delta,
        uncertainty_delta_bps=uncertainty_delta,
    )
