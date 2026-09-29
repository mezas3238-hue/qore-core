"""Research-only materiality and proactive STI state-machine contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
    SharedPositionThreatLevel,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
)


class SharedMaterialityDisposition(StrEnum):
    MATERIAL = "MATERIAL"
    NOT_MATERIAL = "NOT_MATERIAL"
    INSUFFICIENT = "INSUFFICIENT"


class SharedPolicyCalibrationState(StrEnum):
    RESEARCH_UNCALIBRATED = "RESEARCH_UNCALIBRATED"
    PREREGISTERED = "PREREGISTERED"
    EMPIRICALLY_CALIBRATED = "EMPIRICALLY_CALIBRATED"


@dataclass(frozen=True, slots=True)
class SharedAlertMaterialityPolicy:
    """Explicit research policy; no hidden/default thresholds are allowed."""

    policy_id: str
    version: str
    frozen_at: datetime
    calibration_state: SharedPolicyCalibrationState
    policy_evidence_refs: tuple[str, ...]
    min_confidence_change_bps: int
    min_uncertainty_change_bps: int
    min_data_quality_change_bps: int
    require_world_state_change: bool
    require_regime_state_change: bool
    require_directional_hypothesis_change: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("policy_id", "version"):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "materiality policy frozen_at must be timezone-aware"
            )
        if (
            not self.policy_evidence_refs
            or self.policy_evidence_refs
            != tuple(sorted(set(self.policy_evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "materiality policy evidence must be non-empty and canonical"
            )
        for name in (
            "min_confidence_change_bps",
            "min_uncertainty_change_bps",
            "min_data_quality_change_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if self.productive_authority:
            raise SharedTraderIntelligenceValidationError(
                "research materiality policy cannot authorize production"
            )
        if (
            self.calibration_state
            is SharedPolicyCalibrationState.EMPIRICALLY_CALIBRATED
            and not any(
                item.startswith("calibration:")
                for item in self.policy_evidence_refs
            )
        ):
            raise SharedTraderIntelligenceValidationError(
                "calibrated materiality policy requires calibration evidence"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["frozen_at"] = self.frozen_at.astimezone(UTC).isoformat()
        payload["calibration_state"] = self.calibration_state.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedMaterialityAssessment:
    assessment_id: str
    policy_fingerprint: str
    previous_snapshot_id: str
    current_snapshot_id: str
    assessed_at: datetime
    disposition: SharedMaterialityDisposition
    confidence_change_bps: int
    uncertainty_change_bps: int
    data_quality_change_bps: int
    world_state_changed: bool
    regime_state_changed: bool
    directional_hypothesis_changed: bool
    reason_codes: tuple[str, ...]
    emits_alert_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "assessment_id",
            "policy_fingerprint",
            "previous_snapshot_id",
            "current_snapshot_id",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        if len(self.policy_fingerprint) != 64:
            raise SharedTraderIntelligenceValidationError(
                "policy_fingerprint must be sha256 hex"
            )
        try:
            int(self.policy_fingerprint, 16)
        except ValueError as exc:
            raise SharedTraderIntelligenceValidationError(
                "policy_fingerprint must be sha256 hex"
            ) from exc
        if self.assessed_at.tzinfo is None or self.assessed_at.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "materiality assessed_at must be timezone-aware"
            )
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "materiality reason_codes must be non-empty and canonical"
            )
        if self.emits_alert_authority:
            raise SharedTraderIntelligenceValidationError(
                "materiality assessment does not itself emit alerts"
            )


def assess_snapshot_materiality(
    *,
    assessment_id: str,
    previous: SharedTraderIntelligenceSnapshot,
    current: SharedTraderIntelligenceSnapshot,
    policy: SharedAlertMaterialityPolicy,
    assessed_at: datetime,
) -> SharedMaterialityAssessment:
    """Assess state change under an explicit frozen research policy."""

    if previous.canonical_instrument_id != current.canonical_instrument_id:
        raise SharedTraderIntelligenceValidationError(
            "materiality comparison requires identical canonical instrument"
        )
    if previous.trader_horizon != current.trader_horizon:
        raise SharedTraderIntelligenceValidationError(
            "materiality comparison requires identical horizon"
        )
    if previous.observed_at > current.observed_at:
        raise SharedTraderIntelligenceValidationError(
            "materiality snapshots must be chronological"
        )
    if current.observed_at > assessed_at:
        raise SharedTraderIntelligenceValidationError(
            "materiality cannot consume future snapshot"
        )
    if current.evidence_cutoff_at > assessed_at:
        raise SharedTraderIntelligenceValidationError(
            "materiality cannot consume future evidence"
        )

    confidence_delta = abs(current.confidence_bps - previous.confidence_bps)
    uncertainty_delta = abs(current.uncertainty_bps - previous.uncertainty_bps)
    data_quality_delta = abs(
        current.data_quality_bps - previous.data_quality_bps
    )
    world_changed = previous.world_state != current.world_state
    regime_changed = previous.market_regime != current.market_regime
    hypothesis_changed = (
        previous.directional_hypothesis != current.directional_hypothesis
    )

    reasons: list[str] = []
    if confidence_delta >= policy.min_confidence_change_bps:
        reasons.append("CONFIDENCE_CHANGE")
    if uncertainty_delta >= policy.min_uncertainty_change_bps:
        reasons.append("UNCERTAINTY_CHANGE")
    if data_quality_delta >= policy.min_data_quality_change_bps:
        reasons.append("DATA_QUALITY_CHANGE")
    if policy.require_world_state_change and world_changed:
        reasons.append("WORLD_STATE_CHANGE")
    if policy.require_regime_state_change and regime_changed:
        reasons.append("MARKET_REGIME_CHANGE")
    if policy.require_directional_hypothesis_change and hypothesis_changed:
        reasons.append("DIRECTIONAL_HYPOTHESIS_CHANGE")

    required_flags = (
        (not policy.require_world_state_change or world_changed)
        and (not policy.require_regime_state_change or regime_changed)
        and (
            not policy.require_directional_hypothesis_change
            or hypothesis_changed
        )
    )
    numeric_gate = any(
        (
            confidence_delta >= policy.min_confidence_change_bps,
            uncertainty_delta >= policy.min_uncertainty_change_bps,
            data_quality_delta >= policy.min_data_quality_change_bps,
        )
    )
    if current.epistemic_state.value in {"INSUFFICIENT", "UNKNOWN"}:
        disposition = SharedMaterialityDisposition.INSUFFICIENT
        reasons.append("EPISTEMIC_STATE_INSUFFICIENT")
    elif required_flags and numeric_gate:
        disposition = SharedMaterialityDisposition.MATERIAL
    else:
        disposition = SharedMaterialityDisposition.NOT_MATERIAL
        reasons.append("MATERIALITY_GATE_NOT_MET")

    return SharedMaterialityAssessment(
        assessment_id=assessment_id,
        policy_fingerprint=policy.fingerprint(),
        previous_snapshot_id=previous.snapshot_id,
        current_snapshot_id=current.snapshot_id,
        assessed_at=assessed_at,
        disposition=disposition,
        confidence_change_bps=confidence_delta,
        uncertainty_change_bps=uncertainty_delta,
        data_quality_change_bps=data_quality_delta,
        world_state_changed=world_changed,
        regime_state_changed=regime_changed,
        directional_hypothesis_changed=hypothesis_changed,
        reason_codes=tuple(sorted(set(reasons))),
    )


_OPPORTUNITY_TRANSITIONS = {
    SharedOpportunityMaturity.NO_OPPORTUNITY: frozenset(
        {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.INSUFFICIENT,
        }
    ),
    SharedOpportunityMaturity.EARLY: frozenset(
        {
            SharedOpportunityMaturity.NO_OPPORTUNITY,
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.DETERIORATING,
            SharedOpportunityMaturity.EXPIRED,
            SharedOpportunityMaturity.INSUFFICIENT,
        }
    ),
    SharedOpportunityMaturity.DEVELOPING: frozenset(
        {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.MATURE,
            SharedOpportunityMaturity.DETERIORATING,
            SharedOpportunityMaturity.EXPIRED,
            SharedOpportunityMaturity.INSUFFICIENT,
        }
    ),
    SharedOpportunityMaturity.MATURE: frozenset(
        {
            SharedOpportunityMaturity.DEVELOPING,
            SharedOpportunityMaturity.DETERIORATING,
            SharedOpportunityMaturity.EXPIRED,
            SharedOpportunityMaturity.INSUFFICIENT,
        }
    ),
    SharedOpportunityMaturity.DETERIORATING: frozenset(
        {
            SharedOpportunityMaturity.EARLY,
            SharedOpportunityMaturity.NO_OPPORTUNITY,
            SharedOpportunityMaturity.EXPIRED,
            SharedOpportunityMaturity.INSUFFICIENT,
        }
    ),
    SharedOpportunityMaturity.EXPIRED: frozenset(),
    SharedOpportunityMaturity.INSUFFICIENT: frozenset(
        {
            SharedOpportunityMaturity.NO_OPPORTUNITY,
            SharedOpportunityMaturity.EARLY,
        }
    ),
}


def validate_opportunity_maturity_transition(
    previous: SharedOpportunityMaturity,
    next_state: SharedOpportunityMaturity,
) -> bool:
    """Validate lifecycle only. It does not decide when a transition is true."""

    if previous == next_state:
        return False
    if next_state not in _OPPORTUNITY_TRANSITIONS[previous]:
        raise SharedTraderIntelligenceValidationError(
            "illegal opportunity maturity transition"
        )
    return True


def validate_regime_transition_state(
    state: SharedRegimeTransitionState,
    *,
    evidence_refs: tuple[str, ...],
) -> SharedRegimeTransitionState:
    """Require evidence for any explicit regime-transition research state."""

    if (
        state is not SharedRegimeTransitionState.INSUFFICIENT
        and not evidence_refs
    ):
        raise SharedTraderIntelligenceValidationError(
            "regime-transition state requires evidence"
        )
    return state


def validate_continuation_support_state(
    state: SharedSupportState,
    *,
    evidence_refs: tuple[str, ...],
) -> SharedSupportState:
    """Continuation state is evidence, never a mandatory HOLD command."""

    if state is not SharedSupportState.INSUFFICIENT and not evidence_refs:
        raise SharedTraderIntelligenceValidationError(
            "continuation support requires evidence"
        )
    return state


def validate_position_threat_state(
    state: SharedPositionThreatLevel,
    *,
    evidence_refs: tuple[str, ...],
) -> SharedPositionThreatLevel:
    """Threat state is evidence, never a mandatory EXIT/PROTECT command."""

    if state is not SharedPositionThreatLevel.INSUFFICIENT and not evidence_refs:
        raise SharedTraderIntelligenceValidationError(
            "position threat requires evidence"
        )
    return state
