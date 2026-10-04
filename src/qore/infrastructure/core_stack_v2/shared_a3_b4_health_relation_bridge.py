"""B-09/B-10 application bridge for the A3<->B4 seam.

B-09 may update data-health/freshness truth but cannot grant relation authority.
B-10 may update relation eligibility only after the base seam contract already
proves identity, canonical market time, temporal comparability and healthy data.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from qore.infrastructure.core_stack_v2.shared_a3_b4_seam_contract import (
    SharedA3B4RelationEligibility,
    SharedA3B4SeamValidationError,
    SharedA3B4WorldFact,
)


def _validate_evidence(
    *,
    decision_timestamp: datetime,
    evidence_cutoff_at: datetime,
    provenance_refs: tuple[str, ...],
) -> None:
    if evidence_cutoff_at.tzinfo is None or evidence_cutoff_at.utcoffset() is None:
        raise SharedA3B4SeamValidationError(
            "integration evidence cutoff must be timezone-aware"
        )
    if evidence_cutoff_at > decision_timestamp:
        raise SharedA3B4SeamValidationError(
            "integration evidence cannot exceed decision timestamp"
        )
    if (
        not provenance_refs
        or provenance_refs != tuple(sorted(set(provenance_refs)))
    ):
        raise SharedA3B4SeamValidationError(
            "integration provenance must be non-empty, unique and canonical"
        )


def apply_b09_data_health(
    fact: SharedA3B4WorldFact,
    *,
    data_health_state: str,
    uncertainty_floor_bps: int,
    evidence_cutoff_at: datetime,
    provenance_refs: tuple[str, ...],
    target_or_outcome_used: bool = False,
    future_market_used: bool = False,
    productive_authority: bool = False,
) -> SharedA3B4WorldFact:
    """Apply B-09 truth without changing B-10 relation eligibility."""

    if not data_health_state.strip():
        raise SharedA3B4SeamValidationError("B-09 data health state must be explicit")
    if not 0 <= uncertainty_floor_bps <= 10_000:
        raise SharedA3B4SeamValidationError(
            "B-09 uncertainty floor must be within 0..10000"
        )
    _validate_evidence(
        decision_timestamp=fact.decision_timestamp,
        evidence_cutoff_at=evidence_cutoff_at,
        provenance_refs=provenance_refs,
    )
    if target_or_outcome_used or future_market_used or productive_authority:
        raise SharedA3B4SeamValidationError(
            "B-09 evidence carries forbidden authority or hindsight"
        )

    return replace(
        fact,
        source_workstream=f"{fact.source_workstream}+B-09",
        data_health_state=data_health_state,
        fact_timestamp=max(fact.fact_timestamp, evidence_cutoff_at),
        uncertainty_bps=max(fact.uncertainty_bps, uncertainty_floor_bps),
        provenance_refs=tuple(sorted(set(fact.provenance_refs + provenance_refs))),
    )


def apply_b10_relation_eligibility(
    fact: SharedA3B4WorldFact,
    *,
    relation_eligibility: SharedA3B4RelationEligibility,
    evidence_cutoff_at: datetime,
    provenance_refs: tuple[str, ...],
    target_or_outcome_used: bool = False,
    future_market_used: bool = False,
    productive_authority: bool = False,
) -> SharedA3B4WorldFact:
    """Apply B-10 eligibility through the fail-closed seam constructor."""

    _validate_evidence(
        decision_timestamp=fact.decision_timestamp,
        evidence_cutoff_at=evidence_cutoff_at,
        provenance_refs=provenance_refs,
    )
    if target_or_outcome_used or future_market_used or productive_authority:
        raise SharedA3B4SeamValidationError(
            "B-10 evidence carries forbidden authority or hindsight"
        )

    return replace(
        fact,
        source_workstream=f"{fact.source_workstream}+B-10",
        relation_eligibility=relation_eligibility,
        fact_timestamp=max(fact.fact_timestamp, evidence_cutoff_at),
        provenance_refs=tuple(sorted(set(fact.provenance_refs + provenance_refs))),
    )
