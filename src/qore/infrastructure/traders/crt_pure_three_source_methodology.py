"""Owner-authorized CRT THREE-SOURCE methodology governance, not Romeo-only.

The three-source identity means RomeoTPT, SpeculatorFL and TraderFlameseN can
inform QORE's explicitly named strategy. It does NOT mean authors agreed on
unwritten rules or that any geometric coincidence is an approved trade.

No sizing, PnL, capital permissions, broker access, or auto-certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_source_corpus import (
    CRT_PURE_CORROBORATION_CORPUS,
    CRT_PURE_PRIMARY_SOURCE_CORPUS,
    CrtPureSourceArtifactStatus,
)

POLICY_ID = "VT08_CRT_THREE_SOURCE_QORE_V1"
AUTHORIZED_SOURCE_NAMES = ("RomeoTPT", "SpeculatorFL", "TraderFlameseN")


class CrtThreeSourceRule(StrEnum):
    REFERENCE_ELIGIBILITY = "reference_eligibility"
    MULTIPLE_REFERENCE_PRIORITY = "multiple_reference_priority"
    PARENT_CHILD_TIMEFRAME = "parent_child_timeframe"
    ENTRY_CONFIRMATION = "entry_confirmation"
    INVALIDATION_EXPIRY = "invalidation_expiry"
    DESTINATION_LIFECYCLE = "destination_lifecycle"
    CONFLICT_AND_REARM = "conflict_and_rearm"


class CrtThreeSourceDecision(StrEnum):
    OPEN = "OPEN"
    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    OWNER_APPROVED_QORE_ENGINEERING = "OWNER_APPROVED_QORE_ENGINEERING"


@dataclass(frozen=True, slots=True)
class CrtThreeSourceRuleContract:
    rule: CrtThreeSourceRule
    decision: CrtThreeSourceDecision = CrtThreeSourceDecision.OPEN
    operational_rule: str = ""
    source_name: str = ""
    source_locator: str = ""
    independent_adjudication_id: str = ""
    owner_approval_id: str = ""
    conflict_resolution: str = ""
    future_outcome_used: bool = False
    sizing_used: bool = False

    def __post_init__(self) -> None:
        if self.future_outcome_used or self.sizing_used:
            raise ValueError("three-source methodology cannot use outcome or sizing")
        if self.source_name and self.source_name not in AUTHORIZED_SOURCE_NAMES:
            raise ValueError("source must be in Owner-approved triad")
        if self.decision is CrtThreeSourceDecision.OPEN:
            if self.operational_rule or self.owner_approval_id:
                raise ValueError("OPEN rules cannot silently install an executable contract")
            return
        if not self.operational_rule.strip() or not self.independent_adjudication_id.strip():
            raise ValueError("closed rule requires machine contract and independent adjudication")
        if self.decision is CrtThreeSourceDecision.SOURCE_SUPPORTED:
            if not self.source_name or not self.source_locator:
                raise ValueError("source-supported rule must name original evidence")
            if not _known_source_locator(self.source_name, self.source_locator):
                raise ValueError("source locator not present in accepted CRT triad corpus")
        if self.decision is CrtThreeSourceDecision.OWNER_APPROVED_QORE_ENGINEERING:
            if not self.owner_approval_id.strip() or not self.conflict_resolution.strip():
                raise ValueError("QORE-specific rule requires Owner approval and justification")


def _known_source_locator(source_name: str, locator: str) -> bool:
    return any(
        artifact.source_name == source_name
        and artifact.status in (
            CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
            CrtPureSourceArtifactStatus.VERIFIED_CORROBORATION_MIRROR,
        )
        and locator == artifact.canonical_url
        for artifact in (
            *CRT_PURE_PRIMARY_SOURCE_CORPUS,
            *CRT_PURE_CORROBORATION_CORPUS,
        )
    )


@dataclass(frozen=True, slots=True)
class CrtThreeSourceMethodologyAssessment:
    policy_id: str
    source_names: tuple[str, ...]
    methodology_closed: bool
    blockers: tuple[str, ...]
    allows_research_only: bool = True
    grants_trading_authority: bool = False
    grants_volume_authority: bool = False


def evaluate_three_source_methodology(
    contracts: tuple[CrtThreeSourceRuleContract, ...],
) -> CrtThreeSourceMethodologyAssessment:
    """Check ALL Owner-approved composition contracts, not Romeo exclusivity.

    Every rule has its own source or explicitly Owner-approved engineering
    authority. Source-supported never means 'three authors agreed'.
    A proposal does not replace real independent reviewer authentication.
    """
    required = tuple(CrtThreeSourceRule)
    if tuple(c.rule for c in contracts) != required:
        raise ValueError("all seven distinct contracts must be in canonical order")
    missing_sources = tuple(
        name
        for name in AUTHORIZED_SOURCE_NAMES
        if not any(
            artifact.source_name == name
            and artifact.status in (
                CrtPureSourceArtifactStatus.VERIFIED_PRIMARY_LINK,
                CrtPureSourceArtifactStatus.VERIFIED_CORROBORATION_MIRROR,
            )
            for artifact in (
                *CRT_PURE_PRIMARY_SOURCE_CORPUS,
                *CRT_PURE_CORROBORATION_CORPUS,
            )
        )
    )
    blockers = [f"TRIAD_SOURCE_MISSING:{s}" for s in missing_sources]
    blockers.extend(
        f"THREE_SOURCE_RULE_OPEN:{c.rule.value}"
        for c in contracts
        if c.decision is CrtThreeSourceDecision.OPEN
    )
    return CrtThreeSourceMethodologyAssessment(
        policy_id=POLICY_ID,
        source_names=AUTHORIZED_SOURCE_NAMES,
        methodology_closed=not blockers,
        blockers=tuple(blockers),
    )


def current_three_source_methodology() -> CrtThreeSourceMethodologyAssessment:
    """Actual repo state: corpus linked, seven operational policies NOT adjudicated.

    No Romeo-exclusive blocker: failure to certify is missing QORE rule
    adjudication/review, not the absence of an exact Romeo-only selector.
    """
    return evaluate_three_source_methodology(
        tuple(CrtThreeSourceRuleContract(rule) for rule in CrtThreeSourceRule)
    )
