"""V48 historical specification lineage.

This ledger distinguishes:
- source claims,
- QORE/Owner execution contracts,
- CI implementation verification,
- later source-fidelity adjudication.

A CI-green historical contract proves implementation conformance, not source truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_HISTORICAL_SPECIFICATION_LINEAGE"


class V48HistoricalAuthority(StrEnum):
    SOURCE_REVIEW = "SOURCE_REVIEW"
    OWNER_QORE_CONTRACT = "OWNER_QORE_CONTRACT"
    IMPLEMENTATION_VERIFICATION = "IMPLEMENTATION_VERIFICATION"
    CONSUMED_RESEARCH_EVIDENCE = "CONSUMED_RESEARCH_EVIDENCE"
    V48_ADJUDICATION = "V48_ADJUDICATION"


@dataclass(frozen=True, slots=True)
class V48HistoricalDecision:
    decision_id: str
    authority: V48HistoricalAuthority
    github_comment_id: int
    statement: str
    source_fidelity_proof: bool

    def __post_init__(self) -> None:
        if not self.decision_id or self.decision_id != self.decision_id.upper():
            raise ValueError("historical decision id must be non-empty uppercase")
        if self.github_comment_id <= 0:
            raise ValueError("historical decision requires GitHub comment provenance")
        if not self.statement:
            raise ValueError("historical decision requires statement")


DECISIONS: tuple[V48HistoricalDecision, ...] = (
    V48HistoricalDecision(
        "DUAL_SOURCE_ALL_MANDATORY_GATE_FROZEN",
        V48HistoricalAuthority.OWNER_QORE_CONTRACT,
        5752704647,
        (
            "QORE froze eighteen common/ICT/TTrades conditions as simultaneously mandatory "
            "before source-engine risk handoff."
        ),
        False,
    ),
    V48HistoricalDecision(
        "DUAL_SOURCE_GATE_IMPLEMENTATION_CI_GREEN",
        V48HistoricalAuthority.IMPLEMENTATION_VERIFICATION,
        5752704647,
        (
            "Workflow 35537979009 verified fail-closed enforcement of the frozen dual-source "
            "specification. This verifies implementation conformance, not source-fidelity of "
            "the conjunction."
        ),
        False,
    ),
    V48HistoricalDecision(
        "M1_MSS_FVG_OB_DECLARED_QORE_CONTRACT",
        V48HistoricalAuthority.OWNER_QORE_CONTRACT,
        5752850268,
        (
            "GitHub explicitly records that M1 MSS + FVG + validated OB is an Owner/QORE "
            "execution contract and is not falsely attributed as one verbatim author rule."
        ),
        False,
    ),
    V48HistoricalDecision(
        "STRICT_M5_SURROGATE_FUNNEL",
        V48HistoricalAuthority.CONSUMED_RESEARCH_EVIDENCE,
        5752756993,
        (
            "The strict M5 surrogate reduced 55,532 original candidates to 1,872 accepted "
            "surrogate rows, demonstrating the multiplicative effect of stacked gates."
        ),
        False,
    ),
    V48HistoricalDecision(
        "V47_S2_OWNER_DENSITY_REJECTION",
        V48HistoricalAuthority.CONSUMED_RESEARCH_EVIDENCE,
        5902864089,
        (
            "Owner rejected V47-S2 for insufficient density before Fresh Holdout."
        ),
        False,
    ),
    V48HistoricalDecision(
        "V48_SOURCE_RECONSTRUCTION_OPENED",
        V48HistoricalAuthority.V48_ADJUDICATION,
        5903276270,
        (
            "V48 reopens source composition and requires provenance for the conjunction itself."
        ),
        True,
    ),
)


@dataclass(frozen=True, slots=True)
class V48HistoricalSpecificationLineage:
    identity: str = IDENTITY
    decisions: tuple[V48HistoricalDecision, ...] = DECISIONS
    ci_green_implies_source_fidelity: bool = False
    qore_contract_may_be_reclassified_as_author_rule: bool = False
    historical_evidence_must_be_preserved: bool = True
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 historical lineage identity is frozen")
        ids = tuple(item.decision_id for item in self.decisions)
        if len(ids) != len(set(ids)):
            raise ValueError("historical decision ids must be unique")
        if self.ci_green_implies_source_fidelity:
            raise ValueError("CI conformance cannot prove source interpretation")
        if self.qore_contract_may_be_reclassified_as_author_rule:
            raise ValueError("QORE engineering cannot masquerade as author methodology")
        if not self.historical_evidence_must_be_preserved:
            raise ValueError("V48 must preserve V45-V47 evidence")
        if self.fresh_holdout_authorized:
            raise ValueError("lineage audit grants no Fresh Holdout authority")


V48_HISTORICAL_SPECIFICATION_LINEAGE = V48HistoricalSpecificationLineage()
