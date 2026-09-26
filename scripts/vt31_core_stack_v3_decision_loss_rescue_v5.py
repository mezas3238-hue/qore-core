"""Shared Decision Intelligence V5: aggressive loss detector + winner rescue.

The V4 temporal-invariance lab became too conservative on R5:
19/275 losses avoided. Its calibration frontier proved the opposite extreme can
reach ~25.5% loss recall, but sacrifices too much winner R.

V5 separates the pre-entry problem:
1. LOSS DETECTOR: aggressive negative-EV ensemble.
2. WINNER RESCUE: vetoes an abstention when rare/high-payoff positive analogs
   are strongly similar, especially in the recent closed regime.

No journey management, no capital weighting, no execution authority.
R8 -> calibration memory; R6 -> freeze; R5 -> no-retune evaluation.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

from qore.infrastructure.core_stack_v2.analog_memory import (
    AnalogQuery,
    CausalAnalogMemory,
)

SCHEMA = "qore.core_stack_v3.vt31.decision_loss_rescue.v5"
IDENTITY = "VT31_NAS100_SHARED_DECISION_LOSS_DETECTOR_WINNER_RESCUE_V5"


@dataclass(frozen=True, slots=True)
class RescuePolicy:
    loss_policy: decision.Policy
    recent_fraction_numerator: int
    recent_fraction_denominator: int
    rescue_similarity_bps: int
    rescue_minimum_views: int
    rescue_minimum_winner_r: Decimal
    recent_positive_ev_r: Decimal
    recent_positive_views: int
    recent_minimum_confidence_bps: int
    recent_minimum_effective_n: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "loss_policy": self.loss_policy.payload(),
            "recent_fraction": (
                f"{self.recent_fraction_numerator}/"
                f"{self.recent_fraction_denominator}"
            ),
            "rescue_similarity_bps": self.rescue_similarity_bps,
            "rescue_minimum_views": self.rescue_minimum_views,
            "rescue_minimum_winner_r": format(
                self.rescue_minimum_winner_r, "f"
            ),
            "recent_positive_ev_r": format(self.recent_positive_ev_r, "f"),
            "recent_positive_views": self.recent_positive_views,
            "recent_minimum_confidence_bps": (
                self.recent_minimum_confidence_bps
            ),
            "recent_minimum_effective_n": format(
                self.recent_minimum_effective_n, "f"
            ),
        }


LOSS_POLICIES = (
    decision.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        abstain_ev_r=Decimal("-0.05"),
        required_negative_views=2,
        maximum_positive_views=0,
        winner_archetype_ev_floor=Decimal("0.30"),
        winner_archetype_payoff_floor=Decimal("2.5"),
        tail_mean_win_r_floor=Decimal("4.5"),
        tail_payoff_floor=Decimal("3"),
        tail_min_win_rate=Decimal("0.12"),
    ),
    decision.Policy(
        maximum_analogs=32,
        minimum_similarity_bps=6500,
        minimum_confidence_bps=2500,
        abstain_ev_r=Decimal("-0.10"),
        required_negative_views=2,
        maximum_positive_views=0,
        winner_archetype_ev_floor=Decimal("0.30"),
        winner_archetype_payoff_floor=Decimal("2.5"),
        tail_mean_win_r_floor=Decimal("4.5"),
        tail_payoff_floor=Decimal("3"),
        tail_min_win_rate=Decimal("0.12"),
    ),
)

POLICIES = tuple(
    RescuePolicy(
        loss_policy=loss_policy,
        recent_fraction_numerator=recent_num,
        recent_fraction_denominator=2,
        rescue_similarity_bps=similarity,
        rescue_minimum_views=rescue_views,
        rescue_minimum_winner_r=winner_r,
        recent_positive_ev_r=recent_ev,
        recent_positive_views=recent_views,
        recent_minimum_confidence_bps=1500,
        recent_minimum_effective_n=Decimal("4"),
    )
    for loss_policy in LOSS_POLICIES
    for recent_num in (1,)
    for similarity in (8000, 8500, 9000, 9500)
    for rescue_views in (1, 2)
    for winner_r in (Decimal("1.5"), Decimal("2.5"), Decimal("4"))
    for recent_ev in (Decimal("0.10"), Decimal("0.20"))
    for recent_views in (1, 2)
)


def _recent_slice(
    rows: list[dict[str, object]],
    numerator: int,
    denominator: int,
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    count = max(1, len(ordered) * numerator // denominator)
    return ordered[-count:]


def _memories(
    rows: list[dict[str, object]],
) -> dict[str, CausalAnalogMemory]:
    return {
        name: decision._memory(rows, fields)
        for name, fields in decision.VIEWS.items()
    }


def _winner_rescue_view(
    memory: CausalAnalogMemory,
    row: dict[str, object],
    fields: tuple[str, ...],
    policy: RescuePolicy,
) -> dict[str, object]:
    summary = memory.query(
        AnalogQuery(
            market="NAS100",
            as_of=v3._dt(row["signal_at"]),
            signature=v3._signature(row, fields),
            maximum_analogs=policy.loss_policy.maximum_analogs,
            minimum_similarity_bps=policy.loss_policy.minimum_similarity_bps,
        )
    )
    positives = [
        item
        for item in summary.analogs
        if Decimal(item.terminal_r) >= policy.rescue_minimum_winner_r
    ]
    max_similarity = max(
        (item.similarity_bps for item in positives),
        default=0,
    )
    very_close = sum(
        item.similarity_bps >= policy.rescue_similarity_bps
        for item in positives
    )
    return {
        "positive_analog_count": len(positives),
        "max_positive_similarity_bps": max_similarity,
        "very_close_positive_count": very_close,
        "effective_n": summary.effective_sample_size,
        "confidence_bps": summary.confidence_bps,
    }


def _recent_positive_view(
    memory: CausalAnalogMemory,
    row: dict[str, object],
    fields: tuple[str, ...],
    policy: RescuePolicy,
) -> dict[str, object]:
    item = decision._view(
        memory,
        row,
        fields,
        policy.loss_policy,
    )
    ev_raw = item["ev_r"]
    confident = (
        ev_raw is not None
        and int(item["confidence_bps"])
        >= policy.recent_minimum_confidence_bps
        and Decimal(str(item["effective_n"]))
        >= policy.recent_minimum_effective_n
    )
    positive = (
        confident
        and Decimal(str(ev_raw)) >= policy.recent_positive_ev_r
    )
    return {
        "positive": positive,
        "ev_r": ev_raw,
        "confidence_bps": item["confidence_bps"],
        "effective_n": item["effective_n"],
    }


def _decision(
    *,
    long_memories: dict[str, CausalAnalogMemory],
    recent_memories: dict[str, CausalAnalogMemory],
    row: dict[str, object],
    policy: RescuePolicy,
) -> dict[str, object]:
    loss = decision._decision(
        long_memories,
        row,
        policy.loss_policy,
    )
    if loss["action"] != "ABSTAIN_SHADOW":
        return {
            "action": "PASS",
            "loss_detector": loss,
            "rescued": False,
            "rescue_reason": None,
        }

    long_rescue_views = 0
    recent_rescue_views = 0
    recent_positive_views = 0
    rescue_detail: dict[str, object] = {}

    for name, fields in decision.VIEWS.items():
        long_winner = _winner_rescue_view(
            long_memories[name],
            row,
            fields,
            policy,
        )
        recent_winner = _winner_rescue_view(
            recent_memories[name],
            row,
            fields,
            policy,
        )
        recent_positive = _recent_positive_view(
            recent_memories[name],
            row,
            fields,
            policy,
        )
        if (
            int(long_winner["max_positive_similarity_bps"])
            >= policy.rescue_similarity_bps
        ):
            long_rescue_views += 1
        if (
            int(recent_winner["max_positive_similarity_bps"])
            >= policy.rescue_similarity_bps
        ):
            recent_rescue_views += 1
        if bool(recent_positive["positive"]):
            recent_positive_views += 1
        rescue_detail[name] = {
            "long_winner": long_winner,
            "recent_winner": recent_winner,
            "recent_positive": recent_positive,
        }

    rare_winner_rescue = (
        long_rescue_views >= policy.rescue_minimum_views
        and recent_rescue_views >= 1
    )
    regime_positive_rescue = (
        recent_positive_views >= policy.recent_positive_views
    )
    rescued = rare_winner_rescue or regime_positive_rescue
    if rare_winner_rescue:
        reason = "RARE_WINNER_ANALOG_RESCUE"
    elif regime_positive_rescue:
        reason = "RECENT_REGIME_POSITIVE_RESCUE"
    else:
        reason = None

    return {
        "action": "PASS_RESCUED" if rescued else "ABSTAIN_SHADOW",
        "loss_detector": loss,
        "rescued": rescued,
        "rescue_reason": reason,
        "long_rescue_views": long_rescue_views,
        "recent_rescue_views": recent_rescue_views,
        "recent_positive_views": recent_positive_views,
        "rescue_detail": rescue_detail,
    }


def _metrics(
    values: list[Decimal],
) -> dict[str, object]:
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
    *,
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: RescuePolicy,
) -> dict[str, object]:
    recent = _recent_slice(
        history,
        policy.recent_fraction_numerator,
        policy.recent_fraction_denominator,
    )
    long_memories = _memories(history)
    recent_memories = _memories(recent)

    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []
    rescue_reasons: dict[str, int] = {}

    for source in sorted(rows, key=lambda row: cast(str, row["signal_at"])):
        value = v3._d(source["net_r_after_friction"])
        baseline_values.append(value)
        verdict = _decision(
            long_memories=long_memories,
            recent_memories=recent_memories,
            row=source,
            policy=policy,
        )
        if verdict["action"] == "ABSTAIN_SHADOW":
            abstained.append(source)
            continue
        kept_values.append(value)
        if bool(verdict["rescued"]):
            rescued.append(source)
            reason = str(verdict["rescue_reason"])
            rescue_reasons[reason] = rescue_reasons.get(reason, 0) + 1

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        v3._d(row["net_r_after_friction"]) < 0
        for row in abstained
    )
    winners_sacrificed = sum(
        v3._d(row["net_r_after_friction"]) > 0
        for row in abstained
    )
    rescued_winners = sum(
        v3._d(row["net_r_after_friction"]) > 0
        for row in rescued
    )
    rescued_losses = sum(
        v3._d(row["net_r_after_friction"]) < 0
        for row in rescued
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
                    Decimal(losses_avoided) / Decimal(base_losses),
                    "f",
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
                    Decimal(len(kept_values)) / Decimal(len(rows)),
                    "f",
                )
            ),
            "rescued_trades": len(rescued),
            "rescued_winners": rescued_winners,
            "rescued_losses": rescued_losses,
            "rescue_precision": (
                "0"
                if not rescued
                else format(
                    Decimal(rescued_winners) / Decimal(len(rescued)),
                    "f",
                )
            ),
            "rescue_reasons": dict(sorted(rescue_reasons.items())),
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
            v3._d(selection["winner_count_retention"])
            >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            v3._d(selection["winner_r_retention"])
            >= Decimal("0.90")
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
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8 = v3._decorate(v3._load_trades(r8_json), daily)
    r6 = v3._decorate(v3._load_trades(r6_json), daily)
    r5 = v3._decorate(v3._load_trades(r5_json), daily)
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, RescuePolicy] | None = None
    for policy in POLICIES:
        calibration = _evaluate(
            history=r8,
            rows=r6,
            policy=policy,
        )
        gates = _gates(calibration)
        score = _score(calibration)
        frontier.append({
            "policy": policy.payload(),
            "calibration": calibration,
            "gates": gates,
            "selection_score": None if score is None else format(score, "f"),
        })
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
            "passes_shared_decision": False,
            "frontier": frontier,
            "governance": {
                "loss_detector_and_winner_rescue_separate": True,
                "journey_management_used": False,
                "capital_risk_weighting_used": False,
                "current_outcome_used": False,
                "r5_retuned": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(
        history=r8 + r6,
        rows=r5,
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
            "r8": "LOSS_DETECTOR_WINNER_RESCUE_CALIBRATION_MEMORY",
            "r6": "POLICY_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared_decision": passed,
        "frontier": frontier,
        "governance": {
            "loss_detector_and_winner_rescue_separate": True,
            "journey_management_used": False,
            "capital_risk_weighting_used": False,
            "current_outcome_used": False,
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_shared_decision": payload["passes_shared_decision"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
