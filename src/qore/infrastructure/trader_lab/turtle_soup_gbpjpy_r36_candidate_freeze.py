"""Freeze the passing GBPJPY R35 candidate before five-year validation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_GBPJPY_R36_CONFIDENCE_CANDIDATE_001"
SOURCE_IDENTITY = "TURTLE_SOUP_GBPJPY_R35_CONFIDENCE_TIER_ENSEMBLE_LAB_V1"
SOURCE_RUN_ID = 35370716933
SOURCE_ARTIFACT_ID = 10558517399
SOURCE_ARTIFACT_DIGEST = (
    "sha256:c7eaef5c70b200b91b5bae3358b35210676c06a084ad965e928baf521d20c72a"
)
SOURCE_GIT_SHA = "03465666dc235e06002f189d4db476813150960e"
SOURCE_REPORT_SHA256 = (
    "7d6942f98cf1ce7142bb808b816a20365c20f1f17d3aa7f2377fcc4f320435db"
)

SELECTED_ENSEMBLE = "R35_RANGE_DIRECTION_MINIMAL_ROBUST"
SELECTED_POLICY = "CONFIDENCE_100_050_010"
EXPECTED_TRADES = 371
EXPECTED_PF = "1.917321619841829026960123251"
EXPECTED_DD = "5.34575969539718361901697478"
EXPECTED_TOTAL = "61.20501737968874858251138689"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(source_root, "r35-confidence-tier-ensemble-report.json")
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R35 report hash drift")

    report = json.loads(report_bytes)
    if report["identity"] != SOURCE_IDENTITY:
        raise ValueError("R35 identity drift")

    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R35 git binding drift")

    selected = report.get("selected")
    if not isinstance(selected, dict):
        raise ValueError("R35 has no selected passing candidate")
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
    if experiment["r34_range_core_preserved"] is not True:
        raise ValueError("R34 RANGE core drift")
    if experiment["actual_active_cibo_dol_price_used"] is not True:
        raise ValueError("DOL contract drift")
    if experiment["risk_governor_suppresses_trades"] is not False:
        raise ValueError("risk suppression drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpjpy.r36_candidate_freeze.v1",
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
            "r34_range_core_preserved": True,
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
    (output / "r36-candidate-freeze-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R35_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
