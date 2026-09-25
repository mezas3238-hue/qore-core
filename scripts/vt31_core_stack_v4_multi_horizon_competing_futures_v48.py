"""VT31 Shared multi-horizon competing-futures diagnostic V48.

Root-engineering diagnostic for phase-1 natural DD intelligence.

Unlike the phenotype laboratories, V48 performs no outcome-driven rule
selection. For every methodology-valid R8/R6 trade it reconstructs up to 60
closed M1 observations before fill and builds fixed causal horizons:

    5m / 15m / 30m / 60m

The generic Shared competing-futures engine then distinguishes:
- TERMINAL_ADVERSE
- RECOVERABLE_ADVERSE
- SUPPORTIVE
- CONFLICTED
- INSUFFICIENT

Only after the causal assessment is frozen for each trade are realized outcomes
used offline to measure whether Shared distinguished future SL from future
profit. No thresholds are fitted to outcomes and no policy grid exists.

No sizing, weighting, abstention, stop/target mutation, trailing, target
extension, R5, fresh holdout, LIVE or production.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_persistent_preentry_context_journey_v24 as v24
import vt31_core_stack_v4_universal_dd_phenotype_registry_v41 as v41

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CausalHorizonSnapshot,
    CompetingFutureAssessment,
    CompetingFutureState,
    assess_competing_futures,
)
from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentObservation,
    assess_market_environment,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
    assess_market_trajectory,
)

SCHEMA = "qore.core_stack_v4.vt31.multi_horizon_competing_futures.v48"
IDENTITY = "VT31_NAS100_SHARED_MULTI_HORIZON_COMPETING_FUTURES_V48"
ZERO = Decimal("0")
HORIZONS = (5, 15, 30, 60)

v26 = v41.v26
v18 = v41.v18


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _seed_history(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    sp_by_day: object,
    us_by_day: object,
) -> list[MarketTransitionObservation]:
    side = cast(str, row["side"])
    local_day = datetime.fromisoformat(cast(str, row["filled_at"])).date()
    start = max(0, fill_index - max(HORIZONS))
    history: list[MarketTransitionObservation] = []

    for index in range(start, fill_index):
        bar = day_bars[index]
        as_of = cast(object, bar).closed_at
        nas = tuple(day_bars[: index + 1])
        sp = tuple(v18.v13._eligible(sp_by_day, local_day, as_of))
        us = tuple(v18.v13._eligible(us_by_day, local_day, as_of))
        history.append(
            v24._market_transition_observation(
                as_of=as_of,
                side=side,
                nas=nas,
                sp=sp,
                us=us,
            )
        )
    return history


def _environment_for_window(
    window: tuple[MarketTransitionObservation, ...],
) -> object:
    environment_history: list[MarketEnvironmentObservation] = []
    for index, transition in enumerate(window):
        trajectory = assess_market_trajectory(tuple(window[: index + 1]))
        environment_history.append(
            v24._environment_observation(transition, trajectory)
        )
    return assess_market_environment(tuple(environment_history))


def _horizon_snapshot(
    history: list[MarketTransitionObservation],
    *,
    horizon: int,
) -> CausalHorizonSnapshot | None:
    if len(history) < 5:
        return None
    size = min(horizon, len(history))
    if size < 5:
        return None
    window = tuple(history[-size:])
    trajectory = assess_market_trajectory(window)
    environment = _environment_for_window(window)
    latest = window[-1]

    return CausalHorizonSnapshot(
        horizon_minutes=horizon,
        as_of=latest.as_of,
        evidence_count=len(window),
        data_integrity_bps=min(item.data_integrity_bps for item in window),
        support_bps=trajectory.support_bps,
        adversity_bps=trajectory.adversity_bps,
        deterioration_velocity_bps=trajectory.deterioration_velocity_bps,
        recovery_velocity_bps=trajectory.recovery_velocity_bps,
        deterioration_persistence_bps=trajectory.deterioration_persistence_bps,
        recovery_persistence_bps=trajectory.recovery_persistence_bps,
        cross_market_confirmation_bps=latest.cross_market_confirmation_bps,
        cross_market_fragility_bps=environment.cross_market_fragility_bps,
        structural_fragility_bps=environment.structural_fragility_bps,
        trend_support_bps=latest.trend_support_bps,
        uncertainty_bps=latest.uncertainty_bps,
    )


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
    history = _seed_history(
        row=row,
        setup=setup,
        day_bars=day_bars,
        fill_index=fill_index,
        sp_by_day=sp_by_day,
        us_by_day=us_by_day,
    )
    snapshots = tuple(
        snapshot
        for horizon in HORIZONS
        if (
            snapshot := _horizon_snapshot(
                history,
                horizon=horizon,
            )
        )
        is not None
    )

    if not snapshots:
        assessment: CompetingFutureAssessment | None = None
        state = CompetingFutureState.INSUFFICIENT
    else:
        assessment = assess_competing_futures(snapshots)
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
            snapshot.horizon_minutes for snapshot in snapshots
        ),
        "assessment": (
            None
            if assessment is None
            else {
                "terminal_horizon_count": assessment.terminal_horizon_count,
                "recovery_horizon_count": assessment.recovery_horizon_count,
                "conflicted_horizon_count": assessment.conflicted_horizon_count,
                "terminal_evidence_bps": assessment.terminal_evidence_bps,
                "recovery_evidence_bps": assessment.recovery_evidence_bps,
                "separation_margin_bps": assessment.separation_margin_bps,
                "horizon_agreement_bps": assessment.horizon_agreement_bps,
                "confidence_bps": assessment.confidence_bps,
                "reasons": assessment.reasons,
                "horizon_votes": tuple(
                    {
                        "horizon_minutes": vote.horizon_minutes,
                        "state": vote.state.value,
                        "terminal_evidence_count": vote.terminal_evidence_count,
                        "recovery_evidence_count": vote.recovery_evidence_count,
                        "terminal_channels": vote.terminal_channels,
                        "recovery_channels": vote.recovery_channels,
                    }
                    for vote in assessment.horizon_votes
                ),
            }
        ),
    }


def _evaluate(rows: list[dict[str, object]]) -> dict[str, object]:
    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]
    terminal = [
        row for row in rows if row["state"] == CompetingFutureState.TERMINAL_ADVERSE.value
    ]
    recoverable = [
        row for row in rows if row["state"] == CompetingFutureState.RECOVERABLE_ADVERSE.value
    ]
    supportive = [
        row for row in rows if row["state"] == CompetingFutureState.SUPPORTIVE.value
    ]
    conflicted = [
        row for row in rows if row["state"] == CompetingFutureState.CONFLICTED.value
    ]
    insufficient = [
        row for row in rows if row["state"] == CompetingFutureState.INSUFFICIENT.value
    ]

    terminal_losses = [row for row in terminal if row["outcome"] == "LOSS"]
    terminal_winners = [row for row in terminal if row["outcome"] == "WIN"]
    recovery_winners = [
        row
        for row in (*recoverable, *supportive)
        if row["outcome"] == "WIN"
    ]
    recovery_losses = [
        row
        for row in (*recoverable, *supportive)
        if row["outcome"] == "LOSS"
    ]

    terminal_loss_r = -sum((_d(row["baseline_r"]) for row in terminal_losses), ZERO)
    terminal_winner_r = sum((_d(row["baseline_r"]) for row in terminal_winners), ZERO)
    recovery_winner_r = sum((_d(row["baseline_r"]) for row in recovery_winners), ZERO)
    recovery_loss_r = -sum((_d(row["baseline_r"]) for row in recovery_losses), ZERO)

    decided = terminal + recoverable + supportive
    correctly_decided = len(terminal_losses) + len(recovery_winners)

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
        "recoverable_or_supportive": {
            "sample": len(recoverable) + len(supportive),
            "winners": len(recovery_winners),
            "losses": len(recovery_losses),
            "winner_precision": _ratio(
                len(recovery_winners),
                len(recoverable) + len(supportive),
            ),
            "winner_recall": _ratio(len(recovery_winners), len(winners)),
            "winner_r_identified": format(recovery_winner_r, "f"),
            "loss_r_exposure": format(recovery_loss_r, "f"),
        },
        "conflicted": len(conflicted),
        "insufficient": len(insufficient),
        "decided_sample": len(decided),
        "decided_accuracy": _ratio(correctly_decided, len(decided)),
        "forced_binary_guess_used": False,
    }


def _quarter_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    n = len(ordered)
    bounds = [0, n // 4, n // 2, (3 * n) // 4, n]
    return [
        {
            "quarter": index + 1,
            "first_signal_at": (
                None if not ordered[bounds[index] : bounds[index + 1]]
                else ordered[bounds[index]]["signal_at"]
            ),
            "last_signal_at": (
                None if not ordered[bounds[index] : bounds[index + 1]]
                else ordered[bounds[index + 1] - 1]["signal_at"]
            ),
            "evaluation": _evaluate(ordered[bounds[index] : bounds[index + 1]]),
        }
        for index in range(4)
    ]


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
    return {
        "evaluation": _evaluate(rows),
        "quarters": _quarter_summary(rows),
        "rows": rows,
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
        "status": "MULTI_HORIZON_COMPETING_FUTURES_DIAGNOSTIC_NO_ACTUATION",
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
            "realized_dd_reduction_claimed": False,
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
                "r8_quarters": payload["r8"]["quarters"],
                "r6_quarters": payload["r6"]["quarters"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
