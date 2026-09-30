#!/usr/bin/env python3
"""One-shot consumed R5 replication for frozen STI-8 V1.

This wrapper deliberately reuses the exact evaluator from
shared_sti6_sti8_real_position_intelligence.py. It does not fit thresholds,
alter the engine, or inspect R5 before invoking the frozen evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import shared_sti6_sti8_real_position_intelligence as base

IDENTITY = "QORE_SHARED_STI8_R5_REPLICATION_V1"
SCHEMA = "qore.shared.sti8.r5_replication.v1"
EXPECTED_SOURCE_SHA = "711788d89521e051ab3969a9006830068381693e"
EXPECTED_POLICY_ARTIFACT_ID = 11065709899
EXPECTED_POLICY_ARTIFACT_DIGEST = (
    "sha256:10c9941d119878159dfe10ae57997ebe18d638c0fcde07cb5bed176e5a18a415"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    *,
    frozen_policy_path: Path,
    r5_trades: Path,
    r5_nas: Path,
    r5_sp: Path,
    r5_us: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-6/STI-8 policy identity")
    if frozen.get("mode") != "SOURCE_ONLY_POLICY_FREEZE":
        raise ValueError("R5 replication requires source-only frozen policy")
    if frozen.get("future_trade_outcomes_read_for_freeze") is not False:
        raise ValueError("frozen policy is not outcome-clean")
    if frozen.get("r5_opened") is not False:
        raise ValueError("upstream policy artifact already claims R5 opened")
    if frozen.get("protected_holdout_opened") is not False:
        raise ValueError("protected holdout contamination detected")

    evaluation = base.evaluate(
        frozen=frozen,
        r6_trades=r5_trades,
        r6_nas=r5_nas,
        r6_sp=r5_sp,
        r6_us=r5_us,
    )
    sti8 = evaluation["sti8"]
    if not isinstance(sti8, dict):
        raise TypeError("STI-8 evaluation payload malformed")

    replication_pass = bool(sti8["gate_pass"])
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "replication_partition": "r5",
        "frozen_source_sha": EXPECTED_SOURCE_SHA,
        "frozen_policy_artifact_id": EXPECTED_POLICY_ARTIFACT_ID,
        "frozen_policy_artifact_digest": EXPECTED_POLICY_ARTIFACT_DIGEST,
        "frozen_policy_file_sha256": _sha256(frozen_policy_path),
        "sti8_policy_fingerprint": frozen["sti8_policy_fingerprint"],
        "engine_state": (
            "EXACT_FROZEN_ENGINE_REPLAYED_ON_CONSUMED_R5"
        ),
        "replication_status": (
            "STI8_V1_REPLICATION_PASS_R5"
            if replication_pass
            else "STI8_V1_REPLICATION_FALSIFIED_R5"
        ),
        "replication_pass": replication_pass,
        "r5_trade_count": evaluation["r6_trade_count"],
        "r5_source_observation_count": evaluation[
            "r6_source_observation_count"
        ],
        "outcome_population": evaluation["outcome_population"],
        "sti8": {
            "loss_precision_bps": sti8["loss_precision_bps"],
            "loss_recall_bps": sti8["loss_recall_bps"],
            "false_threat_on_nonlosses_bps": (
                sti8["false_threat_on_nonlosses_bps"]
            ),
            "missed_loss_bps": sti8["missed_loss_bps"],
            "median_true_threat_lead_minutes": (
                sti8["median_true_threat_lead_minutes"]
            ),
            "gate_pass": replication_pass,
            "economic_position_management_value_proven": False,
        },
        "frozen_gates": {
            key: value
            for key, value in evaluation["frozen_gates"].items()
            if key.startswith("sti8_")
        },
        "engine_or_policy_retuned_after_r6": False,
        "r5_used_for_threshold_fit": False,
        "future_data_used_for_intelligence": False,
        "terminal_outcome_used_offline_for_evaluation": True,
        "protected_certification_holdout_opened": False,
        "economic_position_management_value_proven": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--r5-trades", type=Path, required=True)
    parser.add_argument("--r5-nas", type=Path, required=True)
    parser.add_argument("--r5-sp", type=Path, required=True)
    parser.add_argument("--r5-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        frozen_policy_path=args.policy,
        r5_trades=args.r5_trades,
        r5_nas=args.r5_nas,
        r5_sp=args.r5_sp,
        r5_us=args.r5_us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "replication_status": payload["replication_status"],
                "replication_pass": payload["replication_pass"],
                "sti8": payload["sti8"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
