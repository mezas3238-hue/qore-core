"""Owner-approved three sources; no exclusive Romeo veto or invented PASS."""

import pytest

from qore.infrastructure.traders.crt_pure_three_source_methodology import (
    AUTHORIZED_SOURCE_NAMES,
    CrtThreeSourceDecision,
    CrtThreeSourceRule,
    CrtThreeSourceRuleContract,
    current_three_source_methodology,
    evaluate_three_source_methodology,
)


def test_actual_tri_source_program_is_unfrozen_and_unapproved() -> None:
    current = current_three_source_methodology()
    assert current.policy_id == "VT08_CRT_THREE_SOURCE_QORE_V1"
    assert current.source_names == (
        "RomeoTPT", "SpeculatorFL", "TraderFlameseN"
    )
    assert current.methodology_closed is False
    assert len(current.blockers) == len(CrtThreeSourceRule)
    assert "THREE_SOURCE_RULE_OPEN:multiple_reference_priority" in current.blockers
    assert current.grants_trading_authority is False
    assert current.grants_volume_authority is False


def test_one_source_may_support_rule_without_romeo_exclusivity() -> None:
    supported = CrtThreeSourceRuleContract(
        rule=CrtThreeSourceRule.REFERENCE_ELIGIBILITY,
        decision=CrtThreeSourceDecision.SOURCE_SUPPORTED,
        source_name="SpeculatorFL",
        source_locator="https://threadreaderapp.com/thread/1784493604473618604#31",
        operational_rule="Hypothetical fully specified causal rule for a future independent review",
        independent_adjudication_id="EXAMPLE_TEST_REVIEW_ONLY",
    )
    assert supported.source_name in AUTHORIZED_SOURCE_NAMES
    rules = (supported,) + tuple(
        CrtThreeSourceRuleContract(rule)
        for rule in tuple(CrtThreeSourceRule)[1:]
    )
    result = evaluate_three_source_methodology(rules)
    assert not result.methodology_closed
    assert "THREE_SOURCE_RULE_OPEN:reference_eligibility" not in result.blockers
    assert "THREE_SOURCE_RULE_OPEN:multiple_reference_priority" in result.blockers


def test_owner_specific_engineering_requires_explicit_approval_and_reason() -> None:
    with pytest.raises(ValueError, match="Owner approval"):
        CrtThreeSourceRuleContract(
            rule=CrtThreeSourceRule.MULTIPLE_REFERENCE_PRIORITY,
            decision=CrtThreeSourceDecision.OWNER_APPROVED_QORE_ENGINEERING,
            operational_rule="example-only deterministic choice",
            independent_adjudication_id="reviewer",
        )
    record = CrtThreeSourceRuleContract(
        rule=CrtThreeSourceRule.MULTIPLE_REFERENCE_PRIORITY,
        decision=CrtThreeSourceDecision.OWNER_APPROVED_QORE_ENGINEERING,
        operational_rule="example-only deterministic choice",
        independent_adjudication_id="reviewer",
        owner_approval_id="EXAMPLE_NOT_APPROVED",
        conflict_resolution="Make synthesized engineering distinct from author quotes",
    )
    assert record.decision is CrtThreeSourceDecision.OWNER_APPROVED_QORE_ENGINEERING


def test_source_supported_contract_does_not_accept_invented_evidence_urls() -> None:
    with pytest.raises(ValueError, match="not in adjudication registry"):
        CrtThreeSourceRuleContract(
            rule=CrtThreeSourceRule.ENTRY_CONFIRMATION,
            decision=CrtThreeSourceDecision.SOURCE_SUPPORTED,
            source_name="RomeoTPT",
            source_locator="https://example.org/fake-new-CRT-source",
            operational_rule="Example",
            independent_adjudication_id="test",
        )


