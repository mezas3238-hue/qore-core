import pytest

from qore.infrastructure.traders.crt_pure_identity import (
    CrtPureAdjudicationState,
    CrtPureSourceTier,
)
from qore.infrastructure.traders.crt_pure_source_registry import (
    CRT_PURE_REQUIRED_CONCEPTS,
    CrtPureConceptId,
    CrtPureConceptRecord,
    CrtPureSourceEvidence,
    evidence_backed_concepts,
    pending_concepts,
    promotable_concepts,
)


def test_required_concepts_are_unique_and_only_primary_closed_concepts_promote() -> None:
    assert len(CRT_PURE_REQUIRED_CONCEPTS) == len(set(CRT_PURE_REQUIRED_CONCEPTS))
    promoted = {
        CrtPureConceptId.TIME_TURTLE_SOUP_RELATION,
        CrtPureConceptId.MARKET_TIMEFRAME_SCOPE,
        CrtPureConceptId.MAKE_OR_BREAK_LEVEL,
        CrtPureConceptId.FIFTY_PERCENT_DESTINATION_FAMILY,
        CrtPureConceptId.INCOMPLETE_CRT_TRAP,
        CrtPureConceptId.OPPOSITE_CRT_BIAS_REVERSAL,
        CrtPureConceptId.OLD_CRTH_CRL_STAB_REACTION,
        CrtPureConceptId.REFERENCE_RANGE,
        CrtPureConceptId.CRH_CRL,
        CrtPureConceptId.LIQUIDATION_SWEEP,
        CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
        CrtPureConceptId.CANDLE_1_2_3,
        CrtPureConceptId.INVALIDATION,
        CrtPureConceptId.ENTRY_FAMILIES,
        CrtPureConceptId.STRUCTURAL_STOP,
        CrtPureConceptId.STRUCTURAL_DESTINATION,
        CrtPureConceptId.MODEL_1_ENTRY,
        CrtPureConceptId.MODEL_1_TIMEFRAME_ALIGNMENT,
    }
    assert set(promotable_concepts()) == promoted
    assert set(pending_concepts()) == set(CRT_PURE_REQUIRED_CONCEPTS) - promoted


def test_level_b_cannot_create_canonical_methodology_rule() -> None:
    with pytest.raises(ValueError, match="LEVEL_B evidence cannot independently be CANONICAL"):
        CrtPureSourceEvidence(
            concept_id=CrtPureConceptId.REFERENCE_RANGE,
            source_name="TTrades",
            source_tier=CrtPureSourceTier.LEVEL_B,
            provenance="approved corroboration source",
            locator="example",
            normalized_statement="example statement",
            adjudication=CrtPureAdjudicationState.CANONICAL,
        )


def test_level_a_canonical_evidence_can_promote_when_uncontested() -> None:
    evidence = CrtPureSourceEvidence(
        concept_id=CrtPureConceptId.REFERENCE_RANGE,
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        provenance="official source",
        locator="source locator",
        normalized_statement="source-proven normalized rule",
        adjudication=CrtPureAdjudicationState.CANONICAL,
    )
    record = CrtPureConceptRecord(
        concept_id=CrtPureConceptId.REFERENCE_RANGE,
        evidence=(evidence,),
    )
    assert record.promotable_to_strategy_identity is True


def test_ambiguity_blocks_promotion_even_with_primary_evidence() -> None:
    canonical = CrtPureSourceEvidence(
        concept_id=CrtPureConceptId.REFERENCE_RANGE,
        source_name="RomeoTPT",
        source_tier=CrtPureSourceTier.LEVEL_A,
        provenance="official source",
        locator="source locator A",
        normalized_statement="candidate normalized rule",
        adjudication=CrtPureAdjudicationState.CANONICAL,
    )
    ambiguous = CrtPureSourceEvidence(
        concept_id=CrtPureConceptId.REFERENCE_RANGE,
        source_name="RomeoTPT author-distributed documents",
        source_tier=CrtPureSourceTier.LEVEL_A_PLUS,
        provenance="official author-distributed document",
        locator="source locator B",
        normalized_statement="unresolved alternative interpretation",
        adjudication=CrtPureAdjudicationState.AMBIGUOUS,
        ambiguity_notes="requires adjudication",
    )
    record = CrtPureConceptRecord(
        concept_id=CrtPureConceptId.REFERENCE_RANGE,
        evidence=(canonical, ambiguous),
    )
    assert record.promotable_to_strategy_identity is False


