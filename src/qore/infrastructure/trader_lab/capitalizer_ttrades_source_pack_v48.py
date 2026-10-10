"""V48 TTrades primary-source semantic pack.

The purpose is not to encode a strategy yet. It records what each source means:
required route structure, alternative route, alternative entry technique, fallback,
context, invalidation, or target rule.

A fact being source-explicit does not make it universal across every route.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_SOURCE_PACK"


class V48SourceStrength(StrEnum):
    SOURCE_EXPLICIT = "SOURCE_EXPLICIT"
    SOURCE_STRONGLY_IMPLIED = "SOURCE_STRONGLY_IMPLIED"


class V48RuleSemantics(StrEnum):
    ROUTE_REQUIRED = "ROUTE_REQUIRED"
    ALTERNATIVE_ROUTE = "ALTERNATIVE_ROUTE"
    ALTERNATIVE_ENTRY_TECHNIQUE = "ALTERNATIVE_ENTRY_TECHNIQUE"
    CONTEXT = "CONTEXT"
    PRIORITY_FALLBACK = "PRIORITY_FALLBACK"
    STOP_RULE = "STOP_RULE"
    TARGET_RULE = "TARGET_RULE"
    OPTIONAL_CONFLUENCE = "OPTIONAL_CONFLUENCE"


@dataclass(frozen=True, slots=True)
class V48TTradesRule:
    rule_id: str
    source_title: str
    source_url: str
    release_date: str
    statement: str
    strength: V48SourceStrength
    semantics: V48RuleSemantics
    route_scope: tuple[str, ...]
    universal_gate_supported: bool = False

    def __post_init__(self) -> None:
        if not self.rule_id or self.rule_id != self.rule_id.upper():
            raise ValueError("rule_id must be non-empty uppercase")
        if not self.source_url.startswith("https://ttrades.com/"):
            raise ValueError("V48 TTrades pack requires a TTrades primary source URL")
        if not self.statement or not self.route_scope:
            raise ValueError("source rule requires statement and route scope")
        if (
            self.semantics
            in {
                V48RuleSemantics.ALTERNATIVE_ROUTE,
                V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
                V48RuleSemantics.PRIORITY_FALLBACK,
                V48RuleSemantics.OPTIONAL_CONFLUENCE,
            }
            and self.universal_gate_supported
        ):
            raise ValueError("alternative/fallback/optional rule cannot be a universal hard gate")


RULES: tuple[V48TTradesRule, ...] = (
    V48TTradesRule(
        "SCALPING_MODEL_TIMEFRAME_STACK",
        "TTrades Scalping Model – Simple Day Trading Strategy",
        "https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        "2026-02-07",
        (
            "The named Scalping Model uses Daily context, H1 scalp bias, M15 swing structure "
            "and M1 execution."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ROUTE_REQUIRED,
        ("GENERIC_SCALP_H1_M15_M1",),
    ),
    V48TTradesRule(
        "SCALPING_MODEL_M1_EXECUTION_NOT_NARRATIVE",
        "TTrades Scalping Model – Simple Day Trading Strategy",
        "https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        "2026-02-07",
        (
            "M1 is the execution timeframe; the trade narrative should already be clear before "
            "reaching M1."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.CONTEXT,
        ("GENERIC_SCALP_H1_M15_M1",),
    ),
    V48TTradesRule(
        "SCALPING_MODEL_M1_CONTINUATION_EXAMPLES",
        "TTrades Scalping Model – Simple Day Trading Strategy",
        "https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        "2026-02-07",
        (
            "M1 continuation behavior is described with examples including FVG interaction, "
            "CISD and protected-swing formation; the source does not state these are one "
            "indivisible global AND gate."
        ),
        V48SourceStrength.SOURCE_STRONGLY_IMPLIED,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        ("GENERIC_SCALP_H1_M15_M1",),
    ),
    V48TTradesRule(
        "ASIA_POSITIONAL_OR_4H15M",
        "How to Trade Asia Using the TTrades Fractal Model",
        "https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",
        "2026-08-15",
        (
            "Asia has two primary approaches: positional execution when a completed HTF "
            "framework/protected swing already exists, OR a 4H Candle-2 plus 15M fractal route."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ALTERNATIVE_ROUTE,
        ("ASIA_POSITIONAL", "ASIA_4H_15M_FRACTAL"),
    ),
    V48TTradesRule(
        "LONDON_DAILY_4H_15M",
        "How to Trade London Using TTrades Fractal Model",
        "https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/",
        "2026-09-12",
        (
            "London starts from Daily bias, uses 4H wick/swing structure, then 15M "
            "CISD/protected-swing confirmation for execution."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ROUTE_REQUIRED,
        ("LONDON_DAILY_4H_15M",),
    ),
    V48TTradesRule(
        "BEST_TIMEFRAMES_DAILY_4H_15M",
        "The Best Timeframes for TTrades Fractal Model (Simple)",
        "https://ttrades.com/the-best-timeframes-for-ttrades-fractal-model-simple/",
        "2026-01-31",
        (
            "A preferred repeatable fractal model uses Daily bias, 4H swing structure and "
            "15M execution."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ROUTE_REQUIRED,
        ("DAILY_4H_15M_FRACTAL",),
    ),
    V48TTradesRule(
        "TIMEFRAME_ALIGNMENT_IS_RELATIONAL_NOT_ONE_FIXED_STACK",
        "Timeframe Alignment: How to Align Higher and Lower Time Frames for Precision Entries",
        "https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/",
        "2025-07-30",
        (
            "The method defines Bias, Structure and Entry layers and gives multiple pairings "
            "(Weekly/4H, Daily/1H, 4H/15M, 1H/5M, 30M/3M, 15M/1M), so the fractal relation "
            "is general while the exact timeframe stack is model/context dependent."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.CONTEXT,
        ("FRACTAL_FAMILY",),
    ),
    V48TTradesRule(
        "TIMEFRAME_ALIGNMENT_POSITIONAL_AND_CONTINUATION_ARE_DIFFERENT_TECHNIQUES",
        "Timeframe Alignment: How to Align Higher and Lower Time Frames for Precision Entries",
        "https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/",
        "2025-07-30",
        (
            "The same aligned thesis can be executed positionally or later through continuation "
            "structure; the source treats them as different entry techniques."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        ("FRACTAL_FAMILY",),
    ),
    V48TTradesRule(
        "REVERSAL_SEQUENCE_PROGRESSIVE_CONFIRMATION",
        "TTrades Reversal Sequence – Blending PD Arrays for Entries",
        "https://ttrades.com/reversal-sequence-building-an-entry-model-for-trading/",
        "2025",
        (
            "Purge, inversion, CISD, FVG and breaker are described as a progression where "
            "later stages add confirmation but can produce later entries."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        ("REVERSAL_FAMILY",),
    ),
    V48TTradesRule(
        "REVERSAL_SEQUENCE_DO_NOT_OVERLOAD_ENTRY_MODELS",
        "TTrades Reversal Sequence – Blending PD Arrays for Entries",
        "https://ttrades.com/reversal-sequence-building-an-entry-model-for-trading/",
        "2025",
        (
            "The source explicitly advises choosing one or two tools/models rather than "
            "overloading the entry with every available PD array/confluence."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        ("REVERSAL_FAMILY",),
    ),
    V48TTradesRule(
        "NY_MANIPULATION_ENTRY_MODEL_CHOICE",
        "Daily Profile: Understanding the New York Manipulation",
        "https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/",
        "2025-07-24",
        (
            "After London context, liquidity sweep and CISD, entries may be refined with an "
            "FVG, an Order Block, or another chosen entry model."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        ("NEW_YORK_MANIPULATION",),
    ),
    V48TTradesRule(
        "CONTINUATION_OB_IS_ONE_ENTRY_TECHNIQUE",
        "Using Order Blocks for Continuations",
        "https://ttrades.com/using-order-blocks-for-continuations/",
        "2025-08-01",
        (
            "After reversal/POI confirmation, a continuation Order Block is one way to enter; "
            "FVG reactions and liquidity sweeps can also define continuation opportunities."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        ("CONTINUATION_FAMILY",),
    ),
    V48TTradesRule(
        "POI_FVG_THEN_SWING_THEN_CISD_FALLBACK",
        "The Only Points of Interest That Actually Matter For Trading",
        "https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/",
        "2026-07-18",
        (
            "The POI framework searches in priority order: FVG first; if absent, swing high/low; "
            "if absent, CISD. This is fallback selection, not FVG AND swing AND CISD."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.PRIORITY_FALLBACK,
        ("FRACTAL_FAMILY",),
    ),
    V48TTradesRule(
        "PROTECTED_SWING_DEFINES_INVALIDATION",
        "Protected Swings in Trading - Identify and Confirm",
        "https://ttrades.com/protected-swings-understanding-trends-and-invalidations/",
        "2025",
        (
            "Confirmed protected swings define structural invalidation and can be used for stop "
            "placement in reversal and continuation contexts."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.STOP_RULE,
        ("FRACTAL_FAMILY", "CONTINUATION_FAMILY"),
    ),
    V48TTradesRule(
        "TARGET_UNTOUCHED_HTF_HIGH_LOW",
        "How to Set Price Targets Using the Fractal Model",
        "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/",
        "2026",
        (
            "Targets are defined from higher-timeframe structure, especially untouched prior "
            "highs/lows; a level already taken is no longer a valid target."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.TARGET_RULE,
        ("FRACTAL_FAMILY",),
    ),
    V48TTradesRule(
        "FTM_FAILURE_THEN_CONTINUATION",
        "How to Trade Breakouts (Failure to Manipulate)",
        "https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",
        "2026-09-05",
        (
            "After a high/low is taken, the expected reversal must actually fail to form before "
            "continuation becomes the actionable thesis."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ROUTE_REQUIRED,
        ("FAILURE_TO_MANIPULATE",),
    ),
    V48TTradesRule(
        "FTM_HTF_REASON_LTF_CONFIRMATION",
        "How to Trade Breakouts (Failure to Manipulate)",
        "https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",
        "2026-09-05",
        (
            "FTM is paired with higher-timeframe bias and uses lower-timeframe closure/structure "
            "to confirm the continuation and new protected swing."
        ),
        V48SourceStrength.SOURCE_EXPLICIT,
        V48RuleSemantics.ROUTE_REQUIRED,
        ("FAILURE_TO_MANIPULATE",),
    ),
)


@dataclass(frozen=True, slots=True)
class V48TTradesSourcePack:
    identity: str = IDENTITY
    rules: tuple[V48TTradesRule, ...] = RULES
    alternatives_must_remain_alternatives: bool = True
    route_scope_must_be_preserved: bool = True
    source_fact_may_be_globalized_without_evidence: bool = False
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 TTrades source pack identity is frozen")
        ids = tuple(rule.rule_id for rule in self.rules)
        if len(ids) != len(set(ids)):
            raise ValueError("TTrades V48 source rule IDs must be unique")
        if not self.alternatives_must_remain_alternatives:
            raise ValueError("alternative source routes/entries must remain alternatives")
        if not self.route_scope_must_be_preserved:
            raise ValueError("source facts cannot escape their route scope without evidence")
        if self.source_fact_may_be_globalized_without_evidence:
            raise ValueError("V48 forbids unsupported globalization of source facts")
        if self.fresh_holdout_authorized:
            raise ValueError("source pack grants no Fresh Holdout authority")


V48_TTRADES_SOURCE_PACK = V48TTradesSourcePack()
