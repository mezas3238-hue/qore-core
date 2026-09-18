"""Freeze the exact passing AUDJPY R41 candidate for final robustness."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_AUDJPY_R42_FINAL_CANDIDATE_001"
SOURCE_IDENTITY = "TURTLE_SOUP_AUDJPY_R41_5Y_STRUCTURAL_FRAGILITY_CORRECTION_V1"
SOURCE_RUN_ID = 35399430491
SOURCE_ARTIFACT_ID = 10569333275
SOURCE_ARTIFACT_DIGEST = (
    "sha256:93492c9d0c982b008b108e9a6a8cd7596fe29cb6bdd59cb2880de808e624c4cf"
)
SOURCE_GIT_SHA = "2976255f2459a17603b0b9385b4c249a720463b8"
SOURCE_REPORT_SHA256 = (
    "e0c32f8fc7d8db9ba3d48391b2d488d65ebbcdbe8421c036f5b59234927f6656"
)
SOURCE_TRADES_SHA256 = (
    "a17501de87921c5095fa004600509a321454cfec6a83469e2e71d557cd31de7e"
)

EXPECTED_5Y_TRADES = 1039
EXPECTED_5Y_PF = "1.957251590510384151212372667"
EXPECTED_5Y_DD = "5.293573269867727808258117465"
EXPECTED_5Y_TOTAL = "68.02344279137424925740640205"
EXPECTED_POSITIVE_ANNUAL_BLOCKS = 5

EXPECTED_2Y_TRADES = 422
EXPECTED_2Y_PF = "2.316526174177060282046559780"
EXPECTED_2Y_DD = "3.13869363160529373642812201"
EXPECTED_2Y_TOTAL = "36.92087632902050211028936863"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(
        source_root,
        "r41-5y-structural-fragility-correction-report.json",
    )
    trades_path = _single(source_root, "r41-5y-corrected-trades.jsonl")
    report_bytes = report_path.read_bytes()
    trades_bytes = trades_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R41 report hash drift")
    if hashlib.sha256(trades_bytes).hexdigest() != SOURCE_TRADES_SHA256:
        raise ValueError("R41 ledger hash drift")

    report = json.loads(report_bytes)
    if report["identity"] != SOURCE_IDENTITY:
        raise ValueError("R41 identity drift")
    git_sha = _single(source_root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R41 git binding drift")
    if report["decision"]["eligible_for_final_freeze"] is not True:
        raise ValueError("R41 is not eligible for final freeze")
    if report["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout drift")

    result5 = report["result_5y"]
    result2 = report["result_2y"]
    expected = {
        "5y_trades": (int(result5["trades"]), EXPECTED_5Y_TRADES),
        "5y_pf": (str(result5["profit_factor_scaled_net_010"]), EXPECTED_5Y_PF),
        "5y_dd": (str(result5["max_drawdown_r"]), EXPECTED_5Y_DD),
        "5y_total": (str(result5["total_scaled_net_010_r"]), EXPECTED_5Y_TOTAL),
        "5y_positive_annual": (
            int(result5["positive_annual_blocks"]),
            EXPECTED_POSITIVE_ANNUAL_BLOCKS,
        ),
        "2y_trades": (int(result2["trades"]), EXPECTED_2Y_TRADES),
        "2y_pf": (str(result2["profit_factor_scaled_net_010"]), EXPECTED_2Y_PF),
        "2y_dd": (str(result2["max_drawdown_r"]), EXPECTED_2Y_DD),
        "2y_total": (str(result2["total_scaled_net_010_r"]), EXPECTED_2Y_TOTAL),
    }
    for name, (actual, wanted) in expected.items():
        if actual != wanted:
            raise ValueError(f"{name} drift: {actual!r} != {wanted!r}")

    contract = report["correction_contract"]
    if contract["signals_added"] is not False:
        raise ValueError("signal addition drift")
    if contract["signals_removed"] is not False:
        raise ValueError("signal removal drift")
    if contract["post_entry_information_used_for_risk"] is not False:
        raise ValueError("risk timing drift")
    if contract["pre_entry_context_only"] is not True:
        raise ValueError("pre-entry contract drift")
    if contract["risk_only_nonzero_scaling"] is not True:
        raise ValueError("nonzero risk contract drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_audjpy.r42_final_candidate_freeze.v1",
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
            "signals_added": False,
            "signals_removed": False,
            "pre_entry_context_only": True,
            "post_entry_information_used_for_risk": False,
            "risk_only_nonzero_scaling": True,
            "second_layer_fragility_flags": contract[
                "second_layer_fragility_flags"
            ],
            "second_layer_policy_0_1_2_3plus": contract[
                "second_layer_policy_0_1_2_3plus"
            ],
            "first_layer_risk_contract_changed": False,
            "entry": "NEXT_SOURCE_OPEN",
            "c2": "EXACT_SWEEP_AND_CLOSE_BACK_INSIDE",
            "cisd": "CAUSAL",
            "stop": "EXACT_PROTECTED_SWING_NEVER_WIDEN",
            "single_position_busy": True,
            "structural_rearm": True,
            "same_m5_bar": "STOP_FIRST",
        },
        "consumed_5y_result": {
            "trades": EXPECTED_5Y_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_5Y_PF,
            "max_drawdown_scaled_r": EXPECTED_5Y_DD,
            "total_scaled_net_010_r": EXPECTED_5Y_TOTAL,
            "positive_annual_blocks": EXPECTED_POSITIVE_ANNUAL_BLOCKS,
        },
        "consumed_2y_result": {
            "trades": EXPECTED_2Y_TRADES,
            "profit_factor_scaled_net_010": EXPECTED_2Y_PF,
            "max_drawdown_scaled_r": EXPECTED_2Y_DD,
            "total_scaled_net_010_r": EXPECTED_2Y_TOTAL,
        },
        "next_stage": {
            "required": "FINAL_ROBUSTNESS_WFO_MC_STRESS_LOYO",
            "rules_must_remain_frozen": True,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
        },
        "governance": {
            "candidate_frozen": True,
            "candidate_certified": False,
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
    (output / "r42-final-candidate-freeze-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R41_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
