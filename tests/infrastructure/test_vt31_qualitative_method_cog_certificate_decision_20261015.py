"""Adjudicate qualitative evidence; never award a trader cert by pytest/PNL."""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.vt31_qualitative_method_cog_certificate_decision_20261015 import (
    ARTIFACTS,
    G3_BLOB,
    adjudicate_qualitative_certification,
)


def fake_review_only_fixtures():
    original = {"git_blob_sha1": G3_BLOB}
    return {
        "london_original": {
            "original_source_hash": original,
            "original_cog_directly_invoked": True,
            "cases": [{"observed": {"action": x}} for x in (
                "LONG", "LONG", "WAIT", "WAIT", "WAIT",
                "WAIT", "WAIT", "REJECT", "LONG", "LONG",
            )],
        },
        "nyam_original": {
            "original_g3_cog_code_sha": original,
            "observed_actual_original_cog_dol": "150",
            "ttrades_source_required_opposite_h1_dol": "110",
            "independent_source_v2_state": "REJECTED",
        },
        "m0_profile": {
            "original_g3_cog_source_hash": original,
            "cases": [{"state": x} for x in (
                "TTRADES_PROFILE_SOURCE_REJECTED",
                "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
                "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
                "PROFILE_SESSION_REJECTED",
            )],
        },
        "nypm_original": {
            "original_g3_source_hash": original,
            "real_original_cog_invoked": True,
            "cases": [{"decision": x} for x in (
                "LONG", "WAIT", "WAIT", "WAIT", "WAIT", "REJECT",
            )],
        },
        "short_original": {
            "original_source": original,
            "original_cog_directly_invoked": True,
            "cases": [
                {"original_cog_side": "SHORT", "session": s,
                 "observed_utc_offset": offset}
                for offset in (-5, -4)
                for s in ("VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM")
            ],
        },
        "source_first": {
            "original_frozen_g3_code_sha": original,
            "cases": [{"status": "RESEARCH_TTRADES_CONTEXT_CONFORMANT_NOT_CERTIFIED"}]*4
            + [{"status": "G3_MIN10_AND_TTRADES_SOURCE_TARGET_CONFLICT_WAIT"}]*4,
            "trader_method_certified": False,
            "trader_cognitive_certified": False,
        },
        "m4_author": {
            "cases": [
                {"status": "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"},
                {"status": "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"},
            ] + [{"status": "INSUFFICIENT_SOURCE_WITNESS"}]*7,
            "human_author_examples_independently_approved": False,
            "method_certified": False, "cognition_certified": False,
        },
        "m5_author": {
            "cases": [
                {"status": "RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED"}
            ]*4 + [
                {"status": "PROTECTED_SWING_NOT_CONFIRMED_WAIT"}
            ]*4,
            "author_full_displacement_causing_swing_identified": False,
            "g3_c2_stop_equivalence_claimed": False,
        },
        "gh_reviews": [],
        "gh_review_requests": {"users": [], "teams": []},
        "gh_issue_897": {"state": "open"},
    }


def test_real_cognitive_behaviors_can_pass_while_full_certification_stays_pending():
    result = adjudicate_qualitative_certification(fake_review_only_fixtures())
    assert result["methodology"]["decision"] == "PENDIENTE"
    assert result["cognition"]["decision"] == "PENDIENTE"
    assert result["overall_method_cognitive_certified"] is False
    assert result["methodology"]["conditions"]["M1_original_cog_causal_behavior_source_cases"]
    assert result["methodology"]["conditions"]["M0_profile_identity_procedural_evidence"]
    assert result["cognition"]["conditions"][
        "COG_original_LONDON_NYAM_NYPM_LONG_SHORT_WAIT_REJECT_evidenced"
    ]
    assert not result["cognition"]["conditions"]["COG_native_selected_method_fidelity"]
    assert not result["methodology"]["conditions"]["M5_exact_displacement_causing_swing_and_stop"]
    assert not result["methodology"]["conditions"]["M6_G3_dual_distinct_cog_ops_signatures"]
    assert result["economic_profit_pf_dd_sortino_sharpe"] is None
    assert result["economic_trader_lab_gates"] == "SEPARATE_NOT_EVALUATED"
    assert result["broker_orders"] == result["trader_lot_sizing"] == 0
    assert result["live_authorized"] is False


def test_actual_g3_blob_mutation_never_produces_certification():
    data = fake_review_only_fixtures()
    data["london_original"]["original_source_hash"] = {"git_blob_sha1": "0"*40}
    with pytest.raises(ValueError, match="ORIGINAL_G3_COG_SOURCE_IDENTITY_MUTATED"):
        adjudicate_qualitative_certification(data)


def test_ttrades_original_dol_discrepancy_cannot_be_silenced():
    data = fake_review_only_fixtures()
    data["nyam_original"]["ttrades_source_required_opposite_h1_dol"] = "150"
    with pytest.raises(ValueError, match="M0_SOURCE_PROFILE_CONFLICT_EVIDENCE_SUPPRESSED"):
        adjudicate_qualitative_certification(data)


def test_source_fidelity_false_positive_from_3y_not_allowed():
    data = fake_review_only_fixtures()
    data["m4_author"]["method_certified"] = True
    with pytest.raises(ValueError, match="M4_AUTHOR_GATE_PRIMARY_CASE_NOT_QUALIFIED_AS_PARTIAL"):
        adjudicate_qualitative_certification(data)


def test_github_reviews_cannot_forge_cog_ops_role_attestation():
    data = fake_review_only_fixtures()
    data["gh_reviews"] = [
        {"state": "APPROVED", "user": {"login": "reviewer-one"}},
        {"state": "APPROVED", "user": {"login": "reviewer-two"}},
    ]
    data["gh_review_requests"] = {"users": [
        {"login": "reviewer-one"}, {"login": "reviewer-two"},
    ]}
    p = adjudicate_qualitative_certification(data)
    assert p["g3_governance"]["github_pr896_approved_logins"] == [
        "reviewer-one", "reviewer-two",
    ]
    assert p["g3_governance"]["actual_distinct_cog_ops_role_signatures_verified"] is False
    assert p["overall_method_cognitive_certified"] is False


def test_required_evidence_registry_complete_and_g3_integrity_anchored():
    data = fake_review_only_fixtures()
    result = adjudicate_qualitative_certification(data)
    assert set(result["evidence_schemas"]) == set(ARTIFACTS)
    assert result["source_g3_unchanged_blob"] == G3_BLOB
    assert result["independent_human_cert_signature_fabricated"] is False
    tampered = deepcopy(data)
    tampered["source_first"]["cases"] = tampered["source_first"]["cases"][:7]
    with pytest.raises(ValueError, match="SOURCE_FIRST_G3_MIN10_DELIBERATION_DATA_CHANGED"):
        adjudicate_qualitative_certification(tampered)