def test_open_contract_cannot_embed_hypothesis_disguised_as_rule() -> None:
    with pytest.raises(ValueError, match="OPEN rules"):
        CrtThreeSourceRuleContract(
            rule=CrtThreeSourceRule.CONFLICT_AND_REARM,
            decision=CrtThreeSourceDecision.OPEN,
            operational_rule="unreviewed first hit wins",
        )


@pytest.mark.parametrize("field", ("future_outcome_used", "sizing_used"))
def test_no_outcome_cherry_pick_and_no_sizing(field: str) -> None:
    with pytest.raises(ValueError, match="outcome or sizing"):
        CrtThreeSourceRuleContract(
            rule=CrtThreeSourceRule.REFERENCE_ELIGIBILITY,
            **{field: True},
        )


def test_duplicate_omitted_or_out_of_order_contracts_cannot_close() -> None:
    wrong = tuple(CrtThreeSourceRuleContract(rule) for rule in CrtThreeSourceRule)[:-1]
    with pytest.raises(ValueError, match="seven distinct"):
        evaluate_three_source_methodology(wrong)
    with pytest.raises(ValueError, match="seven distinct"):
        evaluate_three_source_methodology(tuple(reversed(wrong)))


def test_proposed_qore_engineering_cannot_change_current_certificate() -> None:
    # Simulated agreements prove only code can represent an alternative.
    # The actual frozen source registry is unchanged and all rules remain OPEN.
    example = tuple(
        CrtThreeSourceRuleContract(
            rule=rule,
            decision=CrtThreeSourceDecision.OWNER_APPROVED_QORE_ENGINEERING,
            operational_rule=f"TEST_ONLY_SPEC_NOT_A_REAL_APPROVAL:{rule.value}",
            independent_adjudication_id="EXAMPLE_NOT_REAL_REVIEW",
            owner_approval_id="EXAMPLE_NOT_REAL_APPROVAL",
            conflict_resolution="Test-only QORE synthesis; not an author claim",
        )
        for rule in CrtThreeSourceRule
    )
    hypothetical = evaluate_three_source_methodology(example)
    assert hypothetical.proposal_complete is True
    assert hypothetical.methodology_closed is False
    assert "METHODOLOGY_INDEPENDENT_APPROVAL_UNVERIFIED" in hypothetical.blockers
    assert hypothetical.grants_trading_authority is False
    assert current_three_source_methodology().methodology_closed is False


def test_unrelated_valid_corpus_url_does_not_prove_a_different_rule() -> None:
    with pytest.raises(ValueError, match="source rule evidence"):
        CrtThreeSourceRuleContract(
            rule=CrtThreeSourceRule.DESTINATION_LIFECYCLE,
            decision=CrtThreeSourceDecision.SOURCE_SUPPORTED,
            source_name="SpeculatorFL",
            source_locator="https://threadreaderapp.com/thread/1784493604473618604#31",
            operational_rule="TEST-ONLY non-source destination claim",
            independent_adjudication_id="EXAMPLE_NOT_REAL_REVIEW",
        )


def test_all_seven_arbitrary_string_review_ids_cannot_fake_source_closure() -> None:
    """Regression: complete declarations != real independent signed decisions."""
    claims = tuple(
        CrtThreeSourceRuleContract(
            rule=rule,
            decision=CrtThreeSourceDecision.OWNER_APPROVED_QORE_ENGINEERING,
            operational_rule=f"TEST_ONLY:{rule.value}",
            independent_adjudication_id="FORGED_REVIEWER",
            owner_approval_id="FORGED_OWNER",
            conflict_resolution="Unverified hypothetical",
        )
        for rule in CrtThreeSourceRule
    )
    result = evaluate_three_source_methodology(claims)
    assert result.proposal_complete
    assert not result.methodology_closed
    assert result.blockers == ("METHODOLOGY_INDEPENDENT_APPROVAL_UNVERIFIED",)
    assert not result.grants_trading_authority
    assert not result.grants_volume_authority
