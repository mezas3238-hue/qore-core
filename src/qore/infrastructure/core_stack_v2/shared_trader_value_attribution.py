"""Control/treatment attribution contracts for proactive Shared intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedTraderStudyArm(StrEnum):
    CONTROL_WITHOUT_PROACTIVE_SHARED = "CONTROL_WITHOUT_PROACTIVE_SHARED"
    TREATMENT_WITH_PROACTIVE_SHARED = "TREATMENT_WITH_PROACTIVE_SHARED"


class SharedTraderDecisionCode(StrEnum):
    VALID_TRADE = "VALID_TRADE"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"
    HOLD = "HOLD"
    PROTECT = "PROTECT"
    PARTIAL_EXIT = "PARTIAL_EXIT"
    EXIT = "EXIT"


class SharedTraderValueDimension(StrEnum):
    OPPORTUNITY_DISCOVERY = "OPPORTUNITY_DISCOVERY"
    ENTRY_DECISION = "ENTRY_DECISION"
    POSITION_MANAGEMENT = "POSITION_MANAGEMENT"
    CONTINUATION_POSITIVE_TAIL = "CONTINUATION_POSITIVE_TAIL"


class SharedAttributionDisposition(StrEnum):
    NO_BEHAVIORAL_DIFFERENCE = "NO_BEHAVIORAL_DIFFERENCE"
    BEHAVIORAL_DIFFERENCE_OBSERVED = "BEHAVIORAL_DIFFERENCE_OBSERVED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedTraderAttributionDesign:
    study_id: str
    trader_id: str
    trader_version: str
    trader_config_fingerprint: str
    dataset_fingerprint: str
    opportunity_universe_fingerprint: str
    control_policy_fingerprint: str
    treatment_policy_fingerprint: str
    preregistration_ref: str
    split_identity: str
    evidence_cutoff_at: datetime
    value_dimensions: tuple[SharedTraderValueDimension, ...]
    same_opportunity_universe_required: bool = True
    protected_holdout: bool = False
    productive_behavior_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "study_id",
            "trader_id",
            "trader_version",
            "preregistration_ref",
            "split_identity",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in (
            "trader_config_fingerprint",
            "dataset_fingerprint",
            "opportunity_universe_fingerprint",
            "control_policy_fingerprint",
            "treatment_policy_fingerprint",
        ):
            value = str(getattr(self, name))
            if len(value) != 64:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                )
            try:
                int(value, 16)
            except ValueError as exc:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be sha256 hex"
                ) from exc
        if self.control_policy_fingerprint == self.treatment_policy_fingerprint:
            raise SharedTraderIntelligenceValidationError(
                "control and treatment policy fingerprints must differ"
            )
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise SharedTraderIntelligenceValidationError(
                "study evidence_cutoff_at must be timezone-aware"
            )
        canonical_dimensions = tuple(
            sorted(set(self.value_dimensions), key=lambda item: item.value)
        )
        if self.value_dimensions != canonical_dimensions:
            raise SharedTraderIntelligenceValidationError(
                "value dimensions must be unique and canonical"
            )
        if not self.value_dimensions:
            raise SharedTraderIntelligenceValidationError(
                "value dimensions must be non-empty"
            )
        if not self.same_opportunity_universe_required:
            raise SharedTraderIntelligenceValidationError(
                "STI attribution requires the same opportunity universe"
            )
        if self.protected_holdout:
            raise SharedTraderIntelligenceValidationError(
                "protected holdout cannot be opened by attribution design"
            )
        if self.productive_behavior_authority:
            raise SharedTraderIntelligenceValidationError(
                "attribution design cannot authorize productive behavior"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        payload["value_dimensions"] = tuple(
            item.value for item in self.value_dimensions
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedTraderDecisionRecord:
    study_id: str
    arm: SharedTraderStudyArm
    opportunity_id: str
    decision_id: str
    decision_time: datetime
    decision_code: SharedTraderDecisionCode
    shared_intelligence_ref: str | None
    decision_evidence_refs: tuple[str, ...]
    future_outcome_used: bool = False
    outcome_value: str | None = None

    def __post_init__(self) -> None:
        for name in ("study_id", "opportunity_id", "decision_id"):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        if (
            self.decision_time.tzinfo is None
            or self.decision_time.utcoffset() is None
        ):
            raise SharedTraderIntelligenceValidationError(
                "decision_time must be timezone-aware"
            )
        if (
            not self.decision_evidence_refs
            or self.decision_evidence_refs
            != tuple(sorted(set(self.decision_evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "decision evidence refs must be non-empty and canonical"
            )
        if self.arm is SharedTraderStudyArm.CONTROL_WITHOUT_PROACTIVE_SHARED:
            if self.shared_intelligence_ref is not None:
                raise SharedTraderIntelligenceValidationError(
                    "control arm cannot consume proactive Shared intelligence"
                )
        else:
            if (
                self.shared_intelligence_ref is None
                or not self.shared_intelligence_ref.strip()
            ):
                raise SharedTraderIntelligenceValidationError(
                    "treatment arm requires proactive Shared intelligence ref"
                )
        if self.future_outcome_used or self.outcome_value is not None:
            raise SharedTraderIntelligenceValidationError(
                "decision record cannot contain outcome information"
            )


@dataclass(frozen=True, slots=True)
class SharedTraderOutcomeRecord:
    study_id: str
    opportunity_id: str
    decision_id: str
    outcome_observed_at: datetime
    outcome_code: str
    outcome_evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "study_id",
            "opportunity_id",
            "decision_id",
            "outcome_code",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        if (
            self.outcome_observed_at.tzinfo is None
            or self.outcome_observed_at.utcoffset() is None
        ):
            raise SharedTraderIntelligenceValidationError(
                "outcome_observed_at must be timezone-aware"
            )
        if (
            not self.outcome_evidence_refs
            or self.outcome_evidence_refs
            != tuple(sorted(set(self.outcome_evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "outcome evidence refs must be non-empty and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedTraderPairedDecisionAttribution:
    study_id: str
    opportunity_id: str
    control_decision_id: str
    treatment_decision_id: str
    control_decision_code: SharedTraderDecisionCode
    treatment_decision_code: SharedTraderDecisionCode
    disposition: SharedAttributionDisposition
    behavioral_difference: bool
    causal_economic_value_claim_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "study_id",
            "opportunity_id",
            "control_decision_id",
            "treatment_decision_id",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        expected_difference = (
            self.control_decision_code != self.treatment_decision_code
        )
        if self.behavioral_difference != expected_difference:
            raise SharedTraderIntelligenceValidationError(
                "behavioral_difference does not match paired decisions"
            )
        if expected_difference:
            if (
                self.disposition
                is not SharedAttributionDisposition.BEHAVIORAL_DIFFERENCE_OBSERVED
            ):
                raise SharedTraderIntelligenceValidationError(
                    "different decisions require behavioral-difference disposition"
                )
        elif (
            self.disposition
            is not SharedAttributionDisposition.NO_BEHAVIORAL_DIFFERENCE
        ):
            raise SharedTraderIntelligenceValidationError(
                "identical decisions require no-difference disposition"
            )
        if self.causal_economic_value_claim_authorized:
            raise SharedTraderIntelligenceValidationError(
                "paired decision difference alone cannot prove economic value"
            )


def compare_paired_trader_decisions(
    *,
    design: SharedTraderAttributionDesign,
    control: SharedTraderDecisionRecord,
    treatment: SharedTraderDecisionRecord,
) -> SharedTraderPairedDecisionAttribution:
    """Compare behavior only; economic value requires separate outcome science."""

    if control.study_id != design.study_id:
        raise SharedTraderIntelligenceValidationError(
            "control decision study mismatch"
        )
    if treatment.study_id != design.study_id:
        raise SharedTraderIntelligenceValidationError(
            "treatment decision study mismatch"
        )
    if control.arm is not SharedTraderStudyArm.CONTROL_WITHOUT_PROACTIVE_SHARED:
        raise SharedTraderIntelligenceValidationError(
            "control decision must use control arm"
        )
    if treatment.arm is not SharedTraderStudyArm.TREATMENT_WITH_PROACTIVE_SHARED:
        raise SharedTraderIntelligenceValidationError(
            "treatment decision must use treatment arm"
        )
    if control.opportunity_id != treatment.opportunity_id:
        raise SharedTraderIntelligenceValidationError(
            "paired attribution requires identical opportunity identity"
        )
    if control.decision_time != treatment.decision_time:
        raise SharedTraderIntelligenceValidationError(
            "paired attribution requires identical decision time"
        )
    changed = control.decision_code != treatment.decision_code
    disposition = (
        SharedAttributionDisposition.BEHAVIORAL_DIFFERENCE_OBSERVED
        if changed
        else SharedAttributionDisposition.NO_BEHAVIORAL_DIFFERENCE
    )
    return SharedTraderPairedDecisionAttribution(
        study_id=design.study_id,
        opportunity_id=control.opportunity_id,
        control_decision_id=control.decision_id,
        treatment_decision_id=treatment.decision_id,
        control_decision_code=control.decision_code,
        treatment_decision_code=treatment.decision_code,
        disposition=disposition,
        behavioral_difference=changed,
    )
