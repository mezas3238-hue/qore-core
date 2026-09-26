"""Shared Mission-1-only decision intelligence for VT31 NAS100.

Phase A only. Trade potentiation, risk weighting and position management are
explicitly forbidden here.

Engineering objective:
- reject materially bad opportunities before entry;
- preserve winner count and, critically, winner R;
- use independent causal analog views;
- require consensus for ABSTAIN;
- protect high-payoff winner archetypes from false rejection.

Temporal protocol:
R8 = closed historical memory.
R6 = calibration and one policy freeze.
R5 = no-retune temporal evaluation.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_ev_ensemble_v2 as ev

from qore.infrastructure.core_stack_v2.analog_memory import (
    AnalogQuery,
    CausalAnalogMemory,
)

SCHEMA = "qore.core_stack_v3.vt31.shared_decision_intelligence.v2"
IDENTITY = "VT31_NAS100_SHARED_DECISION_INTELLIGENCE_PHASE_A_V2"

VIEWS = ev.VIEWS


@dataclass(frozen=True, slots=True)
class Policy:
    maximum_analogs: int
    minimum_similarity_bps: int
    minimum_confidence_bps: int
    abstain_ev_r: Decimal
    required_negative_views: int
    maximum_positive_views: int
    winner_archetype_ev_floor: Decimal
    winner_archetype_payoff_floor: Decimal
    tail_mean_win_r_floor: Decimal
    tail_payoff_floor: Decimal
    tail_min_win_rate: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "maximum_analogs": self.maximum_analogs,
            "minimum_similarity_bps": self.minimum_similarity_bps,
            "minimum_confidence_bps": self.minimum_confidence_bps,
            "abstain_ev_r": format(self.abstain_ev_r, "f"),
            "required_negative_views": self.required_negative_views,
            "maximum_positive_views": self.maximum_positive_views,
            "winner_archetype_ev_floor": format(
                self.winner_archetype_ev_floor, "f"
            ),
            "winner_archetype_payoff_floor": format(
                self.winner_archetype_payoff_floor, "f"
            ),
            "tail_mean_win_r_floor": format(
                self.tail_mean_win_r_floor, "f"
            ),
            "tail_payoff_floor": format(
                self.tail_payoff_floor, "f"
            ),
            "tail_min_win_rate": format(
                self.tail_min_win_rate, "f"
            ),
        }


POLICIES = tuple(
    Policy(
        maximum,
        similarity,
        confidence,
        abstain_ev,
        negatives,
        positives,
        winner_ev,
        winner_payoff,
        tail_mean_win,
        tail_payoff,
        tail_win_rate,
    )
    for maximum in (24, 32, 48)
    for similarity in (4500, 5500, 6500)
    for confidence in (2500, 4000)
    for abstain_ev in (
        Decimal("-0.10"),
        Decimal("-0.05"),
        Decimal("0"),
    )
    for negatives in (2, 3, 4)
    for positives in (0, 1)
    for winner_ev in (Decimal("0.20"), Decimal("0.30"))
    for winner_payoff in (Decimal("2.5"), Decimal("3.5"))
    for tail_mean_win in (Decimal("2.5"), Decimal("3.5"), Decimal("4.5"))
    for tail_payoff in (Decimal("3"), Decimal("5"))
    for tail_win_rate in (Decimal("0.08"), Decimal("0.12"))
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


def _view(
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
    total_weight = sum((weight for weight, _ in weighted), Decimal(0))
    wins = [(weight, r) for weight, r in weighted if r > 0]
    losses = [(weight, r) for weight, r in weighted if r < 0]
    win_weight = sum((weight for weight, _ in wins), Decimal(0))
    loss_weight = sum((weight for weight, _ in losses), Decimal(0))
    ev_r = (
        sum((weight * r for weight, r in weighted), Decimal(0))
        / total_weight
    )
    mean_win = (
        None
        if win_weight == 0
        else sum((weight * r for weight, r in wins), Decimal(0)) / win_weight
    )
    mean_loss = (
        None
        if loss_weight == 0
        else sum((weight * r for weight, r in losses), Decimal(0))
        / loss_weight
    )
    payoff = (
        None
        if mean_win is None or mean_loss is None or mean_loss == 0
        else mean_win / abs(mean_loss)
    )
    result = {
        "ev_r": format(ev_r, "f"),
        "win_rate": format(win_weight / total_weight, "f"),
        "mean_win_r": None if mean_win is None else format(mean_win, "f"),
        "mean_loss_r": None if mean_loss is None else format(mean_loss, "f"),
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "confidence_bps": summary.confidence_bps,
        "effective_n": summary.effective_sample_size,
    }
    _VIEW_CACHE[key] = result
    return result


def _decision(
    memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: Policy,
) -> dict[str, object]:
    views: dict[str, dict[str, object]] = {}
    negative = 0
    positive = 0
    protected = 0
    tail_protected = 0
    confident = 0
    weighted_ev = Decimal(0)
    weight_sum = Decimal(0)

    for name, fields in VIEWS.items():
        item = _view(memories[name], row, fields, policy)
        views[name] = item
        ev_raw = item["ev_r"]
        confidence = int(item["confidence_bps"])
        effective_n = Decimal(str(item["effective_n"]))
        if (
            ev_raw is None
            or confidence < policy.minimum_confidence_bps
            or effective_n < Decimal("6")
        ):
            continue
        confident += 1
        ev_r = Decimal(str(ev_raw))
        payoff_raw = item["payoff_ratio"]
        payoff = (
            None
            if payoff_raw is None
            else Decimal(str(payoff_raw))
        )
        mean_win_raw = item["mean_win_r"]
        mean_win = (
            None
            if mean_win_raw is None
            else Decimal(str(mean_win_raw))
        )
        win_rate_raw = item["win_rate"]
        win_rate = (
            None
            if win_rate_raw is None
            else Decimal(str(win_rate_raw))
        )
        weight = Decimal(confidence) / Decimal(10_000)
        weighted_ev += ev_r * weight
        weight_sum += weight

        if ev_r < policy.abstain_ev_r:
            negative += 1
        if ev_r >= policy.winner_archetype_ev_floor:
            positive += 1
        if (
            ev_r >= policy.winner_archetype_ev_floor
            and payoff is not None
            and payoff >= policy.winner_archetype_payoff_floor
        ):
            protected += 1
        if (
            mean_win is not None
            and payoff is not None
            and win_rate is not None
            and mean_win >= policy.tail_mean_win_r_floor
            and payoff >= policy.tail_payoff_floor
            and win_rate >= policy.tail_min_win_rate
        ):
            tail_protected += 1

    ensemble_ev = None if weight_sum == 0 else weighted_ev / weight_sum
    winner_protected = protected > 0 or tail_protected > 0

    abstain = (
        ensemble_ev is not None
        and confident >= 2
        and negative >= policy.required_negative_views
        and positive <= policy.maximum_positive_views
        and ensemble_ev < policy.abstain_ev_r
        and not winner_protected
    )

    if abstain:
        action = "ABSTAIN_SHADOW"
    elif winner_protected:
        action = "PASS_WINNER_ARCHETYPE_PROTECTED"
    elif ensemble_ev is None or confident < 2:
        action = "PASS_INSUFFICIENT"
    else:
        action = "PASS"

    return {
        "action": action,
        "ensemble_ev_r": (
            None if ensemble_ev is None else format(ensemble_ev, "f")
        ),
        "confident_views": confident,
        "negative_views": negative,
        "positive_views": positive,
        "winner_archetype_protected_views": protected,
        "tail_winner_protected_views": tail_protected,
        "views": views,
    }


def _economic_retention(
    rows: list[dict[str, object]],
    abstained: list[dict[str, object]],
) -> dict[str, object]:
    gross_winner_r = sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in rows
            if v3._d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    gross_loss_r = -sum(
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
        "gross_winner_r": format(gross_winner_r, "f"),
        "gross_loss_r": format(gross_loss_r, "f"),
        "winner_r_sacrificed": format(sacrificed, "f"),
        "loss_r_avoided": format(avoided, "f"),
        "winner_r_retention": (
            "1"
            if gross_winner_r == 0
            else format(
                (gross_winner_r - sacrificed) / gross_winner_r,
                "f",
            )
        ),
        "loss_r_avoidance": (
            "0"
            if gross_loss_r == 0
            else format(avoided / gross_loss_r, "f")
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
    abstained: list[dict[str, object]] = []
    actions: dict[str, int] = {}

    for source in rows:
        row = dict(source)
        decision = _decision(memories, row, policy)
        action = str(decision["action"])
        row["shared_decision_intelligence"] = decision
        actions[action] = actions.get(action, 0) + 1
        if action == "ABSTAIN_SHADOW":
            abstained.append(row)
        else:
            kept.append(row)

    baseline = v3._metrics(rows)
    selected = v3._metrics(kept)
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(
        v3._d(row["net_r_after_friction"]) < 0
        for row in abstained
    )
    winners_sacrificed = sum(
        v3._d(row["net_r_after_friction"]) > 0
        for row in abstained
    )
    return {
        "baseline": baseline,
        "shared": {
            "metrics": selected,
            "input_trades": len(rows),
            "kept_trades": len(kept),
            "abstained_trades": len(abstained),
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
            "winner_count_retention": (
                "0"
                if baseline_wins == 0
                else format(
                    Decimal(baseline_wins - winners_sacrificed)
                    / Decimal(baseline_wins),
                    "f",
                )
            ),
            "density_retained": (
                "0"
                if not rows
                else format(
                    Decimal(len(kept)) / Decimal(len(rows)),
                    "f",
                )
            ),
            "economic_retention": _economic_retention(rows, abstained),
            "action_counts": dict(sorted(actions.items())),
        },
    }


def _passes_gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared"])
    metrics = cast(dict[str, object], shared["metrics"])
    economic = cast(dict[str, object], shared["economic_retention"])

    if baseline["profit_factor"] is None or metrics["profit_factor"] is None:
        return {
            "pf_plus_25pct": False,
            "dd_minus_30pct": False,
            "loss_recall_at_least_25pct": False,
            "winner_count_retention_at_least_80pct": False,
            "winner_r_retention_at_least_90pct": False,
            "density_at_least_55pct": False,
        }

    bpf = v3._d(cast(object, baseline["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    spf = v3._d(cast(object, metrics["profit_factor"]))
    sdd = v3._d(metrics["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "loss_recall_at_least_25pct": (
            v3._d(shared["loss_rejection_recall"]) >= Decimal("0.25")
        ),
        "winner_count_retention_at_least_80pct": (
            v3._d(shared["winner_count_retention"]) >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            v3._d(economic["winner_r_retention"]) >= Decimal("0.90")
        ),
        "density_at_least_55pct": (
            v3._d(shared["density_retained"]) >= Decimal("0.55")
        ),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _passes_gates(result)
    if not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared"])
    metrics = cast(dict[str, object], shared["metrics"])
    economic = cast(dict[str, object], shared["economic_retention"])
    bpf = v3._d(cast(object, baseline["profit_factor"]))
    spf = v3._d(cast(object, metrics["profit_factor"]))
    bdd = v3._d(baseline["max_drawdown_r"])
    sdd = v3._d(metrics["max_drawdown_r"])
    return (
        (spf / bpf)
        * (bdd / max(sdd, Decimal("0.000001")))
        * v3._d(economic["winner_r_retention"])
        * (Decimal(1) + v3._d(shared["loss_rejection_recall"]))
    )


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
        calibration = _evaluate(r8_rows, r6_rows, policy)
        gates = _passes_gates(calibration)
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
            "research_phase": "PHASE_A_SHARED_DECISION_INTELLIGENCE_ONLY",
            "potentiator_status": "DEFERRED_BLOCKED",
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared_phase_a": False,
            "frontier": frontier,
            "governance": {
                "trade_potentiation_used": False,
                "risk_weighting_used": False,
                "position_potentiation_used": False,
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
    gates = _passes_gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_A_SHARED_DECISION_INTELLIGENCE_ONLY",
        "potentiator_status": "DEFERRED_BLOCKED",
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if passed
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "CLOSED_EPISODE_MEMORY",
            "r6": "MISSION1_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_TEMPORAL_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared_phase_a": passed,
        "frontier": frontier,
        "governance": {
            "trade_potentiation_used": False,
            "risk_weighting_used": False,
            "position_potentiation_used": False,
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
                "research_phase": payload["research_phase"],
                "potentiator_status": payload["potentiator_status"],
                "economic_status": payload["economic_status"],
                "frozen_policy": payload["frozen_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
                "passes_shared_phase_a": payload["passes_shared_phase_a"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
