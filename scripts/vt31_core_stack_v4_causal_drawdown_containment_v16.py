"""VT31 Shared causal drawdown containment V16.

Owner hard target: maximum drawdown <= 6R. V15 is no longer sufficient because
its R8/R6 calibration drawdowns remain 22.87R / 25.09R.

V16 keeps the frozen V15 entry-side coherence logic as the base screen, then
adds a CURRENT-MARKET drawdown containment head to every trade that V15 would
keep, including negative_views == 0. The head only uses contemporaneous causal
channel evidence already available at decision time. It does not use equity,
prior trade outcomes, the current trade outcome, future bars, sizing, Risk or
execution authority.

R8 is discovery, R6 is calibration/freeze. R5 is deliberately not accepted.
A candidate is valid only when BOTH consumed folds satisfy every hard gate,
including DD <= 6R.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_cross_market_coherence_veto_v15 as v15
import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8

SCHEMA = "qore.core_stack_v4.vt31.causal_drawdown_containment.v16"
IDENTITY = "VT31_NAS100_SHARED_CAUSAL_DRAWDOWN_CONTAINMENT_V16"
ZERO = Decimal("0")
DD_HARD_MAX_R = Decimal("6")


@dataclass(frozen=True, slots=True)
class ContainmentPolicy:
    total_score_ceiling: float
    minimum_adverse_channels: int
    maximum_supportive_channels: int
    cross_sequence_ceiling: float
    breadth_mode: str

    def payload(self) -> dict[str, object]:
        return {
            "total_score_ceiling": self.total_score_ceiling,
            "minimum_adverse_channels": self.minimum_adverse_channels,
            "maximum_supportive_channels": self.maximum_supportive_channels,
            "cross_sequence_ceiling": self.cross_sequence_ceiling,
            "breadth_mode": self.breadth_mode,
        }


POLICIES = tuple(
    ContainmentPolicy(score, adverse, supportive, cross, breadth)
    for score in (-0.60, -0.45, -0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.35, 0.50)
    for adverse in (1, 2, 3, 4, 5)
    for supportive in (0, 1, 2, 3, 7)
    for cross in (-99.0, -0.50, -0.35, -0.25, -0.10, 0.0, 0.15)
    for breadth in ("ANY", "ADVERSE_10", "NOT_FULL_SUPPORT_3")
)


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


def _v15_base_keep(
    row: dict[str, object],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
) -> tuple[bool, dict[str, object]]:
    n_views = v13._negative_views(row, negative)
    scores = v13._channel_scores(row, model)
    total_score, supportive, adverse = v13._tail_score(scores)
    cross_score = scores.get("CROSS_SEQUENCE", 0.0)
    leader = str(row.get("peer_sequence_leader"))

    if n_views == 0:
        keep = True
        base_reason = "V15_AUTO_KEEP_N0"
    elif n_views == 1:
        rescue = (
            total_score >= v15.POLICY.score_threshold
            and supportive >= v15.POLICY.minimum_supportive_channels
            and adverse <= v15.POLICY.maximum_adverse_channels
            and cross_score >= v15.POLICY.minimum_cross_sequence_score
        )
        unilateral = leader in v15.UNILATERAL_LEADERS
        keep = rescue and not unilateral
        base_reason = (
            "V15_N1_RESCUE"
            if keep
            else "V15_N1_REJECT"
        )
    else:
        keep = False
        base_reason = "V15_N2PLUS_REJECT"

    return keep, {
        "negative_views": n_views,
        "total_score": total_score,
        "supportive_channels": supportive,
        "adverse_channels": adverse,
        "cross_sequence_score": cross_score,
        "peer_sequence_leader": leader,
        "channel_scores": scores,
        "base_reason": base_reason,
    }


def _breadth_matches(row: dict[str, object], mode: str) -> bool:
    if mode == "ANY":
        return True
    if mode == "ADVERSE_10":
        return str(row.get("breadth10")) in {"2_ADVERSE", "3_ADVERSE", "SPLIT"}
    if mode == "NOT_FULL_SUPPORT_3":
        return str(row.get("breadth3")) != "3_SUPPORT"
    raise ValueError(f"unknown breadth mode {mode}")


def _containment_veto(
    row: dict[str, object],
    decision: dict[str, object],
    policy: ContainmentPolicy,
) -> bool:
    score = float(decision["total_score"])
    adverse = int(decision["adverse_channels"])
    supportive = int(decision["supportive_channels"])
    cross = float(decision["cross_sequence_score"])
    return (
        score <= policy.total_score_ceiling
        and adverse >= policy.minimum_adverse_channels
        and supportive <= policy.maximum_supportive_channels
        and cross <= policy.cross_sequence_ceiling
        and _breadth_matches(row, policy.breadth_mode)
    )


def _evaluate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
    policy: ContainmentPolicy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    base_rejected: list[dict[str, object]] = []
    containment_vetoed: list[dict[str, object]] = []
    kept_rows: list[dict[str, object]] = []

    for source in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        row = dict(source)
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        base_keep, decision = _v15_base_keep(
            row,
            negative=negative,
            model=model,
        )
        row["v16_decision_facts"] = decision
        if not base_keep:
            base_rejected.append(row)
            continue
        if _containment_veto(row, decision, policy):
            containment_vetoed.append(row)
            continue
        kept_values.append(value)
        kept_rows.append(row)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    abstained = base_rejected + containment_vetoed
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum((v for v in baseline_values if v > 0), ZERO)
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        ZERO,
    )
    return {
        "baseline": baseline,
        "shared_v16": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_rows),
            "abstained": len(abstained),
            "v15_base_rejected": len(base_rejected),
            "containment_vetoed": len(containment_vetoed),
            "containment_vetoed_losses": sum(
                _d(row["net_r_after_friction"]) < 0 for row in containment_vetoed
            ),
            "containment_vetoed_winners": sum(
                _d(row["net_r_after_friction"]) > 0 for row in containment_vetoed
            ),
            "containment_vetoed_total_r": format(
                sum((_d(row["net_r_after_friction"]) for row in containment_vetoed), ZERO),
                "f",
            ),
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
            "density_retained": "0" if not rows else format(
                Decimal(len(kept_rows)) / Decimal(len(rows)), "f"
            ),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v16"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    return {
        "pf_plus_25pct": _d(shared["profit_factor"]) >= _d(baseline["profit_factor"]) * Decimal("1.25"),
        "dd_at_most_6r": _d(shared["max_drawdown_r"]) <= DD_HARD_MAX_R,
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
    shared = cast(dict[str, object], result["shared_v16"])
    selection = cast(dict[str, object], result["selection"])
    dd = max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
    return (
        _d(shared["profit_factor"]) / _d(baseline["profit_factor"])
        * DD_HARD_MAX_R / dd
        * _d(selection["winner_r_retention"])
        * (Decimal("1") + _d(selection["loss_rejection_recall"]))
        * _d(selection["density_retained"])
    )


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

    discovery: list[tuple[Decimal, ContainmentPolicy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(r8, negative=negative, model=model, policy=policy)
        gates = _gates(result)
        score = _score(result)
        if score is not None:
            discovery.append((score, policy))
        # Keep only potentially useful frontier rows to limit artifact size.
        if (
            _d(cast(dict[str, object], result["shared_v16"])["max_drawdown_r"]) <= Decimal("12")
            or all(gates.values())
        ):
            r8_frontier.append({
                "policy": policy.payload(),
                "result": result,
                "gates": gates,
                "score": None if score is None else format(score, "f"),
            })

    discovery.sort(key=lambda item: item[0], reverse=True)
    r8_frontier.sort(
        key=lambda item: (
            _d(cast(dict[str, object], item["result"])["shared_v16"]["max_drawdown_r"]),
            -_d(cast(dict[str, object], item["result"])["shared_v16"]["profit_factor"]),
        )
    )

    r6_frontier: list[dict[str, object]] = []
    best: tuple[Decimal, ContainmentPolicy, dict[str, object]] | None = None
    for _, policy in discovery[:240]:
        result = _evaluate(r6, negative=negative, model=model, policy=policy)
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
            "frozen_policy": None,
            "passes_calibration": False,
            "feature_model": diagnostics,
            "r8_frontier": r8_frontier[:120],
            "r6_frontier": r6_frontier[:120],
            "governance": _governance(),
        }

    score, policy, r6_result = best
    r8_result = _evaluate(r8, negative=negative, model=model, policy=policy)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "CALIBRATION_PASSED_NEW_HOLDOUT_REQUIRED",
        "owner_dd_target": {"preferred_band_r": [4, 6], "hard_max_r": "6"},
        "challenge_set": {"r8": 228, "r6": 278},
        "r5_opened": False,
        "new_holdout_opened": False,
        "frozen_policy": {
            "v15_base_policy": v15.POLICY.payload(),
            "v15_coherence_veto": {
                "reject_peer_sequence_leader": sorted(v15.UNILATERAL_LEADERS)
            },
            "drawdown_containment": policy.payload(),
            "joint_score": format(score, "f"),
        },
        "passes_calibration": True,
        "r8": {"evaluation": r8_result, "gates": _gates(r8_result)},
        "r6": {"evaluation": r6_result, "gates": _gates(r6_result)},
        "feature_model": diagnostics,
        "r8_frontier": r8_frontier[:120],
        "r6_frontier": r6_frontier[:120],
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "r5_opened": False,
        "new_holdout_opened": False,
        "owner_dd_hard_max_6r": True,
        "r8_outcomes_offline_discovery_only": True,
        "r6_outcomes_offline_calibration_only": True,
        "runtime_equity_curve_used": False,
        "runtime_prior_trade_outcomes_used": False,
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
        "production_authorized": False,
        "merge_authorized": False,
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
        "owner_dd_target": payload["owner_dd_target"],
        "passes_calibration": payload["passes_calibration"],
        "frozen_policy": payload["frozen_policy"],
        "r8": payload.get("r8"),
        "r6": payload.get("r6"),
        "r8_frontier": payload["r8_frontier"][:10],
        "r6_frontier": payload["r6_frontier"][:10],
        "r5_opened": payload["r5_opened"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
