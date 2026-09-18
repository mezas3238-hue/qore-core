"""Freeze manifest for the R28 Turtle Soup XAUUSD specialist candidate.

This module does not run research or choose parameters.  It verifies the exact
official R28 artifact and emits the immutable candidate contract that may be
used for a later fresh holdout.  The fresh holdout remains sealed here.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

CANDIDATE_ID = "TURTLE_SOUP_XAUUSD_R28_VALIDATED_SPECIALIST_CANDIDATE_001"
R28_IDENTITY = "TURTLE_SOUP_XAUUSD_R28_VALIDATED_SPECIALIST_BRAIN_V1"
R28_RUN_ID = 35305338898
R28_ARTIFACT_ID = 10531258915
R28_ARTIFACT_DIGEST = (
    "sha256:33d1b590dd8c11c63bc6d9f3164b567a61795abe7b4582800a87aeb43f0a8bed"
)
R28_GIT_SHA = "c35f8414ce59e26a36cdda27c2a964a426c3e5ba"
R28_REPORT_SHA256 = "3482abbda46d71ab9f1e86fbf14d038ead2df3b0936c972b5d70407b604875aa"
COGNITIVE_V3_SHA256 = "95653ca2156b9d3efb1004cc1dd81f5968d37c7d2161b91eab3adc76af3d34fb"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze(r28_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(r28_root, "r28-validated-specialist-brain-report.json")
    cognitive_path = _single(
        r28_root, "turtle-soup-xauusd-specialist-cognitive-memory-v3.json"
    )
    git_sha_path = _single(r28_root, "git-sha.txt")
    if git_sha_path.read_text().strip() != R28_GIT_SHA:
        raise ValueError("unexpected R28 git binding")
    if _sha256(report_path) != R28_REPORT_SHA256:
        raise ValueError("R28 report SHA-256 drift")
    if _sha256(cognitive_path) != COGNITIVE_V3_SHA256:
        raise ValueError("Cognitive Memory V3 SHA-256 drift")

    report = json.loads(report_path.read_text())
    if report["identity"] != R28_IDENTITY:
        raise ValueError("unexpected R28 identity")
    if report["window"] != {
        "open": "2024-09-17T00:00:00+00:00",
        "close": "2026-09-17T00:00:00+00:00",
        "duration_years": 2,
    }:
        raise ValueError("unexpected R28 development window")

    decision = report["decision_contract"]
    required_true = (
        "causal_structure_precedes_economic_validation",
        "economic_validation_uses_full_lifecycle_net_010",
        "actual_strategy_entry",
        "exact_protected_swing",
        "target_from_active_cibo_dol_ladder",
        "structural_rearm",
    )
    if not all(bool(decision[key]) for key in required_true):
        raise ValueError("R28 decision contract drift")
    required_false = (
        "situation_definition_uses_economic_results",
        "regime_definition_uses_economic_results",
        "management_posture_selected_by_economic_results",
        "economic_mean_magnitude_ranks_targets",
        "calendar_year_regime_rule",
        "context_only_can_authorize",
    )
    if any(bool(decision[key]) for key in required_false):
        raise ValueError("R28 forbidden decision input drift")

    behavior = report["behavior"]
    expected = {
        "trades": 202,
        "gross_total_r": "74.22698991652979348745575800",
        "net_005_total_r": "64.12698991652979348745575798",
        "net_010_total_r": "54.02698991652979348745575798",
        "net_010_profit_factor": "1.822422741600908368886238763",
        "net_010_max_drawdown_r": "7.58121231356678898566445439",
    }
    observed = {
        "trades": behavior["net_010"]["trades"],
        "gross_total_r": behavior["gross"]["total_r"],
        "net_005_total_r": behavior["net_005"]["total_r"],
        "net_010_total_r": behavior["net_010"]["total_r"],
        "net_010_profit_factor": behavior["net_010"]["profit_factor"],
        "net_010_max_drawdown_r": behavior["net_010"]["max_drawdown_r"],
    }
    if observed != expected:
        raise ValueError(f"R28 economic evidence drift: {observed!r}")

    manifest = {
        "schema": "qore.turtle_soup_xauusd.candidate_freeze.v1",
        "candidate_id": CANDIDATE_ID,
        "status": "FROZEN_FOR_FRESH_HOLDOUT",
        "strategy_identity": "TURTLE_SOUP_XAUUSD",
        "source_brain": {
            "identity": R28_IDENTITY,
            "run_id": R28_RUN_ID,
            "artifact_id": R28_ARTIFACT_ID,
            "artifact_digest": R28_ARTIFACT_DIGEST,
            "git_sha": R28_GIT_SHA,
            "report_sha256": R28_REPORT_SHA256,
            "cognitive_v3_sha256": COGNITIVE_V3_SHA256,
        },
        "source_memory_chain": {
            "cibo_master_run_id": 35166210458,
            "cibo_master_artifact_id": 10476557530,
            "cibo_master_digest": "sha256:dcb905b11380e3d4e1a4dc621e269bb75d2886806dd662e260d21d1d15362e08",
            "journey_v1_run_id": 35175979474,
            "target_destination_v2_run_id": 35204892665,
            "target_destination_v2_artifact_id": 10489343458,
            "target_destination_v2_digest": "sha256:61f60ee5df2507c3f7eca02fef1bc9252f0eaae0a428b47a6027882a7b74bfff",
            "specialist_raw_memory_v1_run_id": 35304421155,
            "specialist_raw_memory_v1_artifact_id": 10530462645,
            "specialist_raw_memory_v1_digest": "sha256:77e0d4ad729f3c7a5a2e9ca124e3937c8ebb2f1e67ed7e462c82efe98826a64e",
            "specialist_cognitive_v2_run_id": 35305072887,
            "specialist_cognitive_v2_artifact_id": 10530513211,
            "specialist_cognitive_v2_digest": "sha256:99813bf2447afa8c410d0736100b3c693dea715c9e2109f18ed11261d790e0bb",
            "specialist_cognitive_v3_run_id": R28_RUN_ID,
            "specialist_cognitive_v3_artifact_id": R28_ARTIFACT_ID,
            "specialist_cognitive_v3_digest": R28_ARTIFACT_DIGEST,
        },
        "frozen_contract": {
            "methodology_source": "TTRADES_WHEN_AMBIGUOUS",
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "initial_stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "destination": "ACTIVE_CIBO_DOL_LADDER",
            "authority_levels": [
                "exact_regime",
                "causal_core_regime",
                "anatomy_regime",
            ],
            "context_only_level": "regime_journey",
            "regime": "PRE_ENTRY_H1_H4_D1_M5_NO_CALENDAR_YEAR_RULE",
            "minimum_target_observations": 20,
            "minimum_distinct_quarters": 4,
            "minimum_static_protected_swing_reach_rate": "0.50",
            "management": "STRUCTURAL_NON_INFERIOR_TO_STATIC",
            "economic_validation": (
                "FULL_LIFECYCLE_NET_010_COMBINED_POSITIVE_AND_AT_LEAST_2_OF_3_"
                "EQUAL_COUNT_CHRONOLOGICAL_TERCILES_POSITIVE"
            ),
            "economic_mean_magnitude_ranks_targets": False,
            "structural_rearm": "NEW_RAID_AND_NEW_SOURCE_C2_AFTER_TRAILING_EXIT",
            "same_m5_bar_tie": "STOP_FIRST",
            "max_lifecycle": "24H",
        },
        "consumed_development_evidence": {
            "window": "[2024-09-17, 2026-09-17)",
            "trades": 202,
            "gross_total_r": expected["gross_total_r"],
            "net_005_total_r": expected["net_005_total_r"],
            "net_010_total_r": expected["net_010_total_r"],
            "net_010_profit_factor": expected["net_010_profit_factor"],
            "net_010_max_drawdown_r": expected["net_010_max_drawdown_r"],
            "max_losing_streak": behavior["net_010"]["max_losing_streak"],
        },
        "baseline_comparison_consumed": {
            "R20": {
                "trades": 1529,
                "gross_r": "14.62",
                "net_005_r": "-61.83",
                "net_010_r": "-138.28",
            },
            "R22": {
                "trades": 785,
                "gross_r": "46.81",
                "net_005_r": "7.56",
                "net_010_r": "-31.69",
            },
            "R25": {
                "trades": 1411,
                "gross_r": "66.56",
                "net_005_r": "-3.99",
                "net_010_r": "-74.54",
            },
            "R26_DEVELOPMENT_DIAGNOSTIC": {
                "trades": 162,
                "gross_r": "59.29711032950332902467958616",
                "net_005_r": "51.19711032950332902467958616",
                "net_010_r": "43.09711032950332902467958616",
            },
            "R27_STRUCTURAL_ONLY_REJECTED": {
                "trades": 621,
                "gross_r": "58.89491888735415474225196306",
                "net_005_r": "27.84491888735415474225196298",
                "net_010_r": "-3.205081112645845257748036945",
            },
        },
        "governance": {
            "candidate_frozen": True,
            "candidate_promoted": False,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "turtle-soup-xauusd-r28-candidate-freeze.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R28_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
