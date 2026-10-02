"""VT31 Shared Perception Precision Tail Rescue V7.

Focused continuation of the strongest V6 R6 near-miss:
PF 1.7797589, DD 22.0821R, loss recall 28.03%, winner-R retention 90.08%,
winner-count retention 79.49%.

V7 keeps the frozen aggressive negative-state definition and makes only the
winner-rescue perception finer. Tail states use higher-resolution present-state
tuples and must be profitable in both R8 halves.

No R5 tuning. If R6 passes all hard gates, the exact frozen V7 model is
evaluated once on R5.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_perception_state_model_v5 as v5

SCHEMA = "qore.core_stack_v4.vt31.perception_precision_tail_rescue.v7"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_PRECISION_TAIL_RESCUE_V7"

NEGATIVE_VIEWS = v5.STATE_VIEWS

TAIL_VIEWS = {
    **v5.STATE_VIEWS,
    "ALIGN5_REGIME_STRUCTURE_PEER": (
        "alignment5",
        "perception_regime",
        "structure_state",
        "peer_consensus",
    ),
    "ALIGN20_REGIME_STRUCTURE_PEER": (
        "alignment20",
        "perception_regime",
        "structure_state",
        "peer_consensus",
    ),
    "ALIGN5_REGIME_VOLATILITY_PEER": (
        "alignment5",
        "perception_regime",
        "volatility_state",
        "peer_consensus",
    ),
    "ALIGN5_STRUCTURE_VOLATILITY_PEER": (
        "alignment5",
        "structure_state",
        "volatility_state",
        "peer_consensus",
    ),
    "ALIGN5_ALIGN20_REGIME_PEER": (
        "alignment5",
        "alignment20",
        "perception_regime",
        "peer_consensus",
    ),
}


@dataclass(frozen=True, slots=True)
class Policy:
    tail_minimum_half_sample: int
    tail_mean_winner_r_floor: Decimal
    tail_pf_floor: Decimal
    single_negative_tail_views: int
    multiple_negative_tail_views: int

    def payload(self) -> dict[str, object]:
        return {
            "negative_minimum_half_sample": 3,
            "negative_pf_ceiling": "0.80",
            "required_negative_views": 1,
            "tail_minimum_half_sample": self.tail_minimum_half_sample,
            "tail_mean_winner_r_floor": format(
                self.tail_mean_winner_r_floor, "f"
            ),
            "tail_pf_floor": format(self.tail_pf_floor, "f"),
            "single_negative_tail_views": self.single_negative_tail_views,
            "multiple_negative_tail_views": self.multiple_negative_tail_views,
        }


POLICIES = tuple(
    Policy(
        tail_minimum_half_sample=tail_n,
        tail_mean_winner_r_floor=tail_r,
        tail_pf_floor=tail_pf,
        single_negative_tail_views=single,
        multiple_negative_tail_views=multiple,
    )
    for tail_n in (2, 3, 4)
    for tail_r in (Decimal("4"), Decimal("6"), Decimal("8"))
    for tail_pf in (
        Decimal("1.00"),
        Decimal("1.20"),
        Decimal("1.40"),
        Decimal("1.60"),
    )
    for single in (1, 2)
    for multiple in (2, 3)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _split(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    cut = len(ordered) // 2
    return ordered[:cut], ordered[cut:]


def _groups(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[tuple[str, ...], list[dict[str, object]]]:
    groups: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[v5._state(row, fields)].append(row)
    return groups


def _negative_tables(
    history: list[dict[str, object]],
) -> dict[str, set[tuple[str, ...]]]:
    old, recent = _split(history)
    output: dict[str, set[tuple[str, ...]]] = {}
    for name, fields in NEGATIVE_VIEWS.items():
        left_groups = _groups(old, fields)
        right_groups = _groups(recent, fields)
        states: set[tuple[str, ...]] = set()
        for key in set(left_groups).intersection(right_groups):
            left = v5._stats(left_groups[key])
            right = v5._stats(right_groups[key])
            if int(left["sample"]) < 3 or int(right["sample"]) < 3:
                continue
            lpf = cast(Decimal | None, left["profit_factor"])
            rpf = cast(Decimal | None, right["profit_factor"])
            if lpf is None or rpf is None:
                continue
            if (
                lpf <= Decimal("0.80")
                and rpf <= Decimal("0.80")
                and cast(Decimal, left["total_r"]) < 0
                and cast(Decimal, right["total_r"]) < 0
            ):
                states.add(key)
        output[name] = states
    return output


def _tail_tables(
    history: list[dict[str, object]],
    policy: Policy,
) -> tuple[dict[str, set[tuple[str, ...]]], dict[str, object]]:
    old, recent = _split(history)
    output: dict[str, set[tuple[str, ...]]] = {}
    diagnostics: dict[str, object] = {}

    for name, fields in TAIL_VIEWS.items():
        left_groups = _groups(old, fields)
        right_groups = _groups(recent, fields)
        states: set[tuple[str, ...]] = set()
        details: list[dict[str, object]] = []

        for key in set(left_groups).intersection(right_groups):
            left = v5._stats(left_groups[key])
            right = v5._stats(right_groups[key])
            if (
                int(left["sample"]) < policy.tail_minimum_half_sample
                or int(right["sample"]) < policy.tail_minimum_half_sample
            ):
                continue
            lpf = cast(Decimal | None, left["profit_factor"])
            rpf = cast(Decimal | None, right["profit_factor"])
            if lpf is None or rpf is None:
                continue
            lw = int(left["wins"])
            rw = int(right["wins"])
            if lw < 1 or rw < 1:
                continue
            lm = cast(Decimal, left["gross_winner_r"]) / Decimal(lw)
            rm = cast(Decimal, right["gross_winner_r"]) / Decimal(rw)
            qualifies = (
                lpf >= policy.tail_pf_floor
                and rpf >= policy.tail_pf_floor
                and cast(Decimal, left["total_r"]) > 0
                and cast(Decimal, right["total_r"]) > 0
                and lm >= policy.tail_mean_winner_r_floor
                and rm >= policy.tail_mean_winner_r_floor
            )
            if qualifies:
                states.add(key)
                details.append({
                    "state": key,
                    "old_pf": format(lpf, "f"),
                    "recent_pf": format(rpf, "f"),
                    "old_mean_winner_r": format(lm, "f"),
                    "recent_mean_winner_r": format(rm, "f"),
                    "old_sample": left["sample"],
                    "recent_sample": right["sample"],
                })
        output[name] = states
        diagnostics[name] = {
            "tail_state_count": len(states),
            "states": details,
        }

    return output, diagnostics


def _metrics(values: list[Decimal]) -> dict[str, object]:
    gains = sum((v for v in values if v > 0), Decimal(0))
    losses = -sum((v for v in values if v < 0), Decimal(0))
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
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "profit_factor": None if losses == 0 else format(gains / losses, "f"),
        "total_r": format(total, "f"),
        "mean_r": "0" if not values else format(total / Decimal(len(values)), "f"),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _evaluate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    tail: dict[str, set[tuple[str, ...]]],
    policy: Policy,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []
    rescue_histogram: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)

        negative_views = sum(
            v5._state(row, fields) in negative[name]
            for name, fields in NEGATIVE_VIEWS.items()
        )
        if negative_views == 0:
            kept_values.append(value)
            continue

        tail_views = sum(
            v5._state(row, fields) in tail[name]
            for name, fields in TAIL_VIEWS.items()
        )
        required_tail = (
            policy.single_negative_tail_views
            if negative_views == 1
            else policy.multiple_negative_tail_views
        )
        rescue = tail_views >= required_tail
        key = f"N{negative_views}_T{tail_views}_REQ{required_tail}"
        rescue_histogram[key] = rescue_histogram.get(key, 0) + 1

        if rescue:
            kept_values.append(value)
            rescued.append(row)
        else:
            abstained.append(row)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        _d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        _d(row["net_r_after_friction"]) > 0 for row in abstained
    )
    gross_winner_r = sum((v for v in baseline_values if v > 0), Decimal(0))
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    rescued_winners = sum(
        _d(row["net_r_after_friction"]) > 0 for row in rescued
    )
    rescued_losses = sum(
        _d(row["net_r_after_friction"]) < 0 for row in rescued
    )

    return {
        "baseline": baseline,
        "shared_precision_tail": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0" if base_losses == 0
                else format(Decimal(losses_avoided) / Decimal(base_losses), "f")
            ),
            "winner_count_retention": (
                "0" if base_wins == 0
                else format(
                    Decimal(base_wins - winners_sacrificed) / Decimal(base_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1" if gross_winner_r == 0
                else format((gross_winner_r - sacrificed_r) / gross_winner_r, "f")
            ),
            "density_retained": (
                "0" if not rows
                else format(Decimal(len(kept_values)) / Decimal(len(rows)), "f")
            ),
            "rescued_trades": len(rescued),
            "rescued_winners": rescued_winners,
            "rescued_losses": rescued_losses,
            "rescue_precision": (
                "0" if not rescued
                else format(Decimal(rescued_winners) / Decimal(len(rescued)), "f")
            ),
            "rescue_histogram": dict(sorted(rescue_histogram.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_precision_tail"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    bpf = _d(cast(object, baseline["profit_factor"]))
    spf = _d(cast(object, shared["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    sdd = _d(shared["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": _d(selection["loss_rejection_recall"]) >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": _d(selection["winner_count_retention"]) >= Decimal("0.80"),
        "winner_r_retention_at_least_90pct": _d(selection["winner_r_retention"]) >= Decimal("0.90"),
        "density_at_least_55pct": _d(selection["density_retained"]) >= Decimal("0.55"),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_precision_tail"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(cast(object, shared["profit_factor"]))
        / _d(cast(object, baseline["profit_factor"]))
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(selection["winner_r_retention"])
        * (Decimal("1") + _d(selection["loss_rejection_recall"]))
    )


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
    daily = v5.v2.v3._load_daily(daily_path)
    r8 = v5.v2._perception_rows(r8_raw, v5.v2.v3._decorate(v5.v2.v3._load_trades(r8_trades), daily))
    r6 = v5.v2._perception_rows(r6_raw, v5.v2.v3._decorate(v5.v2.v3._load_trades(r6_trades), daily))
    r5 = v5.v2._perception_rows(r5_raw, v5.v2.v3._decorate(v5.v2.v3._load_trades(r5_trades), daily))
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    negative = _negative_tables(r8)
    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy, dict[str, set[tuple[str, ...]]], dict[str, object]] | None = None

    for policy in POLICIES:
        tail, diagnostics = _tail_tables(r8, policy)
        calibration = _evaluate(
            r6,
            negative=negative,
            tail=tail,
            policy=policy,
        )
        gates = _gates(calibration)
        score = _score(calibration)
        frontier.append({
            "policy": policy.payload(),
            "tail_model": diagnostics,
            "calibration": calibration,
            "gates": gates,
            "selection_score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy, tail, diagnostics)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_R6_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "frozen_tail_model": None,
            "evaluation": None,
            "gates": None,
            "passes_precision_tail": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen, tail, diagnostics = best
    evaluation = _evaluate(
        r5,
        negative=negative,
        tail=tail,
        policy=frozen,
    )
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
            "r8": "STABLE_NEGATIVE_PLUS_FINE_TAIL_STATE_DISCOVERY",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "frozen_tail_model": diagnostics,
        "evaluation": evaluation,
        "gates": gates,
        "passes_precision_tail": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "runtime_analog_lookup_used": False,
        "runtime_exact_present_state_lookup_only": True,
        "fine_tail_rescue_present_state_only": True,
        "negative_model_fixed_from_v6_near_miss": True,
        "current_outcome_used_at_runtime": False,
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
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_precision_tail": payload["passes_precision_tail"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
