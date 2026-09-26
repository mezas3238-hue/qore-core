from qore.infrastructure.trader_lab.capitalizer_source_strategy_provenance_v2 import (
    FROZEN_SOURCE_STRATEGY_PROVENANCE,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_review_v2 import (
    FROZEN_SOURCE_STRATEGY_REVIEW,
    CapitalizerSourceFactType,
)


def test_every_grammar_requirement_is_bound_to_reviewed_author_facts() -> None:
    reviewed = {item.fact_id: item for item in FROZEN_SOURCE_STRATEGY_REVIEW.facts}

    for requirement in FROZEN_SOURCE_STRATEGY_PROVENANCE.requirements:
        assert requirement.source_fact_ids or requirement.qore_operationalization
        for fact_id in requirement.source_fact_ids:
            assert fact_id in reviewed
            assert reviewed[fact_id].fact_type is CapitalizerSourceFactType.AUTHOR_SUPPORTED


def test_strategy_provenance_forbids_outcome_derived_rules() -> None:
    assert FROZEN_SOURCE_STRATEGY_PROVENANCE.outcome_derived_rule_allowed is False


def test_core_entry_requirements_have_explicit_provenance() -> None:
    requirement_ids = {
        item.requirement_id for item in FROZEN_SOURCE_STRATEGY_PROVENANCE.requirements
    }

    assert {
        "SOURCE_SESSION_CONTEXT",
        "HIGHER_TIMEFRAME_BIAS_ALIGNED",
        "STRUCTURAL_LIQUIDITY_OBJECTIVE_AVAILABLE",
        "TARGET_HIGHER_TIMEFRAME_OR_STRUCTURAL",
        "PROTECTED_SWING_AVAILABLE",
        "H1_EXPANSION_BIAS_CONFIRMED",
        "M15_SWING_STRUCTURE_CONFIRMED",
        "M1_CONTINUATION_CONFIRMED",
        "LIQUIDITY_LEVEL_TAKEN",
        "EXPECTED_REVERSAL_FAILED_TO_CONFIRM",
        "CONTINUATION_STRUCTURE_CONFIRMED",
    }.issubset(requirement_ids)
