"""Causal intratrade hypothesis invalidation for Capitalizer.

V10-V17 show that admission filters and coarse recovery-mode routing cannot
reliably solve the <=6R drawdown envelope. True-2R trajectory evidence also
shows that many drawdown STOPs never create enough favorable excursion for
ordinary BE/trailing protection.

V18 therefore controls a different object: whether the *entry hypothesis is
still alive after entry*. A trade is invalidated only when all of these are
true before its normal Surface exit:
- the trade has failed to depart at least +0.25R;
- a predeclared minimum number of full M1 bars has elapsed;
- price has accepted adverse displacement for consecutive M1 closes.

The original exit bar is excluded. Trigger generation never reads the trade
outcome label. Runtime activation may use only already-known portfolio DD and
the existing frozen Surface multiplier. All entries, fixed 2R target, original
stop geometry, MAX3 and Surface sizing remain unchanged.

This is consumed research. Any passing policy must be replayed through the full
source competition before the fresh 2018-2020 holdout is opened.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
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
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_INTRATRADE_HYPOTHESIS_INVALIDATION_V18"
DEPARTURE_R = Decimal("0.25")
CONSECUTIVE_CLOSES = 2

# name -> (minimum full M1 bars, adverse close threshold in R)
TRIGGER_SPECS: dict[str, tuple[int, Decimal]] = {
    "STALL3_A025": (3, Decimal("0.25")),
    "STALL5_A025": (5, Decimal("0.25")),
    "STALL5_A040": (5, Decimal("0.40")),
    "STALL10_A025": (10, Decimal("0.25")),
    "STALL10_A040": (10, Decimal("0.40")),
}

# name -> (trigger, minimum current DD, maximum Surface multiplier)
POLICY_SPECS: dict[
    str,
    tuple[str, Decimal | None, Decimal | None],
] = {
    "GLOBAL_STALL5_A025": ("STALL5_A025", None, None),
    "GLOBAL_STALL5_A040": ("STALL5_A040", None, None),
    "DD2_STALL5_A025": ("STALL5_A025", Decimal("2"), None),
    "DD3_STALL5_A025": ("STALL5_A025", Decimal("3"), None),
    "DD2_STALL5_A040": ("STALL5_A040", Decimal("2"), None),
    "DD3_STALL5_A040": ("STALL5_A040", Decimal("3"), None),
    "DEFENSIVE_STALL5_A025": ("STALL5_A025", None, Decimal("0.55")),
    "DEFENSIVE_STALL5_A040": ("STALL5_A040", None, Decimal("0.55")),
    "DD2_STALL10_A040": ("STALL10_A040", Decimal("2"), None),
    "DD3_STALL10_A040": ("STALL10_A040", Decimal("3"), None),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(frozen=True, slots=True)
class TriggerEvent:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    trigger: str
    trigger_at: str
    trigger_r: str
    elapsed_full_bars: int
    max_favorable_r_before_trigger: str
    departure_threshold_r: str = str(DEPARTURE_R)
    current_outcome_visible_to_trigger: bool = False
    original_exit_bar_used_for_trigger: bool = False


@dataclass(slots=True)
class _PathState:
    period: str
    trade: milestone.SimulatedTrade
    elapsed: int = 0
    max_favorable_r: Decimal = Decimal("0")
    departed: bool = False
    consecutive: dict[str, int] | None = None
    triggered: set[str] | None = None

    def __post_init__(self) -> None:
        if self.consecutive is None:
            self.consecutive = {name: 0 for name in TRIGGER_SPECS}
        if self.triggered is None:
            self.triggered = set()


@dataclass(frozen=True, slots=True)
class InvalidationDecision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    current_drawdown_r: str
    base_multiplier: str
    surface_mode: str
    trigger_name: str | None
    trigger_available: bool
    activation_allowed: bool
    invalidation_applied: bool
    final_exit_at: str
    normalized_realized_r: str
    current_outcome_visible_to_decision: bool = False
    future_bars_visible_to_decision: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _aware(value: str) -> datetime:
    return direct._aware(value)


def _market_original(root: Path, *, symbol: str) -> tuple[milestone.SimulatedTrade, ...]:
    pattern = (
        f"capitalizer-{symbol.lower()}-max-recovery-direct-m1-replay-v1-"
        "original-trades.jsonl"
    )
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"V18 requires one {symbol} ORIGINAL ledger")
    rows: list[milestone.SimulatedTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                item = milestone.SimulatedTrade(**json.loads(line))
                if item.symbol != symbol:
                    raise ValueError("V18 market ledger symbol drift")
                rows.append(item)
    if not rows:
        raise ValueError("V18 market ORIGINAL ledger is empty")
    return tuple(sorted(rows, key=lambda row: _aware(row.entry_at)))


def _favorable_r(bar: CapitalizerM1Bar, trade: milestone.SimulatedTrade) -> Decimal:
    entry = Decimal(trade.entry_price)
    stop = Decimal(trade.original_stop_price)
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("V18 requires positive original risk")
    if trade.side == "LONG":
        return max(Decimal("0"), (bar.high - entry) / risk)
    if trade.side == "SHORT":
        return max(Decimal("0"), (entry - bar.low) / risk)
    raise ValueError("V18 trade side must be LONG/SHORT")


def _close_r(bar: CapitalizerM1Bar, trade: milestone.SimulatedTrade) -> Decimal:
    entry = Decimal(trade.entry_price)
    stop = Decimal(trade.original_stop_price)
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("V18 requires positive original risk")
    if trade.side == "LONG":
        return (bar.close - entry) / risk
    if trade.side == "SHORT":
        return (entry - bar.close) / risk
    raise ValueError("V18 trade side must be LONG/SHORT")


def _process_bar(
    state: _PathState,
    bar: CapitalizerM1Bar,
) -> tuple[TriggerEvent, ...]:
    # Only fully completed bars strictly before the normal ORIGINAL exit may
    # participate. This excludes the stop/target exit bar and same-bar order
    # ambiguity from the trigger.
    if bar.opened_at < _aware(state.trade.entry_at):
        return ()
    if bar.closed_at >= _aware(state.trade.exit_at):
        return ()
    if state.departed:
        return ()

    state.elapsed += 1
    state.max_favorable_r = max(
        state.max_favorable_r,
        _favorable_r(bar, state.trade),
    )
    if state.max_favorable_r >= DEPARTURE_R:
        state.departed = True
        return ()

    close_r = _close_r(bar, state.trade)
    events: list[TriggerEvent] = []
    assert state.consecutive is not None
    assert state.triggered is not None
    for name, (minimum_bars, adverse_r) in TRIGGER_SPECS.items():
        if name in state.triggered:
            continue
        if state.elapsed < minimum_bars:
            state.consecutive[name] = 0
            continue
        if close_r <= -adverse_r:
            state.consecutive[name] += 1
        else:
            state.consecutive[name] = 0
        if state.consecutive[name] < CONSECUTIVE_CLOSES:
            continue
        if close_r <= Decimal("-1"):
            raise ValueError(
                "V18 trigger crossed full original stop before ORIGINAL exit"
            )
        state.triggered.add(name)
        events.append(
            TriggerEvent(
                period=state.period,
                symbol=state.trade.symbol,
                session=state.trade.session,
                operating_date=state.trade.operating_date,
                entry_at=state.trade.entry_at,
                trigger=name,
                trigger_at=bar.closed_at.isoformat(),
                trigger_r=str(close_r),
                elapsed_full_bars=state.elapsed,
                max_favorable_r_before_trigger=str(state.max_favorable_r),
            )
        )
    return tuple(events)


def _scan_symbol(
    *,
    symbol: str,
    period_rows: dict[str, tuple[milestone.SimulatedTrade, ...]],
    m1_root: Path,
) -> tuple[TriggerEvent, ...]:
    states = tuple(
        sorted(
            (
                _PathState(period=period, trade=trade)
                for period, rows in period_rows.items()
                for trade in rows
            ),
            key=lambda state: (_aware(state.trade.entry_at), state.period),
        )
    )
    if not states:
        raise ValueError("V18 has no market states")

    roots = tuple(
        path.parent
        for path in m1_root.rglob("RAW_M1_LEDGER")
        if symbol in str(path.parent).upper()
    )
    if len(roots) != 1:
        raise ValueError(f"V18 requires one native-M1 root for {symbol}")

    first_entry = min(_aware(state.trade.entry_at) for state in states)
    last_exit = max(_aware(state.trade.exit_at) for state in states)
    active: list[_PathState] = []
    pointer = 0
    events: list[TriggerEvent] = []

    for bar in iter_cibo_m1(roots[0]):
        if bar.symbol != symbol:
            raise ValueError("V18 M1 symbol drift")
        if bar.closed_at <= first_entry:
            continue
        if bar.opened_at >= last_exit:
            break

        while (
            pointer < len(states)
            and _aware(states[pointer].trade.entry_at) <= bar.opened_at
        ):
            active.append(states[pointer])
            pointer += 1

        next_active: list[_PathState] = []
        for state in active:
            if bar.opened_at >= _aware(state.trade.exit_at):
                continue
            events.extend(_process_bar(state, bar))
            all_done = state.departed or (
                state.triggered is not None
                and len(state.triggered) == len(TRIGGER_SPECS)
            )
            if not all_done and bar.closed_at < _aware(state.trade.exit_at):
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
) -> tuple[dict[str, Any], tuple[TriggerEvent, ...]]:
    periods = {
        "DEVELOPMENT_2024_2026": _market_original(
            development_root, symbol=symbol
        ),
        "CONSUMED_VALIDATION_2022_2024": _market_original(
            validation_root, symbol=symbol
        ),
        "CONSUMED_RESERVED_2020_2022": _market_original(
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
                "minimum_full_m1_bars": minimum,
                "departure_r": str(DEPARTURE_R),
                "adverse_close_r": str(adverse),
                "consecutive_closes": CONSECUTIVE_CLOSES,
            }
            for name, (minimum, adverse) in TRIGGER_SPECS.items()
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
    events: tuple[TriggerEvent, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-intratrade-hypothesis-invalidation-v18"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-events.jsonl").open("w", encoding="utf-8") as handle:
        for row in events:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_events(root: Path) -> dict[tuple[str, str, str, str], TriggerEvent]:
    result: dict[tuple[str, str, str, str], TriggerEvent] = {}
    paths = sorted(root.rglob("*-intratrade-hypothesis-invalidation-v18-events.jsonl"))
    if len(paths) != 9:
        raise ValueError("V18 aggregate requires nine market event ledgers")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = TriggerEvent(**json.loads(line))
                key = (row.period, row.symbol, row.entry_at, row.trigger)
                if key in result:
                    raise ValueError("duplicate V18 trigger event")
                result[key] = row
    return result


def _activation(
    *,
    policy: str,
    current_dd: Decimal,
    base_multiplier: Decimal,
) -> tuple[str | None, bool]:
    spec = POLICY_SPECS.get(policy)
    if spec is None:
        return None, False
    trigger, minimum_dd, maximum_multiplier = spec
    if minimum_dd is not None and current_dd < minimum_dd:
        return trigger, False
    if maximum_multiplier is not None and base_multiplier > maximum_multiplier:
        return trigger, False
    return trigger, True


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    events: dict[tuple[str, str, str, str], TriggerEvent],
) -> tuple[dict[str, Any], tuple[InvalidationDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[InvalidationDecision] = []
    invalidations = 0
    improved_negative_base = 0
    degraded_positive_base = 0
    realized_delta_unscaled = Decimal("0")

    for trade in ordered:
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        key = (trade.symbol, trade.entry_at)
        base = by_mode[pre.mode][key]
        trigger_name, activation_allowed = _activation(
            policy=policy,
            current_dd=pre.current_dd,
            base_multiplier=pre.base_multiplier,
        )
        event = (
            None
            if trigger_name is None
            else events.get((period, trade.symbol, trade.entry_at, trigger_name))
        )
        apply = (
            activation_allowed
            and event is not None
            and _aware(event.trigger_at) < _aware(base.exit_at)
        )

        normalized_r = Decimal(base.realized_gross_r)
        exit_at = base.exit_at
        exit_reason = base.exit_reason
        if apply:
            assert event is not None
            invalidations += 1
            trigger_r = Decimal(event.trigger_r)
            realized_delta_unscaled += trigger_r - normalized_r
            if normalized_r < 0 and trigger_r > normalized_r:
                improved_negative_base += 1
            if normalized_r > 0 and trigger_r < normalized_r:
                degraded_positive_base += 1
            normalized_r = trigger_r
            exit_at = event.trigger_at
            exit_reason = "HYPOTHESIS_INVALIDATION"

        scaled_r = normalized_r * pre.base_multiplier
        effective = replace(
            base,
            exit_at=exit_at,
            realized_gross_r=str(scaled_r),
            exit_reason=exit_reason,
        )
        chosen.append(effective)
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=exit_at,
                normalized_realized_r=str(normalized_r),
            )
        )
        decisions.append(
            InvalidationDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                current_drawdown_r=str(pre.current_dd),
                base_multiplier=str(pre.base_multiplier),
                surface_mode=pre.mode,
                trigger_name=trigger_name,
                trigger_available=event is not None,
                activation_allowed=activation_allowed,
                invalidation_applied=apply,
                final_exit_at=exit_at,
                normalized_realized_r=str(normalized_r),
            )
        )

    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "invalidation_count": invalidations,
        "improved_negative_base_outcomes": improved_negative_base,
        "degraded_positive_base_outcomes": degraded_positive_base,
        "unscaled_realized_delta_r": str(realized_delta_unscaled),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    event_root: Path,
) -> tuple[dict[str, Any], tuple[InvalidationDecision, ...]]:
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
        simultaneous.update(v11._simultaneous_map(period=period, ledgers=ledgers))
    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        controls: dict[str, dict[str, Any]] = {}
        audits: list[InvalidationDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
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
                    current, audit = _simulate(
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
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["total_invalidation_count"] > 0
        and row["all_consumed_full_gate"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "CAUSAL_FAILURE_TO_DEPART_INTRATRADE_INVALIDATION",
        "departure_threshold_r": str(DEPARTURE_R),
        "consecutive_adverse_closes": CONSECUTIVE_CLOSES,
        "trigger_specs": {
            name: [minimum, str(adverse)]
            for name, (minimum, adverse) in TRIGGER_SPECS.items()
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
            "REPLAY_V18_THROUGH_FULL_SOURCE_THEN_OPEN_2018_2020"
            if candidates
            else "BUILD_STRUCTURAL_INTRATRADE_INVALIDATION_V19"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-intratrade-hypothesis-invalidation-v18.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-intratrade-hypothesis-invalidation-v18-decisions.jsonl"
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
