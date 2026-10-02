"""VT31 Shared cross-market coherence veto V15.

Frozen calibration identity derived from Cross-Market Sequence V13 plus the
R8/R6-stable causal finding from DD-tail diagnostics V14:

A dangerous N1 opportunity must NOT be rescued when SP500 and US30 confirmation
onsets are asynchronous enough to designate one peer as the sequence leader.
Those unilateral-leader rescue states were loss-only in both consumed folds.

The rule is market-state causal: it reads only closed M1 peer sequence timing.
It does not use the current trade outcome, future bars, sizing, Risk authority,
execution authority, or an exact historical analog.

R8 and R6 are consumed discovery/calibration. R5 is deliberately not accepted
as an input. Passing both folds freezes the identity and requires a new holdout.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8

SCHEMA = "qore.core_stack_v4.vt31.cross_market_coherence_veto.v15"
IDENTITY = "VT31_NAS100_SHARED_CROSS_MARKET_COHERENCE_VETO_V15"
ZERO = Decimal("0")
POLICY = v13.Policy(
    score_threshold=0.0,
    minimum_supportive_channels=1,
    maximum_adverse_channels=4,
    minimum_cross_sequence_score=-0.25,
    rescue_n2_threshold=None,
)
UNILATERAL_LEADERS = frozenset({"SP500", "US30"})


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _metrics(values: list[Decimal]) -> dict[str, object]:
    gains = sum((v for v in values if v > 0), ZERO)
    losses = -sum((v for v in values if v < 0), ZERO)
    total = sum(values, ZERO)
    equity = peak = dd = ZERO
    streak = maximum = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            maximum = max(maximum, streak)
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
        "max_losing_streak": maximum,
    }


def _evaluate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []
    coherence_vetoed: list[dict[str, object]] = []

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        n_views = v13._negative_views(row, negative)
        if n_views == 0:
            kept_values.append(value)
            continue

        scores = v13._channel_scores(row, model)
        total_score, supportive, adverse = v13._tail_score(scores)
        cross_score = scores.get("CROSS_SEQUENCE", 0.0)
        rescue = False
        if n_views == 1:
            rescue = (
                total_score >= POLICY.score_threshold
                and supportive >= POLICY.minimum_supportive_channels
                and adverse <= POLICY.maximum_adverse_channels
                and cross_score >= POLICY.minimum_cross_sequence_score
            )

        unilateral = str(row.get("peer_sequence_leader")) in UNILATERAL_LEADERS
        if rescue and unilateral:
            rescue = False
            item = dict(row)
            item["coherence_veto"] = {
                "peer_sequence_leader": row.get("peer_sequence_leader"),
                "peer_confirmation_latency": row.get("peer_confirmation_latency"),
                "peer_sync3": row.get("peer_sync3"),
                "breadth3": row.get("breadth3"),
                "breadth_transition": row.get("breadth_transition"),
                "negative_views": n_views,
                "tail_score": total_score,
                "cross_sequence_score": cross_score,
            }
            coherence_vetoed.append(item)

        if rescue:
            kept_values.append(value)
            rescued.append(row)
        else:
            abstained.append(row)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum((v for v in baseline_values if v > 0), ZERO)
    sacrificed_r = sum(
        (_d(row["net_r_after_friction"]) for row in abstained if _d(row["net_r_after_friction"]) > 0),
        ZERO,
    )
    return {
        "baseline": baseline,
        "shared_cross_market_coherence": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": "0" if base_losses == 0 else format(Decimal(losses_avoided) / Decimal(base_losses), "f"),
            "winner_count_retention": "0" if base_wins == 0 else format(Decimal(base_wins - winners_sacrificed) / Decimal(base_wins), "f"),
            "winner_r_retention": "1" if gross_winner_r == 0 else format((gross_winner_r - sacrificed_r) / gross_winner_r, "f"),
            "density_retained": "0" if not rows else format(Decimal(len(kept_values)) / Decimal(len(rows)), "f"),
            "rescued_trades": len(rescued),
            "rescued_winners": sum(_d(row["net_r_after_friction"]) > 0 for row in rescued),
            "rescued_losses": sum(_d(row["net_r_after_friction"]) < 0 for row in rescued),
            "coherence_vetoed": len(coherence_vetoed),
            "coherence_vetoed_winners": sum(_d(row["net_r_after_friction"]) > 0 for row in coherence_vetoed),
            "coherence_vetoed_losses": sum(_d(row["net_r_after_friction"]) < 0 for row in coherence_vetoed),
            "coherence_vetoed_total_r": format(sum((_d(row["net_r_after_friction"]) for row in coherence_vetoed), ZERO), "f"),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_cross_market_coherence"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    return {
        "pf_plus_25pct": _d(shared["profit_factor"]) >= _d(baseline["profit_factor"]) * Decimal("1.25"),
        "dd_minus_30pct": _d(shared["max_drawdown_r"]) <= _d(baseline["max_drawdown_r"]) * Decimal("0.70"),
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": _d(selection["loss_rejection_recall"]) >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": _d(selection["winner_count_retention"]) >= Decimal("0.80"),
        "winner_r_retention_at_least_90pct": _d(selection["winner_r_retention"]) >= Decimal("0.90"),
        "density_at_least_55pct": _d(selection["density_retained"]) >= Decimal("0.55"),
    }


def _load(
    *,
    trades: Path,
    nas: Path,
    sp: Path,
    us: Path,
    daily: object,
) -> list[dict[str, object]]:
    return v13._cross_rows(
        nas_path=nas,
        sp_path=sp,
        us_path=us,
        rows=v2.v3._decorate(v2.v3._load_trades(trades), daily),
    )


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = _load(trades=r8_trades, nas=r8_nas, sp=r8_sp, us=r8_us, daily=daily)
    r6 = _load(trades=r6_trades, nas=r6_nas, sp=r6_sp, us=r6_us, daily=daily)
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    r8_n1 = [row for row in r8 if v13._negative_views(row, negative) == 1]
    model, diagnostics = v13._learn_model(r8_n1)

    e8 = _evaluate(r8, negative=negative, model=model)
    e6 = _evaluate(r6, negative=negative, model=model)
    g8 = _gates(e8)
    g6 = _gates(e6)
    passed = all(g8.values()) and all(g6.values())

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "CALIBRATION_PASSED_HOLDOUT_REQUIRED" if passed else "FALSIFIED_BEFORE_NEW_HOLDOUT",
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "frozen_policy": {
            "base_policy": POLICY.payload(),
            "coherence_veto": {
                "field": "peer_sequence_leader",
                "reject_values": sorted(UNILATERAL_LEADERS),
                "semantics": "N1_RESCUE_REQUIRES_NO_UNILATERAL_PEER_ONSET_LEADER",
            },
        } if passed else None,
        "r8": {"evaluation": e8, "gates": g8},
        "r6": {"evaluation": e6, "gates": g6},
        "feature_model": diagnostics,
        "passes_calibration": passed,
        "governance": {
            "r5_opened": False,
            "new_holdout_opened": False,
            "r8_outcomes_offline_discovery_only": True,
            "r6_outcomes_offline_calibration_only": True,
            "runtime_current_outcome_used": False,
            "runtime_exact_state_lookup_used": False,
            "runtime_nearest_neighbor_used": False,
            "three_index_closed_m1_used": True,
            "future_m1_used": False,
            "capital_risk_weighting_used": False,
            "methodology_modified": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    for fold in ("r8", "r6"):
        parser.add_argument(f"--{fold}-nas", type=Path, required=True)
        parser.add_argument(f"--{fold}-sp", type=Path, required=True)
        parser.add_argument(f"--{fold}-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "r5_opened": payload["r5_opened"],
        "new_holdout_opened": payload["new_holdout_opened"],
        "passes_calibration": payload["passes_calibration"],
        "frozen_policy": payload["frozen_policy"],
        "r8": payload["r8"],
        "r6": payload["r6"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
