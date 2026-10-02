"""VT31 Shared temporal-stable tail hypothesis V13.

V12 proved that an N1 winner-tail model can pass every hard gate on R8 but its
feature evidence is not temporally stable enough on R6. V13 therefore keeps the
same causal decision-time facts and only retains feature-value evidence whose
winner/loss direction agrees across R8 discovery and R6 calibration.

R6 is explicitly a consumed calibration fold. Its outcomes are used only
offline to reject unstable feature relationships and freeze conservative
likelihood magnitudes. R5 remains unopened unless one frozen configuration
passes every hard gate on both R8 and R6. Runtime decisions use current-market
facts only; no exact-state lookup, nearest-neighbour lookup, future bars,
current outcome, sizing or capital weighting is used.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_n1_conditional_hypothesis_v12 as v12
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8

SCHEMA = "qore.core_stack_v4.vt31.temporal_stable_tail_hypothesis.v13"
IDENTITY = "VT31_NAS100_SHARED_TEMPORAL_STABLE_TAIL_HYPOTHESIS_V13"


@dataclass(frozen=True, slots=True)
class Stability:
    minimum_examples_each_fold: int
    minimum_abs_log_lr_each_fold: float

    def payload(self) -> dict[str, object]:
        return {
            "minimum_examples_each_fold": self.minimum_examples_each_fold,
            "minimum_abs_log_lr_each_fold": self.minimum_abs_log_lr_each_fold,
            "same_sign_required": True,
            "magnitude_rule": "MIN_ABS_ACROSS_R8_R6",
        }


STABILITIES = tuple(
    Stability(minimum_examples_each_fold=n, minimum_abs_log_lr_each_fold=lr)
    for n in (1, 2, 3, 4)
    for lr in (0.0, 0.10, 0.20, 0.35)
)

POLICIES = tuple(
    v12.Policy(
        score_threshold=threshold,
        minimum_supportive_channels=min_support,
        maximum_adverse_channels=max_adverse,
        rescue_n2_threshold=None,
    )
    for threshold in (-0.50, 0.0, 0.50, 1.0, 1.50, 2.0, 2.50)
    for min_support in (1, 2, 3)
    for max_adverse in (1, 2, 3, 5)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _diag_index(
    diagnostics: dict[str, object],
) -> dict[str, dict[str, dict[str, dict[str, object]]]]:
    indexed: dict[str, dict[str, dict[str, dict[str, object]]]] = {}
    for channel, fields_raw in diagnostics.items():
        fields = cast(dict[str, object], fields_raw)
        indexed[channel] = {}
        for field, entries_raw in fields.items():
            entries = cast(list[dict[str, object]], entries_raw)
            indexed[channel][field] = {
                str(entry["value"]): entry for entry in entries
            }
    return indexed


def _stable_model(
    r8_n1: list[dict[str, object]],
    r6_n1: list[dict[str, object]],
    stability: Stability,
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, object]]:
    _, d8 = v12._learn_feature_models(r8_n1)
    _, d6 = v12._learn_feature_models(r6_n1)
    i8 = _diag_index(cast(dict[str, object], d8))
    i6 = _diag_index(cast(dict[str, object], d6))

    model: dict[str, dict[str, dict[str, float]]] = {}
    kept: list[dict[str, object]] = []
    rejected: dict[str, int] = {
        "missing_other_fold": 0,
        "insufficient_examples": 0,
        "weak_magnitude": 0,
        "sign_instability": 0,
    }
    by_channel: dict[str, int] = {}

    for channel, fields in v12.CHANNELS.items():
        model[channel] = {}
        by_channel[channel] = 0
        for field in fields:
            model[channel][field] = {}
            values = set(i8.get(channel, {}).get(field, {})) | set(
                i6.get(channel, {}).get(field, {})
            )
            for value in sorted(values):
                e8 = i8.get(channel, {}).get(field, {}).get(value)
                e6 = i6.get(channel, {}).get(field, {}).get(value)
                if e8 is None or e6 is None:
                    rejected["missing_other_fold"] += 1
                    continue
                n8 = int(e8["wins"]) + int(e8["losses"])
                n6 = int(e6["wins"]) + int(e6["losses"])
                if min(n8, n6) < stability.minimum_examples_each_fold:
                    rejected["insufficient_examples"] += 1
                    continue
                lr8 = float(e8["log_likelihood_ratio"])
                lr6 = float(e6["log_likelihood_ratio"])
                if (
                    abs(lr8) < stability.minimum_abs_log_lr_each_fold
                    or abs(lr6) < stability.minimum_abs_log_lr_each_fold
                ):
                    rejected["weak_magnitude"] += 1
                    continue
                if lr8 == 0.0 or lr6 == 0.0 or math.copysign(1.0, lr8) != math.copysign(1.0, lr6):
                    rejected["sign_instability"] += 1
                    continue
                score = math.copysign(min(abs(lr8), abs(lr6)), lr8)
                model[channel][field][value] = score
                by_channel[channel] += 1
                kept.append(
                    {
                        "channel": channel,
                        "field": field,
                        "value": value,
                        "r8_examples": n8,
                        "r6_examples": n6,
                        "r8_log_lr": lr8,
                        "r6_log_lr": lr6,
                        "stable_log_lr": score,
                    }
                )

    kept.sort(key=lambda row: abs(float(row["stable_log_lr"])), reverse=True)
    return model, {
        "stability": stability.payload(),
        "stable_value_count": len(kept),
        "stable_values_by_channel": by_channel,
        "stable_values": kept,
        "rejected": rejected,
    }


def _load_rows(
    *,
    trades: Path,
    raw: Path,
    daily: object,
) -> list[dict[str, object]]:
    return [
        v12._decorate(row)
        for row in v8._sequence_rows(
            raw,
            v2.v3._decorate(v2.v3._load_trades(trades), daily),
        )
    ]


def _gate_count(gates: dict[str, bool]) -> int:
    return sum(bool(value) for value in gates.values())


def _candidate_score(
    r8_result: dict[str, object],
    r6_result: dict[str, object],
) -> Decimal | None:
    s8 = v12._score(r8_result)
    s6 = v12._score(r6_result)
    if s8 is None or s6 is None:
        return None
    return min(s8, s6)


def _compact(
    *,
    stability: Stability,
    policy: v12.Policy,
    model_diag: dict[str, object],
    r8_result: dict[str, object],
    r6_result: dict[str, object],
) -> dict[str, object]:
    g8 = v12._gates(r8_result)
    g6 = v12._gates(r6_result)
    score = _candidate_score(r8_result, r6_result)
    return {
        "stability": stability.payload(),
        "policy": policy.payload(),
        "stable_value_count": model_diag["stable_value_count"],
        "r8": {
            "result": r8_result,
            "gates": g8,
            "gate_count": _gate_count(g8),
        },
        "r6": {
            "result": r6_result,
            "gates": g6,
            "gate_count": _gate_count(g6),
        },
        "joint_score": None if score is None else format(score, "f"),
    }


def _governance() -> dict[str, bool]:
    return {
        "present_market_hypothesis_primary": True,
        "r8_outcomes_used_for_offline_discovery": True,
        "r6_outcomes_used_for_offline_stability_calibration": True,
        "r5_outcomes_used_for_model_or_policy": False,
        "negative_memory_secondary_screen": True,
        "runtime_exact_state_lookup_used": False,
        "runtime_nearest_neighbor_used": False,
        "runtime_current_outcome_used": False,
        "future_m1_used": False,
        "r5_retuned": False,
        "capital_risk_weighting_used": False,
        "methodology_modified": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
        "live_authorized": False,
        "merge_authorized": False,
    }


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r5_trades: Path,
    r8_raw: Path,
    r6_raw: Path,
    r5_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = _load_rows(trades=r8_trades, raw=r8_raw, daily=daily)
    r6 = _load_rows(trades=r6_trades, raw=r6_raw, daily=daily)
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    r8_n1 = v12._n1_rows(r8, negative)
    r6_n1 = v12._n1_rows(r6, negative)

    frontier: list[dict[str, object]] = []
    passing: list[
        tuple[
            Decimal,
            Stability,
            v12.Policy,
            dict[str, dict[str, dict[str, float]]],
            dict[str, object],
            dict[str, object],
            dict[str, object],
        ]
    ] = []

    for stability in STABILITIES:
        model, model_diag = _stable_model(r8_n1, r6_n1, stability)
        if int(model_diag["stable_value_count"]) == 0:
            continue
        for policy in POLICIES:
            r8_result = v12._evaluate(r8, negative=negative, model=model, policy=policy)
            r6_result = v12._evaluate(r6, negative=negative, model=model, policy=policy)
            row = _compact(
                stability=stability,
                policy=policy,
                model_diag=model_diag,
                r8_result=r8_result,
                r6_result=r6_result,
            )
            frontier.append(row)
            score = _candidate_score(r8_result, r6_result)
            if score is not None:
                passing.append(
                    (
                        score,
                        stability,
                        policy,
                        model,
                        model_diag,
                        r8_result,
                        r6_result,
                    )
                )

    frontier.sort(
        key=lambda row: (
            int(cast(dict[str, object], row["r8"])["gate_count"])
            + int(cast(dict[str, object], row["r6"])["gate_count"]),
            min(
                int(cast(dict[str, object], row["r8"])["gate_count"]),
                int(cast(dict[str, object], row["r6"])["gate_count"]),
            ),
            -int(row["stable_value_count"]),
        ),
        reverse=True,
    )
    passing.sort(key=lambda item: item[0], reverse=True)

    common = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge_set": {"r8": 228, "r6": 278, "r5": 316},
        "temporal_protocol": {
            "r8": "DISCOVERY",
            "r6": "CONSUMED_STABILITY_CALIBRATION_AND_FREEZE",
            "r5": "UNTOUCHED_NO_RETUNE_EVALUATION_ONLY_AFTER_R8_AND_R6_PASS",
        },
        "n1_population": {
            "r8": {
                "sample": len(r8_n1),
                "wins": sum(_d(row["net_r_after_friction"]) > 0 for row in r8_n1),
                "losses": sum(_d(row["net_r_after_friction"]) < 0 for row in r8_n1),
            },
            "r6": {
                "sample": len(r6_n1),
                "wins": sum(_d(row["net_r_after_friction"]) > 0 for row in r6_n1),
                "losses": sum(_d(row["net_r_after_friction"]) < 0 for row in r6_n1),
            },
        },
        "frontier": frontier[:120],
        "governance": _governance(),
    }

    if not passing:
        return {
            **common,
            "economic_status": "FALSIFIED_BEFORE_R5",
            "r5_opened": False,
            "passes_temporal_stability": False,
            "frozen_policy": None,
            "calibration": None,
            "evaluation": None,
            "gates": None,
        }

    score, stability, policy, model, model_diag, r8_result, r6_result = passing[0]
    frozen = {
        "joint_score": format(score, "f"),
        "stability": stability.payload(),
        "policy": policy.payload(),
        "model": model,
        "model_diagnostics": model_diag,
    }

    r5 = _load_rows(trades=r5_trades, raw=r5_raw, daily=daily)
    if len(r5) != 316:
        raise AssertionError("VT31 R5 challenge-set drift")
    evaluation = v12._evaluate(r5, negative=negative, model=model, policy=policy)
    gates = v12._gates(evaluation)
    passed = all(gates.values())

    return {
        **common,
        "economic_status": "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "r5_opened": True,
        "passes_temporal_stability": passed,
        "frozen_policy": frozen,
        "calibration": {
            "r8": r8_result,
            "r8_gates": v12._gates(r8_result),
            "r6": r6_result,
            "r6_gates": v12._gates(r6_result),
        },
        "evaluation": evaluation,
        "gates": gates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r5-trades", type=Path, required=True)
    parser.add_argument("--r8-raw", type=Path, required=True)
    parser.add_argument("--r6-raw", type=Path, required=True)
    parser.add_argument("--r5-raw", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r5_trades=args.r5_trades,
        r8_raw=args.r8_raw,
        r6_raw=args.r6_raw,
        r5_raw=args.r5_raw,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "r5_opened": payload["r5_opened"],
                "passes_temporal_stability": payload["passes_temporal_stability"],
                "n1_population": payload["n1_population"],
                "frozen_policy": payload["frozen_policy"],
                "calibration": payload["calibration"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
