"""Read-only Shared facts contract for downstream CIBO evidence consumption."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
    TraderSharedOpportunityAssessment,
    TraderSharedOpportunityDisposition,
)


@dataclass(frozen=True, slots=True)
class SharedCiboReadOnlyFacts:
    """Cognition facts only; CIBO remains the sole capital decision owner."""

    facts_id: str
    trader_opportunity_id: str
    trader_id: str
    shared_snapshot_id: str
    canonical_instrument_id: str
    built_at: datetime
    evidence_cutoff_at: datetime
    opportunity_support: SharedSupportState
    continuation_support: SharedSupportState
    failure_hazard: SharedSupportState
    positive_tail_support: SharedSupportState
    relationship_stability: SharedSupportState
    regime_transition_state: SharedRegimeTransitionState
    systemic_stress: SharedSupportState
    uncertainty_bps: int
    causal_maturity: str
    evidence_refs: tuple[str, ...]
    trader_methodology_validated: bool
    read_only: bool = True
    cibo_may_abstain_or_allocate_zero: bool = True
    sizing_authority: bool = False
    capital_allocation_authority: bool = False
    reserve_authority: bool = False
    release_authority: bool = False
    compound_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "facts_id",
            "trader_opportunity_id",
            "trader_id",
            "shared_snapshot_id",
            "canonical_instrument_id",
            "causal_maturity",
        ):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in ("built_at", "evidence_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.built_at:
            raise SharedTraderIntelligenceValidationError(
                "CIBO facts cannot contain future Shared evidence"
            )
        if type(self.uncertainty_bps) is not int:
            raise SharedTraderIntelligenceValidationError(
                "uncertainty_bps must be int"
            )
        if not 0 <= self.uncertainty_bps <= 10_000:
            raise SharedTraderIntelligenceValidationError(
                "uncertainty_bps must be within 0..10000"
            )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "CIBO fact evidence must be non-empty and canonical"
            )
        if not self.trader_methodology_validated:
            raise SharedTraderIntelligenceValidationError(
                "CIBO Shared facts require a Trader-validated trade"
            )
        if not self.read_only:
            raise SharedTraderIntelligenceValidationError(
                "Shared facts delivered to CIBO must be read-only"
            )
        if not self.cibo_may_abstain_or_allocate_zero:
            raise SharedTraderIntelligenceValidationError(
                "Shared support cannot compel CIBO capital"
            )
        if (
            self.sizing_authority
            or self.capital_allocation_authority
            or self.reserve_authority
            or self.release_authority
            or self.compound_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared-to-CIBO facts cannot carry downstream authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["built_at"] = self.built_at.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        for name in (
            "opportunity_support",
            "continuation_support",
            "failure_hazard",
            "positive_tail_support",
            "relationship_stability",
            "regime_transition_state",
            "systemic_stress",
        ):
            payload[name] = getattr(self, name).value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_cibo_read_only_shared_facts(
    *,
    facts_id: str,
    trader_opportunity_id: str,
    trader_assessment: TraderSharedOpportunityAssessment,
    snapshot: SharedTraderIntelligenceSnapshot,
    built_at: datetime,
    evidence_refs: tuple[str, ...],
) -> SharedCiboReadOnlyFacts:
    """Cross the Shared→CIBO boundary only after Trader methodology validates."""

    if (
        trader_assessment.disposition
        is not TraderSharedOpportunityDisposition.VALID_TRADE
        or not trader_assessment.methodology_validated
    ):
        raise SharedTraderIntelligenceValidationError(
            "Shared facts cannot reach CIBO before Trader validates a trade"
        )
    if snapshot.observed_at > built_at:
        raise SharedTraderIntelligenceValidationError(
            "CIBO facts cannot consume future Shared snapshot"
        )
    return SharedCiboReadOnlyFacts(
        facts_id=facts_id,
        trader_opportunity_id=trader_opportunity_id,
        trader_id=trader_assessment.trader_id,
        shared_snapshot_id=snapshot.snapshot_id,
        canonical_instrument_id=snapshot.canonical_instrument_id,
        built_at=built_at,
        evidence_cutoff_at=snapshot.evidence_cutoff_at,
        opportunity_support=snapshot.relationship_coherence,
        continuation_support=snapshot.continuation_support,
        failure_hazard=snapshot.failure_hazard,
        positive_tail_support=snapshot.positive_tail_support,
        relationship_stability=snapshot.relationship_stability,
        regime_transition_state=snapshot.regime_transition_state,
        systemic_stress=snapshot.systemic_stress,
        uncertainty_bps=snapshot.uncertainty_bps,
        causal_maturity=snapshot.causal_maturity,
        evidence_refs=evidence_refs,
        trader_methodology_validated=True,
    )
