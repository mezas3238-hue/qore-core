"""VT31 Shared cross-market journey defense V18.

V17 falsified NAS100-only journey invalidation under the Owner DD <= 6R target.
V18 adds CLOSED-M1 SP500 and US30 post-entry confirmation to the defense head.

The V15 entry identity remains the base. For an open V15-kept trade, Shared may
DEFEND at the NEXT NAS100 M1 open only when local deterioration and a specified
cross-market adverse condition are both present. Runtime inputs are current
closed bars only. No equity curve, prior trade outcome, current outcome, future
bar, sizing, Risk or execution authority is used.

R8 = discovery, R6 = calibration/freeze. R5 is not accepted.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_integrated_shared_intelligence_v1 as journey
import vt31_core_stack_v3_journey_counterfactual_memory_v2 as counter
import vt31_core_stack_v4_causal_journey_defense_v17 as v17
import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8

SCHEMA = "qore.core_stack_v4.vt31.cross_market_journey_defense.v18"
IDENTITY = "VT31_NAS100_SHARED_CROSS_MARKET_JOURNEY_DEFENSE_V18"
FRICTION = Decimal("0.05")
ZERO = Decimal("0")
DD_HARD_MAX_R = Decimal("6")


@dataclass(frozen=True, slots=True)
class CrossDefensePolicy:
    max_close_r: Decimal
    max_efficiency: Decimal
    max_signed_body_r: Decimal
    cross_mode: str
    minimum_minutes: int

    def payload(self) -> dict[str, object]:
        return {
            "max_close_r": format(self.max_close_r, "f"),
            "max_efficiency": format(self.max_efficiency, "f"),
            "max_signed_body_r": format(self.max_signed_body_r, "f"),
            "cross_mode": self.cross_mode,
            "minimum_minutes": self.minimum_minutes,
        }


POLICIES = tuple(
    CrossDefensePolicy(close_r, efficiency, body, cross_mode, minutes)
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
    for cross_mode in (
        "BOTH_PEERS_ADVERSE3",
        "BREADTH3_ADVERSE",
        "BREADTH10_ADVERSE",
        "BREADTH3_OR_10_ADVERSE",
        "BREADTH10_ADVERSE_NOT_FULL_SUPPORT3",
    )
    for minutes in (1, 3, 5)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _cross_ok(event: dict[str, object], mode: str) -> bool:
    sync3 = str(event["peer_sync3"])
    breadth3 = str(event["breadth3"])
    breadth10 = str(event["breadth10"])
    b3_bad = breadth3 in {"2_ADVERSE", "3_ADVERSE"}
    b10_bad = breadth10 in {"2_ADVERSE", "3_ADVERSE"}
    if mode == "BOTH_PEERS_ADVERSE3":
        return sync3 == "BOTH_ADVERSE"
    if mode == "BREADTH3_ADVERSE":
        return b3_bad
    if mode == "BREADTH10_ADVERSE":
        return b10_bad
    if mode == "BREADTH3_OR_10_ADVERSE":
        return b3_bad or b10_bad
    if mode == "BREADTH10_ADVERSE_NOT_FULL_SUPPORT3":
        return b10_bad and breadth3 != "3_SUPPORT"
    raise ValueError(f"unknown cross mode {mode}")


def _event_matches(event: dict[str, object], policy: CrossDefensePolicy) -> bool:
    return (
        int(event["minutes_since_fill"]) >= policy.minimum_minutes
        and _d(event["close_r"]) <= policy.max_close_r
        and _d(event["efficiency"]) <= policy.max_efficiency
        and _d(event["signed_body_r"]) <= policy.max_signed_body_r
        and _cross_ok(event, policy.cross_mode)
    )


def _prepare_fold(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
    nas_evidence: Path,
    sp_evidence: Path,
    us_evidence: Path,
) -> list[dict[str, object]]:
    paths = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        journey._reconstruct_partition(nas_evidence),
    )
    sp_by_day = v13._group_market(sp_evidence)
    us_by_day = v13._group_market(us_evidence)

    prepared: list[dict[str, object]] = []
    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = _d(row["net_r_after_friction"])
        keep = v17._v15_keep(row, negative=negative, model=model)
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
        side = cast(str, row["side"])
        local_day = date.fromisoformat(cast(str, row["local_date"]))
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
            snapshot_bar = day_bars[snapshot_index]
            decision_at = cast(object, snapshot_bar).closed_at
            nas_observed = tuple(day_bars[fill_index : snapshot_index + 1])
            sp = v13._eligible(sp_by_day, local_day, decision_at)
            us = v13._eligible(us_by_day, local_day, decision_at)
            nas3 = v13._signed_move(nas_observed, side=side, window=3)
            nas10 = v13._signed_move(nas_observed, side=side, window=10)
            sp3 = v13._signed_move(sp, side=side, window=3)
            sp10 = v13._signed_move(sp, side=side, window=10)
            us3 = v13._signed_move(us, side=side, window=3)
            us10 = v13._signed_move(us, side=side, window=10)
            events.append({
                **state,
                "peer_sync3": v13._sync(sp3, us3),
                "breadth3": v13._breadth((nas3, sp3, us3)),
                "breadth10": v13._breadth((nas10, sp10, us10)),
                "sp500_transition": v13._transition(sp3, sp10),
                "us30_transition": v13._transition(us3, us10),
                "defense_r_after_friction": format(defense - FRICTION, "f"),
            })
        item["events"] = events
        prepared.append(item)
    return prepared


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    policy: CrossDefensePolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    selected_baseline: list[Decimal] = []
    shared_values: list[Decimal] = []
    rejected: list[dict[str, object]] = []
    defended: list[dict[str, object]] = []

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        if not bool(item["entry_keep"]):
            rejected.append(row)
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

    baseline = v17._metrics(baseline_values)
    selected = v17._metrics(selected_baseline)
    shared = v17._metrics(shared_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in rejected)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in rejected)
    gross_winner_r = _d(baseline["gross_winner_r"])
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in rejected
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
        "shared_v18": shared,
        "selection": {
            "input": len(prepared),
            "kept": len(shared_values),
            "abstained": len(rejected),
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
                defended, key=lambda item: _d(item["uplift_r"]), reverse=True
            )[:20],
            "worst_defense_examples": sorted(
                defended, key=lambda item: _d(item["uplift_r"])
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v18"])
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
    shared = cast(dict[str, object], result["shared_v18"])
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
        "three_index_post_entry_closed_m1_used": True,
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
    p8 = _prepare_fold(
        r8, negative=negative, model=model,
        nas_evidence=r8_nas, sp_evidence=r8_sp, us_evidence=r8_us,
    )
    p6 = _prepare_fold(
        r6, negative=negative, model=model,
        nas_evidence=r6_nas, sp_evidence=r6_sp, us_evidence=r6_us,
    )

    discovery: list[tuple[Decimal, CrossDefensePolicy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(p8, policy=policy)
        gates = _gates(result)
        score = _score(result)
        if score is not None:
            discovery.append((score, policy))
        if _d(cast(dict[str, object], result["shared_v18"])["max_drawdown_r"]) <= Decimal("12"):
            r8_frontier.append({
                "policy": policy.payload(),
                "result": result,
                "gates": gates,
                "score": None if score is None else format(score, "f"),
            })
    discovery.sort(key=lambda item: item[0], reverse=True)
    r8_frontier.sort(
        key=lambda item: (
            _d(cast(dict[str, object], item["result"])["shared_v18"]["max_drawdown_r"]),
            -_d(cast(dict[str, object], item["result"])["shared_v18"]["profit_factor"]),
        )
    )

    r6_frontier: list[dict[str, object]] = []
    best: tuple[Decimal, CrossDefensePolicy, dict[str, object]] | None = None
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
            "cross_market_journey_defense": policy.payload(),
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
