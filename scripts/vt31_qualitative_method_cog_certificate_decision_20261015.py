#!/usr/bin/env python3
"""VT31 methodological + cognitive certification ledger from immutable evidence.

NO economic acceptance metrics, no auto sign-off, no broker trading authority.
A CI PASS on software cannot replace genuine independent reviewer approvals.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PREREG = "1ef9f86ccecc4e9606855a8d1d706a08a45eb428"
ARTIFACTS = {
    "london_original": (
        "11944328096", "VT31_ORIGINAL_G3_COG_QUALITATIVE_CASE_DOSSIER.json",
    ),
    "nyam_original": (
        "11943793928", "VT31_G3_ORIGINAL_NYAM_TTRADES_SOURCE_MISMATCH.json",
    ),
    "m0_profile": (
        "11958388150", "VT31_M0_ORIGINAL_COG_PROFILE_METHOD_SHADOW.json",
    ),
    "nypm_original": (
        "11959135942",
        "VT31_ORIGINAL_G3_COG_NYPM_QUALITATIVE_DECISION_DOSSIER.json",
    ),
    "short_original": (
        "11960185549", "VT31_COG_ORIGINAL_SHORT_SESSIONS_EST_EDT_QUALITATIVE.json",
    ),
    "source_first": (
        "11959393863", "VT31_TTRADES_PROFILE_SOURCE_BOUND_G3_MIN10_NO_PNL.json",
    ),
    "m4_author": (
        "11961174983", "VT31_M4_OB_BREAKER_AUTHOR_SOURCE_EVIDENCE_NO_PNL.json",
    ),
    "m5_author": (
        "11962555846", "VT31_M5_TTRADES_PROTECTED_SWING_CAUSAL_NO_BROKER_SL.json",
    ),
}
G3_BLOB = "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"


def _read_inputs(root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for label, (artifact, filename) in ARTIFACTS.items():
        path = root / artifact / filename
        if not path.is_file():
            raise ValueError(f"MISSING_IMMUTABLE_QUALITATIVE_EVIDENCE:{label}")
        data[label] = json.loads(path.read_text())
    for field, path in (
        ("gh_reviews", root / "github_reviews_896.json"),
        ("gh_review_requests", root / "github_review_requests_896.json"),
        ("gh_issue_897", root / "github_issue_897.json"),
    ):
        if not path.is_file():
            raise ValueError(f"MISSING_LIVE_GOVERNANCE_EVIDENCE:{field}")
        data[field] = json.loads(path.read_text())
    return data


def adjudicate_qualitative_certification(e: dict[str, Any]) -> dict[str, Any]:
    """Classify actual demonstrated behavior vs human-unverified doctrine.

    A falsely altered or contradictory artifact raises, not "PASS".
    """
    london = e["london_original"]
    nyam = e["nyam_original"]
    m0 = e["m0_profile"]
    nypm = e["nypm_original"]
    short = e["short_original"]
    source = e["source_first"]
    m4 = e["m4_author"]
    m5 = e["m5_author"]
    if (
        london["original_source_hash"]["git_blob_sha1"] != G3_BLOB
        or nyam["original_g3_cog_code_sha"]["git_blob_sha1"] != G3_BLOB
        or m0["original_g3_cog_source_hash"]["git_blob_sha1"] != G3_BLOB
        or nypm["original_g3_source_hash"]["git_blob_sha1"] != G3_BLOB
        or short["original_source"]["git_blob_sha1"] != G3_BLOB
        or source["original_frozen_g3_code_sha"]["git_blob_sha1"] != G3_BLOB
    ):
        raise ValueError("ORIGINAL_G3_COG_SOURCE_IDENTITY_MUTATED")

    # Genuine original cognition: actual outputs across all three sessions.
    london_expected = [
        "LONG", "LONG", "WAIT", "WAIT", "WAIT", "WAIT", "WAIT",
        "REJECT", "LONG", "LONG",
    ]
    nypm_expected = ["LONG", "WAIT", "WAIT", "WAIT", "WAIT", "REJECT"]
    if (
        not london["original_cog_directly_invoked"]
        or [x["observed"]["action"] for x in london["cases"]] != london_expected
        or not nypm["real_original_cog_invoked"]
        or [x["decision"] for x in nypm["cases"]] != nypm_expected
        or not short["original_cog_directly_invoked"]
        or len(short["cases"]) != 6
        or any(x["original_cog_side"] != "SHORT" for x in short["cases"])
        or {x["session"] for x in short["cases"]}
        != {"VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM"}
        or {x["observed_utc_offset"] for x in short["cases"]} != {-5, -4}
    ):
        raise ValueError("ORIGINAL_G3_COG_QUALITATIVE_BEHAVIOR_NOT_REPRODUCED")
    original_behavior_observed = True

    # Preserve negative evidence; never drop incompatibility from a pass score.
    if (
        nyam["observed_actual_original_cog_dol"] != "150"
        or nyam["ttrades_source_required_opposite_h1_dol"] != "110"
        or nyam["independent_source_v2_state"] != "REJECTED"
        or m0["cases"][0]["state"] != "TTRADES_PROFILE_SOURCE_REJECTED"
        or m0["cases"][1]["state"] != "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
        or m0["cases"][2]["state"] != "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
        or m0["cases"][3]["state"] != "PROFILE_SESSION_REJECTED"
    ):
        raise ValueError("M0_SOURCE_PROFILE_CONFLICT_EVIDENCE_SUPPRESSED")
    original_native_ttrades_aligned = False
    m0_profile_separation_evidenced = True

    statuses = [x["status"] for x in source["cases"]]
    if (
        len(statuses) != 8
        or statuses.count("RESEARCH_TTRADES_CONTEXT_CONFORMANT_NOT_CERTIFIED") != 4
        or statuses.count("G3_MIN10_AND_TTRADES_SOURCE_TARGET_CONFLICT_WAIT") != 4
        or source["trader_method_certified"]
        or source["trader_cognitive_certified"]
    ):
        raise ValueError("SOURCE_FIRST_G3_MIN10_DELIBERATION_DATA_CHANGED")
    source_first_partial = True

    m4_status = [x["status"] for x in m4["cases"]]
    if (
        len(m4_status) != 9
        or m4_status.count(
            "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
        ) != 1
        or m4_status.count(
            "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
        ) != 1
        or m4["human_author_examples_independently_approved"]
        or m4["method_certified"] or m4["cognition_certified"]
    ):
        raise ValueError("M4_AUTHOR_GATE_PRIMARY_CASE_NOT_QUALIFIED_AS_PARTIAL")
    m4_source_structural_only = True
    m4_author_examples_verified = False

    m5_status = [x["status"] for x in m5["cases"]]
    if (
        len(m5_status) != 8
        or m5_status.count(
            "RESEARCH_PROTECTED_SWING_SOURCE_CONTEXT_WITNESSED"
        ) != 4
        or m5_status.count("PROTECTED_SWING_NOT_CONFIRMED_WAIT") != 4
        or m5["author_full_displacement_causing_swing_identified"]
        or m5["g3_c2_stop_equivalence_claimed"]
    ):
        raise ValueError("M5_PROTECTED_SWING_NOT_SAME_AS_AUTHOR_STOP_CERT")
    m5_protected_swing_context_only = True
    m5_causing_swing_confirmed = False

    reviews = e["gh_reviews"]
    requests = e["gh_review_requests"]
    issue = e["gh_issue_897"]
    if not isinstance(reviews, list) or not isinstance(requests, dict):
        raise ValueError("INVALID_GITHUB_REVIEW_DATA")
    approved_identified = sorted({
        x.get("user", {}).get("login", "")
        for x in reviews if x.get("state") == "APPROVED"
        and x.get("user", {}).get("login")
    })
    requested_identified = [
        x.get("login") for x in requests.get("users", [])
        if x.get("login")
    ]
    # GitHub reviews alone do not prove distinct *COG* and *OPS* roles on
    # exactly the G3 method/code; that requires separate role attestations.
    dual_cog_ops_authenticated = False
    if issue.get("state") != "open" and not approved_identified:
        raise ValueError("G3_CLOSED_WITH_NO_REVIEW_EVIDENCE")
    human_method_source_approved = False
    human_cognitive_review_approved = False
    native_source_selector_governed = False
    author_mss_fidelity_independently_verified = False

    method_conditions: dict[str, bool] = {
        "M0_profile_identity_procedural_evidence": m0_profile_separation_evidenced,
        "M0_native_profile_selector_governed": native_source_selector_governed,
        "M1_original_cog_causal_behavior_source_cases": original_behavior_observed,
        "M2_ttrades_source_first_research_context": source_first_partial,
        "M2_original_native_ttrades_profile_fidelity": original_native_ttrades_aligned,
        "M3_author_mss_fidelity_verified": author_mss_fidelity_independently_verified,
        "M4_ob_breaker_structural_negative_and_positive_cases": m4_source_structural_only,
        "M4_author_cases_and_zone_rules_approved": m4_author_examples_verified,
        "M5_protected_swing_source_context": m5_protected_swing_context_only,
        "M5_exact_displacement_causing_swing_and_stop": m5_causing_swing_confirmed,
        "M6_method_independent_human_review": human_method_source_approved,
        "M6_G3_dual_distinct_cog_ops_signatures": dual_cog_ops_authenticated,
    }
    cognitive_conditions: dict[str, bool] = {
        "COG_original_LONDON_NYAM_NYPM_LONG_SHORT_WAIT_REJECT_evidenced":
            original_behavior_observed,
        "COG_source_profile_conflict_recognized_by_separate_auditor":
            m0_profile_separation_evidenced,
        "COG_TTrades_research_source_first_abstains_on_G3_conflict":
            source_first_partial,
        "COG_native_selected_method_fidelity": original_native_ttrades_aligned,
        "COG_actual_author_entry_ob_breaker_swing_coverage":
            m4_author_examples_verified and m5_causing_swing_confirmed,
        "COG_independent_human_scenario_review": human_cognitive_review_approved,
        "COG_distinct_cog_ops_G3_signatures": dual_cog_ops_authenticated,
    }
    missing_method = [k for k, ok in method_conditions.items() if not ok]
    missing_cognitive = [k for k, ok in cognitive_conditions.items() if not ok]
    method_certified = not missing_method
    cognition_certified = not missing_cognitive

    return {
        "schema": "qore.vt31.qualitative_method_cognition_cert_decision.v1",
        "prereg_commit": PREREG,
        "evidence_schemas": sorted(ARTIFACTS),
        "source_g3_unchanged_blob": G3_BLOB,
        "certification_scoring": "CONJUNCTIVE_QUALITATIVE_NOT_PROFIT_METRICS",
        "methodology": {
            "conditions": method_conditions,
            "missing_necessary_conditions": missing_method,
            "decision": "CERTIFICADO" if method_certified else "PENDIENTE",
        },
        "cognition": {
            "conditions": cognitive_conditions,
            "missing_necessary_conditions": missing_cognitive,
            "decision": "CERTIFICADO" if cognition_certified else "PENDIENTE",
        },
        "g3_governance": {
            "issue_number": 897, "github_issue_state": issue.get("state"),
            "github_pr896_approved_logins": approved_identified,
            "github_pr896_requested_logins": requested_identified,
            "actual_distinct_cog_ops_role_signatures_verified":
                dual_cog_ops_authenticated,
            "github_reviews_are_not_role_evidence": True,
        },
        "overall_method_cognitive_certified":
            method_certified and cognition_certified,
        "economic_trader_lab_gates": "SEPARATE_NOT_EVALUATED",
        "economic_profit_pf_dd_sortino_sharpe": None,
        "real_market_3y_replayed": False,
        "broker_orders": 0, "trader_lot_sizing": 0,
        "oms_enabled": False, "live_authorized": False,
        "independent_human_cert_signature_fabricated": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    options = p.parse_args()
    raw = _read_inputs(options.evidence_root)
    decision = adjudicate_qualitative_certification(raw)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(
        json.dumps(decision, sort_keys=True, indent=2, ensure_ascii=False)+"\n"
    )
    print(json.dumps({
        "methodology": decision["methodology"]["decision"],
        "cognition": decision["cognition"]["decision"],
        "method_missing": decision["methodology"]["missing_necessary_conditions"],
        "cognition_missing": decision["cognition"]["missing_necessary_conditions"],
        "human_signatures": decision["g3_governance"][
            "actual_distinct_cog_ops_role_signatures_verified"
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
