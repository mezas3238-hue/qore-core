from qore.infrastructure.trader_lab.capitalizer_ict_ttrades_dual_source_fidelity_audit_v1 import (
    IDENTITY,
    FROZEN_DUAL_SOURCE_FIDELITY_AUDIT,
    CapitalizerDualSourceStatus,
    CapitalizerSourceAuthorityTier,
)


def test_dual_source_authority_order_is_frozen() -> None:
    audit = FROZEN_DUAL_SOURCE_FIDELITY_AUDIT

    assert audit.identity == IDENTITY
    assert audit.authority_order == (
        CapitalizerSourceAuthorityTier.ICT_ORIGINAL_PRIMARY,
        CapitalizerSourceAuthorityTier.TTRADES_SECONDARY_REFINEMENT,
        CapitalizerSourceAuthorityTier.QORE_OPERATIONALIZATION,
    )
    assert audit.ict_is_original_primary_source is True
    assert audit.ttrades_may_override_ict is False
    assert audit.qore_may_masquerade_as_author is False


def test_stop_anchor_is_compatible_but_exact_expression_is_not_universal() -> None:
    audit = FROZEN_DUAL_SOURCE_FIDELITY_AUDIT
    checks = {item.component: item for item in audit.checks}

    assert checks["STOP_INVALIDATION_ANCHOR"].status is (
        CapitalizerDualSourceStatus.TTRADES_REFINEMENT_COMPATIBLE
    )
    assert checks["EXACT_INITIAL_STOP_PRICE"].status is (
        CapitalizerDualSourceStatus.ROUTE_SPECIFIC_VARIANCE
    )
    assert audit.universal_stop_offset_supported is False
    assert audit.current_stop_anchor_structurally_compatible is True
    assert audit.current_exact_stop_expression_universally_dual_source_faithful is False


def test_m5_replay_cannot_claim_complete_ict_ttrades_fidelity() -> None:
    audit = FROZEN_DUAL_SOURCE_FIDELITY_AUDIT
    checks = {item.component: item for item in audit.checks}

    assert checks["CURRENT_ECONOMIC_REPLAY"].status is (
        CapitalizerDualSourceStatus.QORE_PROXY_GAP
    )
    assert audit.native_m1_required_for_final_fidelity is True
    assert audit.native_m1_present is False
    assert audit.replay_may_claim_full_source_fidelity is False
    assert audit.rule_promotion_allowed is False
    assert audit.economic_candidate is False
    assert audit.trader_certified is False
