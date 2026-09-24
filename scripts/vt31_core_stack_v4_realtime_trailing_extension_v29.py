"""VT31 Shared real-time third-eye trailing + target extension laboratory V29.

This consumed-fold laboratory measures Shared's true path-management behavior
with position size frozen. Every methodology-valid trade is taken with the same
initial position size. Shared may only:
- improve/tighten the stop,
- trail an established favorable path,
- extend the target when causal continuation capacity supports it,
- hold the original geometry.

Shared never changes sizing, capital weighting, risk budget, entry density, or
methodology. Runtime decisions use only closed causal evidence and become
effective on the next M1. R8/R6 are consumed research folds. R5 and fresh
holdouts remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_ultrafast_instinct_prearm_v27 as v27
import vt31_core_stack_v4_persistent_preentry_context_journey_v24 as v24

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentObservation,
    assess_market_environment,
)
from qore.infrastructure.core_stack_v2.instinct_intelligence import (
    SupportMethodology,
    assess_instinct,
)
from qore.infrastructure.core_stack_v2.journey_intelligence import (
    PositionJourneyEvidence,
    assess_position_journey,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathObservation,
    assess_position_path,
)
from qore.infrastructure.core_stack_v2.realtime_trade_management import (
    RealtimeTradeAction,
    RealtimeTradeManagementDirective,
    StopManagementMode,
    TargetManagementMode,
    assess_realtime_trade_management,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTransitionObservation,
    assess_market_trajectory,
)

SCHEMA = "qore.core_stack_v4.vt31.realtime_trailing_extension.v29"
IDENTITY = "VT31_NAS100_SHARED_REALTIME_TRAILING_EXTENSION_V29"
ZERO = Decimal("0")
ONE = Decimal("1")
FRICTION = Decimal("0.05")
DD_ACCEPTABLE_MAX_R = Decimal("6")
DD_EXCEPTIONAL_R = Decimal("4")
TRAJECTORY_WINDOW = v24.TRAJECTORY_WINDOW
ENVIRONMENT_WINDOW = v24.ENVIRONMENT_WINDOW
v18 = v27.v26.v18


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _clamp_bps(value: int) -> int:
    return max(0, min(10_000, value))


def _mean4(a: int, b: int, c: int, d: int) -> int:
    return (a + b + c + d) // 4


def _improve_stop(
    *,
    current: Decimal,
    candidate: Decimal,
    side: str,
) -> Decimal:
    return max(current, candidate) if side == "long" else min(current, candidate)


def _extend_target(
    *,
    current: Decimal,
    candidate: Decimal,
    side: str,
) -> Decimal:
    return max(current, candidate) if side == "long" else min(current, candidate)


def _entry_prearm_fraction(context: dict[str, object]) -> Decimal | None:
    """Carry the V27 semantic instinct protection into the fill."""
    instinct = v27._instinct(context)
    if instinct.support_methodology is SupportMethodology.IMMEDIATE_DEFENSE:
        return Decimal("0.25")
    if instinct.support_methodology is SupportMethodology.PROGRESSIVE_DEFENSE:
        return Decimal("0.50")
    return None


def _path_observation(
    *,
    as_of: object,
    state: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    current_index: int,
    environment_support_bps: int,
    environment_adverse_bps: int,
    recovery_evidence_bps: int,
) -> PositionPathObservation:
    side = cast(object, setup).side.value
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    progress_fraction = _d(state["progress_fraction"])
    close_r = _d(state["close_r"])
    efficiency = _d(state["efficiency"])
    signed_body_r = _d(state["signed_body_r"])

    observed = day_bars[fill_index : current_index + 1]
    highs = [v18.journey._bar_values(bar)[1] for bar in observed]
    lows = [v18.journey._bar_values(bar)[2] for bar in observed]
    if side == "long":
        adverse_r = max(ZERO, (entry - min(lows)) / risk)
    else:
        adverse_r = max(ZERO, (max(highs) - entry) / risk)

    return PositionPathObservation(
        as_of=cast(object, as_of),
        data_integrity_bps=9800,
        journey_progress_bps=_clamp_bps(int(max(ZERO, progress_fraction) * 10_000)),
        close_support_bps=_clamp_bps(int(5000 + close_r * 2500)),
        directional_efficiency_bps=_clamp_bps(int(5000 + efficiency * 5000)),
        favorable_excursion_bps=_clamp_bps(
            int(max(ZERO, progress_fraction) * 10_000)
        ),
        adverse_excursion_bps=_clamp_bps(int(adverse_r * 10_000)),
        favorable_body_bps=_clamp_bps(
            int(5000 + max(ZERO, signed_body_r) * 5000)
        ),
        adverse_body_bps=_clamp_bps(
            int(max(ZERO, -signed_body_r) * 10_000)
        ),
        market_support_bps=environment_support_bps,
        environment_adverse_bps=environment_adverse_bps,
        recovery_evidence_bps=recovery_evidence_bps,
    )


def _journey_evidence(
    *,
    row: dict[str, object],
    as_of: object,
    state: dict[str, object],
    environment: object,
    trajectory: object,
    transition: MarketTransitionObservation,
) -> PositionJourneyEvidence:
    efficiency = _d(state["efficiency"])
    close_r = _d(state["close_r"])
    progress = _d(state["progress_fraction"])

    directional_efficiency = _clamp_bps(int(5000 + efficiency * 5000))
    close_support = _clamp_bps(int(5000 + close_r * 2500))
    progress_bps = _clamp_bps(int(max(ZERO, progress) * 10_000))
    regime_stability = (
        cast(object, environment).market_support_bps
        + cast(object, trajectory).support_bps
    ) // 2
    liquidity_capacity = 10_000 - cast(object, environment).structural_fragility_bps
    cross_confirmation = 10_000 - cast(object, environment).cross_market_fragility_bps

    return PositionJourneyEvidence(
        trader_id="VT31_FALSIFICATION_LAB",
        market=str(row.get("market", row.get("instrument", "NAS100"))),
        side=str(row["side"]).upper(),
        opened_at=datetime.fromisoformat(str(row["filled_at"])),
        as_of=cast(object, as_of),
        data_integrity_bps=9800,
        regime_stability_bps=_clamp_bps(regime_stability),
        expansion_bps=progress_bps,
        displacement_bps=directional_efficiency,
        momentum_bps=close_support,
        liquidity_capacity_bps=_clamp_bps(liquidity_capacity),
        cross_market_confirmation_bps=_clamp_bps(cross_confirmation),
        exhaustion_bps=cast(object, environment).adverse_environment_bps,
        opposite_displacement_bps=cast(object, trajectory).adversity_bps,
        contradiction_bps=cast(object, environment).structural_fragility_bps,
        anomaly_bps=transition.anomaly_bps,
        uncertainty_bps=transition.uncertainty_bps,
    )


def _apply_directive(
    *,
    directive: RealtimeTradeManagementDirective,
    anchor_close: Decimal,
    current_stop: Decimal,
    active_target: Decimal,
    entry: Decimal,
    original_target: Decimal,
    risk: Decimal,
    side: str,
    sign: Decimal,
) -> tuple[Decimal, Decimal, bool, bool]:
    stop_changed = False
    target_changed = False

    candidate_stop: Decimal | None = None
    if directive.stop_mode is StopManagementMode.CAP_HALF_RISK:
        candidate_stop = entry - sign * risk * Decimal("0.50")
    elif directive.stop_mode is StopManagementMode.CAP_QUARTER_RISK:
        candidate_stop = entry - sign * risk * Decimal("0.25")
    elif directive.stop_mode is StopManagementMode.BREAKEVEN:
        candidate_stop = entry
    elif directive.stop_mode in {
        StopManagementMode.TRAIL_WIDE,
        StopManagementMode.TRAIL_TIGHT,
    }:
        if directive.trail_distance_r is None:
            raise AssertionError("trailing directive missing distance")
        candidate_stop = anchor_close - sign * risk * directive.trail_distance_r

    if candidate_stop is not None:
        improved = _improve_stop(
            current=current_stop,
            candidate=candidate_stop,
            side=side,
        )
        stop_changed = improved != current_stop
        current_stop = improved

    if directive.target_mode is not TargetManagementMode.KEEP:
        distance = abs(original_target - entry) * directive.target_multiplier
        candidate_target = entry + sign * distance
        extended = _extend_target(
            current=active_target,
            candidate=candidate_target,
            side=side,
        )
        target_changed = extended != active_target
        active_target = extended

    return current_stop, active_target, stop_changed, target_changed


def _simulate(
    *,
    item: dict[str, object],
    sp_by_day: object,
    us_by_day: object,
) -> dict[str, object]:
    row = cast(dict[str, object], item["row"])
    setup = item["setup"]
    day_bars = cast(tuple[object, ...], item["day_bars"])
    fill_index, _ = v18.counter._fill_and_exit_indices(setup, day_bars, row)
    side = cast(object, setup).side.value
    sign = v18.journey._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    original_target = cast(object, setup).target_price
    current_stop = cast(object, setup).stop_price
    active_target = original_target
    three_r = cast(object, setup).three_r_price
    be_armed = False

    prearm = _entry_prearm_fraction(cast(dict[str, object], item["entry_context"]))
    if prearm is not None:
        current_stop = _improve_stop(
            current=current_stop,
            candidate=entry - sign * risk * prearm,
            side=side,
        )

    transition_history = v24._seed_transition_history(
        row=row,
        setup=setup,
        day_bars=day_bars,
        fill_index=fill_index,
        sp_by_day=sp_by_day,
        us_by_day=us_by_day,
    )
    environment_history: list[MarketEnvironmentObservation] = []
    for idx, transition in enumerate(transition_history):
        trajectory = assess_market_trajectory(
            tuple(
                transition_history[
                    max(0, idx - TRAJECTORY_WINDOW + 1) : idx + 1
                ]
            )
        )
        environment_history.append(v24._environment_observation(transition, trajectory))

    path_history: list[PositionPathObservation] = []
    pending: RealtimeTradeManagementDirective | None = None
    pending_anchor_close: Decimal | None = None
    action_counts: Counter[str] = Counter()
    stop_improvements = 0
    target_extensions = 0
    max_target_multiplier = ONE
    max_stop_r = sign * (current_stop - entry) / risk

    def terminal(value: Decimal, reason: str, bar_offset: int) -> dict[str, object]:
        return {
            "net_r_after_friction": format(value - FRICTION, "f"),
            "gross_r": format(value, "f"),
            "exit_reason": reason,
            "exit_bar_offset": bar_offset,
            "prearm_fraction_r": None if prearm is None else format(prearm, "f"),
            "action_counts": dict(sorted(action_counts.items())),
            "stop_improvements": stop_improvements,
            "target_extensions": target_extensions,
            "max_target_multiplier": format(max_target_multiplier, "f"),
            "best_stop_r": format(max_stop_r, "f"),
            "sizing_changed": False,
            "density_preserved": True,
        }

    local_day = date.fromisoformat(cast(str, row["local_date"]))

    for index in range(fill_index, len(day_bars)):
        bar = day_bars[index]
        if v18.journey._local_minute(bar) >= v18.journey.LIFECYCLE_MINUTE:
            break

        opened, high, low, close = v18.journey._bar_values(bar)

        if pending is not None:
            if pending_anchor_close is None:
                raise AssertionError("pending directive missing anchor close")
            (
                current_stop,
                active_target,
                changed_stop,
                changed_target,
            ) = _apply_directive(
                directive=pending,
                anchor_close=pending_anchor_close,
                current_stop=current_stop,
                active_target=active_target,
                entry=entry,
                original_target=original_target,
                risk=risk,
                side=side,
                sign=sign,
            )
            if changed_stop:
                stop_improvements += 1
            if changed_target:
                target_extensions += 1
                max_target_multiplier = max(
                    max_target_multiplier,
                    pending.target_multiplier,
                )
            max_stop_r = max(max_stop_r, sign * (current_stop - entry) / risk)
            pending = None
            pending_anchor_close = None

            gap_through_stop = (
                opened <= current_stop
                if side == "long"
                else opened >= current_stop
            )
            if gap_through_stop:
                return terminal(
                    sign * (opened - entry) / risk,
                    "REALTIME_GAP_THROUGH_MANAGED_STOP",
                    index - fill_index,
                )

        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= active_target if side == "long" else low <= active_target
        if hit_stop and hit_target:
            return terminal(
                sign * (current_stop - entry) / risk,
                "REALTIME_STOP_FIRST_AMBIGUITY",
                index - fill_index,
            )
        if hit_stop:
            return terminal(
                sign * (current_stop - entry) / risk,
                "REALTIME_MANAGED_STOP",
                index - fill_index,
            )
        if hit_target:
            return terminal(
                abs(active_target - entry) / risk,
                (
                    "REALTIME_EXTENDED_TARGET"
                    if active_target != original_target
                    else "REALTIME_ORIGINAL_TARGET"
                ),
                index - fill_index,
            )

        if not be_armed:
            touched_three_r = high >= three_r if side == "long" else low <= three_r
            if touched_three_r:
                be_armed = True
                improved = _improve_stop(
                    current=current_stop,
                    candidate=entry,
                    side=side,
                )
                if improved != current_stop:
                    stop_improvements += 1
                current_stop = improved
                max_stop_r = max(max_stop_r, sign * (current_stop - entry) / risk)

        # The fill bar is not used for dynamic post-fill cognition because part
        # of that M1 may precede the fill. From the next full M1 onward, the
        # just-closed bar may produce a directive effective next M1.
        if index <= fill_index:
            continue

        as_of = cast(object, bar).closed_at
        nas = tuple(day_bars[: index + 1])
        sp = tuple(v18.v13._eligible(sp_by_day, local_day, as_of))
        us = tuple(v18.v13._eligible(us_by_day, local_day, as_of))
        transition = v24._market_transition_observation(
            as_of=as_of,
            side=cast(str, row["side"]),
            nas=nas,
            sp=sp,
            us=us,
        )
        transition_history.append(transition)
        trajectory = assess_market_trajectory(
            tuple(transition_history[-TRAJECTORY_WINDOW:])
        )
        environment_history.append(v24._environment_observation(transition, trajectory))
        environment = assess_market_environment(
            tuple(environment_history[-ENVIRONMENT_WINDOW:])
        )

        _, _, state = v18.counter._state_signature(
            row=row,
            bars=list(day_bars),
            setup=setup,
            fill_index=fill_index,
            current_index=index,
        )
        recovery = (
            environment.recovery_velocity_bps
            + trajectory.recovery_velocity_bps
        ) // 2
        path_history.append(
            _path_observation(
                as_of=as_of,
                state=state,
                setup=setup,
                day_bars=day_bars,
                fill_index=fill_index,
                current_index=index,
                environment_support_bps=environment.market_support_bps,
                environment_adverse_bps=environment.adverse_environment_bps,
                recovery_evidence_bps=_clamp_bps(recovery),
            )
        )
        path = assess_position_path(tuple(path_history[-4:]))

        journey = assess_position_journey(
            _journey_evidence(
                row=row,
                as_of=as_of,
                state=state,
                environment=environment,
                trajectory=trajectory,
                transition=transition,
            )
        )

        opportunity_quality = _mean4(
            environment.market_support_bps,
            trajectory.support_bps,
            10_000 - environment.cross_market_fragility_bps,
            10_000 - environment.structural_fragility_bps,
        )
        expansion_capacity = _mean4(
            environment.market_support_bps,
            trajectory.support_bps,
            10_000 - environment.structural_fragility_bps,
            10_000 - environment.cross_market_fragility_bps,
        )
        instinct = assess_instinct(
            environment,
            trajectory,
            path=path,
            opportunity_quality_bps=opportunity_quality,
            expansion_capacity_bps=expansion_capacity,
        )
        progress_bps = _clamp_bps(
            int(max(ZERO, _d(state["progress_fraction"])) * 10_000)
        )
        directive = assess_realtime_trade_management(
            instinct,
            journey,
            path,
            progress_bps=progress_bps,
        )
        action_counts[directive.action.value] += 1
        if directive.action not in {
            RealtimeTradeAction.HOLD,
            RealtimeTradeAction.INSUFFICIENT,
        }:
            pending = directive
            pending_anchor_close = close

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if v18.journey._local_minute(bar) < v18.journey.LIFECYCLE_MINUTE
    ]
    if not eligible:
        raise AssertionError("missing lifecycle bar")
    close = v18.journey._bar_values(eligible[-1])[3]
    return terminal(
        sign * (close - entry) / risk,
        "REALTIME_LIFECYCLE",
        len(eligible) - 1,
    )


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return v27._metrics(values)


def _evaluate(
    prepared: list[dict[str, object]],
    *,
    sp_by_day: object,
    us_by_day: object,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    details: list[dict[str, object]] = []
    action_counts: Counter[str] = Counter()
    stop_improvements = 0
    target_extensions = 0

    for item in prepared:
        row = cast(dict[str, object], item["row"])
        baseline_r = cast(Decimal, item["baseline_r"])
        baseline_values.append(baseline_r)
        result = _simulate(
            item=item,
            sp_by_day=sp_by_day,
            us_by_day=us_by_day,
        )
        shared_r = _d(result["net_r_after_friction"])
        shared_values.append(shared_r)
        for name, count in cast(dict[str, int], result["action_counts"]).items():
            action_counts[name] += count
        stop_improvements += int(result["stop_improvements"])
        target_extensions += int(result["target_extensions"])
        details.append(
            {
                "signal_at": row["signal_at"],
                "baseline_r": format(baseline_r, "f"),
                "shared_r": format(shared_r, "f"),
                "uplift_r": format(shared_r - baseline_r, "f"),
                **result,
            }
        )

    baseline = _metrics(baseline_values)
    shared = _metrics(shared_values)
    baseline_winner_r = _d(baseline["gross_winner_r"])
    shared_winner_r = _d(shared["gross_winner_r"])
    winner_retention = (
        ONE
        if baseline_winner_r == ZERO
        else shared_winner_r / baseline_winner_r
    )
    losses_improved = [
        x
        for x in details
        if _d(x["baseline_r"]) < ZERO
        and _d(x["shared_r"]) > _d(x["baseline_r"])
    ]
    winners_damaged = [
        x
        for x in details
        if _d(x["baseline_r"]) > ZERO
        and _d(x["shared_r"]) < _d(x["baseline_r"])
    ]
    winners_extended = [
        x
        for x in details
        if _d(x["baseline_r"]) > ZERO
        and _d(x["shared_r"]) > _d(x["baseline_r"])
    ]

    return {
        "baseline": baseline,
        "shared_v29": shared,
        "density": {
            "input": len(baseline_values),
            "kept": len(shared_values),
            "retained": "1",
            "entry_abstentions": 0,
            "position_size_changed": False,
        },
        "management": {
            "action_counts": dict(sorted(action_counts.items())),
            "stop_improvements": stop_improvements,
            "target_extensions": target_extensions,
            "losses_improved": len(losses_improved),
            "winners_damaged": len(winners_damaged),
            "winners_extended": len(winners_extended),
            "winner_r_retention": format(winner_retention, "f"),
            "net_uplift_r": format(
                sum((_d(x["uplift_r"]) for x in details), ZERO),
                "f",
            ),
            "loser_uplift_r": format(
                sum(
                    (
                        _d(x["uplift_r"])
                        for x in details
                        if _d(x["baseline_r"]) < ZERO
                    ),
                    ZERO,
                ),
                "f",
            ),
            "winner_delta_r": format(
                sum(
                    (
                        _d(x["uplift_r"])
                        for x in details
                        if _d(x["baseline_r"]) > ZERO
                    ),
                    ZERO,
                ),
                "f",
            ),
            "best_examples": sorted(
                details,
                key=lambda x: _d(x["uplift_r"]),
                reverse=True,
            )[:20],
            "worst_examples": sorted(
                details,
                key=lambda x: _d(x["uplift_r"]),
            )[:20],
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_v29"])
    management = cast(dict[str, object], result["management"])
    baseline_pf = _d(baseline["profit_factor"])
    shared_pf = _d(shared["profit_factor"])
    dd = _d(shared["max_drawdown_r"])
    return {
        "profit_factor_above_baseline": shared_pf > baseline_pf,
        "profit_factor_plus_25pct": shared_pf >= baseline_pf * Decimal("1.25"),
        "drawdown_at_most_6r": dd <= DD_ACCEPTABLE_MAX_R,
        "drawdown_below_4r_exceptional": dd < DD_EXCEPTIONAL_R,
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "density_exactly_preserved": True,
        "position_size_unchanged": True,
        "winner_r_retention_at_least_95pct": (
            _d(management["winner_r_retention"]) >= Decimal("0.95")
        ),
    }


def _hard_pass(gates: dict[str, bool]) -> bool:
    return all(
        gates.get(key, False)
        for key in (
            "profit_factor_above_baseline",
            "profit_factor_plus_25pct",
            "drawdown_at_most_6r",
            "total_r_not_lower",
            "density_exactly_preserved",
            "position_size_unchanged",
            "winner_r_retention_at_least_95pct",
        )
    )


def _governance() -> dict[str, bool]:
    return {
        "vt31_is_falsification_lab_only": True,
        "generic_instinct_engine_used": True,
        "generic_realtime_management_engine_used": True,
        "closed_m1_decisions_effective_next_m1": True,
        "same_initial_position_size": True,
        "sizing_changed": False,
        "capital_weighting_used": False,
        "risk_budget_changed": False,
        "every_methodology_entry_preserved": True,
        "entry_abstention_used": False,
        "stop_can_only_improve": True,
        "stop_widening_used": False,
        "target_can_only_hold_or_extend": True,
        "runtime_terminal_trade_outcome_used": False,
        "runtime_prior_trade_pnl_used": False,
        "future_m1_used": False,
        "r5_opened": False,
        "new_holdout_opened": False,
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
    daily = v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8 = v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6 = v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v27.v26._prepare(
        r8,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v27.v26._prepare(
        r6,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )
    r8_sp_by_day = v18.v13._group_market(r8_sp)
    r8_us_by_day = v18.v13._group_market(r8_us)
    r6_sp_by_day = v18.v13._group_market(r6_sp)
    r6_us_by_day = v18.v13._group_market(r6_us)

    r8_result = _evaluate(
        p8,
        sp_by_day=r8_sp_by_day,
        us_by_day=r8_us_by_day,
    )
    r6_result = _evaluate(
        p6,
        sp_by_day=r6_sp_by_day,
        us_by_day=r6_us_by_day,
    )
    g8 = _gates(r8_result)
    g6 = _gates(r6_result)
    passed = _hard_pass(g8) and _hard_pass(g6)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "CALIBRATION_PASSED_NEW_HOLDOUT_REQUIRED"
            if passed
            else "FALSIFIED_BEFORE_NEW_HOLDOUT"
        ),
        "owner_objective": {
            "profit_factor_must_increase": True,
            "acceptable_drawdown_r": [4, 6],
            "exceptional_drawdown_r": "<4",
            "density_must_be_preserved": True,
            "sizing_must_remain_unchanged": True,
        },
        "management_contract": {
            "trailing_stop": True,
            "loss_compression": True,
            "target_extension": True,
            "position_size_change": False,
            "capital_weighting": False,
            "entry_abstention": False,
            "stop_widening": False,
        },
        "challenge_set": {"r8": 228, "r6": 278},
        "r8": {"evaluation": r8_result, "gates": g8},
        "r6": {"evaluation": r6_result, "gates": g6},
        "passes_calibration": passed,
        "r5_opened": False,
        "new_holdout_opened": False,
        "governance": _governance(),
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
                "economic_status": payload["economic_status"],
                "passes_calibration": payload["passes_calibration"],
                "r8": payload["r8"],
                "r6": payload["r6"],
                "management_contract": payload["management_contract"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
