"""Shared Perception-First Decision Intelligence V6 for VT31 NAS100.

V6 changes the authority of evidence:
CURRENT MARKET PERCEPTION -> situation confirmation/veto -> historical memory.

Historical memory may support a decision, but may not reject a trade by itself.
A current supportive state can rescue a historically negative setup. A current
contradictory state can add a rejection only when causal perception is strong.

No journey management, no capital weighting, no current/future outcome feature.
R8 -> perception-conditioned memory.
R6 -> calibration/freeze.
R5 -> no-retune evaluation.
"""
from __future__ import annotations

import argparse
import bisect
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_nas100_silver_bullet_native_streak_falsification_v1 as native

from qore.infrastructure.core_stack_v2.analog_memory import CausalAnalogMemory
from qore.infrastructure.core_stack_v2.perception import PerceptionVector, perceive

SCHEMA = "qore.core_stack_v3.vt31.perception_first.v6"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_FIRST_DECISION_V6"

PERCEPTION_FIELDS = (
    "side",
    "entry_family",
    "perception_trend",
    "perception_volatility",
    "perception_compression_expansion",
    "perception_displacement",
    "perception_sweep_recovery",
    "perception_cross_market",
    "perception_anomaly",
    "perception_contradiction_bucket",
    "perception_support_bucket",
)


@dataclass(frozen=True, slots=True)
class Policy:
    memory_policy: ev.Policy
    perception_contradiction_min: int
    severe_perception_min: int
    perception_rescue_support_min: int
    perception_rescue_max_contradictions: int
    perception_memory_conflict_ev: Decimal
    perception_memory_min_confidence_bps: int
    allow_perception_only_severe_reject: bool

    def payload(self) -> dict[str, object]:
        return {
            "memory_policy": self.memory_policy.payload(),
            "perception_contradiction_min": self.perception_contradiction_min,
            "severe_perception_min": self.severe_perception_min,
            "perception_rescue_support_min": self.perception_rescue_support_min,
            "perception_rescue_max_contradictions": (
                self.perception_rescue_max_contradictions
            ),
            "perception_memory_conflict_ev": format(
                self.perception_memory_conflict_ev, "f"
            ),
            "perception_memory_min_confidence_bps": (
                self.perception_memory_min_confidence_bps
            ),
            "allow_perception_only_severe_reject": (
                self.allow_perception_only_severe_reject
            ),
        }


MEMORY_POLICIES = (
    ev.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        conflict_ev_r=Decimal("-0.05"),
        favorable_ev_r=Decimal("0.30"),
        minimum_negative_views=2,
        caution_multiplier=Decimal("0.50"),
    ),
    ev.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        conflict_ev_r=Decimal("-0.10"),
        favorable_ev_r=Decimal("0.30"),
        minimum_negative_views=2,
        caution_multiplier=Decimal("0.50"),
    ),
)

POLICIES = tuple(
    Policy(
        memory_policy=memory,
        perception_contradiction_min=confirm,
        severe_perception_min=severe,
        perception_rescue_support_min=rescue,
        perception_rescue_max_contradictions=max_contra,
        perception_memory_conflict_ev=perception_ev,
        perception_memory_min_confidence_bps=confidence,
        allow_perception_only_severe_reject=allow_severe,
    )
    for memory in MEMORY_POLICIES
    for confirm in (1, 2, 3)
    for severe in (3, 4, 5)
    for rescue in (2, 3, 4)
    for max_contra in (0, 1)
    for perception_ev in (Decimal("-0.05"), Decimal("0"))
    for confidence in (1500, 2500)
    for allow_severe in (False, True)
)


class _BarIndex:
    def __init__(self, bars: tuple[object, ...]) -> None:
        self.bars = bars
        self.times = tuple(getattr(bar, "closed_at") for bar in bars)

    def between(self, start: object, end: object) -> tuple[object, ...]:
        left = bisect.bisect_left(self.times, start)
        right = bisect.bisect_right(self.times, end)
        return self.bars[left:right]


