"""Freeze the R33 2Y coverage candidate before 5Y validation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R33_FIVE_FAMILY_RISK_GOVERNOR_CANDIDATE_001"
SOURCE_RUN_ID = 35308249603
SOURCE_ARTIFACT_ID = 10531704421
SOURCE_ARTIFACT_DIGEST = (
    "sha256:7de9708d9c468aca5b1fe7096a84e806b25be5d6c1de098a0025b2b27c2551b1"
)
SOURCE_GIT_SHA = "8dbe6385c7f15945e3f5001c76b70d0e5fc52b63"
SOURCE_REPORT_SHA256 = (
    "b652a07a3347f1731afea5943f0e5c8b5c673c689e217c2eebf7e705a234d45d"
)
SELECTED_FAMILY_SET = "R33_FIVE_FAMILY"
SELECTED_GOVERNOR = "DD_2_4_SCALE_075_025"
EXPECTED_TRADES = 367
EXPECTED_PF = "2.002523896485190572988396913"
EXPECTED_DD = "5.69899493419710124390262490"
EXPECTED_TOTAL = "100.1776792956344955860751459"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(source_root, "r33-subfamily-risk-governor-report.json")
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R33 report hash drift")
    report = json.loads(report_bytes)
    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R33 git binding drift")

    selected = report.get("selected")
    if not isinstance(selected, dict):
        raise ValueError("R33 has no selected passing candidate")
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
        "schema": "qore.turtle_soup_xauusd.r33_candidate_freeze.v1",
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
            "risk_governor": SELECTED_GOVERNOR,
            "risk_governor_parameters": report["experiment_contract"][
                "governors_predeclared"
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
            "risk_governor_suppresses_trades": False,
            "risk_governor_pretrade_state_only": True,
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
    out = output / "r33-candidate-freeze-manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R33_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
