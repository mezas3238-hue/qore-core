"""Cross-lane Shared evidence-to-master reconciliation.

This module belongs to the Integrator support lane. It never upgrades the
canonical Shared master ledger. It only identifies evidence that deserves a
formal closure audit, plus dependency-open evidence that must remain blocked.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qore.infrastructure.core_stack_v2.shared_zero_open_work import (
    SharedWorkState,
    build_shared_master_open_work_ledger,
)


class ReconciliationReadiness(StrEnum):
    EVIDENCE_PRESENT = "EVIDENCE_PRESENT"
    DEPENDENCY_OPEN = "DEPENDENCY_OPEN"
    EXTERNAL_BLOCKED = "EXTERNAL_BLOCKED"


@dataclass(frozen=True, slots=True)
class IntegratorEvidenceCandidate:
    source_lane: str
    source_id: str
    master_work_id: str
    evidence_ref: str
    readiness: ReconciliationReadiness
    note: str

    def __post_init__(self) -> None:
        if self.source_lane not in {"A", "B", "INTEGRATOR"}:
            raise ValueError("unsupported source lane")
        if not self.source_id.strip() or not self.master_work_id.strip():
            raise ValueError("candidate identities must be non-empty")
        if not self.evidence_ref.strip() or not self.note.strip():
            raise ValueError("candidate evidence and note must be non-empty")


INTEGRATOR_EVIDENCE_CANDIDATES: Final = (
    IntegratorEvidenceCandidate(
        "A",
        "MC09_BELIEF_STATE_CALIBRATION_V2",
        "MC-09",
        "github-actions://36754966932/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Belief-state real replay and temporal calibration evidence exist; formal maximum-standard closure audit remains required.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "MC10_MARKET_PHYSICS_TRANSITION_STABILITY",
        "MC-10",
        "github-actions://36755380068/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Market-physics foundation and transition-stability evidence exist; formal maximum-standard closure audit remains required.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "MC11_NEURAL_SYMBOLIC_FOUNDATION",
        "MC-11",
        "github-actions://36757812741/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Neural-symbolic hard-constraint boundary is green; full capability closure still requires explicit audit against Standard 006.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "MC16_SCIENTIFIC_MEMORY",
        "MC-16",
        "github-actions://36752791958/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Scientific-memory verified binding is green and should be reconciled against the canonical MC-16 closure law.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "WP06_AGENCY_TRAJECTORY_V2",
        "WP-06",
        "github-actions://36757160112/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Market Agency V2 evidence exists; WP closure remains a separate governed audit.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "STI10_VT31_REAL_PROJECTION",
        "STI-10",
        "github-actions://36757202255/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Real VT31 projection evidence exists; universal STI-10 closure must not be inferred from one Trader.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "STI11_MATERIALITY",
        "STI-11",
        "github-actions://36747436024/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Source-only materiality and dedup replay is green; closure audit remains required.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "STI12_SWING_SEMANTICS",
        "STI-12",
        "github-actions://36756749733/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Swing-support semantics are green; closure audit must verify scope and evidence sufficiency.",
    ),
    IntegratorEvidenceCandidate(
        "A",
        "STI14_REAL_ATTRIBUTION",
        "STI-14",
        "github-actions://36744108322/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Real control/treatment attribution audit is green; canonical STI-14 state should be reconciled.",
    ),
    IntegratorEvidenceCandidate(
        "B",
        "B-02_PROVIDER_CATALOGUE",
        "GW-1",
        "github-actions://36742519707/SUCCESS",
        ReconciliationReadiness.EVIDENCE_PRESENT,
        "Provider catalogue/drift freeze is integrated and already corresponds to a closed provider-capability layer.",
    ),
    IntegratorEvidenceCandidate(
        "B",
        "B-20_UNKNOWN_WORLD",
        "GW-20",
        "github-actions://36763268609/SUCCESS",
        ReconciliationReadiness.DEPENDENCY_OPEN,
        "Unknown-world semantics are green, but surrounding observability/blindspot completeness remains open; no automatic GW-20 closure.",
    ),
    IntegratorEvidenceCandidate(
        "B",
        "B-18_B19_B20_OBSERVABILITY_CLUSTER",
        "MC-28",
        "github-actions://36763268609/SUCCESS",
        ReconciliationReadiness.DEPENDENCY_OPEN,
        "Core/Broker cognition and blindspot cluster still requires runtime replication and declared-scope completeness.",
    ),
    IntegratorEvidenceCandidate(
        "B",
        "B-16_ACTIVE_PERCEPTION_ACQUISITION",
        "GW-21",
        "github-actions://36757173753/SUCCESS",
        ReconciliationReadiness.DEPENDENCY_OPEN,
        "Sensor resource boundary is green while global 177-sensor causal qualification remains incomplete.",
    ),
    IntegratorEvidenceCandidate(
        "B",
        "B-10_B11_B12_RELATIONAL_WORLD",
        "GW-18",
        "github-actions://36755296952/SUCCESS",
        ReconciliationReadiness.DEPENDENCY_OPEN,
        "Relational lifecycle architecture is green but empirical global population awaits canonical temporal comparability.",
    ),
)


def build_integrator_reconciliation() -> dict[str, object]:
    """Return a conservative reconciliation report with zero auto-promotion."""

    master = {item.work_id: item for item in build_shared_master_open_work_ledger()}
    unknown_ids = sorted(
        candidate.master_work_id
        for candidate in INTEGRATOR_EVIDENCE_CANDIDATES
        if candidate.master_work_id not in master
    )
    if unknown_ids:
        raise ValueError(f"unknown master work ids: {unknown_ids}")

    already_closed: list[dict[str, str]] = []
    closure_audit_candidates: list[dict[str, str]] = []
    blocked_candidates: list[dict[str, str]] = []

    for candidate in INTEGRATOR_EVIDENCE_CANDIDATES:
        current = master[candidate.master_work_id]
        row = {
            "source_lane": candidate.source_lane,
            "source_id": candidate.source_id,
            "master_work_id": candidate.master_work_id,
            "master_state": current.state.value,
            "evidence_ref": candidate.evidence_ref,
            "readiness": candidate.readiness.value,
            "note": candidate.note,
        }
        if current.state is SharedWorkState.COMPLETED_AND_PROVEN:
            already_closed.append(row)
        elif candidate.readiness is ReconciliationReadiness.EVIDENCE_PRESENT:
            closure_audit_candidates.append(row)
        else:
            blocked_candidates.append(row)

    return {
        "identity": "QORE_SHARED_INTEGRATOR_RECONCILIATION_001",
        "candidate_count": len(INTEGRATOR_EVIDENCE_CANDIDATES),
        "already_closed": tuple(already_closed),
        "closure_audit_candidates": tuple(closure_audit_candidates),
        "blocked_candidates": tuple(blocked_candidates),
        "auto_promotions": 0,
        "canonical_ledger_mutated": False,
        "final_holdout_authority": False,
        "productive_authority": False,
    }
