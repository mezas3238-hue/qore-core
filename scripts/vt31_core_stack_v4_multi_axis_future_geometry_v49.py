"""VT31 Shared multi-axis future geometry diagnostic V49.

Root-engineering validation after V48.

V48 showed that scalar/relational competing-futures scoring still confused many
large winners with terminal adversity. V49 keeps every causal axis separate and
builds horizon geometry from the raw MarketTransitionObservation path.

No outcome-driven rule selection, no numeric grid search, no sizing, no
abstention, no stop/target mutation, no trailing, no target extension.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_multi_horizon_competing_futures_v48 as v48

from qore.infrastructure.core_stack_v2.future_geometry_intelligence import (
    FutureGeometryAssessment,
    FutureGeometryState,
    assess_future_geometry,
    build_horizon_geometry,
)

SCHEMA = "qore.core_stack_v4.vt31.multi_axis_future_geometry.v49"
IDENTITY = "VT31_NAS100_SHARED_MULTI_AXIS_FUTURE_GEOMETRY_V49"
ZERO = Decimal("0")
HORIZONS = (5, 15, 30, 60)

v41 = v48.v41
v26 = v48.v26
v18 = v48.v18


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _assess_item(
    item: dict[str, object],
    *,
    sp_by_day: object,
    us_by_day: object,
) -> dict[str, object]:
    row = cast(dict[str, object], item["row"])
    setup = item["setup"]
    day_bars = cast(tuple[object, ...], item["day_bars"])
    fill_index, _ = v18.counter._fill_and_exit_indices(
        setup,
        day_bars,
        row,
    )
    history = v48._seed_history(
        row=row,
        setup=setup,
        day_bars=day_bars,
        fill_index=fill_index,
        sp_by_day=sp_by_day,
        us_by_day=us_by_day,
    )

    geometries = []
    for horizon in HORIZONS:
        if len(history) < 2:
            continue
        window = tuple(history[-min(horizon, len(history)):])
        if len(window) < 2:
            continue
        geometries.append(
            build_horizon_geometry(
                window,
                horizon_minutes=horizon,
            )
        )

    if not geometries:
        assessment: FutureGeometryAssessment | None = None
        state = FutureGeometryState.INSUFFICIENT
    else:
        assessment = assess_future_geometry(tuple(geometries))
        state = assessment.state

    baseline_r = cast(Decimal, item["baseline_r"])
    return {
        "signal_at": row["signal_at"],
        "filled_at": row["filled_at"],
        "baseline_r": format(baseline_r, "f"),
        "outcome": (
            "LOSS" if baseline_r < ZERO else "WIN" if baseline_r > ZERO else "FLAT"
        ),
        "state": state.value,
        "history_observations": len(history),
        "horizons_available": tuple(
            geometry.horizon_minutes for geometry in geometries
        ),
        "assessment": (
            None
            if assessment is None
            else {
                "collapse_horizon_count": assessment.collapse_horizon_count,
                "recovery_horizon_count": assessment.recovery_horizon_count,
                "resilient_horizon_count": assessment.resilient_horizon_count,
                "conflicted_horizon_count": assessment.conflicted_horizon_count,
                "broad_state": assessment.broad_state.value,
                "fast_state": assessment.fast_state.value,
                "structural_agreement_bps": assessment.structural_agreement_bps,
                "reasons": assessment.reasons,
                "horizons": tuple(
                    {
                        "horizon_minutes": geometry.horizon_minutes,
                        "state": geometry.state.value,
                        "supportive_level_count": geometry.supportive_level_count,
                        "adverse_level_count": geometry.adverse_level_count,
                        "support_improving_count": geometry.support_improving_count,
                        "support_weakening_count": geometry.support_weakening_count,
                        "adversity_rising_count": geometry.adversity_rising_count,
                        "adversity_falling_count": geometry.adversity_falling_count,
                        "recovery_core_count": geometry.recovery_core_count,
                        "terminal_core_count": geometry.terminal_core_count,
                    }
                    for geometry in assessment.horizons
                ),
            }
        ),
    }


def _evaluate(rows: list[dict[str, object]]) -> dict[str, object]:
    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]
    terminal = [
        row
        for row in rows
        if row["state"] == FutureGeometryState.TERMINAL_COLLAPSE.value
    ]
    recovery = [
        row
        for row in rows
        if row["state"]
        in {
            FutureGeometryState.RECOVERABLE_ADVERSITY.value,
            FutureGeometryState.SUPPORTIVE_CONTINUATION.value,
        }
    ]
    conflicted = [
        row
        for row in rows
        if row["state"] == FutureGeometryState.CONFLICTED.value
    ]
    insufficient = [
        row
        for row in rows
        if row["state"] == FutureGeometryState.INSUFFICIENT.value
    ]

    terminal_losses = [row for row in terminal if row["outcome"] == "LOSS"]
    terminal_winners = [row for row in terminal if row["outcome"] == "WIN"]
    recovery_winners = [row for row in recovery if row["outcome"] == "WIN"]
    recovery_losses = [row for row in recovery if row["outcome"] == "LOSS"]

    terminal_loss_r = -sum((_d(row["baseline_r"]) for row in terminal_losses), ZERO)
    terminal_winner_r = sum((_d(row["baseline_r"]) for row in terminal_winners), ZERO)
    recovery_winner_r = sum((_d(row["baseline_r"]) for row in recovery_winners), ZERO)
    recovery_loss_r = -sum((_d(row["baseline_r"]) for row in recovery_losses), ZERO)

    decided = terminal + recovery
    correct = len(terminal_losses) + len(recovery_winners)

    return {
        "sample": len(rows),
        "losses": len(losses),
        "winners": len(winners),
        "state_counts": dict(sorted(Counter(str(row["state"]) for row in rows).items())),
        "terminal": {
            "sample": len(terminal),
            "losses": len(terminal_losses),
            "winners": len(terminal_winners),
            "loss_precision": _ratio(len(terminal_losses), len(terminal)),
            "loss_recall": _ratio(len(terminal_losses), len(losses)),
            "winner_false_positive_rate": _ratio(
                len(terminal_winners),
                len(winners),
            ),
            "loss_r_identified": format(terminal_loss_r, "f"),
            "winner_r_exposure": format(terminal_winner_r, "f"),
            "largest_false_winners": sorted(
                (
                    {
                        "signal_at": row["signal_at"],
                        "baseline_r": row["baseline_r"],
                        "assessment": row["assessment"],
                    }
                    for row in terminal_winners
                ),
                key=lambda row: _d(row["baseline_r"]),
                reverse=True,
            )[:20],
        },
        "recovery_or_supportive": {
            "sample": len(recovery),
            "winners": len(recovery_winners),
            "losses": len(recovery_losses),
            "winner_precision": _ratio(len(recovery_winners), len(recovery)),
            "winner_recall": _ratio(len(recovery_winners), len(winners)),
            "winner_r_identified": format(recovery_winner_r, "f"),
            "loss_r_exposure": format(recovery_loss_r, "f"),
        },
        "conflicted": len(conflicted),
        "insufficient": len(insufficient),
        "decided_sample": len(decided),
        "decided_accuracy": _ratio(correct, len(decided)),
        "forced_binary_guess_used": False,
    }


def _fold(
    prepared: list[dict[str, object]],
    *,
    sp_evidence: Path,
    us_evidence: Path,
) -> dict[str, object]:
    sp_by_day = v18.v13._group_market(sp_evidence)
    us_by_day = v18.v13._group_market(us_evidence)
    rows = [
        _assess_item(
            item,
            sp_by_day=sp_by_day,
            us_by_day=us_by_day,
        )
        for item in prepared
    ]
    return {"evaluation": _evaluate(rows), "rows": rows}


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
    daily = v41.v33.v32.v31.v30.v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(
        daily_path
    )
    r8_source = v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6_source = v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v26._prepare(
        r8_source,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v26._prepare(
        r6_source,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "MULTI_AXIS_FUTURE_GEOMETRY_DIAGNOSTIC_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "fixed_horizons_minutes": HORIZONS,
        "outcome_driven_rule_selection_used": False,
        "numeric_threshold_grid_search": False,
        "r8": _fold(p8, sp_evidence=r8_sp, us_evidence=r8_us),
        "r6": _fold(p6, sp_evidence=r6_sp, us_evidence=r6_us),
        "phase_1_contract": {
            "same_trade_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "entry_abstention_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "runtime_outcome_input_used": False,
            "future_market_input_used": False,
            "historical_outcome_lookup_in_assessment_used": False,
            "forced_binary_guess_used": False,
            "r5_opened": False,
            "new_holdout_opened": False,
        },
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
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
    print(
        json.dumps(
            {
                "status": payload["status"],
                "r8": payload["r8"]["evaluation"],
                "r6": payload["r6"]["evaluation"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
