"""VT31 Shared Perception State Model V5.

Learns stable PRESENT-MARKET state semantics from R8, not analog neighbors.
A state must keep the same economic sign in two chronological R8 halves before
it can become a negative or positive perception state.

R6 selects/finalizes thresholds. R5 remains untouched until R6 passes every
hard gate. Runtime uses only the current categorical perception state against a
frozen state table; there is no nearest-neighbor/analog lookup.
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

import vt31_core_stack_v4_perception_first_v2 as v2

SCHEMA = "qore.core_stack_v4.vt31.perception_state_model.v5"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_STATE_MODEL_V5"

STATE_VIEWS = {
    "REGIME_STRUCTURE_PEER": (
        "perception_regime",
        "structure_state",
        "peer_consensus",
    ),
    "ALIGN5_REGIME_PEER": (
        "alignment5",
        "perception_regime",
        "peer_consensus",
    ),
    "ALIGN5_STRUCTURE_PEER": (
        "alignment5",
        "structure_state",
        "peer_consensus",
    ),
    "ALIGN20_REGIME_PEER": (
        "alignment20",
        "perception_regime",
        "peer_consensus",
    ),
    "REGIME_VOLATILITY_PEER": (
        "perception_regime",
        "volatility_state",
        "peer_consensus",
    ),
    "ALIGN5_REGIME_VOLATILITY": (
        "alignment5",
        "perception_regime",
        "volatility_state",
    ),
    "ALIGN5_STRUCTURE_VOLATILITY": (
        "alignment5",
        "structure_state",
        "volatility_state",
    ),
}


@dataclass(frozen=True, slots=True)
class Policy:
    minimum_half_sample: int
    negative_pf_ceiling: Decimal
    positive_pf_floor: Decimal
    required_negative_views: int
    required_positive_views_to_protect: int
    maximum_positive_views_for_abstain: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_half_sample": self.minimum_half_sample,
            "negative_pf_ceiling": format(self.negative_pf_ceiling, "f"),
            "positive_pf_floor": format(self.positive_pf_floor, "f"),
            "required_negative_views": self.required_negative_views,
            "required_positive_views_to_protect": (
                self.required_positive_views_to_protect
            ),
            "maximum_positive_views_for_abstain": (
                self.maximum_positive_views_for_abstain
            ),
        }


POLICIES = tuple(
    Policy(
        minimum_half_sample=min_sample,
        negative_pf_ceiling=neg_pf,
        positive_pf_floor=pos_pf,
        required_negative_views=neg_views,
        required_positive_views_to_protect=protect_views,
        maximum_positive_views_for_abstain=max_pos,
    )
    for min_sample in (3, 4, 5)
    for neg_pf in (Decimal("0.60"), Decimal("0.80"), Decimal("1.00"))
    for pos_pf in (Decimal("1.20"), Decimal("1.40"), Decimal("1.60"))
    for neg_views in (1, 2, 3)
    for protect_views in (1, 2)
    for max_pos in (0, 1)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _state(row: dict[str, object], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "unavailable")) for field in fields)


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in rows]
    gains = sum((v for v in values if v > 0), Decimal(0))
    losses = -sum((v for v in values if v < 0), Decimal(0))
    return {
        "sample": len(rows),
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "profit_factor": None if losses == 0 else gains / losses,
        "total_r": gains - losses,
        "gross_winner_r": gains,
        "gross_loss_r": losses,
    }


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
        groups[_state(row, fields)].append(row)
    return groups


def _stable_state_tables(
    history: list[dict[str, object]],
    policy: Policy,
) -> tuple[dict[str, set[tuple[str, ...]]], dict[str, set[tuple[str, ...]]], dict[str, object]]:
    old, recent = _split(history)
    negative: dict[str, set[tuple[str, ...]]] = {}
    positive: dict[str, set[tuple[str, ...]]] = {}
    diagnostics: dict[str, object] = {}

    for name, fields in STATE_VIEWS.items():
        old_groups = _groups(old, fields)
        recent_groups = _groups(recent, fields)
        shared_keys = set(old_groups).intersection(recent_groups)
        neg: set[tuple[str, ...]] = set()
        pos: set[tuple[str, ...]] = set()
        rows_diag: list[dict[str, object]] = []

        for key in shared_keys:
            left = _stats(old_groups[key])
            right = _stats(recent_groups[key])
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
            is_positive = (
                lpf >= policy.positive_pf_floor
                and rpf >= policy.positive_pf_floor
                and cast(Decimal, left["total_r"]) > 0
                and cast(Decimal, right["total_r"]) > 0
            )
            if is_negative:
                neg.add(key)
            if is_positive:
                pos.add(key)
            if is_negative or is_positive:
                rows_diag.append({
                    "state": key,
                    "classification": (
                        "NEGATIVE"
                        if is_negative
                        else "POSITIVE"
                    ),
                    "old": {
                        "sample": left["sample"],
                        "pf": format(lpf, "f"),
                        "total_r": format(cast(Decimal, left["total_r"]), "f"),
                    },
                    "recent": {
                        "sample": right["sample"],
                        "pf": format(rpf, "f"),
                        "total_r": format(cast(Decimal, right["total_r"]), "f"),
                    },
                })

        negative[name] = neg
        positive[name] = pos
        diagnostics[name] = {
            "negative_state_count": len(neg),
            "positive_state_count": len(pos),
            "stable_states": rows_diag,
        }

    return negative, positive, diagnostics


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
    positive: dict[str, set[tuple[str, ...]]],
    policy: Policy,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    protected: list[dict[str, object]] = []
    match_histogram: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        negative_views = 0
        positive_views = 0
        matched_negative: list[str] = []
        matched_positive: list[str] = []

        for name, fields in STATE_VIEWS.items():
            state = _state(row, fields)
            if state in negative[name]:
                negative_views += 1
                matched_negative.append(name)
            if state in positive[name]:
                positive_views += 1
                matched_positive.append(name)

        protected_now = (
            positive_views >= policy.required_positive_views_to_protect
        )
        abstain_now = (
            not protected_now
            and negative_views >= policy.required_negative_views
            and positive_views <= policy.maximum_positive_views_for_abstain
        )

        key = f"N{negative_views}_P{positive_views}"
        match_histogram[key] = match_histogram.get(key, 0) + 1

        if abstain_now:
            abstained.append(row)
        else:
            kept_values.append(value)
            if protected_now:
                protected.append(row)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(
        _d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        _d(row["net_r_after_friction"]) > 0 for row in abstained
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
    protected_winners = sum(
        _d(row["net_r_after_friction"]) > 0 for row in protected
    )
    protected_losses = sum(
        _d(row["net_r_after_friction"]) < 0 for row in protected
    )

    return {
        "baseline": baseline,
        "shared_state_model": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0" if baseline_losses == 0
                else format(Decimal(losses_avoided) / Decimal(baseline_losses), "f")
            ),
            "winner_count_retention": (
                "0" if baseline_wins == 0
                else format(
                    Decimal(baseline_wins - winners_sacrificed) / Decimal(baseline_wins),
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
            "protected_trades": len(protected),
            "protected_winners": protected_winners,
            "protected_losses": protected_losses,
            "match_histogram": dict(sorted(match_histogram.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_state_model"])
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
    shared = cast(dict[str, object], result["shared_state_model"])
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
    daily = v2.v3._load_daily(daily_path)
    r8 = v2._perception_rows(r8_raw, v2.v3._decorate(v2.v3._load_trades(r8_trades), daily))
    r6 = v2._perception_rows(r6_raw, v2.v3._decorate(v2.v3._load_trades(r6_trades), daily))
    r5 = v2._perception_rows(r5_raw, v2.v3._decorate(v2.v3._load_trades(r5_trades), daily))
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
        negative, positive, diagnostics = _stable_state_tables(r8, policy)
        calibration = _evaluate(
            r6,
            negative=negative,
            positive=positive,
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
            best = (score, policy, negative, positive, diagnostics)

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
            "passes_state_model": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen, negative, positive, diagnostics = best
    evaluation = _evaluate(
        r5,
        negative=negative,
        positive=positive,
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
            "r8": "STABLE_STATE_DISCOVERY_TWO_HALVES",
            "r6": "THRESHOLD_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "frozen_state_model": diagnostics,
        "evaluation": evaluation,
        "gates": gates,
        "passes_state_model": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "runtime_analog_lookup_used": False,
        "runtime_exact_present_state_lookup_only": True,
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
        "passes_state_model": payload["passes_state_model"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
