from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_review_v2 import (
    FROZEN_SOURCE_STRATEGY_REVIEW,
    CapitalizerSourceFactType,
    CapitalizerStrategyAuthor,
)


def test_source_review_contains_complete_ict_scalping_series_and_primary_ttrades() -> None:
    review = FROZEN_SOURCE_STRATEGY_REVIEW
    sources = {item.source_id: item for item in review.sources}

    assert {
        "ICT_HIGH_PROBABILITY_SCALPING_V1",
        "ICT_HIGH_PROBABILITY_SCALPING_V2",
        "ICT_HIGH_PROBABILITY_SCALPING_V3",
    }.issubset(sources)
    assert sources["ICT_HIGH_PROBABILITY_SCALPING_V2"].primary_locator == (
        "youtube:1Wmh8829mZs"
    )
    assert sources["ICT_HIGH_PROBABILITY_SCALPING_V3"].primary_locator == (
        "youtube:UuMaC9n8Uy4"
    )
    assert sources["ICT_ATM_METHOD"].author is CapitalizerStrategyAuthor.ICT
    assert sources["ICT_ATM_METHOD"].primary_locator == "youtube:30petm6SZz0"
    assert sources["ICT_2022_MENTORSHIP_EP3"].author is CapitalizerStrategyAuthor.ICT
    assert sources["ICT_2022_MENTORSHIP_EP3"].primary_locator == "youtube:nQfHZ2DEJ8c"
    assert sources["ICT_2022_MENTORSHIP_EP6"].author is CapitalizerStrategyAuthor.ICT
    assert sources["ICT_2022_MENTORSHIP_EP7"].author is CapitalizerStrategyAuthor.ICT
    assert sources["ICT_RISK_MANAGEMENT"].author is CapitalizerStrategyAuthor.ICT
    assert sources["TTRADES_SCALPING_MODEL"].author is CapitalizerStrategyAuthor.TTRADES
    assert sources["TTRADES_INTRACANDLE_CISD"].author is CapitalizerStrategyAuthor.TTRADES
    assert sources["TTRADES_WICK_THEN_BODY"].author is CapitalizerStrategyAuthor.TTRADES
    assert (
        sources["TTRADES_FAILURE_TO_MANIPULATE"].author
        is CapitalizerStrategyAuthor.TTRADES
    )


def test_author_supported_facts_always_have_reviewed_primary_sources() -> None:
    review = FROZEN_SOURCE_STRATEGY_REVIEW
    available = {item.source_id for item in review.sources}

    for fact in review.facts:
        if fact.fact_type is CapitalizerSourceFactType.AUTHOR_SUPPORTED:
            assert fact.source_ids
            assert set(fact.source_ids).issubset(available)


def test_entry_acceptance_facts_cover_ict_and_ttrades_conditions() -> None:
    facts = {item.fact_id: item for item in FROZEN_SOURCE_STRATEGY_REVIEW.facts}

    for fact_id in (
        "ICT_ENTRY_LIQUIDITY_RAID_PRECEDES_MSS",
        "ICT_ENTRY_MSS_REQUIRES_SIGNIFICANT_DISPLACEMENT",
        "ICT_ENTRY_REQUIRES_FVG_IN_DISPLACEMENT",
        "ICT_ENTRY_USES_RETRACE_TO_FVG_NOT_CHASE",
        "TTRADES_ENTRY_REQUIRES_HTF_POI_CISD_CONTINUATION",
        "TTRADES_ENTRY_INVALID_IF_CISD_MISSING",
        "TTRADES_ENTRY_WICK_FORMED_BEFORE_BODY",
        "TTRADES_ENTRY_REQUIRES_TARGET_INTACT",
    ):
        assert facts[fact_id].fact_type is CapitalizerSourceFactType.AUTHOR_SUPPORTED
        assert facts[fact_id].source_ids


def test_qore_governance_is_not_misattributed_to_ict_or_ttrades() -> None:
    review = FROZEN_SOURCE_STRATEGY_REVIEW
    facts = {item.fact_id: item for item in review.facts}

    for fact_id in (
        "QORE_MAX3_IS_NOT_AUTHOR_RULE",
        "QORE_NINE_MARKET_UNIVERSE_IS_NOT_AUTHOR_RULE",
        "QORE_SESSION_SURVEILLANCE_BUCKETS_ARE_NOT_KILLZONES",
    ):
        fact = facts[fact_id]
        assert fact.fact_type is CapitalizerSourceFactType.QORE_OPERATIONALIZATION
        assert fact.source_ids == ()


def test_source_inventory_and_reviewed_strategy_grammar_are_frozen() -> None:
    review = FROZEN_SOURCE_STRATEGY_REVIEW

    assert review.inventory_status is CapitalizerChainStatus.FROZEN_APT
    assert (
        review.deterministic_strategy_grammar_status
        is CapitalizerChainStatus.FROZEN_APT
    )
    assert review.economic_edge_claimed is False
    assert review.integrated_nine_market_replay_completed is False
    assert review.trader_certified is False
