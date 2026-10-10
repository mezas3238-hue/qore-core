from qore.infrastructure.trader_lab.capitalizer_ttrades_source_pack_v48 import (
    RULES,
    V48_TTRADES_SOURCE_PACK,
    V48RuleSemantics,
)


def test_alternative_and_fallback_rules_are_never_universal_hard_gates() -> None:
    alternative_semantics = {
        V48RuleSemantics.ALTERNATIVE_ROUTE,
        V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE,
        V48RuleSemantics.PRIORITY_FALLBACK,
        V48RuleSemantics.OPTIONAL_CONFLUENCE,
    }
    selected = [rule for rule in RULES if rule.semantics in alternative_semantics]
    assert selected
    assert all(rule.universal_gate_supported is False for rule in selected)


def test_source_pack_contains_multiple_distinct_timeframe_models() -> None:
    ids = {rule.rule_id for rule in RULES}
    assert "SCALPING_MODEL_TIMEFRAME_STACK" in ids
    assert "LONDON_DAILY_4H_15M" in ids
    assert "BEST_TIMEFRAMES_DAILY_4H_15M" in ids
    assert "TIMEFRAME_ALIGNMENT_IS_RELATIONAL_NOT_ONE_FIXED_STACK" in ids


def test_reversal_sequence_is_not_encoded_as_full_and_gate() -> None:
    rule = next(
        rule
        for rule in RULES
        if rule.rule_id == "REVERSAL_SEQUENCE_PROGRESSIVE_CONFIRMATION"
    )
    assert rule.semantics is V48RuleSemantics.ALTERNATIVE_ENTRY_TECHNIQUE
    assert rule.universal_gate_supported is False


def test_poi_is_priority_fallback_not_superintersection() -> None:
    rule = next(rule for rule in RULES if rule.rule_id == "POI_FVG_THEN_SWING_THEN_CISD_FALLBACK")
    assert rule.semantics is V48RuleSemantics.PRIORITY_FALLBACK
    assert rule.universal_gate_supported is False


def test_pack_forbids_globalizing_route_scoped_rules() -> None:
    assert V48_TTRADES_SOURCE_PACK.route_scope_must_be_preserved is True
    assert V48_TTRADES_SOURCE_PACK.source_fact_may_be_globalized_without_evidence is False
    assert V48_TTRADES_SOURCE_PACK.fresh_holdout_authorized is False
