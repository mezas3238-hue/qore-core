"""Frozen cognitive challenge contract: Shared -> VT08 Index V1.

This challenge tests problem-solving intelligence, not trade execution.

VT08 Index remains owned by PR #604. Shared PR #635 must not modify VT08
methodology, risk, sizing, runtime, LIVE, production or the PR #604 branch.

The challenge asks Shared to diagnose why a historically strong/high-density
VT08 Index identity fails to transport robustly into the recent/fresh windows,
despite many targeted causal ablations.

Immutable evidence sources are PR #604 artifacts R128-R131.
"""
from __future__ import annotations

from dataclasses import dataclass


CHALLENGE_ID = "SHARED_VT08_INDEX_COGNITIVE_CHALLENGE_V1"
VT08_PR = 604
SHARED_PR = 635
VT08_HEAD = "5e307ff861df136b92d857693997d8fb950f4d79"

IMMUTABLE_ARTIFACTS = {
    "R128_CONTEXT_TRANSPORT": {
        "run_id": 36075966463,
        "artifact_id": 10839358300,
        "digest": "sha256:d69448f6dc7fe3b4d49c9be54b18c3158238d38e0e0f1e953ef5a43705f103a9",
    },
    "R129_OVERLAP_SATURATION": {
        "run_id": 36076610569,
        "artifact_id": 10839404006,
        "digest": "sha256:db94ff3d983c35e05aa71b3f9133fc8ecb4215d494cf06c8ed1784c6df25677d",
    },
    "R130_LOW_CONCURRENT_RETEST": {
        "run_id": 36077074851,
        "artifact_id": 10839674224,
        "digest": "sha256:5cbf36ba630f60af21726d5dc4259d6d8e2024f92d405a003a6c60ba5a64cfa5",
    },
    "R131_DAILY_COMPRESSED_RETEST": {
        "run_id": 36081844906,
        "artifact_id": 10843125104,
        "digest": "sha256:5e54b0f0f4c99dd34c53a9431e9e655cb91a50279e7079c72c1b690fd29809be",
    },
}

KNOWN_PROBLEM = {
    "canonical_5y_trades": 2448,
    "canonical_recent_2y_trades": 1017,
    "r66_sample": 773,
    "r66_b2_sample": 413,
    "r66_b2_secondary_pf_after_r130": "0.8580505333221605687187232266",
    "r66_b2_secondary_pf_after_r131": "0.8525112561928865070123650131",
    "r130_r66_full_secondary_delta_r": "0.0525000000000000000000000000",
    "r131_r66_full_secondary_delta_r": "0.0175000000000000000000000000",
    "latest_decision": "NO_CANDIDATE_SELECTED",
}

OWNER_OBJECTIVE = {
    "preserve_density": True,
    "do_not_use_sizing": True,
    "do_not_use_calendar_or_year_as_runtime_feature": True,
    "do_not_open_fresh_holdout_for_development": True,
    "do_not_suppress_signals_to_manufacture_pf": True,
    "diagnose_root_cause_before_proposing_actuation": True,
    "must_explain_pf_density_and_drawdown_together": True,
    "must_generalize_across_windows": True,
}

PROHIBITED_SHORTCUTS = (
    "SIZING",
    "CAPITAL_WEIGHTING",
    "YEAR_OR_CALENDAR_RUNTIME_FILTER",
    "HOLDOUT_TUNING",
    "RETROSPECTIVE_OUTCOME_FEATURE",
    "MASS_SIGNAL_SUPPRESSION",
    "MARKET_REMOVAL_AS_PRIMARY_SOLUTION",
    "TRAILING_OR_TARGET_EXTENSION_AS_DIAGNOSTIC_SHORTCUT",
    "RISK_COMPRESSION_AS_SHARED_SUCCESS",
)

REQUIRED_SHARED_OUTPUTS = (
    "ROOT_CAUSE_MODEL",
    "CONTRADICTION_MAP_5Y_VS_RECENT_2Y_VS_R66_B1_VS_R66_B2",
    "CAUSAL_MECHANISMS_RANKED_WITH_EVIDENCE",
    "WHICH_PRIOR_ABLATIONS_FAILED_AND_WHY",
    "WHAT_INFORMATION_IS_STILL_MISSING",
    "MINIMAL_PREREGISTERED_NEXT_EXPERIMENTS",
    "FALSIFICATION_CRITERIA_FOR_EACH_HYPOTHESIS",
    "EXPECTED_EFFECT_ON_PF_DD_AND_DENSITY_IF_HYPOTHESIS_IS_TRUE",
)

@dataclass(frozen=True, slots=True)
class CognitiveChallengeContract:
    challenge_id: str = CHALLENGE_ID
    source_pr: int = VT08_PR
    evaluator_pr: int = SHARED_PR
    source_head: str = VT08_HEAD
    research_only: bool = True
    shared_may_modify_vt08: bool = False
    live_authorized: bool = False
    production_authorized: bool = False
    sizing_allowed: bool = False
    outcome_leakage_allowed: bool = False
    holdout_tuning_allowed: bool = False
    mass_abstention_allowed: bool = False
    fresh_holdout_opened: bool = False


def challenge_contract() -> CognitiveChallengeContract:
    return CognitiveChallengeContract()
