"""X-12 second-order blindspot cognition for Shared.

Consumes already-declared observability/health evidence. It does not acquire
sensors, choose providers, mutate ontology or authorize trading actions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedBlindspotClass(StrEnum):
    DATA_CORRUPTION = "DATA_CORRUPTION"
    KNOWN_OBSERVABILITY_GAP = "KNOWN_OBSERVABILITY_GAP"
    SECOND_ORDER_UNKNOWN_UNKNOWN = "SECOND_ORDER_UNKNOWN_UNKNOWN"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedSecondOrderBlindspotPolicy:
    policy_id: str
    minimum_data_health_bps: int
    low_sensor_coverage_bps: int
    low_ontology_fit_bps: int
    high_prediction_error_bps: int
    high_uncertainty_bps: int
    minimum_recurrence_count: int
    source_only: bool = True
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "blindspot policy_id must be non-empty"
            )
        for name in (
            "minimum_data_health_bps",
            "low_sensor_coverage_bps",
            "low_ontology_fit_bps",
            "high_prediction_error_bps",
            "high_uncertainty_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if self.minimum_recurrence_count < 1:
            raise SharedTraderIntelligenceValidationError(
                "minimum_recurrence_count must be positive"
            )
        if not self.source_only or self.productive_authority:
            raise SharedTraderIntelligenceValidationError(
                "blindspot policy is source-only research"
            )


@dataclass(frozen=True, slots=True)
class SharedBlindspotEvidence:
    evidence_id: str
    observed_at: datetime
    evidence_cutoff_at: datetime
    domain: str
    prediction_error_bps: int
    uncertainty_bps: int
    data_health_bps: int
    known_sensor_coverage_bps: int
    ontology_fit_bps: int
    recurrence_count: int
    downstream_importance_bps: int
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.domain.strip():
            raise SharedTraderIntelligenceValidationError(
                "blindspot evidence identity/domain must be non-empty"
            )
        for name in ("observed_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.observed_at:
            raise SharedTraderIntelligenceValidationError(
                "blindspot cognition cannot consume future evidence"
            )
        for name in (
            "prediction_error_bps",
            "uncertainty_bps",
            "data_health_bps",
            "known_sensor_coverage_bps",
            "ontology_fit_bps",
            "downstream_importance_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if self.recurrence_count < 0:
            raise SharedTraderIntelligenceValidationError(
                "recurrence_count cannot be negative"
            )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "blindspot provenance must be non-empty and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedSecondOrderBlindspotAssessment:
    evidence_id: str
    blindspot_class: SharedBlindspotClass
    research_priority_bps: int
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    sensor_acquisition_authority: bool = False
    ontology_mutation_authority: bool = False
    trader_methodology_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "blindspot assessment requires identity and reasons"
            )
        if (
            type(self.research_priority_bps) is not int
            or not 0 <= self.research_priority_bps <= 10_000
        ):
            raise SharedTraderIntelligenceValidationError(
                "research_priority_bps must be int within 0..10000"
            )
        if (
            self.sensor_acquisition_authority
            or self.ontology_mutation_authority
            or self.trader_methodology_authority
            or self.execution_authority
            or self.risk_authority
            or self.capital_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "blindspot cognition cannot seize sovereign authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["blindspot_class"] = self.blindspot_class.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


FROZEN_SECOND_ORDER_BLINDSPOT_POLICY = SharedSecondOrderBlindspotPolicy(
    policy_id="QORE_SHARED_X12_SECOND_ORDER_BLINDSPOT_POLICY_001",
    minimum_data_health_bps=9_500,
    low_sensor_coverage_bps=3_000,
    low_ontology_fit_bps=3_000,
    high_prediction_error_bps=7_000,
    high_uncertainty_bps=7_000,
    minimum_recurrence_count=3,
)


def assess_second_order_blindspot(
    evidence: SharedBlindspotEvidence,
    *,
    policy: SharedSecondOrderBlindspotPolicy = FROZEN_SECOND_ORDER_BLINDSPOT_POLICY,
) -> SharedSecondOrderBlindspotAssessment:
    reasons: list[str] = []

    if evidence.data_health_bps < policy.minimum_data_health_bps:
        classification = SharedBlindspotClass.DATA_CORRUPTION
        reasons.append("DATA_HEALTH_BELOW_BLINDSPOT_GATE")
    else:
        severe_model_surprise = (
            evidence.prediction_error_bps >= policy.high_prediction_error_bps
            or evidence.uncertainty_bps >= policy.high_uncertainty_bps
        )
        low_coverage = (
            evidence.known_sensor_coverage_bps <= policy.low_sensor_coverage_bps
        )
        low_fit = evidence.ontology_fit_bps <= policy.low_ontology_fit_bps
        recurrent = evidence.recurrence_count >= policy.minimum_recurrence_count

        if severe_model_surprise and low_coverage and low_fit and recurrent:
            classification = SharedBlindspotClass.SECOND_ORDER_UNKNOWN_UNKNOWN
            reasons.extend(
                (
                    "RECURRENT_HIGH_SURPRISE",
                    "OBSERVATION_SPACE_POORLY_INSTRUMENTED",
                    "KNOWN_ONTOLOGY_POOR_FIT",
                )
            )
        elif (
            evidence.known_sensor_coverage_bps < 8_000
            or evidence.ontology_fit_bps < 8_000
        ):
            classification = SharedBlindspotClass.KNOWN_OBSERVABILITY_GAP
            reasons.append("KNOWN_COVERAGE_OR_ONTOLOGY_GAP")
        else:
            classification = SharedBlindspotClass.INSUFFICIENT
            reasons.append("NO_SECOND_ORDER_BLINDSPOT_EVIDENCE")

    if classification is SharedBlindspotClass.DATA_CORRUPTION:
        priority = 0
    else:
        priority = (
            evidence.prediction_error_bps
            + evidence.uncertainty_bps
            + (10_000 - evidence.known_sensor_coverage_bps)
            + (10_000 - evidence.ontology_fit_bps)
            + evidence.downstream_importance_bps
        ) // 5

    return SharedSecondOrderBlindspotAssessment(
        evidence_id=evidence.evidence_id,
        blindspot_class=classification,
        research_priority_bps=max(0, min(10_000, priority)),
        reason_codes=tuple(sorted(set(reasons))),
        evidence_refs=evidence.provenance_refs,
    )
