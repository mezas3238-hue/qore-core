"""Freeze the exact GBPUSD R43 five-year passing candidate."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_GBPUSD_R43_5Y_CANDIDATE_001"
SOURCE_RUN_ID = 35357443440
SOURCE_ARTIFACT_ID = 10552052483
SOURCE_ARTIFACT_DIGEST = (
    "sha256:1157e9e3079d46e04d541744c012f75cc5405cb0e299d593622ab11777b9308f"
)
SOURCE_GIT_SHA = "2748596bd132e6577e87851849a338b9a7a9c42e"
SOURCE_REPORT_SHA256 = (
    "39df0bb2984e8ad9e62b7eac0cf4f716ae88f0d0f9e7c81173965e037e48cbe0"
)
SOURCE_TRADES_SHA256 = (
    "4af1c2977b2b80437f1a58436efa4967fec09d0d8968946e41f41f5c9db1025e"
)

EXPECTED_TRADES = 907
EXPECTED_PF = "1.713624514596208498825398640"
EXPECTED_DD = "4.401231922815307849576052766"
EXPECTED_TOTAL = "35.40396721533287699752413575"
EXPECTED_POSITIVE_ANNUAL_BLOCKS = 5
EXPECTED_POLICY = "R43_RANK2_025"
EXPECTED_SHORT_SCALE = "0.005"
EXPECTED_RANK2_SCALE = "0.25"


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, got {len(matches)}")
    return matches[0]


def freeze(source_root: Path, output: Path) -> dict[str, Any]:
    report_path = _single(source_root, "r43-rank2-fragility-correction-report.json")
    trades_path = _single(source_root, "r43-5y-corrected-trades.jsonl")
    git_path = _single(source_root, "git-sha.txt")

    if hashlib.sha256(report_path.read_bytes()).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R43 report hash drift")
    if hashlib.sha256(trades_path.read_bytes()).hexdigest() != SOURCE_TRADES_SHA256:
        raise ValueError("R43 trades hash drift")
    if git_path.read_text().strip() != SOURCE_GIT_SHA:
        raise ValueError("R43 git binding drift")

    report = json.loads(report_path.read_text())
    if report["identity"] != "TURTLE_SOUP_GBPUSD_R43_RANK2_FRAGILITY_CORRECTION_V1":
        raise ValueError("unexpected R43 identity")
    selected = report["selected"]
    if selected is None or selected["acceptance_pass"] is not True:
        raise ValueError("R43 has no accepted candidate")
    if selected["policy"] != EXPECTED_POLICY:
        raise ValueError("policy drift")
    if selected["short_scale"] != EXPECTED_SHORT_SCALE:
        raise ValueError("SHORT scale drift")
    if selected["rank2_scale"] != EXPECTED_RANK2_SCALE:
        raise ValueError("rank2 scale drift")
    stats = selected["stats"]
    if int(stats["trades"]) != EXPECTED_TRADES:
        raise ValueError("trade count drift")
    if str(stats["profit_factor"]) != EXPECTED_PF:
        raise ValueError("PF drift")
    if str(stats["max_drawdown_r"]) != EXPECTED_DD:
        raise ValueError("DD drift")
    if str(stats["total_r"]) != EXPECTED_TOTAL:
        raise ValueError("total-R drift")
    if int(selected["positive_annual_blocks"]) != EXPECTED_POSITIVE_ANNUAL_BLOCKS:
        raise ValueError("annual stability drift")
    if any(not bool(block["positive_total"]) for block in selected["annual_blocks"]):
        raise ValueError("all 5 annual blocks must be positive")

    contract = report["correction_contract"]
    if contract["signals_suppressed"] is not False:
        raise ValueError("signals were suppressed")
    if contract["all_907_trades_preserved"] is not True:
        raise ValueError("trade preservation drift")
    if contract["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout drift")

    manifest: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpusd.r44_candidate_freeze.v1",
        "identity": IDENTITY,
        "status": "FROZEN_FOR_FINAL_ROBUSTNESS",
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
            "trades_sha256": SOURCE_TRADES_SHA256,
        },
        "frozen_contract": {
            "source_candidate": "TURTLE_SOUP_GBPUSD_R43_RANK2_FRAGILITY_CORRECTION_V1",
            "policy": EXPECTED_POLICY,
            "short_scale": EXPECTED_SHORT_SCALE,
            "rank2_scale": EXPECTED_RANK2_SCALE,
            "signals_suppressed": False,
            "all_907_trades_preserved": True,
            "calendar_time_used_as_rule": False,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
        },
        "consumed_5y_result": {
            "trades": EXPECTED_TRADES,
            "profit_factor": EXPECTED_PF,
            "max_drawdown_r": EXPECTED_DD,
            "total_r": EXPECTED_TOTAL,
            "positive_annual_blocks": EXPECTED_POSITIVE_ANNUAL_BLOCKS,
        },
        "next_stage": {
            "required": "FINAL_WFO_MC_FRICTION_SLIPPAGE_LOYO_ROBUSTNESS",
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
    (output / "r44-candidate-freeze-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R43_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(freeze(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
