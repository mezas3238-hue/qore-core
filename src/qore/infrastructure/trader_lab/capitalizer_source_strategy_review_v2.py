"""Source-fidelity inventory and author-supported facts for Capitalizer Strategy Closure V2.

This module fixes the provenance boundary before deterministic strategy grammar is encoded.
Author-supported facts are kept separate from QORE portfolio/session operationalization.

It does not claim economic edge, integrated replay completion, or trader certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)

SOURCE_STRATEGY_REVIEW_ID = "QORE_CAPITALIZER_SOURCE_STRATEGY_REVIEW_V2"


class CapitalizerStrategyAuthor(StrEnum):
    ICT = "ICT"
    TTRADES = "TTRADES"
    QORE = "QORE"


class CapitalizerPrimarySourceKind(StrEnum):
    VIDEO = "VIDEO"
    ARTICLE = "ARTICLE"


class CapitalizerSourceReviewState(StrEnum):
    CONTENT_REVIEWED = "CONTENT_REVIEWED"
    LOCATOR_VERIFIED = "LOCATOR_VERIFIED"


class CapitalizerSourceFactType(StrEnum):
    AUTHOR_SUPPORTED = "AUTHOR_SUPPORTED"
    QORE_OPERATIONALIZATION = "QORE_OPERATIONALIZATION"


@dataclass(frozen=True, slots=True)
class CapitalizerReviewedSource:
    source_id: str
    author: CapitalizerStrategyAuthor
    kind: CapitalizerPrimarySourceKind
    title: str
    primary_locator: str
    review_state: CapitalizerSourceReviewState

    def __post_init__(self) -> None:
        if not self.source_id or self.source_id != self.source_id.upper():
            raise ValueError("source_id must be non-empty uppercase")
        if not self.title or not self.primary_locator:
            raise ValueError("reviewed source requires title and primary locator")
        if self.author is CapitalizerStrategyAuthor.QORE:
            raise ValueError("QORE operationalization is not an author primary source")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceFact:
    fact_id: str
    fact_type: CapitalizerSourceFactType
    statement: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.fact_id or self.fact_id != self.fact_id.upper():
            raise ValueError("fact_id must be non-empty uppercase")
        if not self.statement:
            raise ValueError("source fact statement must be non-empty")
        if self.fact_type is CapitalizerSourceFactType.AUTHOR_SUPPORTED:
            if not self.source_ids:
                raise ValueError("author-supported fact requires primary sources")
        elif self.source_ids:
            raise ValueError("QORE operationalization cannot masquerade as author-sourced")


REVIEWED_SOURCES: tuple[CapitalizerReviewedSource, ...] = (
    CapitalizerReviewedSource(
        source_id="ICT_ASIAN_KILLZONE",
        author=CapitalizerStrategyAuthor.ICT,
        kind=CapitalizerPrimarySourceKind.VIDEO,
        title="ICT Forex - The ICT Asian Killzone",
        primary_locator="youtube:ley5HZs4bUM",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="ICT_HIGH_PROBABILITY_SCALPING_V1",
        author=CapitalizerStrategyAuthor.ICT,
        kind=CapitalizerPrimarySourceKind.VIDEO,
        title="ICT - Mastering High Probability Scalping Vol. 1 of 3",
        primary_locator="youtube:uE-aaP16nOw",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="ICT_HIGH_PROBABILITY_SCALPING_V2",
        author=CapitalizerStrategyAuthor.ICT,
        kind=CapitalizerPrimarySourceKind.VIDEO,
        title="ICT - Mastering High Probability Scalping Vol. 2 of 3",
        primary_locator="youtube:1Wmh8829mZs",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="ICT_HIGH_PROBABILITY_SCALPING_V3",
        author=CapitalizerStrategyAuthor.ICT,
        kind=CapitalizerPrimarySourceKind.VIDEO,
        title="ICT - Mastering High Probability Scalping Vol. 3 of 3",
        primary_locator="youtube:UuMaC9n8Uy4",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="ICT_LONDON_KILLZONE",
        author=CapitalizerStrategyAuthor.ICT,
        kind=CapitalizerPrimarySourceKind.VIDEO,
        title="ICT Forex - The ICT London Killzone",
        primary_locator="youtube:G8OEsUAoIWE",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="ICT_NEW_YORK_KILLZONE",
        author=CapitalizerStrategyAuthor.ICT,
        kind=CapitalizerPrimarySourceKind.VIDEO,
        title="ICT Forex - The ICT New York Killzone",
        primary_locator="youtube:plNN9n7nrxc",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="TTRADES_FAILURE_TO_MANIPULATE",
        author=CapitalizerStrategyAuthor.TTRADES,
        kind=CapitalizerPrimarySourceKind.ARTICLE,
        title="How to Trade Breakouts (Failure to Manipulate)",
        primary_locator="https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
    CapitalizerReviewedSource(
        source_id="TTRADES_SCALPING_MODEL",
        author=CapitalizerStrategyAuthor.TTRADES,
        kind=CapitalizerPrimarySourceKind.ARTICLE,
        title="TTrades Scalping Model - Simple Day Trading Strategy",
        primary_locator=(
            "https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/"
        ),
        review_state=CapitalizerSourceReviewState.CONTENT_REVIEWED,
    ),
)


SOURCE_FACTS: tuple[CapitalizerSourceFact, ...] = (
    CapitalizerSourceFact(
        fact_id="ICT_ASIA_FAVORS_AUD_NZD_JPY_ACTIVITY",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "ICT identifies AUD, NZD and JPY-related markets/crosses as more active candidates "
            "for the Asian kill-zone context than EUR/GBP dollar majors."
        ),
        source_ids=("ICT_ASIAN_KILLZONE",),
    ),
    CapitalizerSourceFact(
        fact_id="ICT_DAILY_BIAS_PRECEDES_SCALP_EXECUTION",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "ICT High Probability Scalping establishes higher-timeframe directional bias before "
            "intraday liquidity-run execution."
        ),
        source_ids=(
            "ICT_HIGH_PROBABILITY_SCALPING_V1",
            "ICT_HIGH_PROBABILITY_SCALPING_V2",
            "ICT_HIGH_PROBABILITY_SCALPING_V3",
        ),
    ),
    CapitalizerSourceFact(
        fact_id="ICT_LIQUIDITY_TARGETS_RECENT_DAILY_HIGHS_LOWS",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "The ICT scalp framework explicitly studies runs on recent previous-day highs/lows "
            "as liquidity objectives rather than arbitrary short-term targets."
        ),
        source_ids=(
            "ICT_HIGH_PROBABILITY_SCALPING_V1",
            "ICT_HIGH_PROBABILITY_SCALPING_V2",
        ),
    ),
    CapitalizerSourceFact(
        fact_id="ICT_LONDON_KILLZONE_0200_0500_NY",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "The ICT London Killzone lesson defines the learning kill-zone window as "
            "02:00-05:00 New York time and emphasizes EUR/GBP pairs."
        ),
        source_ids=("ICT_LONDON_KILLZONE",),
    ),
    CapitalizerSourceFact(
        fact_id="ICT_NEW_YORK_KILLZONE_0700_0900_NY",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "The ICT New York Killzone lesson defines the classic window as 07:00-09:00 "
            "New York time and emphasizes dollar-linked majors."
        ),
        source_ids=("ICT_NEW_YORK_KILLZONE",),
    ),
    CapitalizerSourceFact(
        fact_id="ICT_STUDY_DAILY_DO_NOT_FORCE_DAILY_TRADES",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "ICT distinguishes daily study opportunity from an instruction to trade live every "
            "day; the scalp framework is selective rather than a daily quota."
        ),
        source_ids=(
            "ICT_HIGH_PROBABILITY_SCALPING_V1",
            "ICT_NEW_YORK_KILLZONE",
        ),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_SCALP_TOP_DOWN_H1_M15_M1",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "The TTrades Scalping Model uses hourly bias, fifteen-minute swing structure and "
            "one-minute execution; lower-timeframe execution does not define the narrative."
        ),
        source_ids=("TTRADES_SCALPING_MODEL",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_H1_EXPANSION_BIAS_C2_C3",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "TTrades uses hourly candle-two/candle-three closure context to anticipate the "
            "hourly expansion being scalped."
        ),
        source_ids=("TTRADES_SCALPING_MODEL",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_M15_SWING_THEN_M1_CONTINUATION",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "After hourly bias, TTrades seeks aligned fifteen-minute swing structure and then "
            "one-minute continuation behavior such as FVG interaction, CISD and protected swing."
        ),
        source_ids=("TTRADES_SCALPING_MODEL",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_PROTECTED_SWING_STOP",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement="TTrades places the scalp stop at a logical protected swing.",
        source_ids=("TTRADES_SCALPING_MODEL",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_TARGET_USES_HIGHER_TIMEFRAME_OBJECTIVE",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "TTrades frames scalp targets from higher-timeframe objectives/structure rather "
            "than an arbitrary exit chosen only because the trade is a scalp."
        ),
        source_ids=("TTRADES_SCALPING_MODEL",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "Failure to Manipulate is not the breakout itself: after a high/low is taken, the "
            "expected reversal must fail to form and continuation structure must develop."
        ),
        source_ids=("TTRADES_FAILURE_TO_MANIPULATE",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_FAILURE_TO_MANIPULATE_USES_HTF_BIAS",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "TTrades treats Failure to Manipulate as a continuation concept that must be paired "
            "with higher-timeframe directional reasoning rather than traded standalone."
        ),
        source_ids=("TTRADES_FAILURE_TO_MANIPULATE",),
    ),
    CapitalizerSourceFact(
        fact_id="TTRADES_WAIT_FOR_CANDLE_CLOSURE_CONFIRMATION",
        fact_type=CapitalizerSourceFactType.AUTHOR_SUPPORTED,
        statement=(
            "TTrades explicitly requires waiting for candle closures/structure confirmation "
            "rather than assuming a reversal immediately after a sweep."
        ),
        source_ids=("TTRADES_FAILURE_TO_MANIPULATE",),
    ),
    CapitalizerSourceFact(
        fact_id="QORE_MAX3_IS_NOT_AUTHOR_RULE",
        fact_type=CapitalizerSourceFactType.QORE_OPERATIONALIZATION,
        statement="MAX3 per session is QORE portfolio governance, not an ICT/TTrades rule.",
        source_ids=(),
    ),
    CapitalizerSourceFact(
        fact_id="QORE_NINE_MARKET_UNIVERSE_IS_NOT_AUTHOR_RULE",
        fact_type=CapitalizerSourceFactType.QORE_OPERATIONALIZATION,
        statement=(
            "The frozen nine-market Capitalizer universe is a QORE research/portfolio choice, "
            "not a claim attributed to ICT or TTrades."
        ),
        source_ids=(),
    ),
    CapitalizerSourceFact(
        fact_id="QORE_SESSION_SURVEILLANCE_BUCKETS_ARE_NOT_KILLZONES",
        fact_type=CapitalizerSourceFactType.QORE_OPERATIONALIZATION,
        statement=(
            "QORE broad session surveillance buckets must remain distinct from narrower "
            "source-defined ICT kill-zone windows."
        ),
        source_ids=(),
    ),
)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceStrategyReview:
    review_id: str = SOURCE_STRATEGY_REVIEW_ID
    sources: tuple[CapitalizerReviewedSource, ...] = REVIEWED_SOURCES
    facts: tuple[CapitalizerSourceFact, ...] = SOURCE_FACTS
    inventory_status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT
    deterministic_strategy_grammar_status: CapitalizerChainStatus = (
        CapitalizerChainStatus.RESEARCH_OPEN
    )
    economic_edge_claimed: bool = False
    integrated_nine_market_replay_completed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.review_id != SOURCE_STRATEGY_REVIEW_ID:
            raise ValueError("source strategy review identity is frozen")
        source_ids = tuple(item.source_id for item in self.sources)
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("reviewed source ids must be unique")
        fact_ids = tuple(item.fact_id for item in self.facts)
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("source fact ids must be unique")
        available = set(source_ids)
        for fact in self.facts:
            missing = set(fact.source_ids) - available
            if missing:
                raise ValueError(f"source fact references missing source ids: {sorted(missing)}")
        if self.inventory_status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("reviewed source inventory must be FROZEN_APT")
        if self.deterministic_strategy_grammar_status is not CapitalizerChainStatus.RESEARCH_OPEN:
            raise ValueError("strategy grammar is not frozen by source inventory alone")
        if (
            self.economic_edge_claimed
            or self.integrated_nine_market_replay_completed
            or self.trader_certified
        ):
            raise ValueError("source review cannot claim replay/economic certification")


FROZEN_SOURCE_STRATEGY_REVIEW = CapitalizerSourceStrategyReview()
