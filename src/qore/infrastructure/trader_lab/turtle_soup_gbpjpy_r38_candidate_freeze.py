"""Freeze the exact passing GBPJPY R38 corrected candidate."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_GBPJPY_R38_STRUCTURAL_FRAGILITY_CANDIDATE_001"
SOURCE_IDENTITY = "TURTLE_SOUP_GBPJPY_R38_5Y_STRUCTURAL_FRAGILITY_CORRECTION_V1"
SOURCE_RUN_ID = 35373705221
SOURCE_ARTIFACT_ID = 10559845896
SOURCE_ARTIFACT_DIGEST = (
    "sha256:862bd7951806e17d62dddafb800ac18f19a600b5b9dfcb7b16bc79703ca1fd1f"
)
SOURCE_GIT_SHA = "93b887a257bef65b151983501d7d0017795f1040"
SOURCE_REPORT_SHA256 = (
    "9e0d30d4ba6553439ec675077e05c1579a65b6c32476ac0b616427f0663c802c"
)
SOURCE_TRADES_SHA256 = (
    "0021b69adf8862178915b68c5208bc9b409b533c8a123e35642443bbad257e8c"
)

EXPECTED_TRADES = 897
EXPECTED_PF = "1.852918712035185462516517131"
EXPECTED_DD = "5.06150896610739539086014902"
EXPECTED_TOTAL = "92.83988286566161467727272231"
EXPECTED_POSITIVE_ANNUAL_BLOCKS = 5

EXPECTED_2Y_TRADES = 371
EXPECTED_2Y_PF = "2.217710737671459829306457352"
EXPECTED_2Y_DD = "3.25486421385985457309113347"
EXPECTED_2Y_TOTAL = "44.91758149029640653742711557"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(
        source_root,
        "r38-5y-structural-fragility-correction-report.json",
    )
    trades_path = _single(source_root, "r38-5y-corrected-trades.jsonl")
    report_bytes = report_path.read_bytes()
    trades_bytes = trades_path.read_bytes()

    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R38 report hash drift")
    if hashlib.sha256(trades_bytes).hexdigest() != SOURCE_TRADES_SHA256:
        raise ValueError("R38 trade-ledger hash drift")

    report = json.loads(report_bytes)
    if report["identity"] != SOURCE_IDENTITY:
        raise ValueError("R38 identity drift")

    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R38 git binding drift")

    result = report["result_5y"]
    result_2y = report["result_2y_recheck"]
    if result["acceptance_pass"] is not True:
        raise ValueError("R38 5Y did not pass")
    if result_2y["acceptance_pass"] is not True:
        raise ValueError("R38 2Y recheck did not pass")
    if report["decision"]["eligible_for_final_freeze"] is not True:
        raise ValueError("R38 is not eligible for final freeze")

    expected = {
        "trades": (int(result["trades"]), EXPECTED_TRADES),
        "pf": (str(result["profit_factor_scaled_net_010"]), EXPECTED_PF),
        "dd": (str(result["max_drawdown_r"]), EXPECTED_DD),
        "total": (str(result["total_scaled_net_010_r"]), EXPECTED_TOTAL),
        "positive_annual_blocks": (
            int(result["positive_annual_blocks"]),
            EXPECTED_POSITIVE_ANNUAL_BLOCKS,
        ),
        "2y_trades": (int(result_2y["trades"]), EXPECTED_2Y_TRADES),
        "2y_pf": (str(result_2y["profit_factor_scaled_net_010"]), EXPECTED_2Y_PF),
        "2y_dd": (str(result_2y["max_drawdown_r"]), EXPECTED_2Y_DD),
        "2y_total": (str(result_2y["total_scaled_net_010_r"]), EXPECTED_2Y_TOTAL),
    }
    for name, (actual, wanted) in expected.items():
        if actual != wanted:
            raise ValueError(f"{name} drift: {actual!r} != {wanted!r}")

    contract = report["correction_contract"]
    if contract["signal_count_preserved"] is not True:
        raise ValueError("signal count was not preserved")
    if contract["signals_suppressed"] is not False:
        raise ValueError("signal suppression drift")
    if contract["risk_only_nonzero_scaling"] is not True:
        raise ValueError("R38 is not a risk-only correction")
    if report["decision"]["fresh_holdout_status"] != "SEALED_UNTOUCHED":
        raise ValueError("fresh holdout seal drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpjpy.r38_candidate_freeze.v1",
        "identity": IDENTITY,
        "status": "FROZEN_FOR_FINAL_ROBUSTNESS",
        "source": {
            "identity": SOURCE_IDENTITY,
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
            "trades_sha256": SOURCE_TRADES_SHA256,
        },
        "frozen_contract": {
            "r36_signal_contract_preserved": True,
            "signals_suppressed": False,
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "dol": "REAL_ACTIVE_CIBO_DOL",
            "stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "single_position_busy": True,
            "structural_rearm": True,
            "risk_overlay_only": True,
            "gbpjpy_specific_fragility_flags": contract[
                "gbpjpy_specific_fragility_flags"
            ],
            "fragility_policy_0_1_2_3plus": contract[
                "fragility_policy_0_1_2_3plus"
            ],
        },
        "consumed_5y_result": {
            "trades": EXPECTED_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_PF,
            "max_drawdown_scaled_r": EXPECTED_DD,
            "total_scaled_net_010_r": EXPECTED_TOTAL,
            "positive_annual_blocks": EXPECTED_POSITIVE_ANNUAL_BLOCKS,
        },
        "consumed_2y_recheck": {
            "trades": EXPECTED_2Y_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_2Y_PF,
            "max_drawdown_scaled_r": EXPECTED_2Y_DD,
            "total_scaled_net_010_r": EXPECTED_2Y_TOTAL,
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
