"""High-resolution causal perception falsification for Shared x VT31.

Adds the missing decision-time perception layer before the EV ensemble:
- full closed-M1 pre-entry path state;
- H1/H4 causal state reconstructed from completed M1 bars;
- prior admitted day context;
- premarket and cash-open state;
- path efficiency / overlap;
- pre-entry FVG, sweep-reclaim and displacement counts;
- local plus cross-index context.

No current-trade outcome or future bar is an input.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import cibo_atlas_vt31_complete_behavior_explainer as complete
import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_ev_ensemble_v2 as ev
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_market_context_runtime import (
    build_higher_context,
)

SCHEMA = "qore.core_stack_v4.vt31.high_resolution_perception.v1"
IDENTITY = "VT31_NAS100_SHARED_HIGH_RESOLUTION_PERCEPTION_V4"

MICRO_PATH_FIELDS = (
    "side",
    "entry_family",
    "pre_behavior_proxy",
    "pre_path_efficiency",
    "pre_overlap_rate",
    "pre_fvg_count",
    "pre_sweep_reclaim_count",
    "pre_displacement_count",
    "pre_last5_range_fraction",
    "recent_path_efficiency_hr",
    "recent_overlap_rate_hr",
)
HIGHER_CONTEXT_FIELDS = (
    "side",
    "entry_family",
    "prior_day_state_hr",
    "prior_day_body_fraction_hr",
    "h4_state_hr",
    "h1_state_hr",
    "premarket_state_hr",
    "cash_open_state_hr",
    "position_in_prior_day_range_hr",
    "current_path_vs_previous_hr",
    "reference_width_vs_prior5_hr",
    "raid_depth_ref_hr",
)
VIEWS = {
    "MICRO_PATH": MICRO_PATH_FIELDS,
    "HIGHER_CONTEXT": HIGHER_CONTEXT_FIELDS,
    "GEOMETRY": ev.GEOMETRY_FIELDS,
    "TIMING": ev.TIMING_FIELDS,
    "REGIME": ev.REGIME_FIELDS,
    "GLOBAL": ev.GLOBAL_FIELDS,
}

POLICIES = tuple(
    ev.Policy(maximum, similarity, confidence, conflict, favorable, negatives, caution)
    for maximum in (24, 32, 48)
    for similarity in (4000, 5000)
    for confidence in (2000, 3500)
    for conflict in (Decimal("-0.05"), Decimal("0"), Decimal("0.05"))
    for favorable in (Decimal("0.20"), Decimal("0.30"))
    for negatives in (2, 3)
    for caution in (Decimal("0.25"), Decimal("0.50"))
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _range(bars: tuple[object, ...]) -> Decimal | None:
    if not bars:
        return None
    return max(_d(getattr(bar, "high")) for bar in bars) - min(
        _d(getattr(bar, "low")) for bar in bars
    )


def _raw_context(
    path: Path,
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    series, _, _, _, _, _ = load_market_evidence(path)
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[_day(getattr(bar, "opened_at"))].append(bar)
    by_day: dict[date, tuple[object, ...]] = {
        key: tuple(sorted(values, key=lambda bar: getattr(bar, "opened_at")))
        for key, values in grouped.items()
    }
    context_map = specialist._context_map(by_day)

    output: list[dict[str, object]] = []
    for source in rows:
        row = dict(source)
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        day_bars = by_day.get(local_day)
        if day_bars is None:
            raise ValueError(f"missing raw M1 day {local_day}")
        decision_at = v3._dt(row["signal_at"])
        prior_path, prior_ref_median, prior_day_bars = context_map[local_day]

        reference = tuple(
            bar
            for bar in day_bars
            if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
        )
        if len(reference) != 60:
            raise ValueError(f"incomplete reference {local_day}")
        ref_high = max(_d(getattr(bar, "high")) for bar in reference)
        ref_low = min(_d(getattr(bar, "low")) for bar in reference)
        ref_width = ref_high - ref_low

        pre_entry = tuple(
            bar
            for bar in day_bars
            if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
            and getattr(bar, "closed_at") <= decision_at
        )
        pre_state = complete.pre_entry_state(cast(tuple, pre_entry))
        higher = build_higher_context(
            day_bars=cast(tuple, day_bars),
            prior_admitted_day_bars=cast(tuple, prior_day_bars),
            decision_at=decision_at,
            side=str(row["side"]),
            reference_high=ref_high,
            reference_low=ref_low,
        )

        current_path = tuple(
            bar
            for bar in day_bars
            if (0, 0, 0) <= _wall(getattr(bar, "opened_at")) < (16, 0, 0)
            and getattr(bar, "closed_at") <= decision_at
        )
        current_range = _range(current_path)
        current_ratio = (
            None
            if current_range is None or prior_path is None or prior_path <= 0
            else current_range / prior_path
        )
        ref_ratio = (
            None
            if prior_ref_median is None or prior_ref_median <= 0
            else ref_width / prior_ref_median
        )

        row.update(
            {
                "pre_behavior_proxy": str(
                    pre_state.get("behavior_proxy", "unavailable")
                ),
                "pre_path_efficiency": str(
                    pre_state.get("path_efficiency", "unavailable")
                ),
                "pre_overlap_rate": str(
                    pre_state.get("overlap_rate", "unavailable")
                ),
                "pre_fvg_count": str(
                    pre_state.get("fvg_count", "unavailable")
                ),
                "pre_sweep_reclaim_count": str(
                    pre_state.get("local_sweep_reclaim_count", "unavailable")
                ),
                "pre_displacement_count": str(
                    pre_state.get("displacement_event_count", "unavailable")
                ),
                "pre_last5_range_fraction": str(
                    pre_state.get(
                        "last5_range_to_full_pre_entry_range",
                        "unavailable",
                    )
                ),
                "prior_day_state_hr": higher.prior_day_state,
                "prior_day_body_fraction_hr": (
                    "unavailable"
                    if higher.prior_day_body_fraction is None
                    else format(higher.prior_day_body_fraction, "f")
                ),
                "h4_state_hr": higher.h4_state,
                "h1_state_hr": higher.h1_state,
                "premarket_state_hr": higher.premarket_state,
                "cash_open_state_hr": higher.cash_open_state,
                "position_in_prior_day_range_hr": (
                    higher.position_in_prior_day_range
                ),
                "raid_depth_ref_hr": (
                    "unavailable"
                    if higher.raid_depth_ref is None
                    else format(higher.raid_depth_ref, "f")
                ),
                "recent_path_efficiency_hr": (
                    "unavailable"
                    if higher.recent_path_efficiency is None
                    else format(higher.recent_path_efficiency, "f")
                ),
                "recent_overlap_rate_hr": (
                    "unavailable"
                    if higher.recent_overlap_rate is None
                    else format(higher.recent_overlap_rate, "f")
                ),
                "current_path_vs_previous_hr": (
                    "unavailable"
                    if current_ratio is None
                    else format(current_ratio, "f")
                ),
                "reference_width_vs_prior5_hr": (
                    "unavailable"
                    if ref_ratio is None
                    else format(ref_ratio, "f")
                ),
            }
        )
        output.append(row)
    return output


def _ensemble(
    memories: dict[str, object],
    row: dict[str, object],
    policy: ev.Policy,
) -> dict[str, object]:
    views: dict[str, dict[str, object]] = {}
    weighted_ev = Decimal(0)
    confidence_sum = Decimal(0)
    negative = 0
    positive = 0
    confident = 0

    for name, fields in VIEWS.items():
        memory = cast(object, memories[name])
        view = ev._analog_economics(
            cast(object, memory),
            row,
            fields,
            policy,
        )
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
        value = Decimal(str(ev_raw))
        weight = Decimal(confidence) / Decimal(10_000)
        weighted_ev += value * weight
        confidence_sum += weight
        if value < policy.conflict_ev_r:
            negative += 1
        if value >= policy.favorable_ev_r:
            positive += 1

    ensemble_ev = None if confidence_sum == 0 else weighted_ev / confidence_sum
    if ensemble_ev is None or confident < 3:
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


def _evaluate(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: ev.Policy,
) -> dict[str, object]:
    memories = {
        name: ev._memory(history, fields)
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
        row["shared_high_resolution"] = view
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
            "economic_retention": ev._economic_retention(rows, abstained),
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


def run(
    r8_trades: Path,
    r6_trades: Path,
    r5_trades: Path,
    r8_raw: Path,
    r6_raw: Path,
    r5_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8 = _raw_context(
        r8_raw,
        v3._decorate(v3._load_trades(r8_trades), daily),
    )
    r6 = _raw_context(
        r6_raw,
        v3._decorate(v3._load_trades(r6_trades), daily),
    )
    r5 = _raw_context(
        r5_raw,
        v3._decorate(v3._load_trades(r5_trades), daily),
    )
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, ev.Policy] | None = None
    for policy in POLICIES:
        result = _evaluate(r8, r6, policy)
        score = ev._calibration_score(result)
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
            "passes_high_resolution": False,
            "frontier": frontier,
            "governance": {
                "methodology_modified": False,
                "current_outcome_used": False,
                "future_m1_used": False,
                "r5_retuned": False,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(r8 + r6, r5, frozen)
    gates = ev._final_gates(evaluation)
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
            "r8": "DISCOVERY_HIGH_RESOLUTION_CAUSAL_MEMORY",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "NO_RETUNE_TEMPORAL_EVALUATION",
        },
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_high_resolution": all(gates.values()),
        "governance": {
            "methodology_modified": False,
            "current_outcome_used": False,
            "future_m1_used": False,
            "historical_closed_outcomes_allowed": True,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
        "frontier": frontier,
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
        args.r8_trades,
        args.r6_trades,
        args.r5_trades,
        args.r8_raw,
        args.r6_raw,
        args.r5_raw,
        args.daily_path,
    )
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
                "passes_high_resolution": payload["passes_high_resolution"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
