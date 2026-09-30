#!/usr/bin/env python3
"""Evaluate exact frozen STI-8 V1 on preregistered burnable research OOS.

The threat engine and R8-frozen policy are unchanged. The OOS partition label
is explicit so source-time provenance remains correct. Terminal outcomes are
touched only after the full causal threat sequence has been materialized.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    assess_position_threat,
)

IDENTITY = "QORE_SHARED_STI8_RESEARCH_OOS_V1"
PARTITION = "sti8_research_oos_v1"
EXPECTED_SOURCE_SHA = "711788d89521e051ab3969a9006830068381693e"
EXPECTED_POLICY_ARTIFACT_ID = 11065709899
EXPECTED_POLICY_ARTIFACT_DIGEST = (
    "sha256:10c9941d119878159dfe10ae57997ebe18d638c0fcde07cb5bed176e5a18a415"
)


def _ratio_bps(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def run(
    *,
    frozen_policy_path: Path,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-8 policy identity")
    if frozen.get("mode") != "SOURCE_ONLY_POLICY_FREEZE":
        raise ValueError("STI-8 OOS requires source-only frozen policy")
    if frozen.get("future_trade_outcomes_read_for_freeze") is not False:
        raise ValueError("frozen STI-8 policy is outcome contaminated")
    if frozen.get("protected_holdout_opened") is not False:
        raise ValueError("protected holdout contamination detected")

    policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition=PARTITION,
        trades_path=trades_path,
        nas_path=nas_path,
        sp_path=sp_path,
        us_path=us_path,
    )
    if not sequences:
        raise ValueError("STI-8 research OOS contains no methodology-valid trades")

    tp = fp = fn = tn = 0
    losses = winners_or_flats = 0
    signals = 0
    leads: list[int] = []
    source_observation_count = 0
    provenance_checked_count = 0

    materialized: list[
        tuple[
            dict[str, object],
            tuple[SharedPositionCausalObservation, ...],
            int | None,
        ]
    ] = []

    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(
            tuple[SharedPositionCausalObservation, ...],
            sequence["observations"],
        )
        source_observation_count += len(observations)

        first_threat: int | None = None
        for index, observation in enumerate(observations):
            if not any(
                ref.startswith(f"immutable-{PARTITION}-")
                for ref in observation.provenance_refs
            ):
                raise ValueError(
                    "STI-8 OOS source observation lost partition provenance"
                )
            provenance_checked_count += 1
            assessment = assess_position_threat(observation, policy=policy)
            if (
                first_threat is None
                and assessment.threat_level in base.THREAT_LEVELS
            ):
                first_threat = index

        # Seal source-time cognition before touching the terminal label.
        materialized.append((row, observations, first_threat))

    for row, observations, first_threat in materialized:
        final_r = Decimal(str(row["net_r_after_friction"]))
        is_loss = final_r < 0
        signal = first_threat is not None
        losses += int(is_loss)
        winners_or_flats += int(not is_loss)
        signals += int(signal)

        if signal and is_loss:
            tp += 1
            leads.append(len(observations) - 1 - cast(int, first_threat))
        elif signal and not is_loss:
            fp += 1
        elif not signal and is_loss:
            fn += 1
        else:
            tn += 1

    precision = _ratio_bps(tp, tp + fp)
    recall = _ratio_bps(tp, tp + fn)
    false_threat = _ratio_bps(fp, tp + fp)
    missed_loss = _ratio_bps(fn, tp + fn)
    gate_pass = (
        precision >= base.STI8_MIN_PRECISION_BPS
        and recall >= base.STI8_MIN_RECALL_BPS
        and false_threat <= base.STI8_MAX_FALSE_THREAT_ON_WINNERS_BPS
        and missed_loss <= base.STI8_MAX_MISSED_LOSS_BPS
    )

    return {
        "identity": IDENTITY,
        "mode": "PREREGISTERED_BURNABLE_RESEARCH_OOS",
        "partition": PARTITION,
        "frozen_source_sha": EXPECTED_SOURCE_SHA,
        "frozen_policy_artifact_id": EXPECTED_POLICY_ARTIFACT_ID,
        "frozen_policy_artifact_digest": EXPECTED_POLICY_ARTIFACT_DIGEST,
        "sti8_policy_fingerprint": frozen["sti8_policy_fingerprint"],
        "oos_status": (
            "STI8_V1_RESEARCH_OOS_PASS"
            if gate_pass
            else "STI8_V1_RESEARCH_OOS_FALSIFIED"
        ),
        "oos_pass": gate_pass,
        "trade_count": len(sequences),
        "source_observation_count": source_observation_count,
        "partition_provenance_checked_count": provenance_checked_count,
        "outcome_population": {
            "losses": losses,
            "nonlosses": winners_or_flats,
        },
        "confusion": {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
        },
        "metrics": {
            "loss_precision_bps": precision,
            "loss_recall_bps": recall,
            "false_threat_on_nonlosses_bps": false_threat,
            "missed_loss_bps": missed_loss,
            "median_true_threat_lead_minutes": (
                None if not leads else median(leads)
            ),
        },
        "frozen_gates": {
            "minimum_loss_precision_bps": base.STI8_MIN_PRECISION_BPS,
            "minimum_loss_recall_bps": base.STI8_MIN_RECALL_BPS,
            "maximum_false_threat_on_nonlosses_bps": (
                base.STI8_MAX_FALSE_THREAT_ON_WINNERS_BPS
            ),
            "maximum_missed_loss_bps": base.STI8_MAX_MISSED_LOSS_BPS,
        },
        "all_source_time_assessments_materialized_before_outcome_scoring": True,
        "engine_or_policy_retuned_after_r6_or_r5": False,
        "oos_used_for_threshold_fit": False,
        "future_data_used_for_intelligence": False,
        "terminal_outcome_used_offline_for_evaluation": True,
        "research_oos_burned_after_open": True,
        "protected_certification_holdout_opened": False,
        "economic_position_management_value_proven": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    parser.add_argument("--nas", type=Path, required=True)
    parser.add_argument("--sp", type=Path, required=True)
    parser.add_argument("--us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        frozen_policy_path=args.policy,
        trades_path=args.trades,
        nas_path=args.nas,
        sp_path=args.sp,
        us_path=args.us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "oos_status": payload["oos_status"],
                "oos_pass": payload["oos_pass"],
                "trade_count": payload["trade_count"],
                "metrics": payload["metrics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