def _load_index(path: Path) -> _BarIndex:
    series, _, _, _, _, _ = native.load_market_evidence(path)
    ordered = tuple(
        sorted(series, key=lambda bar: getattr(bar, "closed_at"))
    )
    return _BarIndex(ordered)


def _bucket(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_plus"


def _perception_for(
    row: dict[str, object],
    *,
    nas: _BarIndex,
    sp500: _BarIndex,
    us30: _BarIndex,
) -> PerceptionVector:
    signal = v3._dt(row["signal_at"])
    raid = v3._dt(row["raid_at"])
    nas_recent = nas.between(signal - timedelta(minutes=10), signal)
    nas_prior = nas.between(
        signal - timedelta(minutes=30),
        signal - timedelta(minutes=5),
    )
    sweep = nas.between(raid, signal)
    sp_recent = sp500.between(signal - timedelta(minutes=10), signal)
    us_recent = us30.between(signal - timedelta(minutes=10), signal)
    return perceive(
        as_of=signal,
        side=str(row["side"]),
        reference_width=v3._d(row["reference_width"]),
        nas_recent=cast(tuple, nas_recent),
        nas_prior=cast(tuple, nas_prior),
        sweep_to_signal=cast(tuple, sweep),
        sp500_recent=cast(tuple, sp_recent),
        us30_recent=cast(tuple, us_recent),
    )


def _annotate(
    rows: list[dict[str, object]],
    *,
    nas_path: Path,
    sp500_path: Path,
    us30_path: Path,
) -> list[dict[str, object]]:
    nas = _load_index(nas_path)
    sp500 = _load_index(sp500_path)
    us30 = _load_index(us30_path)
    output: list[dict[str, object]] = []
    for source in rows:
        row = dict(source)
        view = _perception_for(row, nas=nas, sp500=sp500, us30=us30)
        row.update(
            {
                "perception_trend": view.trend_state.value,
                "perception_volatility": view.volatility_state.value,
                "perception_compression_expansion": (
                    view.compression_expansion_state.value
                ),
                "perception_displacement": view.displacement_state.value,
                "perception_sweep_recovery": view.sweep_recovery_state.value,
                "perception_cross_market": view.cross_market_state.value,
                "perception_anomaly": view.anomaly_state.value,
                "perception_contradiction_score": view.contradiction_score,
                "perception_support_score": view.support_score,
                "perception_contradiction_bucket": _bucket(
                    view.contradiction_score
                ),
                "perception_support_bucket": _bucket(view.support_score),
            }
        )
        output.append(row)
    return output


def _memories(
    rows: list[dict[str, object]],
) -> dict[str, CausalAnalogMemory]:
    memories = {
        name: ev._memory(rows, fields)
        for name, fields in ev.VIEWS.items()
    }
    memories["PERCEPTION"] = ev._memory(rows, PERCEPTION_FIELDS)
    return memories


def _historical_view(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    negatives = 0
    positives = 0
    weighted_ev = Decimal(0)
    weight_sum = Decimal(0)
    details: dict[str, object] = {}
    for name, fields in ev.VIEWS.items():
        item = ev._analog_economics(
            memories[name],
            row,
            fields,
            policy.memory_policy,
        )
        details[name] = item
        raw = item["ev_r"]
        if raw is None:
            continue
        confidence = int(item["confidence_bps"])
        effective_n = v3._d(item["effective_n"])
        if (
            confidence < policy.memory_policy.minimum_confidence_bps
            or effective_n < Decimal("6")
        ):
            continue
        value = v3._d(raw)
        weight = Decimal(confidence) / Decimal(10_000)
        weighted_ev += value * weight
        weight_sum += weight
        if value < policy.memory_policy.conflict_ev_r:
            negatives += 1
        if value >= policy.memory_policy.favorable_ev_r:
            positives += 1
    ensemble = None if weight_sum == 0 else weighted_ev / weight_sum
    return {
        "negative_views": negatives,
        "positive_views": positives,
        "ensemble_ev_r": (
            None if ensemble is None else format(ensemble, "f")
        ),
        "details": details,
    }


def _perception_memory_view(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    item = ev._analog_economics(
        memories["PERCEPTION"],
        row,
        PERCEPTION_FIELDS,
        policy.memory_policy,
    )
    raw = item["ev_r"]
    negative = (
        raw is not None
        and int(item["confidence_bps"])
        >= policy.perception_memory_min_confidence_bps
        and v3._d(item["effective_n"]) >= Decimal("4")
        and v3._d(raw) < policy.perception_memory_conflict_ev
    )
    return {**item, "negative": negative}


def _decide(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    current_contradictions = int(row["perception_contradiction_score"])
    current_support = int(row["perception_support_score"])
    historical = _historical_view(memories, row, policy)
    p_memory = _perception_memory_view(memories, row, policy)

    current_rescue = (
        current_support >= policy.perception_rescue_support_min
        and current_contradictions
        <= policy.perception_rescue_max_contradictions
    )
    historical_negative = (
        int(historical["negative_views"])
        >= policy.memory_policy.minimum_negative_views
        and int(historical["positive_views"]) == 0
    )
    perception_confirmed_memory_reject = (
        historical_negative
        and current_contradictions >= policy.perception_contradiction_min
    )
    situation_memory_reject = (
        bool(p_memory["negative"])
        and current_contradictions >= policy.perception_contradiction_min
    )
    severe_current_reject = (
        policy.allow_perception_only_severe_reject
        and current_contradictions >= policy.severe_perception_min
        and current_support == 0
    )

    reject = (
        perception_confirmed_memory_reject
        or situation_memory_reject
        or severe_current_reject
    )
    if current_rescue:
        reject = False

    return {
        "action": "ABSTAIN_SHADOW" if reject else "PASS",
        "current_rescue": current_rescue,
        "current_contradictions": current_contradictions,
        "current_support": current_support,
        "historical": historical,
        "perception_memory": p_memory,
        "reasons": {
            "perception_confirmed_memory_reject": (
                perception_confirmed_memory_reject
            ),
            "situation_memory_reject": situation_memory_reject,
            "severe_current_reject": severe_current_reject,
        },
    }


def _metrics(values: list[Decimal]) -> dict[str, object]:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    equity = peak = dd = Decimal(0)
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "profit_factor": (
            None if losses == 0 else format(gains / losses, "f")
        ),
        "total_r": format(total, "f"),
        "mean_r": (
            "0" if not values else format(total / Decimal(len(values)), "f")
        ),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _evaluate(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    memories = _memories(history)
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    reason_counts: dict[str, int] = {}
    rescue_count = 0

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = v3._d(row["net_r_after_friction"])
        baseline_values.append(value)
        verdict = _decide(memories, row, policy)
        if bool(verdict["current_rescue"]):
            rescue_count += 1
        for key, active in cast(
            dict[str, bool], verdict["reasons"]
        ).items():
            if active:
                reason_counts[key] = reason_counts.get(key, 0) + 1
        if verdict["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
        else:
            kept_values.append(value)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        v3._d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        v3._d(row["net_r_after_friction"]) > 0 for row in abstained
    )
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0),
        Decimal(0),
    )
    sacrificed_r = sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in abstained
            if v3._d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    return {
        "baseline": baseline,
        "shared": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if base_losses == 0
                else format(
                    Decimal(losses_avoided) / Decimal(base_losses), "f"
                )
            ),
            "winner_count_retention": (
                "0"
                if base_wins == 0
                else format(
                    Decimal(base_wins - winners_sacrificed)
                    / Decimal(base_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1"
                if gross_winner_r == 0
                else format(
                    (gross_winner_r - sacrificed_r) / gross_winner_r,
                    "f",
                )
            ),
            "density_retained": (
                "0"
                if not rows
                else format(
                    Decimal(len(kept_values)) / Decimal(len(rows)), "f"
                )
            ),
            "current_rescue_count": rescue_count,
            "reason_counts": dict(sorted(reason_counts.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    spf = v3._d(cast(object, shared["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    sdd = v3._d(shared["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "loss_recall_at_least_25pct": (
            v3._d(selection["loss_rejection_recall"])
            >= Decimal("0.25")
        ),
        "winner_count_retention_at_least_80pct": (
            v3._d(selection["winner_count_retention"]) >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            v3._d(selection["winner_r_retention"]) >= Decimal("0.90")
        ),
        "density_at_least_55pct": (
            v3._d(selection["density_retained"]) >= Decimal("0.55")
        ),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared"])
    selection = cast(dict[str, object], result["selection"])
    return (
        v3._d(cast(object, shared["profit_factor"]))
        / v3._d(cast(object, baseline["profit_factor"]))
        * v3._d(baseline["max_drawdown_r"])
        / max(v3._d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * (
            Decimal(1)
            + v3._d(selection["loss_rejection_recall"])
        )
        * v3._d(selection["winner_r_retention"])
    )


def run(
    *,
    r8_json: Path,
    r6_json: Path,
    r5_json: Path,
    daily_path: Path,
    r8_nas: Path,
    r8_sp500: Path,
    r8_us30: Path,
    r6_nas: Path,
    r6_sp500: Path,
    r6_us30: Path,
    r5_nas: Path,
    r5_sp500: Path,
    r5_us30: Path,
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8 = v3._decorate(v3._load_trades(r8_json), daily)
    r6 = v3._decorate(v3._load_trades(r6_json), daily)
    r5 = v3._decorate(v3._load_trades(r5_json), daily)

    r8 = _annotate(
        r8, nas_path=r8_nas, sp500_path=r8_sp500, us30_path=r8_us30
    )
    r6 = _annotate(
        r6, nas_path=r6_nas, sp500_path=r6_sp500, us30_path=r6_us30
    )
    r5 = _annotate(
        r5, nas_path=r5_nas, sp500_path=r5_sp500, us30_path=r5_us30
    )

    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for policy in POLICIES:
        calibration = _evaluate(r8, r6, policy)
        gates = _gates(calibration)
        score = _score(calibration)
        frontier.append(
            {
                "policy": policy.payload(),
                "calibration": calibration,
                "gates": gates,
                "selection_score": (
                    None if score is None else format(score, "f")
                ),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared_perception": False,
            "frontier": frontier,
            "governance": {
                "perception_precedes_memory": True,
                "memory_can_reject_alone": False,
                "current_outcome_used": False,
                "journey_management_used": False,
                "capital_risk_weighting_used": False,
                "r5_retuned": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(r8 + r6, r5, frozen)
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if passed
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "PERCEPTION_CONDITIONED_MEMORY",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared_perception": passed,
        "frontier": frontier,
        "governance": {
            "perception_precedes_memory": True,
            "memory_can_reject_alone": False,
            "current_outcome_used": False,
            "journey_management_used": False,
            "capital_risk_weighting_used": False,
            "r5_retuned": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-json", type=Path, required=True)
    parser.add_argument("--r6-json", type=Path, required=True)
    parser.add_argument("--r5-json", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    for partition in ("r8", "r6", "r5"):
        for market in ("nas", "sp500", "us30"):
            parser.add_argument(
                f"--{partition}-{market}",
                type=Path,
                required=True,
            )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
        r8_nas=args.r8_nas,
        r8_sp500=args.r8_sp500,
        r8_us30=args.r8_us30,
        r6_nas=args.r6_nas,
        r6_sp500=args.r6_sp500,
        r6_us30=args.r6_us30,
        r5_nas=args.r5_nas,
        r5_sp500=args.r5_sp500,
        r5_us30=args.r5_us30,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_shared_perception": payload[
                    "passes_shared_perception"
                ],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