def test_discovered_level_a_evidence_is_retained_but_not_promoted() -> None:
    assert set(evidence_backed_concepts()) == {
        CrtPureConceptId.REFERENCE_RANGE,
        CrtPureConceptId.CRH_CRL,
        CrtPureConceptId.EQUILIBRIUM,
        CrtPureConceptId.LIQUIDATION_SWEEP,
        CrtPureConceptId.CANDLE_1_2_3,
        CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
        CrtPureConceptId.INVALIDATION,
        CrtPureConceptId.STRUCTURAL_STOP,
        CrtPureConceptId.NESTED_CRT,
        CrtPureConceptId.TIMEFRAME_HIERARCHY,
        CrtPureConceptId.SESSION_TIME_RULES,
        CrtPureConceptId.ENTRY_FAMILIES,
        CrtPureConceptId.STRUCTURAL_DESTINATION,
        CrtPureConceptId.TIME_TURTLE_SOUP_RELATION,
        CrtPureConceptId.MARKET_TIMEFRAME_SCOPE,
        CrtPureConceptId.MAKE_OR_BREAK_LEVEL,
        CrtPureConceptId.FIFTY_PERCENT_DESTINATION_FAMILY,
        CrtPureConceptId.INCOMPLETE_CRT_TRAP,
        CrtPureConceptId.OPPOSITE_CRT_BIAS_REVERSAL,
        CrtPureConceptId.OLD_CRTH_CRL_STAB_REACTION,
        CrtPureConceptId.MODEL_1_ENTRY,
        CrtPureConceptId.MODEL_1_TIMEFRAME_ALIGNMENT,
        CrtPureConceptId.MODEL_1_REFERENCE_SELECTION,
    }
    assert set(promotable_concepts()) == {
        CrtPureConceptId.TIME_TURTLE_SOUP_RELATION,
        CrtPureConceptId.MARKET_TIMEFRAME_SCOPE,
        CrtPureConceptId.MAKE_OR_BREAK_LEVEL,
        CrtPureConceptId.FIFTY_PERCENT_DESTINATION_FAMILY,
        CrtPureConceptId.INCOMPLETE_CRT_TRAP,
        CrtPureConceptId.OPPOSITE_CRT_BIAS_REVERSAL,
        CrtPureConceptId.OLD_CRTH_CRL_STAB_REACTION,
        CrtPureConceptId.REFERENCE_RANGE,
        CrtPureConceptId.CRH_CRL,
        CrtPureConceptId.LIQUIDATION_SWEEP,
        CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
        CrtPureConceptId.CANDLE_1_2_3,
        CrtPureConceptId.INVALIDATION,
        CrtPureConceptId.ENTRY_FAMILIES,
        CrtPureConceptId.STRUCTURAL_STOP,
        CrtPureConceptId.STRUCTURAL_DESTINATION,
        CrtPureConceptId.MODEL_1_ENTRY,
        CrtPureConceptId.MODEL_1_TIMEFRAME_ALIGNMENT,
    }


def test_level_b_never_promotes_without_primary_closure() -> None:
    assert CrtPureConceptId.REFERENCE_RANGE in promotable_concepts()
    assert CrtPureConceptId.CANDLE_1_2_3 in promotable_concepts()
    assert CrtPureConceptId.NESTED_CRT in evidence_backed_concepts()
    assert CrtPureConceptId.NESTED_CRT not in promotable_concepts()
    assert CrtPureConceptId.MODEL_1_REFERENCE_SELECTION in evidence_backed_concepts()
    assert CrtPureConceptId.MODEL_1_REFERENCE_SELECTION not in promotable_concepts()
