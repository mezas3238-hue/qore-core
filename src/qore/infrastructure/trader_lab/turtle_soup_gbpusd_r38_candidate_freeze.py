"""Freeze exact GBPUSD R37 two-year passing candidate for five-year validation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_GBPUSD_R37_STRUCTURAL_QUALITY_CANDIDATE_001"
SOURCE_RUN_ID = 35352145888
SOURCE_ARTIFACT_ID = 10550221115
SOURCE_ARTIFACT_DIGEST = (
    "sha256:544471a071b772e395d3ec9c4b54fa0aecbdb5953730ab6e6f704c335639a5cd"
)
SOURCE_GIT_SHA = "75b70f877794f018a41e02f91626262079bbf15d"
SOURCE_REPORT_SHA256 = (
    "e778365e57fdd374eaa3a4d2210a48e6ef690936c5675754d764fbc18af170a2"
)
EXPECTED_TRADES = 374
EXPECTED_PF = "1.914184192504076803125810726"
EXPECTED_DD = "4.650727254116239059338971594"
EXPECTED_TOTAL = "38.01388831945717726176873916"
FAMILY_SET = "R37_G25_FIXED"
STRUCTURAL_POLICY = "SQ3_H1_BALANCED"
DRAWDOWN_GOVERNOR = "DD_1_3_SCALE_075_025"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(source_root, "r37-structural-quality-governor-report.json")
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R37 report hash drift")
    report = json.loads(report_bytes)
    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R37 git binding drift")
    if report["identity"] != "TURTLE_SOUP_GBPUSD_R37_STRUCTURAL_QUALITY_GOVERNOR_V1":
        raise ValueError("unexpected R37 identity")

    selected = report["selected"]
    if selected is None:
        raise ValueError("R37 has no selected candidate")
    if selected["family_set"] != FAMILY_SET:
        raise ValueError("family-set drift")
    if selected["policy"] != STRUCTURAL_POLICY:
        raise ValueError("structural-policy drift")
    if selected["drawdown_governor"] != DRAWDOWN_GOVERNOR:
        raise ValueError("drawdown-governor drift")
    result = selected["stats"]
    if int(result["trades"]) != EXPECTED_TRADES:
        raise ValueError("trade-count drift")
    if str(result["profit_factor_scaled_net_010"]) != EXPECTED_PF:
        raise ValueError("profit-factor drift")
    if str(result["max_drawdown_scaled_r"]) != EXPECTED_DD:
        raise ValueError("drawdown drift")
    if str(result["total_scaled_net_010_r"]) != EXPECTED_TOTAL:
        raise ValueError("total-R drift")

    contract = report["experiment_contract"]
    if contract["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout drift")
    if contract["risk_governor_suppresses_trades"] is not False:
        raise ValueError("trade suppression drift")
    governance = report["governance"]
    if governance["structural_risk_policy_preentry_only"] is not True:
        raise ValueError("structural risk causality drift")
    if governance["risk_governor_suppresses_trades"] is not False:
        raise ValueError("governor suppression drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpusd.r38_candidate_freeze.v1",
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
            "family_set": FAMILY_SET,
            "families": [
                "OTHER_SESSION_D1_BODY_OPPOSED",
                "EXACT_EQUAL_LIQUIDITY_LARGE_REJECTION",
            ],
            "r32_core": "R32_REGIME_ROUTE_TYPES",
            "structural_policy": STRUCTURAL_POLICY,
            "drawdown_governor": DRAWDOWN_GOVERNOR,
            "core_robust_scale": "1",
            "core_majority_scale": "0.25",
            "f5_scale": "1",
            "f2_strong_scale": "1",
            "f2_weak_scale": "0.10",
            "f2_strong_mode": "PRISK_Q2_OR_H1_BALANCED",
            "drawdown_first_r": "1",
            "drawdown_second_r": "3",
            "drawdown_middle_scale": "0.75",
            "drawdown_deep_scale": "0.25",
            "signals_suppressed": False,
            "risk_governor_pretrade_context_only": True,
            "expansion_target_rank": 1,
            "actual_active_cibo_dol_price_used": True,
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "single_position_busy": True,
            "structural_rearm": True,
        },
        "consumed_2y_result": {
            "trades": EXPECTED_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_PF,
            "max_drawdown_scaled_r": EXPECTED_DD,
            "total_scaled_net_010_r": EXPECTED_TOTAL,
        },
        "next_stage": {
            "required": "FROZEN_5Y_ROBUSTNESS_VALIDATION",
            "rules_must_remain_frozen": True,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
        },
        "governance": {
            "candidate_frozen": True,
            "candidate_certified": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r38-candidate-freeze-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R37_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
