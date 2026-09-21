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
    TIME_TURTLE_SOUP_RELATION = "time_turtle_soup_relation"
    MARKET_TIMEFRAME_SCOPE = "market_timeframe_scope"
    ENTRY_FAMILIES = "entry_families"
    STRUCTURAL_STOP = "structural_stop"
    STRUCTURAL_DESTINATION = "structural_destination"
    CONTINUATION_REVERSAL = "continuation_reversal"
    FAILURE_CONDITIONS = "failure_conditions"
    MAKE_OR_BREAK_LEVEL = "make_or_break_level"
    FIFTY_PERCENT_DESTINATION_FAMILY = "fifty_percent_destination_family"
    INCOMPLETE_CRT_TRAP = "incomplete_crt_trap"
    OPPOSITE_CRT_BIAS_REVERSAL = "opposite_crt_bias_reversal"
    OLD_CRTH_CRL_STAB_REACTION = "old_crth_crl_stab_reaction"
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


_DISCOVERED_SOURCE_EVIDENCE: dict[
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
    CrtPureConceptId.TIME_TURTLE_SOUP_RELATION: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.TIME_TURTLE_SOUP_RELATION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?after=6340",
            normalized_statement=(
                "RomeoTPT states that T stands for theory and also symbolizes Time "
                "and Turtle Soup; Time is the heart/brain and Turtle Soup the limbs "
                "that combine to deliver CRT function."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.MARKET_TIMEFRAME_SCOPE: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.MARKET_TIMEFRAME_SCOPE,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt/6455",
            normalized_statement=(
                "RomeoTPT states that his concepts work across all markets "
                "and all timeframes."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
            ambiguity_notes=(
                "Scope applicability does not define identical session timing, "
                "selection filters, or execution parameters across markets."
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
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "The source keeps multiple entry contexts; the baseline C3 family is "
                "closed separately and does not erase other source-authorized families."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.ENTRY_FAMILIES,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical CRT Secrets episode 7 and foundational video; "
                "indexed transcript extraction used only as transport"
            ),
            locator="https://www.youtube.com/watch?v=h7NCST2wPw8",
            normalized_statement=(
                "A source-authorized baseline entry family waits for Candle 2 to close "
                "and trades the Candle 3 opportunity in relation to a key level; "
                "the source also teaches additional entry families."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.REFERENCE_RANGE: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.REFERENCE_RANGE,
            source_name="SpeculatorFL",
            source_tier=CrtPureSourceTier.LEVEL_B,
            provenance="approved SpeculatorFL CRT thread mirror",
            locator="https://threadreaderapp.com/thread/1784493604473618604#31",
            normalized_statement=(
                "SpeculatorFL describes the CRT core concept as every candle being "
                "a range with high, low, open and close."
            ),
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "Level B corroboration only. Primary RomeoTPT evidence is still required "
                "before the reference-range definition can become CANONICAL."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.REFERENCE_RANGE,
            source_name="TraderFlameseN",
            source_tier=CrtPureSourceTier.LEVEL_B,
            provenance="approved TraderFlameseN CRT thread mirror",
            locator="https://threadreaderapp.com/thread/1790141530461622525#29",
            normalized_statement=(
                "TraderFlameseN independently describes every candle as a range "
                "with high, low, open and close."
            ),
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes="Primary RomeoTPT evidence remains required.",
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.REFERENCE_RANGE,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical foundational RomeoTPT video; timestamp extraction "
                "cross-checked through indexed transcript summaries"
            ),
            locator="https://www.youtube.com/watch?v=UUq_wKQ61Wo&t=79s",
            normalized_statement=(
                "Every candle represents a range with its own open, high, low and close; "
                "the trader must select which candle range is being traded."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical foundational RomeoTPT video; timestamp extraction "
                "cross-checked through indexed transcript summaries"
            ),
            locator="https://www.youtube.com/watch?v=UUq_wKQ61Wo&t=116s",
            normalized_statement=(
                "The Turtle Soup outcome is distinguished from breakout acceptance by "
                "penetrating a range boundary and closing back on the range side of it."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.CANDLE_1_2_3: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.CANDLE_1_2_3,
            source_name="SpeculatorFL",
            source_tier=CrtPureSourceTier.LEVEL_B,
            provenance="approved SpeculatorFL Telegram channel",
            locator="https://t.me/s/ShamSpeculatorFL?before=503",
            normalized_statement=(
                "SpeculatorFL describes a three-candle liquidity cycle: Candle 1 "
                "generates/accumulates liquidity; Candle 2 purges/manipulates liquidity; "
                "Candle 3 neutralizes/distributes liquidity."
            ),
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "This is a navigation hypothesis for RomeoTPT episode 7 and related "
                "primary material, not a canonical CRT rule yet."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.CANDLE_1_2_3,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical foundational video plus CRT Secrets episode 7; "
                "indexed transcript extraction used only as transport"
            ),
            locator="https://www.youtube.com/watch?v=h7NCST2wPw8",
            normalized_statement=(
                "The baseline three-candle cycle is Candle 1 accumulation/range, "
                "Candle 2 manipulation, and Candle 3 distribution; Candle 2 must close "
                "before the Candle 3 opportunity is acted upon."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.INVALIDATION: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.INVALIDATION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical foundational video and CRT Secrets episode 8; "
                "indexed transcript extraction used only as transport"
            ),
            locator="https://www.youtube.com/watch?v=UUq_wKQ61Wo&t=2589s",
            normalized_statement=(
                "Do not force a reversal when the required Turtle Soup is absent; "
                "acceptance by close outside the selected range is a breakout rather than "
                "the reclaimed Turtle Soup thesis."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.NESTED_CRT: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.NESTED_CRT,
            source_name="SpeculatorFL",
            source_tier=CrtPureSourceTier.LEVEL_B,
            provenance="approved SpeculatorFL CRT thread mirror",
            locator="https://threadreaderapp.com/thread/1784493604473618604#113",
            normalized_statement=(
                "SpeculatorFL describes lower-timeframe CRT inside higher-timeframe CRT "
                "as a protocol for bias/direction-of-liquidity confirmation."
            ),
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes="Exact source-faithful nesting semantics remain open.",
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
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "Telegram confirms CRTH/L relevance; the selected-candle derivation "
                "is closed separately from the canonical foundational/KOD videos."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.CRH_CRL,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical CRT Secrets episode 2 with foundational range definition; "
                "transcript extraction used only as transport"
            ),
            locator="https://www.youtube.com/watch?v=FYr6J5pIDB4",
            normalized_statement=(
                "For the selected CRT reference candle, the candle high and low define "
                "the CRT range boundaries used as CRTH and CRTL."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
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
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "Telegram corroborates the penetration reaction; exact Turtle Soup "
                "penetration/reclaim semantics are closed from the foundational video."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.LIQUIDATION_SWEEP,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical foundational RomeoTPT video; timestamp extraction "
                "cross-checked through indexed transcript summaries"
            ),
            locator="https://www.youtube.com/watch?v=UUq_wKQ61Wo&t=116s",
            normalized_statement=(
                "A Turtle Soup manipulates one boundary of the selected candle range "
                "by trading beyond that boundary rather than accepting the breakout."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.STRUCTURAL_STOP: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.STRUCTURAL_STOP,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical CRT Secrets episode 2; indexed transcript extraction "
                "used only as transport"
            ),
            locator="https://www.youtube.com/watch?v=FYr6J5pIDB4",
            normalized_statement=(
                "For the KOD/Turtle Soup execution family, risk is placed beyond the "
                "Turtle Soup manipulation area, so the stop is structural rather than "
                "an arbitrary fixed distance."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
            ambiguity_notes=(
                "This closes the baseline structural-stop family; other source-authorized "
                "entry families may use their own tighter structural invalidation."
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
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "The destination hierarchy is closed separately: 50 percent first, "
                "then contextual continuation toward the opposite range edge."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.STRUCTURAL_DESTINATION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?before=6612",
            normalized_statement=(
                "RomeoTPT posts an example described as Nasdaq range high to range low."
            ),
            adjudication=CrtPureAdjudicationState.CORROBORATED,
            ambiguity_notes=(
                "Opposite-edge travel is an extension family, not a mandatory first target."
            ),
        ),
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.STRUCTURAL_DESTINATION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance=(
                "canonical CRT Secrets episode 8 plus official Telegram teaching; "
                "indexed transcript extraction used only as transport"
            ),
            locator="https://www.youtube.com/watch?v=-mWYppebugo",
            normalized_statement=(
                "CRT target number one is the 50 percent midpoint of the selected CRT "
                "candle; after that target completes, continuation may extend toward "
                "the opposite range edge or price may reverse."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
        ),
    ),
    CrtPureConceptId.FIFTY_PERCENT_DESTINATION_FAMILY: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.FIFTY_PERCENT_DESTINATION_FAMILY,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram around CRT Secrets episode 8",
            locator="https://t.me/s/officialRomeotpt/6455",
            normalized_statement=(
                "RomeoTPT explicitly states that trading from CRT highs/lows "
                "toward the 50 percent can form a complete trading approach."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
            ambiguity_notes=(
                "This closes 50 percent as a source-authorized destination family, "
                "not as the mandatory universal final target for every CRT."
            ),
        ),
    ),
    CrtPureConceptId.INCOMPLETE_CRT_TRAP: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.INCOMPLETE_CRT_TRAP,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram / CRT Secrets episode 8 excerpt",
            locator="https://t.me/s/officialRomeotpt?before=6521",
            normalized_statement=(
                "RomeoTPT identifies incomplete CRTs as a market-maker CRT trap."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
            ambiguity_notes=(
                "The existence of incomplete CRT failure is closed; the exact "
                "machine definition of incomplete remains part of FAILURE_CONDITIONS."
            ),
        ),
    ),
    CrtPureConceptId.OPPOSITE_CRT_BIAS_REVERSAL: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.OPPOSITE_CRT_BIAS_REVERSAL,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt?after=6340",
            normalized_statement=(
                "When the market presents a convincing CRT opposite to the expected "
                "bias, RomeoTPT instructs the trader to evaluate changing bias and act."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
            ambiguity_notes=(
                "The source closes bias adaptability; what qualifies as convincing "
                "still requires the complete CRT validity contract."
            ),
        ),
    ),
    CrtPureConceptId.OLD_CRTH_CRL_STAB_REACTION: (
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.OLD_CRTH_CRL_STAB_REACTION,
            source_name="RomeoTPT",
            source_tier=CrtPureSourceTier.LEVEL_A,
            provenance="official RomeoTPT Telegram",
            locator="https://t.me/s/officialRomeotpt/6615",
            normalized_statement=(
                "For an ideal bearish reaction, RomeoTPT describes a candle opening, "
                "stabbing into an old CRTH, then dumping."
            ),
            adjudication=CrtPureAdjudicationState.CANONICAL,
            ambiguity_notes=(
                "This closes the existence of an old-CRTH stab reaction family. "
                "It does not by itself close universal sweep or entry semantics."
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
        evidence=_DISCOVERED_SOURCE_EVIDENCE.get(concept_id, ()),
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
