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


def test_required_concepts_are_unique_and_only_mob_is_promotable() -> None:
    assert len(CRT_PURE_REQUIRED_CONCEPTS) == len(set(CRT_PURE_REQUIRED_CONCEPTS))
    assert promotable_concepts() == (CrtPureConceptId.MAKE_OR_BREAK_LEVEL,)
    assert set(pending_concepts()) == (
        set(CRT_PURE_REQUIRED_CONCEPTS) - {CrtPureConceptId.MAKE_OR_BREAK_LEVEL}
    )


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
        CrtPureConceptId.NESTED_CRT,
        CrtPureConceptId.TIMEFRAME_HIERARCHY,
        CrtPureConceptId.SESSION_TIME_RULES,
        CrtPureConceptId.ENTRY_FAMILIES,
        CrtPureConceptId.STRUCTURAL_DESTINATION,
        CrtPureConceptId.MAKE_OR_BREAK_LEVEL,
    }
    assert promotable_concepts() == (CrtPureConceptId.MAKE_OR_BREAK_LEVEL,)


def test_level_b_corroboration_never_promotes_core_crt_concepts() -> None:
    assert CrtPureConceptId.REFERENCE_RANGE in evidence_backed_concepts()
    assert CrtPureConceptId.CANDLE_1_2_3 in evidence_backed_concepts()
    assert CrtPureConceptId.NESTED_CRT in evidence_backed_concepts()
    assert CrtPureConceptId.REFERENCE_RANGE not in promotable_concepts()
    assert CrtPureConceptId.CANDLE_1_2_3 not in promotable_concepts()
    assert CrtPureConceptId.NESTED_CRT not in promotable_concepts()
