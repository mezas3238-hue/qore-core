from qore.infrastructure.trader_lab.capitalizer_cross_author_composition_audit_v48 import (
    CLAIMS,
    V48_CROSS_AUTHOR_COMPOSITION_AUDIT,
    V48CompositionAuthority,
)


def test_individual_source_support_does_not_promote_qore_conjunction() -> None:
    claims = {claim.claim_id: claim for claim in CLAIMS}

    assert claims["ICT_2022_LIQUIDITY_MSS_DISPLACEMENT_FVG_SEQUENCE"].authority is (
        V48CompositionAuthority.AUTHOR_EXPLICIT
    )
    assert claims["TTRADES_FRACTAL_CISD_PROTECTED_SWING_SEQUENCE"].authority is (
        V48CompositionAuthority.AUTHOR_EXPLICIT
    )

    conjunction = claims["EVERY_TRADE_MUST_PASS_FULL_ICT_AND_FULL_TTRADES"]
    assert conjunction.authority is V48CompositionAuthority.QORE_SYNTHESIS
    assert conjunction.may_be_universal_hard_gate is False


def test_m1_superintersection_is_qore_synthesis_not_author_rule() -> None:
    claim = next(
        item
        for item in CLAIMS
        if item.claim_id == "M1_MSS_FVG_OB_ALL_REQUIRED_AFTER_TTRADES_CONFIRMATION"
    )
    assert claim.authority is V48CompositionAuthority.QORE_SYNTHESIS
    assert claim.may_be_universal_hard_gate is False


def test_composition_audit_requires_provenance_for_conjunction_itself() -> None:
    audit = V48_CROSS_AUTHOR_COMPOSITION_AUDIT
    assert audit.conjunction_requires_own_provenance is True
    assert audit.qore_synthesis_may_masquerade_as_author_rule is False
    assert audit.fresh_holdout_authorized is False
    assert audit.economics_authorized is False
