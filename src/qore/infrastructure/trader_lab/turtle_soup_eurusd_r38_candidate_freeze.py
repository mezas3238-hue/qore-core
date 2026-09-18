"""Freeze exact EURUSD R38 corrected 5Y candidate."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_EURUSD_R38_STRUCTURAL_RISK_CANDIDATE_001"
SOURCE_RUN_ID = 35327677519
SOURCE_ARTIFACT_ID = 10539313228
SOURCE_ARTIFACT_DIGEST = (
    "sha256:2fc7246d9aac4b7c281301e94b71ff336d3f0967859a46a33f3fa62e4fe74e00"
)
SOURCE_GIT_SHA = "324fb91d44a6fa328e66de2e22ace7386630c7aa"
SOURCE_REPORT_SHA256 = (
    "baafaaf385a91b17d9427ba56dc563ab30e453f065fe84d88436a7ba6c402b27"
)
EXPECTED_TRADES = 863
EXPECTED_PF = "2.958703779880710298093151891"
EXPECTED_DD = "5.824645307409961208739068649"
EXPECTED_TOTAL = "294.8274112858301220583196574"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(source_root, "r38-5y-correction-report.json")
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R38 report hash drift")
    report = json.loads(report_bytes)
    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R38 git binding drift")

    result = report["result"]
    if result["acceptance_pass"] is not True:
        raise ValueError("R38 did not pass acceptance")
    if int(result["trades"]) != EXPECTED_TRADES:
        raise ValueError("trade-count drift")
    if str(result["profit_factor_scaled_net_010"]) != EXPECTED_PF:
        raise ValueError("profit-factor drift")
    if str(result["max_drawdown_scaled_r"]) != EXPECTED_DD:
        raise ValueError("drawdown drift")
    if str(result["total_scaled_net_010_r"]) != EXPECTED_TOTAL:
        raise ValueError("total-R drift")

    contract = report["correction_contract"]
    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_eurusd.r38_candidate_freeze.v1",
        "identity": IDENTITY,
        "status": "FROZEN_FOR_FINAL_ROBUSTNESS",
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
        },
        "frozen_contract": {
            "r36_signal_contract_preserved": True,
            "family_set": "R36_F235_FROZEN",
            "base_fragility_governor": "FRAGILITY_050_025_010",
            "f5_short_overlay_scale": contract["f5_short_overlay_scale"],
            "unstable_long_route": contract["unstable_long_route"],
            "unstable_long_route_overlay_scale": contract[
                "unstable_long_route_overlay_scale"
            ],
            "signals_suppressed": False,
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "single_position_busy": True,
            "structural_rearm": True,
            "max_lifecycle": "24H",
        },
        "consumed_5y_result": {
            "trades": EXPECTED_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_PF,
            "max_drawdown_scaled_r": EXPECTED_DD,
            "total_scaled_net_010_r": EXPECTED_TOTAL,
            "positive_annual_blocks": int(result["positive_annual_blocks"]),
        },
        "next_stage": {
            "required": "FINAL_ROBUSTNESS_WFO_MC_STRESS",
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
        raise SystemExit("usage: module R38_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
