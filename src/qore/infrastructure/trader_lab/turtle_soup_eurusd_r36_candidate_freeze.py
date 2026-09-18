"""Freeze the EURUSD R36 structural-fragility candidate before 5Y validation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_EURUSD_R36_FRAGILITY_CANDIDATE_001"
SOURCE_RUN_ID = 35325383868
SOURCE_ARTIFACT_ID = 10538108144
SOURCE_ARTIFACT_DIGEST = (
    "sha256:329c64129ce1d7b925d3da8a82aeec1974e57293bede85abcaf1d5bb7a83db6a"
)
SOURCE_GIT_SHA = "bcf11b8a040b343eb89dcb1faa463cef150d68a6"
SOURCE_REPORT_SHA256 = (
    "35e8a7b6dba194bd29b433be1be98e707d93775e169bb051da2f50dbcfb31da9"
)
SELECTED_FAMILY_SET = "R36_F235_FROZEN"
SELECTED_GOVERNOR = "FRAGILITY_050_025_010"
EXPECTED_TRADES = 366
EXPECTED_PF = "3.235289727084444144145496287"
EXPECTED_DD = "3.83972573211060055575442915"
EXPECTED_TOTAL = "153.1838491331511895037068291"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(source_root, "r36-structural-fragility-governor-report.json")
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R36 report hash drift")
    report = json.loads(report_bytes)
    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R36 git binding drift")

    selected = report.get("selected")
    if not isinstance(selected, dict):
        raise ValueError("R36 has no selected passing candidate")
    if selected["family_set"] != SELECTED_FAMILY_SET:
        raise ValueError("family-set drift")
    if selected["governor"] != SELECTED_GOVERNOR:
        raise ValueError("governor drift")
    stats = selected["stats"]
    if int(stats["trades"]) != EXPECTED_TRADES:
        raise ValueError("trade-count drift")
    if str(stats["profit_factor_scaled_net_010"]) != EXPECTED_PF:
        raise ValueError("profit-factor drift")
    if str(stats["max_drawdown_scaled_r"]) != EXPECTED_DD:
        raise ValueError("drawdown drift")
    if str(stats["total_scaled_net_010_r"]) != EXPECTED_TOTAL:
        raise ValueError("total-R drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_eurusd.r36_candidate_freeze.v1",
        "identity": IDENTITY,
        "status": "FROZEN_FOR_5Y_VALIDATION",
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
        },
        "frozen_contract": {
            "family_set": SELECTED_FAMILY_SET,
            "families": report["experiment_contract"]["family_sets_predeclared"][
                SELECTED_FAMILY_SET
            ],
            "fragility_flags": report["experiment_contract"][
                "fragility_flags_predeclared"
            ],
            "risk_governor": SELECTED_GOVERNOR,
            "risk_governor_parameters": report["experiment_contract"][
                "fragility_policies_predeclared"
            ][SELECTED_GOVERNOR],
            "r30_core_preserved": True,
            "expansion_only_when_r30_abstains": True,
            "expansion_target_rank": 1,
            "actual_active_cibo_dol_price_used": True,
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "expansion_posture": "STATIC",
            "single_position_busy": True,
            "structural_rearm": True,
            "risk_governor_suppresses_trades": False,
            "risk_governor_pretrade_context_only": True,
            "same_m5_bar": "STOP_FIRST",
            "max_lifecycle": "24H",
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
        },
        "next_stage": {
            "required": "5Y_VALIDATION",
            "rules_must_remain_frozen": True,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
        },
        "governance": {
            "candidate_frozen": True,
            "candidate_promoted": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    out = output / "r36-candidate-freeze-manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R36_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
