"""Provenance map for every deterministic Capitalizer source-strategy requirement V2."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_source_strategy_review_v2 import (
    FROZEN_SOURCE_STRATEGY_REVIEW,
    CapitalizerSourceFactType,
)

SOURCE_STRATEGY_PROVENANCE_ID = "QORE_CAPITALIZER_SOURCE_STRATEGY_PROVENANCE_V2"


@dataclass(frozen=True, slots=True)
class CapitalizerGrammarRequirementProvenance:
    requirement_id: str
    source_fact_ids: tuple[str, ...]
    qore_operationalization: bool = False

    def __post_init__(self) -> None:
        if not self.requirement_id or self.requirement_id != self.requirement_id.upper():
            raise ValueError("requirement_id must be non-empty uppercase")
        if not self.source_fact_ids and not self.qore_operationalization:
            raise ValueError("grammar requirement needs source facts or explicit QORE provenance")


GRAMMAR_REQUIREMENT_PROVENANCE: tuple[
    CapitalizerGrammarRequirementProvenance, ...
] = (
    CapitalizerGrammarRequirementProvenance(
        "SOURCE_SESSION_CONTEXT",
        (
            "ICT_ASIA_FAVORS_AUD_NZD_JPY_ACTIVITY",
            "ICT_LONDON_KILLZONE_0200_0500_NY",
            "ICT_NEW_YORK_KILLZONE_0700_0900_NY",
        ),
    ),
    CapitalizerGrammarRequirementProvenance(
        "HIGHER_TIMEFRAME_BIAS_ALIGNED",
        (
            "ICT_DAILY_BIAS_PRECEDES_SCALP_EXECUTION",
            "TTRADES_FAILURE_TO_MANIPULATE_USES_HTF_BIAS",
            "TTRADES_SCALP_TOP_DOWN_H1_M15_M1",
        ),
    ),
    CapitalizerGrammarRequirementProvenance(
        "STRUCTURAL_LIQUIDITY_OBJECTIVE_AVAILABLE",
        ("ICT_LIQUIDITY_TARGETS_RECENT_DAILY_HIGHS_LOWS",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "TARGET_HIGHER_TIMEFRAME_OR_STRUCTURAL",
        ("TTRADES_TARGET_USES_HIGHER_TIMEFRAME_OBJECTIVE",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "PROTECTED_SWING_AVAILABLE",
        ("TTRADES_PROTECTED_SWING_STOP",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "H1_EXPANSION_BIAS_CONFIRMED",
        ("TTRADES_H1_EXPANSION_BIAS_C2_C3",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "M15_SWING_STRUCTURE_CONFIRMED",
        ("TTRADES_M15_SWING_THEN_M1_CONTINUATION",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "M1_CONTINUATION_CONFIRMED",
        ("TTRADES_M15_SWING_THEN_M1_CONTINUATION",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "LIQUIDITY_LEVEL_TAKEN",
        ("TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "CANDLE_CLOSURE_CONFIRMATION_COMPLETE",
        ("TTRADES_WAIT_FOR_CANDLE_CLOSURE_CONFIRMATION",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "EXPECTED_REVERSAL_FAILED_TO_CONFIRM",
        ("TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",),
    ),
    CapitalizerGrammarRequirementProvenance(
        "CONTINUATION_STRUCTURE_CONFIRMED",
        (
            "TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",
            "TTRADES_FAILURE_TO_MANIPULATE_USES_HTF_BIAS",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceStrategyProvenanceMap:
    provenance_id: str = SOURCE_STRATEGY_PROVENANCE_ID
    requirements: tuple[
        CapitalizerGrammarRequirementProvenance, ...
    ] = GRAMMAR_REQUIREMENT_PROVENANCE
    outcome_derived_rule_allowed: bool = False

    def __post_init__(self) -> None:
        if self.provenance_id != SOURCE_STRATEGY_PROVENANCE_ID:
            raise ValueError("strategy provenance identity is frozen")
        if self.outcome_derived_rule_allowed:
            raise ValueError("source strategy grammar cannot learn rules from terminal outcomes")

        requirement_ids = tuple(item.requirement_id for item in self.requirements)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("strategy provenance requirements must be unique")

        reviewed = {item.fact_id: item for item in FROZEN_SOURCE_STRATEGY_REVIEW.facts}
        for requirement in self.requirements:
            for fact_id in requirement.source_fact_ids:
                fact = reviewed.get(fact_id)
                if fact is None:
                    raise ValueError(f"grammar references unknown reviewed fact: {fact_id}")
                if fact.fact_type is not CapitalizerSourceFactType.AUTHOR_SUPPORTED:
                    raise ValueError(
                        "author grammar requirement cannot cite QORE operationalization"
                    )


FROZEN_SOURCE_STRATEGY_PROVENANCE = CapitalizerSourceStrategyProvenanceMap()
