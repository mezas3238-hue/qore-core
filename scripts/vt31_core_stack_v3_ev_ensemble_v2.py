"""Shared EV-ensemble falsification for VT31 NAS100.

Corrects the V3 failure mode: a low win-rate methodology must not be judged by
loss probability alone. Shared estimates expected economic value from multiple
independent causal analog views and penalizes false rejection of high-payoff
winners.

Current-trade outcome remains forbidden. Historical outcomes are allowed only
for episodes fully closed before the evaluated temporal partition.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3

from qore.infrastructure.core_stack_v2.analog_memory import (
    AnalogQuery,
    CausalAnalogMemory,
)

SCHEMA = "qore.core_stack_v3.vt31.ev_ensemble.v2"
IDENTITY = "VT31_NAS100_SHARED_EV_ENSEMBLE_V4"

GEOMETRY_FIELDS = (
    "side",
    "entry_family",
    "raid_depth_ref",
    "risk_ref",
    "planned_target_r_native",
    "entry_location_ref",
    "zone_width_ref",
    "extreme_body_fraction",
    "reference_width_pct_mid",
    "candidate_count",
    "candidate_combo",
)
TIMING_FIELDS = (
    "side",
    "entry_family",
    "raid_minute",
    "confirmation_minute",
    "decision_minute",
    "raid_to_confirmation_minutes",
    "confirmation_to_decision_minutes",
)
REGIME_FIELDS = (
    "side",
    "entry_family",
    "prior_nas100_regime",
    "prior_nas100_first_breach",
    "prior_nas100_objective_hit",
    "prior_nas100_reference_width",
    "prior3_reversal_rate",
    "prior3_objective_rate",
    "prior3_same_breach_rate",
)
GLOBAL_FIELDS = (
    "side",
    "entry_family",
    "prior_peer_direction_state",
    "prior_sp500_regime",
    "prior_us30_regime",
    "sp500_breach_asof",
    "us30_breach_asof",
    "peer_consensus",
)
VIEWS = {
    "GEOMETRY": GEOMETRY_FIELDS,
    "TIMING": TIMING_FIELDS,
    "REGIME": REGIME_FIELDS,
    "GLOBAL": GLOBAL_FIELDS,
}


@dataclass(frozen=True, slots=True)
class Policy:
    maximum_analogs: int
    minimum_similarity_bps: int
    minimum_confidence_bps: int
    conflict_ev_r: Decimal
    favorable_ev_r: Decimal
    minimum_negative_views: int
    caution_multiplier: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "maximum_analogs": self.maximum_analogs,
            "minimum_similarity_bps": self.minimum_similarity_bps,
            "minimum_confidence_bps": self.minimum_confidence_bps,
            "conflict_ev_r": format(self.conflict_ev_r, "f"),
            "favorable_ev_r": format(self.favorable_ev_r, "f"),
            "minimum_negative_views": self.minimum_negative_views,
            "caution_multiplier": format(self.caution_multiplier, "f"),
        }


POLICIES = tuple(
    Policy(maximum, similarity, confidence, conflict, favorable, negatives, caution)
    for maximum in (24, 32, 48)
    for similarity in (4000, 5000, 6000)
    for confidence in (2000, 3500)
    for conflict in (Decimal("-0.05"), Decimal("0"), Decimal("0.05"))
    for favorable in (Decimal("0.20"), Decimal("0.30"))
    for negatives in (2, 3)
    for caution in (Decimal("0.25"), Decimal("0.50"))
)

_MEMORY_CACHE: dict[
    tuple[int, tuple[str, ...]],
    CausalAnalogMemory,
] = {}
_VIEW_CACHE: dict[
    tuple[int, int, int, str],
    dict[str, object],
] = {}


def _memory(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> CausalAnalogMemory:
    key = (id(rows), fields)
    cached = _MEMORY_CACHE.get(key)
    if cached is not None:
        return cached
    memory = v3._memory(rows, fields)
    _MEMORY_CACHE[key] = memory
    return memory


def _analog_economics(
    memory: CausalAnalogMemory,
    row: dict[str, object],
    fields: tuple[str, ...],
    policy: Policy,
) -> dict[str, object]:
    key = (
        id(memory),
        policy.maximum_analogs,
        policy.minimum_similarity_bps,
        cast(str, row["signal_at"]),
    )
    cached = _VIEW_CACHE.get(key)
    if cached is not None:
        return cached

    summary = memory.query(
        AnalogQuery(
            market="NAS100",
            as_of=v3._dt(row["signal_at"]),
            signature=v3._signature(row, fields),
            maximum_analogs=policy.maximum_analogs,
            minimum_similarity_bps=policy.minimum_similarity_bps,
        )
    )
    if not summary.analogs:
        result = {
            "ev_r": None,
            "win_rate": None,
            "mean_win_r": None,
            "mean_loss_r": None,
            "payoff_ratio": None,
            "confidence_bps": 0,
            "effective_n": "0",
            "analog_count": 0,
        }
        _VIEW_CACHE[key] = result
        return result

    weighted = [
        (
            Decimal(item.similarity_bps) / Decimal(10_000),
            Decimal(item.terminal_r),
        )
        for item in summary.analogs
    ]
    total_weight = sum((w for w, _ in weighted), Decimal(0))
    wins = [(w, r) for w, r in weighted if r > 0]
    losses = [(w, r) for w, r in weighted if r < 0]
    win_weight = sum((w for w, _ in wins), Decimal(0))
    loss_weight = sum((w for w, _ in losses), Decimal(0))
    ev = sum((w * r for w, r in weighted), Decimal(0)) / total_weight
    mean_win = (
        None
        if win_weight == 0
        else sum((w * r for w, r in wins), Decimal(0)) / win_weight
    )
    mean_loss = (
        None
        if loss_weight == 0
        else sum((w * r for w, r in losses), Decimal(0)) / loss_weight
    )
    payoff = (
        None
        if mean_win is None or mean_loss is None or mean_loss == 0
        else mean_win / abs(mean_loss)
    )
    result = {
        "ev_r": format(ev, "f"),
        "win_rate": format(win_weight / total_weight, "f"),
        "mean_win_r": None if mean_win is None else format(mean_win, "f"),
        "mean_loss_r": None if mean_loss is None else format(mean_loss, "f"),
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "confidence_bps": summary.confidence_bps,
        "effective_n": summary.effective_sample_size,
        "analog_count": len(summary.analogs),
    }
    _VIEW_CACHE[key] = result
    return result


def _ensemble(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    views: dict[str, dict[str, object]] = {}
    weighted_ev = Decimal(0)
    confidence_sum = Decimal(0)
    negative = 0
    positive = 0
    confident = 0

    for name, fields in VIEWS.items():
        view = _analog_economics(memories[name], row, fields, policy)
        views[name] = view
        ev_raw = view["ev_r"]
        confidence = int(view["confidence_bps"])
        effective_n = Decimal(str(view["effective_n"]))
        if (
            ev_raw is None
            or confidence < policy.minimum_confidence_bps
            or effective_n < Decimal("6")
        ):
            continue
        confident += 1
        ev = Decimal(str(ev_raw))
        weight = Decimal(confidence) / Decimal(10_000)
        weighted_ev += ev * weight
        confidence_sum += weight
        if ev < policy.conflict_ev_r:
            negative += 1
        if ev >= policy.favorable_ev_r:
            positive += 1

    ensemble_ev = (
        None if confidence_sum == 0 else weighted_ev / confidence_sum
    )
    if ensemble_ev is None or confident < 2:
        disposition = "INSUFFICIENT"
    elif (
        negative >= policy.minimum_negative_views
        and ensemble_ev < policy.conflict_ev_r
    ):
        disposition = "CONFLICT"
    elif negative >= 2 or ensemble_ev < Decimal("0.10"):
        disposition = "CAUTION"
    elif positive >= 2 and ensemble_ev >= policy.favorable_ev_r:
        disposition = "FAVORABLE"
    else:
        disposition = "NEUTRAL"

    return {
        "disposition": disposition,
        "ensemble_ev_r": (
            None if ensemble_ev is None else format(ensemble_ev, "f")
        ),
        "confident_views": confident,
        "negative_views": negative,
        "positive_views": positive,
        "views": views,
    }


def _economic_retention(
    rows: list[dict[str, object]],
    abstained: list[dict[str, object]],
) -> dict[str, object]:
    gross_wins = sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in rows
            if v3._d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    gross_losses = -sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in rows
            if v3._d(row["net_r_after_friction"]) < 0
        ),
        Decimal(0),
    )
    sacrificed = sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in abstained
            if v3._d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    avoided = -sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in abstained
            if v3._d(row["net_r_after_friction"]) < 0
        ),
        Decimal(0),
    )
    return {
        "gross_winner_r": format(gross_wins, "f"),
        "gross_loss_r": format(gross_losses, "f"),
        "winner_r_sacrificed": format(sacrificed, "f"),
        "loss_r_avoided": format(avoided, "f"),
        "winner_r_retention": (
            "1"
            if gross_wins == 0
            else format((gross_wins - sacrificed) / gross_wins, "f")
        ),
        "loss_r_avoidance": (
            "0"
            if gross_losses == 0
            else format(avoided / gross_losses, "f")
        ),
    }


def _evaluate(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    memories = {
        name: _memory(history, fields)
        for name, fields in VIEWS.items()
    }
    kept: list[dict[str, object]] = []
    weighted: list[dict[str, object]] = []
    combined: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    dispositions: dict[str, int] = {}

    for source in rows:
        row = dict(source)
        view = _ensemble(memories, row, policy)
        disposition = str(view["disposition"])
        row["shared_ev_ensemble"] = view
        dispositions[disposition] = dispositions.get(disposition, 0) + 1
        raw = v3._d(row["net_r_after_friction"])

        if disposition == "CONFLICT":
            multiplier = Decimal("0.25")
            abstained.append(row)
        elif disposition == "CAUTION":
            multiplier = policy.caution_multiplier
            kept.append(row)
        elif disposition == "NEUTRAL":
            multiplier = Decimal("0.75")
            kept.append(row)
        else:
            multiplier = Decimal("1")
            kept.append(row)

        weighted_row = dict(row)
        weighted_row["shared_weighted_r"] = format(raw * multiplier, "f")
        weighted.append(weighted_row)
        if disposition != "CONFLICT":
            combined.append(weighted_row)

    baseline = v3._metrics(rows)
    mission1 = v3._metrics(kept)
    mission2 = v3._metrics(weighted, "shared_weighted_r")
    combo = v3._metrics(combined, "shared_weighted_r")
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(
        v3._d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        v3._d(row["net_r_after_friction"]) > 0 for row in abstained
    )

    return {
        "baseline": baseline,
        "disposition_counts": dict(sorted(dispositions.items())),
        "mission_1": {
            "metrics": mission1,
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if baseline_losses == 0
                else format(
                    Decimal(losses_avoided) / Decimal(baseline_losses),
                    "f",
                )
            ),
            "winner_retention": (
                "0"
                if baseline_wins == 0
                else format(
                    Decimal(baseline_wins - winners_sacrificed)
                    / Decimal(baseline_wins),
                    "f",
                )
            ),
            "density_retained": format(
                Decimal(len(kept)) / Decimal(len(rows)),
                "f",
            ),
            "economic_retention": _economic_retention(rows, abstained),
        },
        "mission_2": {
            "metrics": mission2,
            "trade_count_preserved": len(weighted) == len(rows),
        },
        "combined": {
            "metrics": combo,
            "trade_count": len(combined),
        },
    }


def _calibration_score(result: dict[str, object]) -> Decimal | None:
    baseline = cast(dict[str, object], result["baseline"])
    m1 = cast(dict[str, object], result["mission_1"])
    m2 = cast(dict[str, object], result["mission_2"])
    m1m = cast(dict[str, object], m1["metrics"])
    m2m = cast(dict[str, object], m2["metrics"])
    econ = cast(dict[str, object], m1["economic_retention"])
    if (
        baseline["profit_factor"] is None
        or m1m["profit_factor"] is None
        or m2m["profit_factor"] is None
    ):
        return None
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    m1pf = v3._d(cast(object, m1m["profit_factor"]))
    m2pf = v3._d(cast(object, m2m["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    if v3._d(m1["density_retained"]) < Decimal("0.55"):
        return None
    if v3._d(m1["winner_retention"]) < Decimal("0.80"):
        return None
    if v3._d(econ["winner_r_retention"]) < Decimal("0.90"):
        return None
    if v3._d(m1["loss_rejection_recall"]) < Decimal("0.12"):
        return None
    if m1pf < bpf * Decimal("1.15"):
        return None
    if v3._d(m1m["max_drawdown_r"]) > bdd * Decimal("0.80"):
        return None
    if m2pf < bpf * Decimal("1.15"):
        return None
    if v3._d(m2m["max_drawdown_r"]) > bdd:
        return None
    return (
        (m1pf / bpf)
        * (m2pf / bpf)
        * v3._d(econ["winner_r_retention"])
        * (bdd / max(v3._d(m1m["max_drawdown_r"]), Decimal("0.000001")))
    )


def _final_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    m1 = cast(dict[str, object], result["mission_1"])
    m2 = cast(dict[str, object], result["mission_2"])
    combo = cast(dict[str, object], result["combined"])
    m1m = cast(dict[str, object], m1["metrics"])
    m2m = cast(dict[str, object], m2["metrics"])
    cm = cast(dict[str, object], combo["metrics"])
    econ = cast(dict[str, object], m1["economic_retention"])
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    return {
        "mission1_pf_plus_25pct": (
            v3._d(cast(object, m1m["profit_factor"]))
            >= bpf * Decimal("1.25")
        ),
        "mission1_dd_minus_30pct": (
            v3._d(m1m["max_drawdown_r"]) <= bdd * Decimal("0.70")
        ),
        "mission1_winner_count_retention_80pct": (
            v3._d(m1["winner_retention"]) >= Decimal("0.80")
        ),
        "mission1_winner_r_retention_90pct": (
            v3._d(econ["winner_r_retention"]) >= Decimal("0.90")
        ),
        "mission1_loss_recall_20pct": (
            v3._d(m1["loss_rejection_recall"]) >= Decimal("0.20")
        ),
        "mission1_density_55pct": (
            v3._d(m1["density_retained"]) >= Decimal("0.55")
        ),
        "mission2_pf_plus_25pct": (
            v3._d(cast(object, m2m["profit_factor"]))
            >= bpf * Decimal("1.25")
        ),
        "mission2_dd_not_worse": (
            v3._d(m2m["max_drawdown_r"]) <= bdd
        ),
        "mission2_trade_count_preserved": bool(
            m2["trade_count_preserved"]
        ),
        "combined_pf_at_least_1_75": (
            v3._d(cast(object, cm["profit_factor"])) >= Decimal("1.75")
        ),
        "combined_dd_at_most_60pct_baseline": (
            v3._d(cm["max_drawdown_r"]) <= bdd * Decimal("0.60")
        ),
    }


def run(
    r8: Path,
    r6: Path,
    r5: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8_rows = v3._decorate(v3._load_trades(r8), daily)
    r6_rows = v3._decorate(v3._load_trades(r6), daily)
    r5_rows = v3._decorate(v3._load_trades(r5), daily)
    all_rows = r8_rows + r6_rows + r5_rows
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for policy in POLICIES:
        result = _evaluate(r8_rows, r6_rows, policy)
        score = _calibration_score(result)
        frontier.append(
            {
                "policy": policy.payload(),
                "calibration": result,
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
            "passes_shared_ev": False,
            "frontier": frontier,
            "governance": {
                "methodology_modified": False,
                "current_outcome_used": False,
                "r5_retuned": False,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(r8_rows + r6_rows, r5_rows, frozen)
    gates = _final_gates(evaluation)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if all(gates.values())
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "DISCOVERY_CLOSED_EPISODE_MEMORY",
            "r6": "EV_ENSEMBLE_CALIBRATION_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared_ev": all(gates.values()),
        "frontier": frontier,
        "governance": {
            "methodology_modified": False,
            "current_outcome_used": False,
            "historical_closed_outcomes_allowed": True,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", type=Path, required=True)
    parser.add_argument("--r6", type=Path, required=True)
    parser.add_argument("--r5", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.r8, args.r6, args.r5, args.daily_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload.get("gates"),
                "passes_shared_ev": payload["passes_shared_ev"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
