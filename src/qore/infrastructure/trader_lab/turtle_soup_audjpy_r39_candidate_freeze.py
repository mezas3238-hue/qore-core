"""Freeze the passing AUDJPY R38 candidate before five-year validation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_AUDJPY_R39_STRUCTURAL_RISK_CANDIDATE_001"
SOURCE_IDENTITY = "TURTLE_SOUP_AUDJPY_R38_STRUCTURAL_FRAGILITY_RISK_CORRECTION_V1"
SOURCE_RUN_ID = 35396621959
SOURCE_ARTIFACT_ID = 10567832804
SOURCE_ARTIFACT_DIGEST = (
    "sha256:f3c6958644cdf07c00f6bdf59e7da50d1dcaec886a4a37083fa27525aca3777b"
)
SOURCE_GIT_SHA = "389ab392fda4cf216fdf078a9386a4812316f430"
SOURCE_REPORT_SHA256 = (
    "323f38262a2a03f9f3fa847f029f581d5a4e7c6707f6c3ce6c038cf4a6a228a6"
)

SELECTED_ENSEMBLE = "R38_FROZEN_SIGNAL_BASELINE"
SELECTED_POLICY = "AUDJPY_CONFIDENCE_100_075_025"
EXPECTED_TRADES = 422
EXPECTED_PF = "1.914983646549167839637883832"
EXPECTED_DD = "5.04830244641349726210448727"
EXPECTED_TOTAL = "52.20034416864185681619198775"
EXPECTED_FRAGILITY_FLAGS = (
    "M5_EFFICIENCY_MEDIUM",
    "D1_RANGE_EXPANDED",
    "PROJECTED_R_Q2_LE_1",
)
EXPECTED_FRAGILITY_POLICY = ("1", "0.20", "0.05", "0.01")


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(
        source_root,
        "r38-structural-fragility-risk-correction-report.json",
    )
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R38 report hash drift")

    report = json.loads(report_bytes)
    if report["identity"] != SOURCE_IDENTITY:
        raise ValueError("R38 identity drift")

    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R38 git binding drift")

    selected = report.get("selected")
    if not isinstance(selected, dict):
        raise ValueError("R38 has no selected passing candidate")
    if selected["ensemble"] != SELECTED_ENSEMBLE:
        raise ValueError("ensemble drift")
    if selected["policy"] != SELECTED_POLICY:
        raise ValueError("policy drift")

    stats = selected["stats"]
    if int(stats["trades"]) != EXPECTED_TRADES:
        raise ValueError("trade-count drift")
    if str(stats["profit_factor_scaled_net_010"]) != EXPECTED_PF:
        raise ValueError("profit-factor drift")
    if str(stats["max_drawdown_scaled_r"]) != EXPECTED_DD:
        raise ValueError("drawdown drift")
    if str(stats["total_scaled_net_010_r"]) != EXPECTED_TOTAL:
        raise ValueError("total-R drift")

    experiment = report["experiment_contract"]
    if experiment["r32_core_is_primary_authority"] is not True:
        raise ValueError("R32 core authority drift")
    if experiment["r34_range_used_for_authority"] is not False:
        raise ValueError("falsified RANGE authority drift")
    if experiment["actual_active_cibo_dol_price_used"] is not True:
        raise ValueError("DOL contract drift")
    if experiment["risk_governor_suppresses_trades"] is not False:
        raise ValueError("risk suppression drift")
    if tuple(experiment["fragility_flags_predeclared"]) != EXPECTED_FRAGILITY_FLAGS:
        raise ValueError("fragility flag drift")
    if tuple(experiment["fragility_policy_0_1_2_3plus"]) != EXPECTED_FRAGILITY_POLICY:
        raise ValueError("fragility policy drift")
    if experiment["fragility_uses_pre_entry_context_only"] is not True:
        raise ValueError("fragility timing drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_audjpy.r39_candidate_freeze.v1",
        "identity": IDENTITY,
        "status": "FROZEN_FOR_5Y_VALIDATION",
        "source": {
            "identity": SOURCE_IDENTITY,
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
        },
        "frozen_contract": {
            "ensemble": SELECTED_ENSEMBLE,
            "layers": experiment["ensembles_predeclared"][SELECTED_ENSEMBLE],
            "risk_policy": SELECTED_POLICY,
            "risk_policy_parameters": experiment["risk_policies_predeclared"][
                SELECTED_POLICY
            ],
            "fragility_flags": list(EXPECTED_FRAGILITY_FLAGS),
            "fragility_policy_0_1_2_3plus": list(EXPECTED_FRAGILITY_POLICY),
            "fragility_uses_pre_entry_context_only": True,
            "r32_core_is_primary_authority": True,
            "r34_range_used_for_authority": False,
            "expansion_only_when_higher_authority_layer_abstains": True,
            "actual_active_cibo_dol_price_used": True,
            "nearest_validated_dol_within_each_layer": True,
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "single_position_busy": True,
            "structural_rearm": True,
            "risk_governor_suppresses_trades": False,
            "risk_governor_pretrade_memory_only": True,
            "same_m5_bar": "STOP_FIRST",
        },
        "development_2y_result": {
            "trades": EXPECTED_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_PF,
            "max_drawdown_scaled_r": EXPECTED_DD,
            "total_scaled_net_010_r": EXPECTED_TOTAL,
            "max_losing_streak": int(stats["max_losing_streak"]),
            "risk_scale_counts": stats["risk_scale_counts"],
            "fragility_flag_count_distribution": stats[
                "fragility_flag_count_distribution"
            ],
            "fragility_flag_counts": stats["fragility_flag_counts"],
            "authority_class_counts": stats["authority_class_counts"],
            "source_counts": stats["source_counts"],
        },
        "next_stage": {
            "required": "FROZEN_5Y_VALIDATION",
            "rules_must_remain_frozen": True,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
        },
        "governance": {
            "candidate_frozen": True,
            "candidate_promoted": False,
            "fresh_holdout_consumed": False,
            "trader_certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r39-candidate-freeze-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R38_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
