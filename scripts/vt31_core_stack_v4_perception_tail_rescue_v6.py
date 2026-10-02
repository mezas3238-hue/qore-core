"""VT31 Shared Perception Tail-Rescue State Model V6.

V5 isolated the trade-off:
- aggressive negative-state detection raises PF / lowers DD / removes losses,
  but sacrifices rare high-payoff winners;
- conservative detection preserves winner R but misses too many losses.

V6 keeps the aggressive perception-state detector and adds a tail-winner rescue
head learned from PRESENT-MARKET state cells that contain high-payoff winners
in both chronological halves of R8.

Runtime remains exact current-state lookup only. No analog nearest neighbors.
R6 calibrates/finalizes. R5 is untouched until R6 passes every hard gate.
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

SCHEMA = "qore.core_stack_v4.vt31.perception_tail_rescue.v6"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_TAIL_RESCUE_V6"


@dataclass(frozen=True, slots=True)
class Policy:
    minimum_half_sample: int
    negative_pf_ceiling: Decimal
    required_negative_views: int
    tail_mean_winner_r_floor: Decimal
    tail_pf_floor: Decimal
    required_tail_views_to_rescue: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_half_sample": self.minimum_half_sample,
            "negative_pf_ceiling": format(self.negative_pf_ceiling, "f"),
            "required_negative_views": self.required_negative_views,
            "tail_mean_winner_r_floor": format(
                self.tail_mean_winner_r_floor, "f"
            ),
            "tail_pf_floor": format(self.tail_pf_floor, "f"),
            "required_tail_views_to_rescue": self.required_tail_views_to_rescue,
        }


POLICIES = tuple(
    Policy(
        minimum_half_sample=min_sample,
        negative_pf_ceiling=neg_pf,
        required_negative_views=neg_views,
        tail_mean_winner_r_floor=tail_r,
        tail_pf_floor=tail_pf,
        required_tail_views_to_rescue=tail_views,
    )
    for min_sample in (3, 4)
    for neg_pf in (Decimal("0.80"), Decimal("1.00"))
    for neg_views in (1, 2)
    for tail_r in (Decimal("4"), Decimal("6"), Decimal("8"))
    for tail_pf in (Decimal("0.60"), Decimal("0.80"), Decimal("1.00"))
    for tail_views in (2, 3, 4)
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


def _state_tables(
    history: list[dict[str, object]],
    policy: Policy,
) -> tuple[
    dict[str, set[tuple[str, ...]]],
    dict[str, set[tuple[str, ...]]],
    dict[str, object],
]:
    old, recent = _split(history)
    negative: dict[str, set[tuple[str, ...]]] = {}
    tail: dict[str, set[tuple[str, ...]]] = {}
    diagnostics: dict[str, object] = {}

    for name, fields in v5.STATE_VIEWS.items():
        left_groups = _groups(old, fields)
        right_groups = _groups(recent, fields)
        keys = set(left_groups).intersection(right_groups)
        negative_states: set[tuple[str, ...]] = set()
        tail_states: set[tuple[str, ...]] = set()
        rows_diag: list[dict[str, object]] = []

        for key in keys:
            left = v5._stats(left_groups[key])
            right = v5._stats(right_groups[key])
            if (
                int(left["sample"]) < policy.minimum_half_sample
                or int(right["sample"]) < policy.minimum_half_sample
            ):
                continue
            lpf = cast(Decimal | None, left["profit_factor"])
            rpf = cast(Decimal | None, right["profit_factor"])
            if lpf is None or rpf is None:
                continue

            is_negative = (
                lpf <= policy.negative_pf_ceiling
                and rpf <= policy.negative_pf_ceiling
                and cast(Decimal, left["total_r"]) < 0
                and cast(Decimal, right["total_r"]) < 0
            )
            left_wins = int(left["wins"])
            right_wins = int(right["wins"])
            left_mean_win = (
                Decimal(0)
                if left_wins == 0
                else cast(Decimal, left["gross_winner_r"]) / Decimal(left_wins)
            )
            right_mean_win = (
                Decimal(0)
                if right_wins == 0
                else cast(Decimal, right["gross_winner_r"]) / Decimal(right_wins)
            )
            is_tail = (
                left_wins >= 1
                and right_wins >= 1
                and left_mean_win >= policy.tail_mean_winner_r_floor
                and right_mean_win >= policy.tail_mean_winner_r_floor
                and lpf >= policy.tail_pf_floor
                and rpf >= policy.tail_pf_floor
            )

            if is_negative:
                negative_states.add(key)
            if is_tail:
                tail_states.add(key)
            if is_negative or is_tail:
                rows_diag.append({
                    "state": key,
                    "negative": is_negative,
                    "tail": is_tail,
                    "old": {
                        "sample": left["sample"],
                        "wins": left_wins,
                        "pf": format(lpf, "f"),
                        "total_r": format(cast(Decimal, left["total_r"]), "f"),
                        "mean_winner_r": format(left_mean_win, "f"),
                    },
                    "recent": {
                        "sample": right["sample"],
                        "wins": right_wins,
                        "pf": format(rpf, "f"),
                        "total_r": format(cast(Decimal, right["total_r"]), "f"),
                        "mean_winner_r": format(right_mean_win, "f"),
                    },
                })

        negative[name] = negative_states
        tail[name] = tail_states
        diagnostics[name] = {
            "negative_state_count": len(negative_states),
            "tail_state_count": len(tail_states),
            "states": rows_diag,
        }

    return negative, tail, diagnostics


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
    histogram: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        negative_views = 0
        tail_views = 0
        for name, fields in v5.STATE_VIEWS.items():
            state = v5._state(row, fields)
            if state in negative[name]:
                negative_views += 1
            if state in tail[name]:
                tail_views += 1

        candidate_abstain = negative_views >= policy.required_negative_views
        rescue = (
            candidate_abstain
            and tail_views >= policy.required_tail_views_to_rescue
        )
        key = f"N{negative_views}_T{tail_views}"
        histogram[key] = histogram.get(key, 0) + 1

        if candidate_abstain and not rescue:
            abstained.append(row)
        else:
            kept_values.append(value)
            if rescue:
                rescued.append(row)

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
    rescued_winners = sum(
        _d(row["net_r_after_friction"]) > 0 for row in rescued
    )
    rescued_losses = sum(
        _d(row["net_r_after_friction"]) < 0 for row in rescued
    )
    gross_winner_r = sum(
        (v for v in baseline_values if v > 0),
        Decimal(0),
    )
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )

    return {
        "baseline": baseline,
        "shared_tail_rescue": shared,
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
            "match_histogram": dict(sorted(histogram.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_tail_rescue"])
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
    shared = cast(dict[str, object], result["shared_tail_rescue"])
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

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy, dict[str, set[tuple[str, ...]]], dict[str, set[tuple[str, ...]]], dict[str, object]] | None = None

    for policy in POLICIES:
        negative, tail, diagnostics = _state_tables(r8, policy)
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
            "state_model": diagnostics,
            "calibration": calibration,
            "gates": gates,
            "selection_score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy, negative, tail, diagnostics)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_R6_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "frozen_state_model": None,
            "evaluation": None,
            "gates": None,
            "passes_tail_rescue": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen, negative, tail, diagnostics = best
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
            "r8": "STABLE_NEGATIVE_AND_TAIL_STATE_DISCOVERY",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "frozen_state_model": diagnostics,
        "evaluation": evaluation,
        "gates": gates,
        "passes_tail_rescue": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "runtime_analog_lookup_used": False,
        "runtime_exact_present_state_lookup_only": True,
        "tail_rescue_uses_present_state_only": True,
        "r8_outcomes_used_offline_for_state_learning": True,
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
        "passes_tail_rescue": payload["passes_tail_rescue"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
