"""Causal intratrade hypothesis lifecycle state machine for Capitalizer.

V18 showed that generic failure-to-depart plus adverse closes is informative but
too coarse. V19 strengthens the terminal trigger structurally, but remains a
single binary event. V20 models the hypothesis itself as a causal state machine:

ALIVE -> WEAKENING -> INVALIDATING -> DEAD
                         |
                         +-> RECOVERED -> ALIVE

A pullback may therefore weaken or even provisionally invalidate the thesis and
still recover through a causal reclaim. Only persistent adverse displacement,
acceptance and extension without reclaim may declare DEAD.

No state transition can read the trade outcome, future bars, the original exit
bar, or unchosen counterfactuals. Entry, true 2R target, original stop geometry,
MAX3 and frozen Surface sizing remain unchanged. Consumed research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
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
from qore.infrastructure.trader_lab import (
    capitalizer_structural_intratrade_invalidation_v19 as v19,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_INTRATRADE_HYPOTHESIS_STATE_MACHINE_V20"
DEPARTURE_R = Decimal("0.25")
MIN_BODY_FRACTION = Decimal("0.60")
WEAKENING_CLOSES = 2


class Phase(StrEnum):
    ALIVE = "ALIVE"
    WEAKENING = "WEAKENING"
    INVALIDATING = "INVALIDATING"
    RECOVERED = "RECOVERED"
    DEAD = "DEAD"


# name -> (
# minimum bars,
# weakening adverse close R,
# displacement body R,
# displacement adverse close R,
# acceptance bars,
# invalidating patience bars,
# )
STATE_SPECS: dict[
    str,
    tuple[int, Decimal, Decimal, Decimal, int, int],
] = {
    "HSM_FAST": (
        3,
        Decimal("0.08"),
        Decimal("0.15"),
        Decimal("0.10"),
        1,
        1,
    ),
    "HSM_BASE": (
        3,
        Decimal("0.10"),
        Decimal("0.20"),
        Decimal("0.15"),
        2,
        2,
    ),
    "HSM_STRICT": (
        5,
        Decimal("0.12"),
        Decimal("0.25"),
        Decimal("0.20"),
        2,
        3,
    ),
}

# name -> (state spec, minimum current DD, maximum Surface multiplier)
POLICY_SPECS: dict[
    str,
    tuple[str, Decimal | None, Decimal | None],
] = {
    "GLOBAL_HSM_FAST": ("HSM_FAST", None, None),
    "GLOBAL_HSM_BASE": ("HSM_BASE", None, None),
    "DD2_HSM_BASE": ("HSM_BASE", Decimal("2"), None),
    "DEFENSIVE_HSM_BASE": ("HSM_BASE", None, Decimal("0.55")),
    "GLOBAL_HSM_STRICT": ("HSM_STRICT", None, None),
    "DD2_HSM_STRICT": ("HSM_STRICT", Decimal("2"), None),
    "DEFENSIVE_HSM_STRICT": ("HSM_STRICT", None, Decimal("0.55")),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(frozen=True, slots=True)
class TransitionEvent:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    spec: str
    observed_at: str
    from_phase: str
    to_phase: str
    reason: str
    close_r: str
    max_favorable_r: str
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    original_exit_bar_used: bool = False


@dataclass(slots=True)
class _Track:
    phase: Phase = Phase.ALIVE
    adverse_closes: int = 0
    midpoint: Decimal | None = None
    adverse_extreme: Decimal | None = None
    acceptance_count: int = 0
    extension_seen: bool = False
    invalidating_age: int = 0


@dataclass(slots=True)
class _State:
    period: str
    trade: milestone.SimulatedTrade
    elapsed: int = 0
    max_favorable_r: Decimal = Decimal("0")
    departed: bool = False
    history: list[CapitalizerM1Bar] | None = None
    tracks: dict[str, _Track] | None = None
    dead: set[str] | None = None

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = []
        if self.tracks is None:
            self.tracks = {name: _Track() for name in STATE_SPECS}
        if self.dead is None:
            self.dead = set()


def _transition(
    *,
    state: _State,
    spec: str,
    track: _Track,
    to_phase: Phase,
    reason: str,
    bar: CapitalizerM1Bar,
    close_r: Decimal,
) -> TransitionEvent:
    previous = track.phase
    track.phase = to_phase
    return TransitionEvent(
        period=state.period,
        symbol=state.trade.symbol,
        session=state.trade.session,
        operating_date=state.trade.operating_date,
        entry_at=state.trade.entry_at,
        spec=spec,
        observed_at=bar.closed_at.isoformat(),
        from_phase=previous.value,
        to_phase=to_phase.value,
        reason=reason,
        close_r=str(close_r),
        max_favorable_r=str(state.max_favorable_r),
    )


def _reset_track(track: _Track) -> None:
    track.adverse_closes = 0
    track.midpoint = None
    track.adverse_extreme = None
    track.acceptance_count = 0
    track.extension_seen = False
    track.invalidating_age = 0


def _reclaim(
    *,
    bar: CapitalizerM1Bar,
    track: _Track,
    trade: milestone.SimulatedTrade,
    close_r: Decimal,
) -> bool:
    if close_r >= Decimal("0"):
        return True
    if track.midpoint is None:
        return False
    pending = v19._Pending(
        midpoint=track.midpoint,
        adverse_extreme=(
            track.adverse_extreme
            if track.adverse_extreme is not None
            else track.midpoint
        ),
    )
    return v19._reclaimed(bar, pending=pending, trade=trade)


def _process_bar(
    state: _State,
    bar: CapitalizerM1Bar,
) -> tuple[tuple[v18.TriggerEvent, ...], tuple[TransitionEvent, ...]]:
    if bar.opened_at < v18._aware(state.trade.entry_at):
        return (), ()
    if bar.closed_at >= v18._aware(state.trade.exit_at):
        return (), ()
    if state.departed:
        return (), ()

    state.elapsed += 1
    state.max_favorable_r = max(
        state.max_favorable_r,
        v18._favorable_r(bar, state.trade),
    )
    if state.max_favorable_r >= DEPARTURE_R:
        state.departed = True
        return (), ()

    assert state.history is not None
    assert state.tracks is not None
    assert state.dead is not None

    close_r = v18._close_r(bar, state.trade)
    triggers: list[v18.TriggerEvent] = []
    transitions: list[TransitionEvent] = []

    for spec, (
        minimum_bars,
        weakening_r,
        body_r,
        displacement_close_r,
        acceptance_required,
        patience,
    ) in STATE_SPECS.items():
        if spec in state.dead:
            continue
        track = state.tracks[spec]

        if track.phase is Phase.RECOVERED:
            transitions.append(
                _transition(
                    state=state,
                    spec=spec,
                    track=track,
                    to_phase=Phase.ALIVE,
                    reason="RECOVERY_CONFIRMED_NEXT_BAR",
                    bar=bar,
                    close_r=close_r,
                )
            )
            _reset_track(track)

        if track.phase in {Phase.WEAKENING, Phase.INVALIDATING} and _reclaim(
            bar=bar,
            track=track,
            trade=state.trade,
            close_r=close_r,
        ):
            transitions.append(
                _transition(
                    state=state,
                    spec=spec,
                    track=track,
                    to_phase=Phase.RECOVERED,
                    reason="CAUSAL_RECLAIM",
                    bar=bar,
                    close_r=close_r,
                )
            )
            _reset_track(track)
            continue

        if close_r <= -weakening_r:
            track.adverse_closes += 1
        else:
            track.adverse_closes = 0

        if (
            track.phase is Phase.ALIVE
            and state.elapsed >= minimum_bars
            and track.adverse_closes >= WEAKENING_CLOSES
        ):
            transitions.append(
                _transition(
                    state=state,
                    spec=spec,
                    track=track,
                    to_phase=Phase.WEAKENING,
                    reason="SUSTAINED_ADVERSE_ACCEPTANCE",
                    bar=bar,
                    close_r=close_r,
                )
            )

        if (
            track.phase in {Phase.ALIVE, Phase.WEAKENING}
            and state.elapsed >= minimum_bars
            and len(state.history) >= 2
        ):
            prior = (state.history[-2], state.history[-1])
            if v19._displacement_qualifies(
                bar=bar,
                prior=prior,
                trade=state.trade,
                minimum_body_r=body_r,
                minimum_adverse_close_r=displacement_close_r,
            ):
                track.midpoint = v19._midpoint(bar)
                track.adverse_extreme = v19._adverse_extreme(
                    bar,
                    state.trade,
                )
                track.acceptance_count = 0
                track.extension_seen = False
                track.invalidating_age = 0
                transitions.append(
                    _transition(
                        state=state,
                        spec=spec,
                        track=track,
                        to_phase=Phase.INVALIDATING,
                        reason="ADVERSE_DISPLACEMENT_BREAK",
                        bar=bar,
                        close_r=close_r,
                    )
                )
                continue

        if track.phase is not Phase.INVALIDATING:
            continue

        track.invalidating_age += 1
        if _reclaim(
            bar=bar,
            track=track,
            trade=state.trade,
            close_r=close_r,
        ):
            transitions.append(
                _transition(
                    state=state,
                    spec=spec,
                    track=track,
                    to_phase=Phase.RECOVERED,
                    reason="DISPLACEMENT_MIDPOINT_RECLAIM",
                    bar=bar,
                    close_r=close_r,
                )
            )
            _reset_track(track)
            continue

        track.acceptance_count += 1
        if track.adverse_extreme is not None:
            pending = v19._Pending(
                midpoint=(
                    track.midpoint
                    if track.midpoint is not None
                    else Decimal(state.trade.entry_price)
                ),
                adverse_extreme=track.adverse_extreme,
            )
            if v19._extends(bar, pending=pending, trade=state.trade):
                track.extension_seen = True
                track.adverse_extreme = v19._adverse_extreme(
                    bar,
                    state.trade,
                )

        if (
            track.invalidating_age >= patience
            and track.acceptance_count >= acceptance_required
            and track.extension_seen
        ):
            if close_r <= Decimal("-1"):
                raise ValueError(
                    "V20 DEAD transition crossed original stop "
                    "before ORIGINAL exit"
                )
            transitions.append(
                _transition(
                    state=state,
                    spec=spec,
                    track=track,
                    to_phase=Phase.DEAD,
                    reason="PERSISTENT_INVALIDATION_WITH_EXTENSION",
                    bar=bar,
                    close_r=close_r,
                )
            )
            state.dead.add(spec)
            triggers.append(
                v18.TriggerEvent(
                    period=state.period,
                    symbol=state.trade.symbol,
                    session=state.trade.session,
                    operating_date=state.trade.operating_date,
                    entry_at=state.trade.entry_at,
                    trigger=spec,
                    trigger_at=bar.closed_at.isoformat(),
                    trigger_r=str(close_r),
                    elapsed_full_bars=state.elapsed,
                    max_favorable_r_before_trigger=str(
                        state.max_favorable_r
                    ),
                )
            )

    state.history.append(bar)
    if len(state.history) > 6:
        del state.history[:-6]
    return tuple(triggers), tuple(transitions)


def _scan_symbol(
    *,
    symbol: str,
    period_rows: dict[str, tuple[milestone.SimulatedTrade, ...]],
    m1_root: Path,
) -> tuple[tuple[v18.TriggerEvent, ...], tuple[TransitionEvent, ...]]:
    states = tuple(
        sorted(
            (
                _State(period=period, trade=trade)
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
        raise ValueError("V20 has no market states")
    roots = tuple(path.parent for path in m1_root.rglob("RAW_M1_LEDGER"))
    if len(roots) != 1:
        raise ValueError(f"V20 requires one native-M1 root for {symbol}")

    first_entry = min(v18._aware(s.trade.entry_at) for s in states)
    last_exit = max(v18._aware(s.trade.exit_at) for s in states)
    active: list[_State] = []
    pointer = 0
    triggers: list[v18.TriggerEvent] = []
    transitions: list[TransitionEvent] = []

    for bar in iter_cibo_m1(roots[0]):
        if bar.symbol != symbol:
            raise ValueError("V20 M1 symbol drift")
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

        next_active: list[_State] = []
        for state in active:
            if bar.opened_at >= v18._aware(state.trade.exit_at):
                continue
            found, moved = _process_bar(state, bar)
            triggers.extend(found)
            transitions.extend(moved)
            all_done = state.departed or (
                state.dead is not None
                and len(state.dead) == len(STATE_SPECS)
            )
            if not all_done and bar.closed_at < v18._aware(state.trade.exit_at):
                next_active.append(state)
        active = next_active

    return tuple(triggers), tuple(transitions)


def build_market_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[
    dict[str, Any],
    tuple[v18.TriggerEvent, ...],
    tuple[TransitionEvent, ...],
]:
    periods = {
        "DEVELOPMENT_2024_2026": v18._market_original(
            development_root,
            symbol=symbol,
        ),
        "CONSUMED_VALIDATION_2022_2024": v18._market_original(
            validation_root,
            symbol=symbol,
        ),
        "CONSUMED_RESERVED_2020_2022": v18._market_original(
            reserved_root,
            symbol=symbol,
        ),
    }
    triggers, transitions = _scan_symbol(
        symbol=symbol,
        period_rows=periods,
        m1_root=m1_root,
    )
    trigger_counts = Counter(row.trigger for row in triggers)
    transition_counts = Counter(
        f"{row.spec}:{row.from_phase}->{row.to_phase}"
        for row in transitions
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_trade_counts": {
            period: len(rows) for period, rows in periods.items()
        },
        "state_specs": {
            name: {
                "minimum_full_m1_bars": minimum_bars,
                "weakening_adverse_close_r": str(weakening_r),
                "displacement_body_r": str(body_r),
                "displacement_adverse_close_r": str(displacement_close_r),
                "acceptance_bars": acceptance,
                "invalidating_patience_bars": patience,
                "departure_r": str(DEPARTURE_R),
            }
            for name, (
                minimum_bars,
                weakening_r,
                body_r,
                displacement_close_r,
                acceptance,
                patience,
            ) in STATE_SPECS.items()
        },
        "trigger_counts": dict(sorted(trigger_counts.items())),
        "transition_counts": dict(sorted(transition_counts.items())),
        "recovery_transition_supported": True,
        "terminal_state": Phase.DEAD.value,
        "current_outcome_visible_to_transition": False,
        "future_bars_visible_to_transition": False,
        "original_exit_bar_excluded": True,
        "market_session_specific_thresholds_used": False,
        "trader_certified": False,
    }, triggers, transitions


def write_market(
    report: dict[str, Any],
    triggers: tuple[v18.TriggerEvent, ...],
    transitions: tuple[TransitionEvent, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-intratrade-hypothesis-state-machine-v20"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-events.jsonl").open("w", encoding="utf-8") as handle:
        for trigger_row in triggers:
            handle.write(json.dumps(asdict(trigger_row), sort_keys=True) + "\n")
    with (output / f"{stem}-transitions.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for transition_row in transitions:
            handle.write(
                json.dumps(asdict(transition_row), sort_keys=True) + "\n"
            )


def _load_events(
    root: Path,
) -> dict[tuple[str, str, str, str], v18.TriggerEvent]:
    result: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    paths = sorted(root.rglob("*-intratrade-hypothesis-state-machine-v20-events.jsonl"))
    if len(paths) != 9:
        raise ValueError("V20 aggregate requires nine market event ledgers")
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = v18.TriggerEvent(**json.loads(line))
                key = (row.period, row.symbol, row.entry_at, row.trigger)
                if key in result:
                    raise ValueError("duplicate V20 DEAD event")
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
            total_dead_exits = sum(
                int(row["invalidation_count"])
                for row in heldouts.values()
            )
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "total_dead_exits": total_dead_exits,
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
        and row["total_dead_exits"] > 0
        and row["all_consumed_full_gate"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "CAUSAL_INTRATRADE_HYPOTHESIS_LIFECYCLE_STATE_MACHINE",
        "phases": [phase.value for phase in Phase],
        "recovery_transition_supported": True,
        "state_specs": {
            name: [
                minimum_bars,
                str(weakening_r),
                str(body_r),
                str(displacement_close_r),
                acceptance,
                patience,
            ]
            for name, (
                minimum_bars,
                weakening_r,
                body_r,
                displacement_close_r,
                acceptance,
                patience,
            ) in STATE_SPECS.items()
        },
        "policy_specs": {
            name: [
                spec,
                None if dd is None else str(dd),
                None if multiplier is None else str(multiplier),
            ]
            for name, (spec, dd, multiplier) in POLICY_SPECS.items()
        },
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_multiplier_preserved": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved": True,
        "max3_preserved": True,
        "current_outcome_visible_to_transition": False,
        "future_bars_visible_to_transition": False,
        "original_exit_bar_excluded": True,
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "full_source_recompetition_required_before_freeze": True,
        "fresh_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "REPLAY_V20_THROUGH_FULL_SOURCE_THEN_OPEN_2018_2020"
            if candidates
            else "BUILD_HYPOTHESIS_SURVIVAL_MODEL_V21"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-intratrade-hypothesis-state-machine-v20.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-intratrade-hypothesis-state-machine-v20-decisions.jsonl"
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
        report, triggers, transitions = build_market_report(
            args.development_root,
            args.validation_root,
            args.reserved_root,
            args.m1_root,
            symbol=str(args.symbol).upper(),
        )
        write_market(report, triggers, transitions, args.output)
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
