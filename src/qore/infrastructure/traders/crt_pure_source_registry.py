"""Source-evidence registry primitives for CRT PURE.

No concept in this module is an executable trading rule.  The registry exists to force
source provenance and adjudication before a concept can be promoted into Strategy
Identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_identity import (
    CrtPureAdjudicationState,
    CrtPureSourceTier,
)


class CrtPureConceptId(StrEnum):
    REFERENCE_RANGE = "reference_range"
    CRH_CRL = "crh_crl"
    EQUILIBRIUM = "equilibrium"
    LIQUIDATION_SWEEP = "liquidation_sweep"
    ONE_VS_TWO_SIDED_SWEEP = "one_vs_two_sided_sweep"
    RECLAIM_CLOSE_BACK_INSIDE = "reclaim_close_back_inside"
    ACCEPTANCE_OUTSIDE_RANGE = "acceptance_outside_range"
    CANDLE_1_2_3 = "candle_1_2_3"
    KISS_OF_DEATH = "kiss_of_death"
    JOURNEY = "journey"
    KEY_LEVELS = "key_levels"
    INVALIDATION = "invalidation"
    OPPORTUNITY_EXPIRY = "opportunity_expiry"
    NESTED_CRT = "nested_crt"
    TIMEFRAME_HIERARCHY = "timeframe_hierarchy"
    SESSION_TIME_RULES = "session_time_rules"
    ENTRY_FAMILIES = "entry_families"
    STRUCTURAL_STOP = "structural_stop"
    STRUCTURAL_DESTINATION = "structural_destination"
    CONTINUATION_REVERSAL = "continuation_reversal"
    FAILURE_CONDITIONS = "failure_conditions"
    MAKE_OR_BREAK_LEVEL = "make_or_break_level"
    REARM_IDENTITY = "rearm_identity"
    SAME_BAR_AMBIGUITY = "same_bar_ambiguity"
    BTCUSD_CONTINUOUS_MARKET = "btcusd_continuous_market"


@dataclass(frozen=True, slots=True)
class CrtPureSourceEvidence:
    """One source-bound piece of evidence for a CRT concept."""

    concept_id: CrtPureConceptId
    source_name: str
    source_tier: CrtPureSourceTier
    provenance: str
    locator: str
    normalized_statement: str
    adjudication: CrtPureAdjudicationState
    content_sha256: str | None = None
    ambiguity_notes: str = ""
    contradiction_notes: str = ""

    def __post_init__(self) -> None:
        for field_name, value in (
            ("source_name", self.source_name),
            ("provenance", self.provenance),
            ("locator", self.locator),
            ("normalized_statement", self.normalized_statement),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.content_sha256 is not None:
            digest = self.content_sha256.lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("content_sha256 must be a 64-character hex digest")
        if (
            self.adjudication is CrtPureAdjudicationState.CANONICAL
            and self.source_tier is CrtPureSourceTier.LEVEL_B
        ):
            raise ValueError("LEVEL_B evidence cannot independently be CANONICAL")


@dataclass(frozen=True, slots=True)
class CrtPureConceptRecord:
    """Evidence collected for one CRT concept."""

    concept_id: CrtPureConceptId
    evidence: tuple[CrtPureSourceEvidence, ...] = ()

    @property
    def promotable_to_strategy_identity(self) -> bool:
        canonical = tuple(
            item
            for item in self.evidence
            if item.adjudication is CrtPureAdjudicationState.CANONICAL
            and item.source_tier in {
                CrtPureSourceTier.LEVEL_A,
                CrtPureSourceTier.LEVEL_A_PLUS,
            }
        )
        unresolved = any(
            item.adjudication is CrtPureAdjudicationState.AMBIGUOUS
            for item in self.evidence
        )
        contradicted = any(bool(item.contradiction_notes.strip()) for item in canonical)
        return bool(canonical) and not unresolved and not contradicted


CRT_PURE_REQUIRED_CONCEPTS: tuple[CrtPureConceptId, ...] = tuple(CrtPureConceptId)


_DISCOVERED_LEVEL_A_EVIDENCE: dict[
    CrtPureConceptId,
    tuple[CrtPureSourceEvidence, ...],
] = {
    CrtPureConceptId.SESSION_TIME_RULES: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.SESSION_TIME_RULES,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?after=6244",
            normalized_statement=(
                "RomeoTPT published market-family timing notation: "
                "Forex 159159; Index futures 26102610; Crypto 12481248."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "The post does not by itself define machine semantics, timezone, "
                "anchor interpretation, eligible candles, or execution windows."
            ),
        ),
    ),
    CrtPureConceptId.TIMEFRAME_HIERARCHY: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.TIMEFRAME_HIERARCHY,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?after=6244",
            normalized_statement=(
                "RomeoTPT states that the lower-timeframe picture can be difficult "
                "to see and that moving to a higher timeframe can make the answer clearer."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "This supports higher-timeframe contextual relevance but does not "
                "define a fixed top-down mapping or executable timeframe ladder."
            ),
        ),
    ),
    CrtPureConceptId.EQUILIBRIUM: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.EQUILIBRIUM,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram around CRT Secrets episode 8",
            locator="https://t.me/s/officialRomeotpt?before=6461",
            normalized_statement=(
                "RomeoTPT references trading CRT highs/lows toward the 50 percent area."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "This is not enough to freeze 50 percent as a universal target, "
                "partial, equilibrium rule, stop rule, or exit policy."
            ),
        ),
    ),
    CrtPureConceptId.ENTRY_FAMILIES: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.ENTRY_FAMILIES,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt",
            normalized_statement=(
                "RomeoTPT states that some trades are entered after chart analysis "
                "and price action provides a reason, while some entries are based on time."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "The post establishes more than one entry context but does not define "
                "the exact CRT entry families or their deterministic triggers."
            ),
        ),
    ),
    CrtPureConceptId.CRH_CRL: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.CRH_CRL,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?before=6354",
            normalized_statement=(
                "RomeoTPT explicitly refers to CRTH/L as structural price levels "
                "from which price can travel toward the 50 percent area."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "The source confirms CRTH/L terminology and relevance but does not "
                "in this post define the exact candle-selection algorithm that creates them."
            ),
        ),
    ),
    CrtPureConceptId.LIQUIDATION_SWEEP: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.LIQUIDATION_SWEEP,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt/6615",
            normalized_statement=(
                "For an ideal bearish reaction, RomeoTPT describes a candle opening, "
                "stabbing into an old CRTH, and then dumping."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "This directly supports penetration of an old CRTH as relevant behavior, "
                "but does not yet define universal sweep depth, close requirement, or entry trigger."
            ),
        ),
    ),
    CrtPureConceptId.STRUCTURAL_DESTINATION: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.STRUCTURAL_DESTINATION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?before=6354",
            normalized_statement=(
                "RomeoTPT explicitly describes taking price from CRTH/L toward 50 percent."
            ),
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "Other official examples also describe range-high to range-low travel. "
                "More context is required before freezing one universal destination hierarchy."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.STRUCTURAL_DESTINATION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?before=6612",
            normalized_statement="RomeoTPT posts an example described as Nasdaq range high to range low.",
            adjudication=CrtPureAdjudicationState.AMBIGUOUS,
            ambiguity_notes=(
                "The example proves opposite-range travel exists in the source corpus, "
                "not that it is always the mandatory target."
            ),
        ),
    ),
    CrtPureConceptId.MAKE_OR_BREAK_LEVEL: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.MAKE_OR_BREAK_LEVEL,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?before=6745",
            normalized_statement=(
                "MOB means make-or-break level. If price breaks through it, RomeoTPT "
                "states the target will be hit; if the level is respected, it blocks "
                "the target and the trade idea should be scratched."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
}


CRT_PURE_SOURCE_REGISTRY: tuple[CrtPureConceptRecord, ...] = tuple(
    CrtPureConceptRecord(
        concept_id=concept_id,
        evidence=_DISCOVERED_LEVEL_A_EVIDENCE.get(concept_id, ()),
    )
    for concept_id in CRT_PURE_REQUIRED_CONCEPTS
)


def pending_concepts() -> tuple[CrtPureConceptId, ...]:
    """Return concepts that are not yet source-promotable."""

    return tuple(
        record.concept_id
        for record in CRT_PURE_SOURCE_REGISTRY
        if not record.promotable_to_strategy_identity
    )


def evidence_backed_concepts() -> tuple[CrtPureConceptId, ...]:
    """Return concepts with discovered source evidence, regardless of promotion state."""

    return tuple(
        record.concept_id
        for record in CRT_PURE_SOURCE_REGISTRY
        if record.evidence
    )


def promotable_concepts() -> tuple[CrtPureConceptId, ...]:
    """Return concepts whose current primary evidence is closed enough for Identity."""

    return tuple(
        record.concept_id
        for record in CRT_PURE_SOURCE_REGISTRY
        if record.promotable_to_strategy_identity
    )
