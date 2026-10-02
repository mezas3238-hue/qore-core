"""VT31 Shared causal journey defense V17.

V16 proved that entry rejection alone can approach 6R drawdown only by destroying
winner-R and density. V17 therefore keeps the V15 causal entry screen and moves
drawdown control into the open-trade journey.

For every V15-kept trade, V17 observes only CLOSED NAS100 M1 bars after fill.
A DEFEND decision becomes effective at the NEXT M1 open. The stop is never
widened, sizing is never changed, and no equity-curve or prior-trade outcome is
an input. Offline R8/R6 outcomes are used only to discover/calibrate a fixed
causal invalidation rule.

R8 = discovery. R6 = calibration/freeze. R5 is not accepted.
Owner hard gate: maximum drawdown <= 6R on BOTH folds while preserving PF,
density, entry winner retention and >=90% selected winner-R through journey.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_integrated_shared_intelligence_v1 as journey
import vt31_core_stack_v3_journey_counterfactual_memory_v2 as counter
import vt31_core_stack_v4_cross_market_coherence_veto_v15 as v15
import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8

SCHEMA = "qore.core_stack_v4.vt31.causal_journey_defense.v17"
IDENTITY = "VT31_NAS100_SHARED_CAUSAL_JOURNEY_DEFENSE_V17"
FRICTION = Decimal("0.05")
ZERO = Decimal("0")
DD_HARD_MAX_R = Decimal("6")


@dataclass(frozen=True, slots=True)
class DefensePolicy:
    max_close_r: Decimal
    max_efficiency: Decimal
    max_signed_body_r: Decimal
    minimum_adverse_bodies: int
    mode: str
    minimum_minutes: int

    def payload(self) -> dict[str, object]:
        return {
            "max_close_r": format(self.max_close_r, "f"),
            "max_efficiency": format(self.max_efficiency, "f"),
            "max_signed_body_r": format(self.max_signed_body_r, "f"),
            "minimum_adverse_bodies": self.minimum_adverse_bodies,
            "mode": self.mode,
            "minimum_minutes": self.minimum_minutes,
        }


POLICIES = tuple(
    DefensePolicy(close_r, efficiency, body, adverse, mode, minutes)
    for close_r in (
        Decimal("0"),
        Decimal("-0.10"),
        Decimal("-0.25"),
        Decimal("-0.50"),
    )
    for efficiency in (
        Decimal("0.25"),
        Decimal("0"),
        Decimal("-0.20"),
        Decimal("-0.40"),
    )
    for body in (
        Decimal("0"),
        Decimal("-0.10"),
        Decimal("-0.25"),
        Decimal("-0.40"),
    )
    for adverse in (0, 1, 2)
    for mode in ("ANY", "NON_TREND", "TRANSITION_ANOMALOUS")
    for minutes in (1, 3, 5)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _v15_keep(
    row: dict[str, object],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
) -> bool:
    n_views = v13._negative_views(row, negative)
    if n_views == 0:
        return True
    if n_views != 1:
        return False
    scores = v13._channel_scores(row, model)
    total_score, supportive, adverse = v13._tail_score(scores)
    cross_score = scores.get("CROSS_SEQUENCE", 0.0)
    rescue = (
        total_score >= v15.POLICY.score_threshold
        and supportive >= v15.POLICY.minimum_supportive_channels
        and adverse <= v15.POLICY.maximum_adverse_channels
        and cross_score >= v15.POLICY.minimum_cross_sequence_score
    )
    unilateral = str(row.get("peer_sequence_leader")) in v15.UNILATERAL_LEADERS
    return rescue and not unilateral


def _mode_ok(mode: str, policy_mode: str) -> bool:
    if policy_mode == "ANY":
        return True
    if policy_mode == "NON_TREND":
        return mode != "TREND"
    if policy_mode == "TRANSITION_ANOMALOUS":
        return mode in {"TRANSITION", "ANOMALOUS"}
    raise ValueError(f"unknown defense mode {policy_mode}")


def _event_matches(event: dict[str, object], policy: DefensePolicy) -> bool:
    return (
        int(event["minutes_since_fill"]) >= policy.minimum_minutes
        and _d(event["close_r"]) <= policy.max_close_r
        and _d(event["efficiency"]) <= policy.max_efficiency
        and _d(event["signed_body_r"]) <= policy.max_signed_body_r
        and int(event["adverse_body_count"]) >= policy.minimum_adverse_bodies
        and _mode_ok(str(event["mode"]), policy.mode)
    )


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
        "gross_winner_r": format(gains, "f"),
        "gross_loss_r": format(losses, "f"),
    }


def _prepare_fold(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
    nas_evidence: Path,
) -> list[dict[str, object]]:
    paths = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        journey._reconstruct_partition(nas_evidence),
    )
    prepared: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = _d(row["net_r_after_friction"])
        keep = _v15_keep(row, negative=negative, model=model)
        item: dict[str, object] = {
            "row": row,
            "baseline_r": baseline_r,
            "entry_keep": keep,
            "events": [],
        }
        if not keep:
            prepared.append(item)
            continue

        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        fill_index, exit_index = counter._fill_and_exit_indices(setup, day_bars, row)
        events: list[dict[str, object]] = []
        for snapshot_index in range(fill_index + 1, exit_index):
            _, _, state = counter._state_signature(
                row=row,
                bars=list(day_bars),
                setup=setup,
                fill_index=fill_index,
                current_index=snapshot_index,
            )
            defense = counter._defend_counterfactual(
                setup=setup,
                day_bars=day_bars,
                snapshot_index=snapshot_index,
            )
            if defense is None:
                continue
            observed = list(day_bars[fill_index : snapshot_index + 1])
            adverse_count = journey._adverse_confirmation_count(
                observed,
                side=cast(object, setup).side.value,
                risk=cast(object, setup).initial_risk,
                body_threshold=Decimal("0.10"),
            )
            events.append({
                **state,
                "adverse_body_count": adverse_count,
                "defense_r_after_friction": format(defense - FRICTION, "f"),
            })
        item["events"] = events
        prepared.append(item)
    return prepared


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: DefensePolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    selected_baseline: list[Decimal] = []
    shared_values: list[Decimal] = []
    rejected_rows: list[dict[str, object]] = []
    defended: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        if not bool(item["entry_keep"]):
            rejected_rows.append(row)
            continue
        selected_baseline.append(baseline_r)
        shared_r = baseline_r
        for event in cast(list[dict[str, object]], item["events"]):
            if _event_matches(event, policy):
                shared_r = _d(event["defense_r_after_friction"])
                defended.append({
                    "signal_at": row["signal_at"],
                    "baseline_r": format(baseline_r, "f"),
                    "defense_r": format(shared_r, "f"),
                    "uplift_r": format(shared_r - baseline_r, "f"),
                    "event": event,
                })
                break
        shared_values.append(shared_r)

    baseline = _metrics(baseline_values)
    selected = _metrics(selected_baseline)
    shared = _metrics(shared_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in rejected_rows)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in rejected_rows)
    gross_winner_r = _d(baseline["gross_winner_r"])
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in rejected_rows
            if _d(row["net_r_after_friction"]) > 0
        ),
        ZERO,
    )
    selected_winner_r = _d(selected["gross_winner_r"])
    journey_winner_retention = (
        Decimal("1")
        if selected_winner_r == 0
        else _d(shared["gross_winner_r"]) / selected_winner_r
    )
    return {
        "baseline": baseline,
        "selected_baseline_before_journey": selected,
        "shared_v17": shared,
        "selection": {
            "input": len(prepared),
            "kept": len(shared_values),
            "abstained": len(rejected_rows),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": "0" if base_losses == 0 else format(
                Decimal(losses_avoided) / Decimal(base_losses), "f"
            ),
            "winner_count_retention": "0" if base_wins == 0 else format(
                Decimal(base_wins - winners_sacrificed) / Decimal(base_wins), "f"
            ),
            "winner_r_retention": "1" if gross_winner_r == 0 else format(
                (gross_winner_r - sacrificed_r) / gross_winner_r, "f"
            ),
            "density_retained": "0" if not prepared else format(
                Decimal(len(shared_values)) / Decimal(len(prepared)), "f"
            ),
        },
        "journey": {
            "defended_trades": len(defended),
            "defended_baseline_losses": sum(_d(item["baseline_r"]) < 0 for item in defended),
            "defended_baseline_winners": sum(_d(item["baseline_r"]) > 0 for item in defended),
            "defense_total_uplift_r": format(
                sum((_d(item["uplift_r"]) for item in defended), ZERO), "f"
            ),
            "selected_winner_r_retention_after_defense": format(
                journey_winner_retention, "f"
            ),
            "best_defense_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_defense_examples": sorted(
                defended,
                key=lambda item: _d(item["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v17"])
    selection = cast(dict[str, object], result["selection"])
    journey_stats = cast(dict[str, object], result["journey"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    return {
        "pf_plus_25pct": _d(shared["profit_factor"]) >= _d(baseline["profit_factor"]) * Decimal("1.25"),
        "dd_at_most_6r": _d(shared["max_drawdown_r"]) <= DD_HARD_MAX_R,
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": _d(selection["loss_rejection_recall"]) >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": _d(selection["winner_count_retention"]) >= Decimal("0.80"),
        "entry_winner_r_retention_at_least_90pct": _d(selection["winner_r_retention"]) >= Decimal("0.90"),
        "journey_winner_r_retention_at_least_90pct": _d(
            journey_stats["selected_winner_r_retention_after_defense"]
        ) >= Decimal("0.90"),
        "density_at_least_55pct": _d(selection["density_retained"]) >= Decimal("0.55"),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v17"])
    journey_stats = cast(dict[str, object], result["journey"])
    dd = max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
    return (
        _d(shared["profit_factor"]) / _d(baseline["profit_factor"])
        * DD_HARD_MAX_R / dd
        * _d(journey_stats["selected_winner_r_retention_after_defense"])
    )


def _load_cross_rows(
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


def _governance() -> dict[str, bool]:
    return {
        "owner_dd_hard_max_6r": True,
        "r5_opened": False,
        "new_holdout_opened": False,
        "v15_entry_identity_base": True,
        "defense_next_m1_open_only": True,
        "stop_widening_used": False,
        "runtime_equity_curve_used": False,
        "runtime_prior_trade_outcomes_used": False,
        "runtime_current_outcome_used": False,
        "historical_outcomes_offline_calibration_only": True,
        "future_m1_used": False,
        "capital_risk_weighting_used": False,
        "methodology_entry_modified": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
        "live_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
    }


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
    r8 = _load_cross_rows(
        trades=r8_trades, nas=r8_nas, sp=r8_sp, us=r8_us, daily=daily
    )
    r6 = _load_cross_rows(
        trades=r6_trades, nas=r6_nas, sp=r6_sp, us=r6_us, daily=daily
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    r8_n1 = [row for row in r8 if v13._negative_views(row, negative) == 1]
    model, diagnostics = v13._learn_model(r8_n1)
    p8 = _prepare_fold(r8, negative=negative, model=model, nas_evidence=r8_nas)
    p6 = _prepare_fold(r6, negative=negative, model=model, nas_evidence=r6_nas)

    discovery: list[tuple[Decimal, DefensePolicy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(p8, policy=policy)
        gates = _gates(result)
        score = _score(result)
        if score is not None:
            discovery.append((score, policy))
        if _d(cast(dict[str, object], result["shared_v17"])["max_drawdown_r"]) <= Decimal("12"):
            r8_frontier.append({
                "policy": policy.payload(),
                "result": result,
                "gates": gates,
                "score": None if score is None else format(score, "f"),
            })
    discovery.sort(key=lambda item: item[0], reverse=True)
    r8_frontier.sort(
        key=lambda item: (
            _d(cast(dict[str, object], item["result"])["shared_v17"]["max_drawdown_r"]),
            -_d(cast(dict[str, object], item["result"])["shared_v17"]["profit_factor"]),
        )
    )

    r6_frontier: list[dict[str, object]] = []
    best: tuple[Decimal, DefensePolicy, dict[str, object]] | None = None
    for _, policy in discovery[:160]:
        result = _evaluate(p6, policy=policy)
        gates = _gates(result)
        score = _score(result)
        r6_frontier.append({
            "policy": policy.payload(),
            "result": result,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy, result)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_BEFORE_NEW_HOLDOUT",
            "owner_dd_target": {"preferred_band_r": [4, 6], "hard_max_r": "6"},
            "challenge_set": {"r8": 228, "r6": 278},
            "r5_opened": False,
            "new_holdout_opened": False,
            "passes_calibration": False,
            "frozen_policy": None,
            "feature_model": diagnostics,
            "r8_frontier": r8_frontier[:100],
            "r6_frontier": r6_frontier[:100],
            "governance": _governance(),
        }

    score, policy, r6_result = best
    r8_result = _evaluate(p8, policy=policy)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "CALIBRATION_PASSED_NEW_HOLDOUT_REQUIRED",
        "owner_dd_target": {"preferred_band_r": [4, 6], "hard_max_r": "6"},
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "passes_calibration": True,
        "frozen_policy": {
            "v15_entry_policy": v15.POLICY.payload(),
            "v15_coherence_veto": sorted(v15.UNILATERAL_LEADERS),
            "journey_defense": policy.payload(),
            "joint_score": format(score, "f"),
        },
        "r8": {"evaluation": r8_result, "gates": _gates(r8_result)},
        "r6": {"evaluation": r6_result, "gates": _gates(r6_result)},
        "feature_model": diagnostics,
        "r8_frontier": r8_frontier[:100],
        "r6_frontier": r6_frontier[:100],
        "governance": _governance(),
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
        "passes_calibration": payload["passes_calibration"],
        "owner_dd_target": payload["owner_dd_target"],
        "frozen_policy": payload["frozen_policy"],
        "r8": payload.get("r8"),
        "r6": payload.get("r6"),
        "r8_frontier": payload["r8_frontier"][:10],
        "r6_frontier": payload["r6_frontier"][:10],
        "r5_opened": payload["r5_opened"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
