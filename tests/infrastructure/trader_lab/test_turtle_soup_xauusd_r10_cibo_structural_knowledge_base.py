from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r10_cibo_structural_knowledge_base import (
    CLAIMS,
    KnowledgeStrength,
    OperatingUse,
    claim_by_code,
    claims_for_subject,
    knowledge_manifest,
)


def test_claim_codes_are_unique() -> None:
    codes = [claim.code for claim in CLAIMS]
    assert len(codes) == len(set(codes))


def test_only_frozen_robust_invalid_claim_can_drive_structural_abstention() -> None:
    allowed = [
        claim
        for claim in CLAIMS
        if claim.operating_use is OperatingUse.STRUCTURAL_ABSTENTION_ALLOWED
    ]
    assert [claim.code for claim in allowed] == [
        "K01_ROBUST_INVALID_DEEP_RAID_LATE_CISD"
    ]
    assert allowed[0].strength is KnowledgeStrength.ESTABLISHED_STRUCTURAL_NEGATIVE


def test_break_a_protected_swing_relation_is_clue_not_rule() -> None:
    claim = claim_by_code("K05_BREAK_A_OPPOSING_SERIES_LENGTH_CLUE")
    assert claim.strength is KnowledgeStrength.STABLE_CLUE_NOT_RULE
    assert claim.operating_use is OperatingUse.REASONING_CONTEXT_ONLY
    assert any(item.code == "R10_PROTECTED_SWING_CAUSALITY_FORENSICS" for item in claim.evidence)
    assert claim.limitations


def test_positive_entry_validity_remains_unresolved_and_non_operating() -> None:
    claim = claim_by_code("K08_POSITIVE_VALIDITY_NOT_YET_PROVEN")
    assert claim.strength is KnowledgeStrength.UNRESOLVED
    assert claim.operating_use is OperatingUse.NO_OPERATING_USE


def test_subject_lookup_preserves_mechanism_specific_knowledge() -> None:
    ps_claims = claims_for_subject("protected_swing_causality")
    assert {claim.code for claim in ps_claims} == {
        "K05_BREAK_A_OPPOSING_SERIES_LENGTH_CLUE",
        "K06_PROTECTED_SWING_NOT_UNIVERSAL_DISCRIMINATOR",
    }


def test_all_evidence_refs_are_immutable_run_artifact_digest_bindings() -> None:
    refs = {
        (item.code, item.run_id, item.artifact_id, item.digest)
        for claim in CLAIMS
        for item in claim.evidence
    }
    assert refs
    for code, run_id, artifact_id, digest in refs:
        assert code
        assert run_id > 0
        assert artifact_id > 0
        assert digest.startswith("sha256:")
        assert len(digest) == len("sha256:") + 64


def test_manifest_is_fail_closed_and_not_a_scoring_model() -> None:
    payload = knowledge_manifest()
    contract = payload["reasoning_contract"]
    governance = payload["governance"]

    assert contract["historical_return_score"] is False
    assert contract["automatic_probability_of_trade_success"] is False
    assert contract["automatic_threshold_search"] is False
    assert contract["year_or_date_operating_rule"] is False
    assert contract["post_entry_label_allowed_as_live_input"] is False
    assert contract["positive_permission_requires_separate_frozen_validity_contract"] is True
    assert contract["unknown_means_permission"] is False

    assert governance["candidate_promoted"] is False
    assert governance["fresh_holdout_consumed"] is False
    assert governance["demo_eligible"] is False
    assert governance["live_authorized"] is False
    assert governance["real_capital_authorized"] is False
    assert governance["production_authorized"] is False
