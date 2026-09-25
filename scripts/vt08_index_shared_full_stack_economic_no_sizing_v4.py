"""Economic replay of full Shared Core against VT08 Index with sizing frozen.

This is the actuation follow-up to V3.  VT08 contributes the methodology-valid
opportunity universe and deterministic M15 execution surface.  Shared supplies
all cognition.  Every opportunity is entered at the same initial 1R size.

Shared may only improve/hold the stop, trail, hold/extend the target, and reason
from causally available market state plus already-closed Shared-managed history.
It may not resize, risk-weight, suppress an entry, remove a market, filter a
calendar/year, widen a stop, or look up the current/future trade outcome.

Management directives become active only after the M15 bar that produced them,
so same-bar favorable ordering is never credited.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import bisect
import heapq
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import vt08_index_shared_full_stack_no_sizing_v3 as v3

from qore.infrastructure.core_stack_v2.instinct_intelligence import assess_instinct
from qore.infrastructure.core_stack_v2.journey_intelligence import (
    PositionJourneyEvidence,
    assess_position_journey,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathObservation,
    assess_position_path,
)
from qore.infrastructure.core_stack_v2.realtime_trade_management import (
    StopManagementMode,
    TargetManagementMode,
    assess_realtime_trade_management,
)
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _intrabar_exit,
)

SCHEMA = "qore.shared.vt08_index.full_stack_economic_replay.v4"
IDENTITY = "QORE_SHARED_VT08_INDEX_FULL_STACK_ECONOMIC_NO_SIZING_V4"
ZERO = Decimal("0")
ONE = Decimal("1")
TARGET_R = Decimal("2.5")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class ManagedReplay:
    trade_id: int
    market: str
    signal_at: datetime
    exited_at: datetime
    r_multiple: Decimal
    exit_reason: str
    stop_change_count: int
    target_extension_count: int
    action_counts: tuple[tuple[str, int], ...]
    maximum_target_r: Decimal
    maximum_locked_r: Decimal
    bars_observed: int


def _clip(value: int) -> int:
    return max(0, min(10_000, int(value)))


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _side_sign(side: str) -> Decimal:
    return ONE if side == "long" else Decimal("-1")


def _price_at_r(entry: Decimal, risk: Decimal, side: str, level_r: Decimal) -> Decimal:
    return entry + _side_sign(side) * risk * level_r


def _r_at_price(entry: Decimal, risk: Decimal, side: str, price: Decimal) -> Decimal:
    if side == "long":
        return (price - entry) / risk
    return (entry - price) / risk


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


def _apply_directive(
    *,
    directive: object,
    anchor_close: Decimal,
    entry: Decimal,
    risk: Decimal,
    side: str,
    current_stop: Decimal,
    active_target: Decimal,
    original_target: Decimal,
) -> tuple[Decimal, Decimal, bool, bool]:
    sign = _side_sign(side)
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
            raise ValueError("Shared trailing directive missing causal distance")
        candidate_stop = anchor_close - sign * risk * directive.trail_distance_r

    stop_changed = False
    if candidate_stop is not None:
        improved = _improve_stop(
            current=current_stop,
            candidate=candidate_stop,
            side=side,
        )
        stop_changed = improved != current_stop
        current_stop = improved

    target_changed = False
    if directive.target_mode is not TargetManagementMode.KEEP:
        base_distance = abs(original_target - entry)
        candidate_target = entry + sign * base_distance * directive.target_multiplier
        extended = _extend_target(
            current=active_target,
            candidate=candidate_target,
            side=side,
        )
        target_changed = extended != active_target
        active_target = extended

    return current_stop, active_target, stop_changed, target_changed


def _directive_at_close(
    item: object,
    *,
    entry_context: dict[str, object],
    bar: object,
    max_mfe_r: Decimal,
    max_mae_r: Decimal,
    path_history: list[PositionPathObservation],
    bars_by_symbol: dict[str, tuple[object, ...]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> object:
    signal = item.opportunity.signal
    symbol = str(signal.symbol)
    side = str(signal.side.value).lower()
    risk = abs(_d(signal.entry) - _d(signal.stop))
    as_of = bar.closed_at.astimezone(UTC)

    history = v3._history(
        item,
        bars_by_symbol=bars_by_symbol,
        closed_by_symbol=closed_by_symbol,
        as_of=as_of,
    )
    trajectory = v3._trajectory(history)
    environment = v3._environment(history)
    latest = history[-1]

    close_r = _r_at_price(
        _d(signal.entry),
        risk,
        side,
        _d(bar.close),
    )
    body_r = (
        (_d(bar.close) - _d(bar.open)) / risk
        if side == "long"
        else (_d(bar.open) - _d(bar.close)) / risk
    )
    progress_bps = _clip(
        int(max(ZERO, max_mfe_r) / TARGET_R * Decimal(10_000))
    )
    close_support = _clip(int(Decimal(5_000) + close_r * Decimal(2_500)))
    recovery_evidence = _clip(
        (trajectory.recovery_velocity_bps + environment.recovery_velocity_bps) // 2
    )

    path_history.append(
        PositionPathObservation(
            as_of=as_of,
            data_integrity_bps=latest.data_integrity_bps,
            journey_progress_bps=progress_bps,
            close_support_bps=close_support,
            directional_efficiency_bps=latest.momentum_bps,
            favorable_excursion_bps=progress_bps,
            adverse_excursion_bps=_clip(
                int(max(ZERO, max_mae_r) * Decimal(10_000))
            ),
            favorable_body_bps=_clip(
                int(max(ZERO, body_r) * Decimal(10_000))
            ),
            adverse_body_bps=_clip(
                int(max(ZERO, -body_r) * Decimal(10_000))
            ),
            market_support_bps=environment.market_support_bps,
            environment_adverse_bps=environment.adverse_environment_bps,
            recovery_evidence_bps=recovery_evidence,
        )
    )

    path = assess_position_path(
        tuple(path_history[-min(v3.PATH_WINDOW, len(path_history)):])
    )
    journey = assess_position_journey(
        PositionJourneyEvidence(
            trader_id="VT08_INDEX_FALSIFICATION_LAB",
            market=symbol,
            side=side.upper(),
            opened_at=signal.signal_at.astimezone(UTC),
            as_of=as_of,
            data_integrity_bps=latest.data_integrity_bps,
            regime_stability_bps=_clip(
                (environment.market_support_bps + trajectory.support_bps) // 2
            ),
            expansion_bps=progress_bps,
            displacement_bps=latest.displacement_bps,
            momentum_bps=latest.momentum_bps,
            liquidity_capacity_bps=latest.liquidity_capacity_bps,
            cross_market_confirmation_bps=latest.cross_market_confirmation_bps,
            exhaustion_bps=environment.adverse_environment_bps,
            opposite_displacement_bps=latest.opposite_pressure_bps,
            contradiction_bps=latest.contradiction_bps,
            anomaly_bps=latest.anomaly_bps,
            uncertainty_bps=latest.uncertainty_bps,
        )
    )
    expansion_capacity = _clip(
        (
            latest.trend_support_bps
            + latest.momentum_bps
            + latest.displacement_bps
            + latest.cross_market_confirmation_bps
            + latest.volatility_stability_bps
            + (10_000 - latest.anomaly_bps)
        )
        // 6
    )
    instinct = assess_instinct(
        environment,
        trajectory,
        path=path,
        opportunity_quality_bps=int(entry_context["opportunity_quality_bps"]),
        expansion_capacity_bps=expansion_capacity,
        data_integrity_bps=latest.data_integrity_bps,
    )
    return assess_realtime_trade_management(
        instinct,
        journey,
        path,
        progress_bps=progress_bps,
        data_integrity_bps=latest.data_integrity_bps,
    )


def _simulate_trade(
    item: object,
    *,
    entry_context: dict[str, object],
    bars_by_symbol: dict[str, tuple[object, ...]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
    closed_by_symbol: dict[str, tuple[datetime, ...]],
) -> ManagedReplay:
    signal = item.opportunity.signal
    market = str(signal.symbol)
    side = str(signal.side.value).lower()
    entry = _d(signal.entry)
    initial_stop = _d(signal.stop)
    risk = abs(entry - initial_stop)
    if risk <= ZERO:
        raise ValueError("VT08 Shared V4 invalid initial risk")

    original_target = _price_at_r(entry, risk, side, TARGET_R)
    current_stop = initial_stop
    active_target = original_target

    bars = bars_by_symbol[market]
    opens = opened_by_symbol[market]
    start = bisect.bisect_left(opens, signal.signal_at.astimezone(UTC))
    retained = bars[start:]
    if not retained:
        return ManagedReplay(
            trade_id=item.trade_id,
            market=market,
            signal_at=signal.signal_at.astimezone(UTC),
            exited_at=signal.signal_at.astimezone(UTC),
            r_multiple=ZERO,
            exit_reason="no-bars",
            stop_change_count=0,
            target_extension_count=0,
            action_counts=(),
            maximum_target_r=TARGET_R,
            maximum_locked_r=Decimal("-1"),
            bars_observed=0,
        )

    max_mfe = ZERO
    max_mae = ZERO
    max_target_r = TARGET_R
    max_locked_r = Decimal("-1")
    stop_changes = 0
    target_extensions = 0
    actions: Counter[str] = Counter()
    path_history: list[PositionPathObservation] = []
    last = retained[-1]

    for bar_index, bar in enumerate(retained, start=1):
        resolved = _gap_exit(
            side=signal.side,
            bar=bar,
            stop=current_stop,
            target=active_target,
        )
        if resolved is None:
            resolved = _intrabar_exit(
                bar=bar,
                stop=current_stop,
                target=active_target,
            )
        if resolved is not None:
            exit_price, reason = resolved
            return ManagedReplay(
                trade_id=item.trade_id,
                market=market,
                signal_at=signal.signal_at.astimezone(UTC),
                exited_at=bar.closed_at.astimezone(UTC),
                r_multiple=_r_at_price(entry, risk, side, _d(exit_price)),
                exit_reason=f"shared-{reason}",
                stop_change_count=stop_changes,
                target_extension_count=target_extensions,
                action_counts=tuple(sorted(actions.items())),
                maximum_target_r=max_target_r,
                maximum_locked_r=max_locked_r,
                bars_observed=bar_index,
            )

        if side == "long":
            max_mfe = max(max_mfe, (_d(bar.high) - entry) / risk)
            max_mae = max(max_mae, (entry - _d(bar.low)) / risk)
        else:
            max_mfe = max(max_mfe, (entry - _d(bar.low)) / risk)
            max_mae = max(max_mae, (_d(bar.high) - entry) / risk)

        directive = _directive_at_close(
            item,
            entry_context=entry_context,
            bar=bar,
            max_mfe_r=max_mfe,
            max_mae_r=max_mae,
            path_history=path_history,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        actions[directive.action.value] += 1

        new_stop, new_target, stop_changed, target_changed = _apply_directive(
            directive=directive,
            anchor_close=_d(bar.close),
            entry=entry,
            risk=risk,
            side=side,
            current_stop=current_stop,
            active_target=active_target,
            original_target=original_target,
        )
        if stop_changed:
            stop_changes += 1
            current_stop = new_stop
            max_locked_r = max(
                max_locked_r,
                _r_at_price(entry, risk, side, current_stop),
            )
        if target_changed:
            target_extensions += 1
            active_target = new_target
            max_target_r = max(
                max_target_r,
                abs(active_target - entry) / risk,
            )

    return ManagedReplay(
        trade_id=item.trade_id,
        market=market,
        signal_at=signal.signal_at.astimezone(UTC),
        exited_at=last.closed_at.astimezone(UTC),
        r_multiple=_r_at_price(entry, risk, side, _d(last.close)),
        exit_reason="shared-boundary-mark",
        stop_change_count=stop_changes,
        target_extension_count=target_extensions,
        action_counts=tuple(sorted(actions.items())),
        maximum_target_r=max_target_r,
        maximum_locked_r=max_locked_r,
        bars_observed=len(retained),
    )


def _metrics(
    rows: tuple[ManagedReplay, ...],
    *,
    stress: Decimal,
) -> dict[str, object]:
    ordered = tuple(sorted(rows, key=lambda row: (row.exited_at, row.trade_id)))
    equity = ZERO
    peak = ZERO
    max_dd = ZERO
    gross_profit = ZERO
    gross_loss = ZERO
    wins = losses = flats = 0
    values: list[Decimal] = []

    for row in ordered:
        value = row.r_multiple - stress
        values.append(value)
        if value > ZERO:
            gross_profit += value
            wins += 1
        elif value < ZERO:
            gross_loss += -value
            losses += 1
        else:
            flats += 1
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    pf = None if gross_loss == ZERO else gross_profit / gross_loss
    return {
        "sample": len(ordered),
        "profit_factor": None if pf is None else str(pf),
        "total_r": str(sum(values, ZERO)),
        "max_drawdown_r": str(max_dd),
        "gross_profit_r": str(gross_profit),
        "gross_loss_r": str(gross_loss),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "mean_r": (
            "0"
            if not values
            else str(sum(values, ZERO) / Decimal(len(values)))
        ),
    }


def _delta(
    *,
    baseline: dict[str, object],
    managed: dict[str, object],
) -> dict[str, object]:
    baseline_pf = _d(baseline["profit_factor"] or 0)
    managed_pf = _d(managed["profit_factor"] or 0)
    return {
        "profit_factor_delta": str(managed_pf - baseline_pf),
        "total_r_delta": str(
            _d(managed["total_r"]) - _d(baseline["total_r"])
        ),
        "max_drawdown_r_delta": str(
            _d(managed["max_drawdown_r"]) - _d(baseline["max_drawdown_r"])
        ),
        "pf_improved": managed_pf > baseline_pf,
        "drawdown_reduced": (
            _d(managed["max_drawdown_r"])
            < _d(baseline["max_drawdown_r"])
        ),
        "total_r_improved": (
            _d(managed["total_r"]) > _d(baseline["total_r"])
        ),
    }


def _window(
    *,
    roots: dict[str, Path],
    window_id: str,
) -> dict[str, object]:
    source_window_id = {
        "five_year": "5Y",
        "recent_two_year": "2Y",
        "r66_consumed_failed_holdout": "R66",
    }[window_id]
    canonical, bars_raw, provenance = v3.v2.r74._load_window(
        roots=roots,
        window_id=source_window_id,
    )
    start_date, end_date, expected = v3.v2.r74._window_contract(source_window_id)
    bars_by_symbol: dict[str, tuple[object, ...]] = {
        symbol: tuple(rows)
        for symbol, rows in bars_raw.items()
    }
    opened_by_symbol = {
        symbol: tuple(bar.opened_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }
    closed_by_symbol = {
        symbol: tuple(bar.closed_at.astimezone(UTC) for bar in rows)
        for symbol, rows in bars_by_symbol.items()
    }

    base, _ = v3.v2.r58._exact_r47(
        tuple(canonical),
        bars_by_symbol=bars_by_symbol,
    )
    control, _ = v3.v2.r102._apply_confidence_policy(
        tuple(base),
        bars_by_symbol=bars_by_symbol,
        policy_id=v3.v2.r102.POLICY_EXPLICIT_FULL,
    )
    control = v3.v2._unitize(tuple(control))
    if len(control) != expected:
        raise ValueError(f"VT08 Shared V4 {window_id} density drift")

    ordered = tuple(
        sorted(
            control,
            key=lambda item: (
                item.opportunity.signal.signal_at.astimezone(UTC),
                item.trade_id,
            ),
        )
    )
    pending: list[tuple[datetime, int, dict[str, object]]] = []
    closed_memory: list[dict[str, object]] = []
    managed: list[ManagedReplay] = []

    for item in ordered:
        signal_at = item.opportunity.signal.signal_at.astimezone(UTC)
        while pending and pending[0][0] <= signal_at:
            _closed_at, _trade_id, record = heapq.heappop(pending)
            closed_memory.append(record)

        entry_context = v3._entry_assessment(
            item,
            bars_by_symbol=bars_by_symbol,
            closed_by_symbol=closed_by_symbol,
            closed_memory=closed_memory,
        )
        replay = _simulate_trade(
            item,
            entry_context=entry_context,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            closed_by_symbol=closed_by_symbol,
        )
        managed.append(replay)
        record = {
            "episode_id": f"{window_id}:{item.trade_id}",
            "market": replay.market,
            "closed_at": replay.exited_at,
            "terminal_r": replay.r_multiple,
            "signature": entry_context["signature"],
            "phenotype_views": entry_context["phenotype_views"],
        }
        heapq.heappush(
            pending,
            (replay.exited_at, item.trade_id, record),
        )

    baseline = v3.v2.r108._bundle(
        control,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        window_id=source_window_id,
        start_date=start_date,
        end_date=end_date,
    )
    managed_rows = tuple(managed)
    primary = _metrics(managed_rows, stress=PRIMARY_STRESS)
    secondary = _metrics(managed_rows, stress=SECONDARY_STRESS)

    action_counts: Counter[str] = Counter()
    stop_changed = target_extended = 0
    target_levels: Counter[str] = Counter()
    for row in managed_rows:
        action_counts.update(dict(row.action_counts))
        stop_changed += int(row.stop_change_count > 0)
        target_extended += int(row.target_extension_count > 0)
        target_levels[str(row.maximum_target_r)] += 1

    return {
        "window_id": window_id,
        "sample": len(managed_rows),
        "canonical_expected": expected,
        "density_retained": "1",
        "baseline": baseline,
        "shared_managed": {
            "primary": primary,
            "secondary": secondary,
        },
        "delta_vs_baseline": {
            "primary": _delta(
                baseline=dict(baseline["primary"]),
                managed=primary,
            ),
            "secondary": _delta(
                baseline=dict(baseline["secondary"]),
                managed=secondary,
            ),
        },
        "management": {
            "trades_with_stop_improvement": stop_changed,
            "trades_with_target_extension": target_extended,
            "action_counts": dict(sorted(action_counts.items())),
            "maximum_target_r_distribution": dict(sorted(target_levels.items())),
        },
        "trades": [
            {
                "trade_id": row.trade_id,
                "market": row.market,
                "signal_at": row.signal_at.isoformat(),
                "exited_at": row.exited_at.isoformat(),
                "r_multiple": str(row.r_multiple),
                "exit_reason": row.exit_reason,
                "stop_change_count": row.stop_change_count,
                "target_extension_count": row.target_extension_count,
                "action_counts": dict(row.action_counts),
                "maximum_target_r": str(row.maximum_target_r),
                "maximum_locked_r": str(row.maximum_locked_r),
                "bars_observed": row.bars_observed,
            }
            for row in managed_rows
        ],
        "provenance": provenance,
    }


def run(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five = _window(roots=roots, window_id="five_year")
    recent = _window(roots=roots, window_id="recent_two_year")
    r66 = _window(roots=roots, window_id="r66_consumed_failed_holdout")
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge": {
            "source_pr": 604,
            "source_head": v3.VT08_HEAD,
            "shared_is_only_cognitive_engine": True,
            "vt08_role": "METHODOLOGY_AND_EXECUTION_SURFACE_ONLY",
            "vt31_cognition_used": False,
            "vt08_cognition_used_by_shared": False,
            "same_opportunity_universe": True,
            "same_initial_position_size": True,
            "initial_size_r": "1",
            "sizing_used": False,
            "capital_weighting_used": False,
            "risk_weighting_used": False,
            "signal_suppression_used": False,
            "market_removal_used": False,
            "calendar_filter_used": False,
            "stop_widening_used": False,
            "target_reduction_used": False,
            "shared_management_actuation_replayed": True,
            "management_effective_next_m15_bar": True,
            "runtime_current_trade_outcome_used": False,
            "runtime_future_market_used": False,
            "closed_shared_managed_history_only_for_memory": True,
        },
        "five_year": five,
        "recent_two_year": recent,
        "r66_consumed_failed_holdout": r66,
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "sizing_forbidden": True,
            "sizing_used": False,
            "risk_budget_changed": False,
            "vt08_methodology_modified": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(v3._jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "five_year": {
                    "baseline": payload["five_year"]["baseline"]["primary"],
                    "managed": payload["five_year"]["shared_managed"]["primary"],
                    "delta": payload["five_year"]["delta_vs_baseline"]["primary"],
                    "management": payload["five_year"]["management"],
                },
                "recent_two_year": {
                    "baseline": payload["recent_two_year"]["baseline"]["primary"],
                    "managed": payload["recent_two_year"]["shared_managed"]["primary"],
                    "delta": payload["recent_two_year"]["delta_vs_baseline"]["primary"],
                    "management": payload["recent_two_year"]["management"],
                },
                "r66": {
                    "baseline": payload["r66_consumed_failed_holdout"]["baseline"]["primary"],
                    "managed": payload["r66_consumed_failed_holdout"]["shared_managed"]["primary"],
                    "delta": payload["r66_consumed_failed_holdout"]["delta_vs_baseline"]["primary"],
                    "management": payload["r66_consumed_failed_holdout"]["management"],
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
