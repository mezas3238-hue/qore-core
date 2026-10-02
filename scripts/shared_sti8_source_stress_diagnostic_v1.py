#!/usr/bin/env python3
"""Source-evidence stress diagnostics for frozen STI-8 V1.

All stresses are preregistered deterministic perturbations of source-time
observations. The frozen policy and threat engine are reused unchanged.
Consumed R6/R5 outcomes are attached only after threat outputs are created.
This is robustness evidence, not fresh OOS evidence.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import replace
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

IDENTITY = "QORE_SHARED_STI8_SOURCE_STRESS_DIAGNOSTIC_V1"

StressFn = Callable[[SharedPositionCausalObservation], SharedPositionCausalObservation]


def _clip(value: int) -> int:
    return max(0, min(10_000, value))


def _identity(obs: SharedPositionCausalObservation) -> SharedPositionCausalObservation:
    return obs


def _world_support_minus_1000(
    obs: SharedPositionCausalObservation,
) -> SharedPositionCausalObservation:
    return replace(obs, world_support_bps=_clip(obs.world_support_bps - 1_000))


def _world_fragility_plus_1000(
    obs: SharedPositionCausalObservation,
) -> SharedPositionCausalObservation:
    return replace(obs, world_fragility_bps=_clip(obs.world_fragility_bps + 1_000))


def _peer_adverse_plus_1000(
    obs: SharedPositionCausalObservation,
) -> SharedPositionCausalObservation:
    return replace(
        obs,
        peer_transition_adverse_bps=_clip(
            obs.peer_transition_adverse_bps + 1_000
        ),
    )


def _cross_asset_stress(
    obs: SharedPositionCausalObservation,
) -> SharedPositionCausalObservation:
    return replace(
        obs,
        peer_confirmation_bps=_clip(obs.peer_confirmation_bps - 1_000),
        breadth_bps=_clip(obs.breadth_bps - 1_000),
        peer_transition_adverse_bps=_clip(
            obs.peer_transition_adverse_bps + 1_000
        ),
        world_support_bps=_clip(obs.world_support_bps - 1_000),
        world_fragility_bps=_clip(obs.world_fragility_bps + 1_000),
    )


def _integrity_below_gate(
    obs: SharedPositionCausalObservation,
) -> SharedPositionCausalObservation:
    return replace(obs, data_integrity_bps=9_400)


STRESSES: tuple[tuple[str, StressFn], ...] = (
    ("BASELINE", _identity),
    ("WORLD_SUPPORT_MINUS_1000", _world_support_minus_1000),
    ("WORLD_FRAGILITY_PLUS_1000", _world_fragility_plus_1000),
    ("PEER_TRANSITION_ADVERSE_PLUS_1000", _peer_adverse_plus_1000),
    ("CROSS_ASSET_STRESS_COMBINED", _cross_asset_stress),
    ("DATA_INTEGRITY_BELOW_GATE", _integrity_below_gate),
)


def _ratio_bps(numerator: int, denominator: int) -> int:
    return 0 if denominator <= 0 else numerator * 10_000 // denominator


def _evaluate_partition(
    *,
    partition: str,
    frozen: dict[str, object],
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
) -> dict[str, object]:
    policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades,
        nas_path=nas,
        sp_path=sp,
        us_path=us,
    )
    results: list[dict[str, object]] = []

    for stress_name, stress_fn in STRESSES:
        tp = fp = fn = 0
        signals = losses = 0
        leads: list[int] = []
        insufficient_count = 0

        for sequence in sequences:
            row = cast(dict[str, object], sequence["row"])
            observations = cast(
                tuple[SharedPositionCausalObservation, ...],
                sequence["observations"],
            )
            stressed = tuple(stress_fn(obs) for obs in observations)

            first_threat = None
            for index, observation in enumerate(stressed):
                assessment = assess_position_threat(observation, policy=policy)
                if assessment.threat_level.value == "INSUFFICIENT":
                    insufficient_count += 1
                if (
                    first_threat is None
                    and assessment.threat_level in base.THREAT_LEVELS
                ):
                    first_threat = index

            # Outcome touched only after all stressed source-time assessments exist.
            final_r = Decimal(str(row["net_r_after_friction"]))
            is_loss = final_r < 0
            losses += int(is_loss)
            signal = first_threat is not None
            signals += int(signal)

            if signal and is_loss:
                tp += 1
                leads.append(len(stressed) - 1 - cast(int, first_threat))
            elif signal and not is_loss:
                fp += 1
            elif not signal and is_loss:
                fn += 1

        precision = _ratio_bps(tp, tp + fp)
        recall = _ratio_bps(tp, tp + fn)
        false_threat = _ratio_bps(fp, tp + fp)
        missed_loss = _ratio_bps(fn, tp + fn)
        gate = (
            precision >= base.STI8_MIN_PRECISION_BPS
            and recall >= base.STI8_MIN_RECALL_BPS
            and false_threat <= base.STI8_MAX_FALSE_THREAT_ON_WINNERS_BPS
            and missed_loss <= base.STI8_MAX_MISSED_LOSS_BPS
        )
        results.append(
            {
                "stress": stress_name,
                "trade_count": len(sequences),
                "loss_count": losses,
                "threat_signal_count": signals,
                "loss_precision_bps": precision,
                "loss_recall_bps": recall,
                "false_threat_on_nonlosses_bps": false_threat,
                "missed_loss_bps": missed_loss,
                "median_true_threat_lead_minutes": (
                    None if not leads else median(leads)
                ),
                "insufficient_assessment_count": insufficient_count,
                "frozen_gate_pass": gate,
            }
        )

    baseline = next(row for row in results if row["stress"] == "BASELINE")
    return {
        "partition": partition,
        "stress_count": len(results),
        "baseline_reproduced": bool(baseline["frozen_gate_pass"]),
        "stress_results": results,
    }


def run(
    *,
    frozen_policy: Path,
    r6_trades: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    r5_trades: Path,
    r5_nas: Path,
    r5_sp: Path,
    r5_us: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected STI-8 frozen policy identity")
    if frozen.get("sti8_policy_fingerprint") is None:
        raise ValueError("missing STI-8 policy fingerprint")

    partitions = {
        "r6": _evaluate_partition(
            partition="r6",
            frozen=frozen,
            trades=r6_trades,
            nas=r6_nas,
            sp=r6_sp,
            us=r6_us,
        ),
        "r5": _evaluate_partition(
            partition="r5",
            frozen=frozen,
            trades=r5_trades,
            nas=r5_nas,
            sp=r5_sp,
            us=r5_us,
        ),
    }
    non_integrity_stresses = {
        row["stress"]
        for row in partitions["r6"]["stress_results"]
        if row["stress"] not in {"BASELINE", "DATA_INTEGRITY_BELOW_GATE"}
    }
    robust = all(
        bool(row["frozen_gate_pass"])
        for partition in partitions.values()
        for row in cast(list[dict[str, object]], partition["stress_results"])
        if row["stress"] in non_integrity_stresses
    )
    integrity_fail_closed = all(
        int(row["threat_signal_count"]) == 0
        and int(row["insufficient_assessment_count"]) > 0
        for partition in partitions.values()
        for row in cast(list[dict[str, object]], partition["stress_results"])
        if row["stress"] == "DATA_INTEGRITY_BELOW_GATE"
    )
    return {
        "identity": IDENTITY,
        "mode": "CONSUMED_SOURCE_EVIDENCE_STRESS_DIAGNOSTIC",
        "frozen_source_engine_sha": (
            "711788d89521e051ab3969a9006830068381693e"
        ),
        "sti8_policy_fingerprint": frozen["sti8_policy_fingerprint"],
        "stress_definitions_frozen_in_code": True,
        "partitions": partitions,
        "all_non_integrity_stresses_pass_frozen_gate": robust,
        "data_integrity_stress_fails_closed": integrity_fail_closed,
        "stress_is_fresh_oos": False,
        "engine_or_threshold_retuning_used": False,
        "outcome_used_to_define_stresses": False,
        "future_data_used_for_intelligence": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-trades", type=Path, required=True)
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        frozen_policy=args.policy,
        r6_trades=args.r6_trades,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        r5_trades=args.r5_trades,
        r5_nas=args.r5_nas,
        r5_sp=args.r5_sp,
        r5_us=args.r5_us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
