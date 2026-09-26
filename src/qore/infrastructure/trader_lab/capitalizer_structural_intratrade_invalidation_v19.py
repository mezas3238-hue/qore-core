"""Structural intratrade hypothesis invalidation for Capitalizer.

V18 proved that failure-to-depart plus generic adverse closes contains some
signal but is too coarse: it improves many losing base outcomes while also
cutting enough winners to fail the consumed-window envelope.

V19 tests a stricter causal thesis. A trade may invalidate only after:
1. it still has not departed +0.25R;
2. a directional adverse M1 displacement candle forms with meaningful body;
3. that candle closes through the prior two-bar adverse extreme;
4. subsequent full M1 bars accept beyond the displacement midpoint;
5. at least one acceptance bar extends the adverse extreme;
6. the displacement midpoint is not reclaimed before the trigger.

The original exit bar is excluded. Current outcome, future bars and blocked
counterfactuals are never visible to the trigger. Entries, true 2R target,
original stop geometry, MAX3 and frozen Surface sizing are preserved.

Consumed research only. Any passing policy must be replayed through full source
competition before the sealed 2018-2020 holdout is opened.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_STRUCTURAL_INTRATRADE_INVALIDATION_V19"
DEPARTURE_R = Decimal("0.25")
MIN_BODY_FRACTION = Decimal("0.60")

# name -> (minimum bars, minimum adverse body R, minimum adverse close R,
#          required acceptance bars)
TRIGGER_SPECS: dict[str, tuple[int, Decimal, Decimal, int]] = {
    "STRUCT3_B015_C010_A1": (3, Decimal("0.15"), Decimal("0.10"), 1),
    "STRUCT3_B020_C015_A2": (3, Decimal("0.20"), Decimal("0.15"), 2),
    "STRUCT5_B020_C015_A2": (5, Decimal("0.20"), Decimal("0.15"), 2),
    "STRUCT5_B025_C020_A2": (5, Decimal("0.25"), Decimal("0.20"), 2),
}

# name -> (trigger, minimum current DD, maximum Surface multiplier)
POLICY_SPECS: dict[
    str,
    tuple[str, Decimal | None, Decimal | None],
] = {
    "GLOBAL_STRUCT3_B020_A2": ("STRUCT3_B020_C015_A2", None, None),
    "DD2_STRUCT3_B020_A2": (
        "STRUCT3_B020_C015_A2",
        Decimal("2"),
        None,
    ),
    "DEFENSIVE_STRUCT3_B020_A2": (
        "STRUCT3_B020_C015_A2",
        None,
        Decimal("0.55"),
    ),
    "GLOBAL_STRUCT5_B020_A2": ("STRUCT5_B020_C015_A2", None, None),
    "DD2_STRUCT5_B020_A2": (
        "STRUCT5_B020_C015_A2",
        Decimal("2"),
        None,
    ),
    "DEFENSIVE_STRUCT5_B020_A2": (
        "STRUCT5_B020_C015_A2",
        None,
        Decimal("0.55"),
    ),
    "GLOBAL_STRUCT5_B025_A2": ("STRUCT5_B025_C020_A2", None, None),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(slots=True)
class _Pending:
    midpoint: Decimal
    adverse_extreme: Decimal
    acceptance_count: int = 0
    extension_seen: bool = False


@dataclass(slots=True)
class _StructuralState:
    period: str
    trade: milestone.SimulatedTrade
    elapsed: int = 0
    max_favorable_r: Decimal = Decimal("0")
    departed: bool = False
    history: list[CapitalizerM1Bar] | None = None
    pending: dict[str, _Pending | None] | None = None
    triggered: set[str] | None = None

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = []
        if self.pending is None:
            self.pending = {name: None for name in TRIGGER_SPECS}
        if self.triggered is None:
            self.triggered = set()


def _risk(trade: milestone.SimulatedTrade) -> Decimal:
    value = abs(
        Decimal(trade.entry_price) - Decimal(trade.original_stop_price)
    )
    if value <= 0:
        raise ValueError("V19 requires positive original risk")
    return value


def _body_r(bar: CapitalizerM1Bar, trade: milestone.SimulatedTrade) -> Decimal:
    return bar.body / _risk(trade)


def _adverse_direction(
    bar: CapitalizerM1Bar,
    trade: milestone.SimulatedTrade,
) -> bool:
    if trade.side == "LONG":
        return bar.bearish
    if trade.side == "SHORT":
        return bar.bullish
    raise ValueError("V19 trade side must be LONG/SHORT")


def _breaks_prior_extreme(
    bar: CapitalizerM1Bar,
    prior: tuple[CapitalizerM1Bar, CapitalizerM1Bar],
    trade: milestone.SimulatedTrade,
) -> bool:
    if trade.side == "LONG":
        return bar.close < min(row.low for row in prior)
    if trade.side == "SHORT":
        return bar.close > max(row.high for row in prior)
    raise ValueError("V19 trade side must be LONG/SHORT")


def _qualifying_displacement(
    *,
    bar: CapitalizerM1Bar,
    prior: tuple[CapitalizerM1Bar, CapitalizerM1Bar],
    trade: milestone.SimulatedTrade,
    body_r: Decimal,
    close_r: Decimal,
) -> bool:
    if bar.range <= 0:
        return False
    if not _adverse_direction(bar, trade):
        return False
    if _body_r(bar, trade) < body_r:
        return False
    if bar.body / bar.range < MIN_BODY_FRACTION:
        return False
    if close_r > -close_r.copy_abs():
        return False
    return _breaks_prior_extreme(bar, prior, trade)


def _displacement_qualifies(
    *,
    bar: CapitalizerM1Bar,
    prior: tuple[CapitalizerM1Bar, CapitalizerM1Bar],
    trade: milestone.SimulatedTrade,
    minimum_body_r: Decimal,
    minimum_adverse_close_r: Decimal,
) -> bool:
    actual_close_r = v18._close_r(bar, trade)
    if actual_close_r > -minimum_adverse_close_r:
        return False
    return _qualifying_displacement(
        bar=bar,
        prior=prior,
        trade=trade,
        body_r=minimum_body_r,
        close_r=minimum_adverse_close_r,
    )


def _midpoint(bar: CapitalizerM1Bar) -> Decimal:
    return (bar.open + bar.close) / Decimal("2")


def _adverse_extreme(
    bar: CapitalizerM1Bar,
    trade: milestone.SimulatedTrade,
) -> Decimal:
    return bar.low if trade.side == "LONG" else bar.high


def _reclaimed(
    bar: CapitalizerM1Bar,
    *,
    pending: _Pending,
    trade: milestone.SimulatedTrade,
) -> bool:
    if trade.side == "LONG":
        return bar.close >= pending.midpoint
    return bar.close <= pending.midpoint


def _extends(
    bar: CapitalizerM1Bar,
    *,
    pending: _Pending,
    trade: milestone.SimulatedTrade,
) -> bool:
    if trade.side == "LONG":
        return bar.low < pending.adverse_extreme
    return bar.high > pending.adverse_extreme


def _process_bar(
    state: _StructuralState,
    bar: CapitalizerM1Bar,
) -> tuple[v18.TriggerEvent, ...]:
    if bar.opened_at < v18._aware(state.trade.entry_at):
        return ()
    if bar.closed_at >= v18._aware(state.trade.exit_at):
        return ()
    if state.departed:
        return ()

    state.elapsed += 1
    state.max_favorable_r = max(
        state.max_favorable_r,
        v18._favorable_r(bar, state.trade),
    )
    if state.max_favorable_r >= DEPARTURE_R:
        state.departed = True
        return ()

    assert state.history is not None
    assert state.pending is not None
    assert state.triggered is not None
    close_r = v18._close_r(bar, state.trade)
    events: list[v18.TriggerEvent] = []

    for name, (
        minimum_bars,
        minimum_body_r,
        minimum_adverse_close_r,
        required_acceptance,
    ) in TRIGGER_SPECS.items():
        if name in state.triggered:
            continue

        pending = state.pending[name]
        if pending is not None:
            if _reclaimed(bar, pending=pending, trade=state.trade):
                state.pending[name] = None
                continue
            pending.acceptance_count += 1
            if _extends(bar, pending=pending, trade=state.trade):
                pending.extension_seen = True
                pending.adverse_extreme = _adverse_extreme(bar, state.trade)
            if (
                pending.acceptance_count >= required_acceptance
                and pending.extension_seen
            ):
                if close_r <= Decimal("-1"):
                    raise ValueError(
                        "V19 structural trigger crossed original stop "
                        "before ORIGINAL exit"
                    )
                state.triggered.add(name)
                events.append(
                    v18.TriggerEvent(
                        period=state.period,
                        symbol=state.trade.symbol,
                        session=state.trade.session,
                        operating_date=state.trade.operating_date,
                        entry_at=state.trade.entry_at,
                        trigger=name,
                        trigger_at=bar.closed_at.isoformat(),
                        trigger_r=str(close_r),
                        elapsed_full_bars=state.elapsed,
                        max_favorable_r_before_trigger=str(
                            state.max_favorable_r
                        ),
                    )
                )
                continue

        if state.pending[name] is not None:
            continue
        if state.elapsed < minimum_bars or len(state.history) < 2:
            continue
        prior = (state.history[-2], state.history[-1])
        if _displacement_qualifies(
            bar=bar,
            prior=prior,
            trade=state.trade,
            minimum_body_r=minimum_body_r,
            minimum_adverse_close_r=minimum_adverse_close_r,
        ):
            state.pending[name] = _Pending(
                midpoint=_midpoint(bar),
                adverse_extreme=_adverse_extreme(bar, state.trade),
            )

    state.history.append(bar)
    if len(state.history) > 4:
        del state.history[:-4]
    return tuple(events)


def _scan_symbol(
    *,
    symbol: str,
    period_rows: dict[str, tuple[milestone.SimulatedTrade, ...]],
    m1_root: Path,
) -> tuple[v18.TriggerEvent, ...]:
    states = tuple(
        sorted(
            (
                _StructuralState(period=period, trade=trade)
                for period, rows in period_rows.items()
                for trade in rows
            ),
            key=lambda state: (
                v18._aware(state.trade.entry_at),
                state.period,
            ),
        )
    )
    if not states:
        raise ValueError("V19 has no market states")
    roots = tuple(path.parent for path in m1_root.rglob("RAW_M1_LEDGER"))
    if len(roots) != 1:
        raise ValueError(f"V19 requires one native-M1 root for {symbol}")

    first_entry = min(v18._aware(s.trade.entry_at) for s in states)
    last_exit = max(v18._aware(s.trade.exit_at) for s in states)
    active: list[_StructuralState] = []
    pointer = 0
    events: list[v18.TriggerEvent] = []

    for bar in iter_cibo_m1(roots[0]):
        if bar.symbol != symbol:
            raise ValueError("V19 M1 symbol drift")
        if bar.closed_at <= first_entry:
            continue
        if bar.opened_at >= last_exit:
            break
        while (
            pointer < len(states)
            and v18._aware(states[pointer].trade.entry_at) <= bar.opened_at
        ):
            active.append(states[pointer])
            pointer += 1

        next_active: list[_StructuralState] = []
        for state in active:
            if bar.opened_at >= v18._aware(state.trade.exit_at):
                continue
            events.extend(_process_bar(state, bar))
            all_done = state.departed or (
                state.triggered is not None
                and len(state.triggered) == len(TRIGGER_SPECS)
            )
            if not all_done and bar.closed_at < v18._aware(state.trade.exit_at):
                next_active.append(state)
        active = next_active
    return tuple(events)


def build_market_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[v18.TriggerEvent, ...]]:
    periods = {
        "DEVELOPMENT_2024_2026": v18._market_original(
            development_root, symbol=symbol
        ),
        "CONSUMED_VALIDATION_2022_2024": v18._market_original(
            validation_root, symbol=symbol
        ),
        "CONSUMED_RESERVED_2020_2022": v18._market_original(
            reserved_root, symbol=symbol
        ),
    }
    events = _scan_symbol(
        symbol=symbol,
        period_rows=periods,
        m1_root=m1_root,
    )
    counts = Counter(event.trigger for event in events)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_trade_counts": {
            period: len(rows) for period, rows in periods.items()
        },
        "trigger_specs": {
            name: {
                "minimum_full_m1_bars": minimum_bars,
                "minimum_adverse_body_r": str(body_r),
                "minimum_adverse_close_r": str(close_r),
                "minimum_body_fraction": str(MIN_BODY_FRACTION),
                "required_acceptance_bars": acceptance,
                "departure_r": str(DEPARTURE_R),
                "prior_extreme_break_required": True,
                "midpoint_reclaim_fails_trigger": True,
                "adverse_extension_required": True,
            }
            for name, (
                minimum_bars,
                body_r,
                close_r,
                acceptance,
            ) in TRIGGER_SPECS.items()
        },
        "trigger_counts": dict(sorted(counts.items())),
        "current_outcome_visible_to_trigger": False,
        "future_bars_visible_to_trigger": False,
        "original_exit_bar_excluded": True,
        "same_bar_stop_target_ambiguity_can_trigger": False,
        "market_session_specific_thresholds_used": False,
        "strategy_rules_changed": False,
        "trader_certified": False,
    }, events


def write_market(
    report: dict[str, Any],
    events: tuple[v18.TriggerEvent, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-structural-intratrade-invalidation-v19"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-events.jsonl").open("w", encoding="utf-8") as handle:
        for row in events:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_events(
    root: Path,
) -> dict[tuple[str, str, str, str], v18.TriggerEvent]:
    result: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    paths = sorted(
        root.rglob("*-structural-intratrade-invalidation-v19-events.jsonl")
    )
    if len(paths) != 9:
        raise ValueError("V19 aggregate requires nine market event ledgers")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = v18.TriggerEvent(**json.loads(line))
                key = (row.period, row.symbol, row.entry_at, row.trigger)
                if key in result:
                    raise ValueError("duplicate V19 trigger event")
                result[key] = row
    return result


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    event_root: Path,
) -> tuple[dict[str, Any], tuple[v18.InvalidationDecision, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    events = _load_events(event_root)

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    previous_policy_specs = dict(v18.POLICY_SPECS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    v18.POLICY_SPECS.clear()
    v18.POLICY_SPECS.update(POLICY_SPECS)

    try:
        controls: dict[str, dict[str, Any]] = {}
        audits: list[v18.InvalidationDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = v18._simulate(
                period=period,
                policy="SURFACE_CONTROL",
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                events=events,
            )
            controls[period] = control
            audits.extend(audit)

        results: list[dict[str, Any]] = []
        for policy in POLICIES:
            heldouts: dict[str, Any] = {}
            for period, (ledgers, contexts) in windows.items():
                if policy == "SURFACE_CONTROL":
                    current = controls[period]
                else:
                    current, audit = v18._simulate(
                        period=period,
                        policy=policy,
                        ledgers=ledgers,
                        contexts=contexts,
                        contextual_model=contextual_model,
                        events=events,
                    )
                    audits.extend(audit)
                v10._annotate(current, controls[period])
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            full_gate = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                and row["dd_at_or_below_6r"]
                and row["losing_streak_not_worse"]
                for row in heldouts.values()
            )
            total_invalidations = sum(
                int(row["invalidation_count"]) for row in heldouts.values()
            )
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "total_invalidation_count": total_invalidations,
                    "all_consumed_full_gate": full_gate,
                }
            )
    finally:
        v18.POLICY_SPECS.clear()
        v18.POLICY_SPECS.update(previous_policy_specs)
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous_simultaneous)

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["total_invalidation_count"] > 0
        and row["all_consumed_full_gate"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": (
            "STRUCTURAL_DISPLACEMENT_ACCEPTANCE_RECLAIM_INVALIDATION"
        ),
        "departure_threshold_r": str(DEPARTURE_R),
        "minimum_body_fraction": str(MIN_BODY_FRACTION),
        "trigger_specs": {
            name: [
                minimum,
                str(body_r),
                str(close_r),
                acceptance,
            ]
            for name, (
                minimum,
                body_r,
                close_r,
                acceptance,
            ) in TRIGGER_SPECS.items()
        },
        "policy_specs": {
            name: [
                trigger,
                None if dd is None else str(dd),
                None if multiplier is None else str(multiplier),
            ]
            for name, (trigger, dd, multiplier) in POLICY_SPECS.items()
        },
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_multiplier_preserved": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved": True,
        "max3_preserved": True,
        "current_outcome_visible_to_trigger": False,
        "future_bars_visible_to_trigger": False,
        "original_exit_bar_excluded": True,
        "prior_extreme_break_required": True,
        "midpoint_reclaim_failure_required": True,
        "adverse_extension_required": True,
        "trigger_must_precede_surface_exit": True,
        "market_session_specific_thresholds_used": False,
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "full_source_recompetition_required_before_freeze": True,
        "fresh_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "REPLAY_V19_THROUGH_FULL_SOURCE_THEN_OPEN_2018_2020"
            if candidates
            else "BUILD_INTRATRADE_HYPOTHESIS_STATE_MACHINE_V20"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-structural-intratrade-invalidation-v19.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-structural-intratrade-invalidation-v19-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("development_root", type=Path)
    market.add_argument("validation_root", type=Path)
    market.add_argument("reserved_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("development_root", type=Path)
    aggregate.add_argument("validation_root", type=Path)
    aggregate.add_argument("reserved_root", type=Path)
    aggregate.add_argument("development_validation_context_root", type=Path)
    aggregate.add_argument("reserved_context_root", type=Path)
    aggregate.add_argument("event_root", type=Path)
    aggregate.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, events = build_market_report(
            args.development_root,
            args.validation_root,
            args.reserved_root,
            args.m1_root,
            symbol=str(args.symbol).upper(),
        )
        write_market(report, events, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.event_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
