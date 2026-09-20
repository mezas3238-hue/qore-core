from qore.infrastructure.trader_lab.capitalizer_source_stop_fidelity_audit_v1 import (
    IDENTITY,
    build_source_stop_fidelity_audit,
)


def test_source_stop_fidelity_audit_reopens_exact_stop_placement() -> None:
    audit = build_source_stop_fidelity_audit()

    assert audit.identity == IDENTITY
    assert audit.source_invalidation_anchor == "CONFIRMED_LOGICAL_PROTECTED_SWING"
    assert audit.source_stop_relation == "PROTECTED_SWING_ANCHOR_DEFAULT_AT_SWING_WITH_BEYOND_VARIANTS"
    assert audit.source_universal_numeric_padding_defined is False
    assert audit.current_trade_plan_relation == "DEFAULT_AT_PROTECTED_SWING"
    assert audit.current_trade_plan_source_faithful is True
    assert audit.current_m5_replay_stop == "SOURCE_M5_DIRECTIONAL_EXTREME"
    assert audit.current_m5_replay_source_faithful_stop is False
    assert audit.m1_protected_swing_required_for_source_replay is True
    assert audit.native_m1_evidence_present is False
    assert audit.exact_outward_stop_distance_resolved is False
    assert audit.source_strategy_status == "REPLAY_STOP_PROXY_REQUIRES_CORRECTION"
    assert audit.numeric_buffer_selected is False
    assert audit.stop_widening_authorized is False
    assert audit.rule_promotion_allowed is False
    assert audit.economic_candidate is False
    assert audit.trader_certified is False
