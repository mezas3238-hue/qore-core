from qore.infrastructure.traders.crt_pure_source_registry import CrtPureConceptId
from qore.infrastructure.traders.crt_pure_strategy_identity_memory import (
    CRT_PURE_CORE_EXECUTION_CONCEPTS,
    MODEL1_SOURCE_CONCEPTS,
    model1_source_ready,
    strategy_identity_fingerprint,
    strategy_identity_payload,
    strategy_identity_ready,
    unresolved_core_execution_concepts,
    unresolved_model1_source_concepts,
    validate_strategy_identity,
)


def test_strategy_identity_exposes_only_canonical_source_rules() -> None:
    payload = strategy_identity_payload()
    assert payload["methodology_family"] == "CRT"
    assert payload["methodology_variant"] == "PURE"
    assert payload["markets"] == ("AUDUSD", "USDJPY", "BTCUSD")
    assert set(payload["canonical_concepts"]) == {
        "time_turtle_soup_relation",
        "market_timeframe_scope",
        "make_or_break_level",
        "fifty_percent_destination_family",
        "incomplete_crt_trap",
        "opposite_crt_bias_reversal",
        "old_crth_crl_stab_reaction",
        "reference_range",
        "crh_crl",
        "liquidation_sweep",
        "reclaim_close_back_inside",
        "candle_1_2_3",
        "invalidation",
        "entry_families",
        "structural_stop",
        "structural_destination",
        "model_1_entry",
        "model_1_timeframe_alignment",
        "key_levels",
    }
    rules = payload["canonical_rules"]
    assert isinstance(rules, dict)
    assert set(rules) == {
        "time_turtle_soup_relation",
        "market_timeframe_scope",
        "make_or_break_level",
        "fifty_percent_destination_family",
        "incomplete_crt_trap",
        "opposite_crt_bias_reversal",
        "old_crth_crl_stab_reaction",
        "reference_range",
        "crh_crl",
        "liquidation_sweep",
        "reclaim_close_back_inside",
        "candle_1_2_3",
        "invalidation",
        "entry_families",
        "structural_stop",
        "structural_destination",
        "model_1_entry",
        "model_1_timeframe_alignment",
        "key_levels",
    }


def test_core_execution_source_contract_is_closed() -> None:
    assert strategy_identity_ready() is True
    assert unresolved_core_execution_concepts() == ()
    assert set(CRT_PURE_CORE_EXECUTION_CONCEPTS) == {
        CrtPureConceptId.REFERENCE_RANGE,
        CrtPureConceptId.CRH_CRL,
        CrtPureConceptId.LIQUIDATION_SWEEP,
        CrtPureConceptId.RECLAIM_CLOSE_BACK_INSIDE,
        CrtPureConceptId.CANDLE_1_2_3,
        CrtPureConceptId.INVALIDATION,
        CrtPureConceptId.ENTRY_FAMILIES,
        CrtPureConceptId.STRUCTURAL_STOP,
        CrtPureConceptId.STRUCTURAL_DESTINATION,
    }


def test_strategy_identity_guards_exclude_amd_and_level_b_authority() -> None:
    payload = strategy_identity_payload()
    guards = payload["identity_guards"]
    assert isinstance(guards, dict)
    assert guards["crt_amd_allowed"] is False
    assert guards["level_b_may_define_methodology"] is False
    assert guards["unresolved_rule_may_execute"] is False
    assert payload["strategy_identity_ready"] is True


def test_strategy_identity_is_fingerprinted_and_valid() -> None:
    validate_strategy_identity()
    assert len(strategy_identity_fingerprint()) == 64



def test_model1_specific_readiness_stays_blocked_when_reference_selector_unknown() -> None:
    """Legacy generic core readiness is NOT evidence of Model #1 source closure."""
    assert strategy_identity_ready() is True
    assert set(MODEL1_SOURCE_CONCEPTS) == {
        CrtPureConceptId.MODEL_1_ENTRY,
        CrtPureConceptId.MODEL_1_TIMEFRAME_ALIGNMENT,
        CrtPureConceptId.MODEL_1_REFERENCE_SELECTION,
    }
    assert unresolved_model1_source_concepts() == (
        CrtPureConceptId.MODEL_1_REFERENCE_SELECTION,
    )
    assert model1_source_ready() is False
