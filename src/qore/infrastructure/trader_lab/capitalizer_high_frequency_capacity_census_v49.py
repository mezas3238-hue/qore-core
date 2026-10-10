"""V49 high-frequency pre-economic capacity census.

This census measures the topology change, not profitability:
- H1 bias events establish a persistent state;
- the last causal H1 state may be inherited into a session;
- every distinct M15 CISD/protected-swing setup inside that state is eligible;
- each M15 setup may produce one earliest M1 trigger from the documented trigger families;
- multiple M15/M1 opportunities may share one H1 state;
- H1/M15/M1 are the only decision timeframes.

Daily/H4 are never read. Outcomes, P&L, R, Fresh Holdout, sizing and capital are never read.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
    _aggregate,
    _build_h1_bias_events,
    _operating_date,
    _timed_m15,
)
from qore.infrastructure.trader_lab.capitalizer_h1_context_state_v49 import (
    V49H1BiasSignal,
    V49H1ContextState,
    build_h1_context_states,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_density_gate_v49 import (
    assess_v49_density,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    V48M1CISDStatus,
    observe_first_m1_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    observe_first_m1_fvg_cisd_continuation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48StructuralCISDObservation,
    V48TimedSourceBar,
    observe_first_structural_cisd,
)

IDENTITY = "QORE_CAPITALIZER_V49_HIGH_FREQUENCY_CAPACITY_CENSUS"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V49_NINE_MARKET_HIGH_FREQUENCY_CAPACITY"
DEV_WINDOW_START = datetime(2025, 9, 17, tzinfo=UTC)
DEV_WINDOW_END = datetime(2026, 9, 17, tzinfo=UTC)
DEFAULT_LOOKBACK = timedelta(days=14)


@dataclass(frozen=True, slots=True)
class V49Opportunity:
    symbol: str
    session: str
    operating_date: str
    h1_state_direction: str
    h1_state_from: str
    h1_state_until: str
    h1_state_basis: str
    m15_setup_confirmed_at: str
    m15_protected_swing_price: str
    m1_trigger_confirmed_at: str
    m1_trigger_family: str
    decision_reference_price: str
    structural_target_witness_price: str
    outcome_used: bool = False
    economics_used: bool = False
    daily_used: bool = False
    h4_used: bool = False

    def __post_init__(self) -> None:
        if self.outcome_used or self.economics_used:
            raise ValueError("V49 capacity opportunity must remain pre-economic")
        if self.daily_used or self.h4_used:
            raise ValueError("V49 high-frequency opportunity cannot use Daily/H4")


@dataclass(frozen=True, slots=True)
class V49MarketCapacity:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    h1_bias_events: int
    h1_states: int
    m15_setups: int
    m1_triggers: int
    target_witnesses: int
    source_complete_opportunities: int
    by_trigger_family: tuple[tuple[str, int], ...]
    outcome_used: bool = False
    economics_used: bool = False
    daily_used: bool = False
    h4_used: bool = False
    fresh_holdout_used: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V49 capacity identity")
        if (
            self.outcome_used
            or self.economics_used
            or self.daily_used
            or self.h4_used
            or self.fresh_holdout_used
            or self.live_authorized
        ):
            raise ValueError("V49 capacity census is pre-economic H1/M15/M1 only")


def _untouched_h1_target_fast(
    h1: tuple[V48AggregatedBar, ...],
    m1: tuple[CapitalizerM1Bar, ...],
    m1_opened: tuple[datetime, ...],
    *,
    decision_at: datetime,
    decision_price: Decimal,
    direction: CapitalizerSourceDirection,
) -> Decimal | None:
    eligible = tuple(bar for bar in h1 if bar.closed_at <= decision_at)
    # Only M1 bars completed at the decision instant can prove a prior touch.
    # A bar opening exactly at decision_at is still in progress: its high/low
    # would leak the next minute into the target-availability decision.
    right = bisect.bisect_left(m1_opened, decision_at)
    for candidate in reversed(eligible[-24:]):
        target = (
            candidate.source.high
            if direction is CapitalizerSourceDirection.BULLISH
            else candidate.source.low
        )
        ahead = (
            target > decision_price
            if direction is CapitalizerSourceDirection.BULLISH
            else target < decision_price
        )
        if not ahead:
            continue
        # A minute beginning when H1 closes is the FIRST possible post-H1
        # touch and must not be excluded by bisect_right.
        left = bisect.bisect_left(m1_opened, candidate.closed_at)
        touched = any(
            bar.closed_at <= decision_at
            and (
                bar.high >= target
                if direction is CapitalizerSourceDirection.BULLISH
                else bar.low <= target
            )
            for bar in m1[left:right]
        )
        if not touched:
            return target
    return None


def _side(direction: CapitalizerSourceDirection) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )


def _slice(
    bars: tuple[Any, ...],
    opened: tuple[datetime, ...],
    *,
    start: datetime,
    end: datetime,
    context: int = 3,
) -> tuple[Any, ...]:
    left = max(0, bisect.bisect_left(opened, start) - context)
    right = bisect.bisect_left(opened, end)
    return bars[left:right]


def _session_groups(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    window_start: datetime,
    window_end: datetime,
) -> tuple[tuple[str, tuple[CapitalizerM1Bar, ...]], ...]:
    grouped: dict[str, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        if not (window_start <= bar.opened_at < window_end):
            continue
        if capitalizer_session_at(bar.opened_at) is not session:
            continue
        grouped[_operating_date(bar.opened_at, session)].append(bar)
    return tuple(
        (day, tuple(sorted(rows, key=lambda item: item.opened_at)))
        for day, rows in sorted(grouped.items())
        if rows
    )


def _all_m15_setups(
    bars: tuple[V48TimedSourceBar, ...],
    *,
    state: V49H1ContextState,
) -> tuple[V48StructuralCISDObservation, ...]:
    cursor = state.active_from
    setups: list[V48StructuralCISDObservation] = []
    seen: set[datetime] = set()

    while cursor < state.active_until:
        observation = observe_first_structural_cisd(
            bars,
            direction=state.direction,
            after=cursor,
            before=state.active_until,
            higher_timeframe_closure_confirmed=True,
        )
        if not observation.source_valid or observation.confirmed_at is None:
            break
        if observation.confirmed_at in seen:
            break
        seen.add(observation.confirmed_at)
        setups.append(observation)
        cursor = observation.confirmed_at

    return tuple(setups)


def _earliest_m1_trigger(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    thesis_at: datetime,
    deadline_at: datetime,
) -> tuple[datetime, str, Decimal] | None:
    if deadline_at <= thesis_at:
        return None

    candidates: list[tuple[datetime, str, Decimal]] = []
    sweep = observe_first_m1_cisd(
        bars,
        thesis_at=thesis_at,
        deadline_at=deadline_at,
        side=_side(direction),
    )
    if (
        sweep.status is V48M1CISDStatus.CONFIRMED
        and sweep.confirmed_at is not None
        and sweep.confirmation_close is not None
    ):
        candidates.append(
            (
                sweep.confirmed_at,
                "LIQUIDITY_SWEEP_CISD",
                sweep.confirmation_close,
            )
        )

    fvg = observe_first_m1_fvg_cisd_continuation(
        bars,
        thesis_at=thesis_at,
        deadline_at=deadline_at,
        direction=direction,
    )
    if fvg.confirmed and fvg.cisd_confirmed_at is not None:
        bar = next(
            (item for item in bars if item.closed_at == fvg.cisd_confirmed_at),
            None,
        )
        if bar is None:
            raise ValueError("FVG trigger confirmation bar must exist")
        candidates.append(
            (
                fvg.cisd_confirmed_at,
                "FVG_RETRACE_CISD",
                bar.close,
            )
        )

    return min(candidates, key=lambda item: (item[0], item[1])) if candidates else None


def _portfolio_max3(
    opportunities: tuple[V49Opportunity, ...],
) -> tuple[V49Opportunity, ...]:
    grouped: dict[tuple[str, str], list[V49Opportunity]] = defaultdict(list)
    for item in opportunities:
        grouped[(item.session, item.operating_date)].append(item)

    selected: list[V49Opportunity] = []
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=lambda item: item.m1_trigger_confirmed_at)
        selected.extend(rows[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda item: item.m1_trigger_confirmed_at))


def build_market_capacity(
    m1_root: Path,
    *,
    session: CapitalizerSession,
    window_start: datetime = DEV_WINDOW_START,
    window_end: datetime = DEV_WINDOW_END,
) -> tuple[V49MarketCapacity, tuple[V49Opportunity, ...]]:
    if window_start.tzinfo is None or window_start.utcoffset() is None:
        raise ValueError("V49 window_start must be timezone-aware")
    if window_end.tzinfo is None or window_end.utcoffset() is None:
        raise ValueError("V49 window_end must be timezone-aware")
    if window_end <= window_start:
        raise ValueError("V49 capacity window must be positive")
    lookback_start = window_start - DEFAULT_LOOKBACK
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if lookback_start <= bar.opened_at < window_end
    )
    if not bars:
        raise ValueError("V49 capacity census found no retained M1")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("one V49 census root must contain one symbol")
    if symbol not in allowed_markets(session):
        raise ValueError("symbol/session outside Capitalizer identity")

    h1 = _aggregate(bars, minutes=60)
    m15 = _timed_m15(_aggregate(bars, minutes=15))
    m15_opened = tuple(item.opened_at for item in m15)
    m1_opened = tuple(item.opened_at for item in bars)
    bias_events = tuple(
        item
        for item in _build_h1_bias_events(h1)
        if lookback_start <= item.confirmed_at < window_end
    )
    signals = tuple(
        V49H1BiasSignal(
            confirmed_at=item.confirmed_at,
            direction=item.direction,
            basis_id=f"{item.closure_kind}:{item.poi_kind}",
        )
        for item in bias_events
    )

    counters: Counter[str] = Counter()
    trigger_families: Counter[str] = Counter()
    opportunities: list[V49Opportunity] = []

    for operating_day, session_bars in _session_groups(
        bars,
        session=session,
        window_start=window_start,
        window_end=window_end,
    ):
        session_start = session_bars[0].opened_at
        session_end = session_bars[-1].closed_at
        states = build_h1_context_states(
            signals,
            session=session,
            session_start=session_start,
            session_end=session_end,
        )
        counters["H1_STATES"] += len(states)

        for state in states:
            m15_window = _slice(
                m15,
                m15_opened,
                start=state.active_from,
                end=state.active_until,
            )
            setups = _all_m15_setups(m15_window, state=state)
            counters["M15_SETUPS"] += len(setups)

            for index, setup in enumerate(setups):
                if setup.confirmed_at is None or setup.swing_price is None:
                    raise ValueError("source-valid M15 setup requires full payload")
                next_boundary = (
                    setups[index + 1].confirmed_at
                    if index + 1 < len(setups)
                    else state.active_until
                )
                if next_boundary is None:
                    next_boundary = state.active_until
                m1_window = _slice(
                    bars,
                    m1_opened,
                    start=setup.confirmed_at,
                    end=next_boundary,
                    context=0,
                )
                if len(m1_window) < 4:
                    continue
                trigger = _earliest_m1_trigger(
                    m1_window,
                    direction=state.direction,
                    thesis_at=setup.confirmed_at,
                    deadline_at=next_boundary,
                )
                if trigger is None:
                    continue

                trigger_at, family, decision_price = trigger
                if capitalizer_session_at(trigger_at) is not session:
                    continue
                counters["M1_TRIGGERS"] += 1
                trigger_families[family] += 1

                stop_valid = (
                    setup.swing_price < decision_price
                    if state.direction is CapitalizerSourceDirection.BULLISH
                    else setup.swing_price > decision_price
                )
                if not stop_valid:
                    continue

                target = _untouched_h1_target_fast(
                    h1,
                    bars,
                    m1_opened,
                    decision_at=trigger_at,
                    decision_price=decision_price,
                    direction=state.direction,
                )
                if target is None:
                    continue
                counters["TARGET_WITNESSES"] += 1

                opportunities.append(
                    V49Opportunity(
                        symbol=symbol,
                        session=session.value,
                        operating_date=operating_day,
                        h1_state_direction=state.direction.value,
                        h1_state_from=state.active_from.isoformat(),
                        h1_state_until=state.active_until.isoformat(),
                        h1_state_basis=state.established_by,
                        m15_setup_confirmed_at=setup.confirmed_at.isoformat(),
                        m15_protected_swing_price=str(setup.swing_price),
                        m1_trigger_confirmed_at=trigger_at.isoformat(),
                        m1_trigger_family=family,
                        decision_reference_price=str(decision_price),
                        structural_target_witness_price=str(target),
                    )
                )

    ordered = tuple(
        sorted(opportunities, key=lambda item: item.m1_trigger_confirmed_at)
    )
    return (
        V49MarketCapacity(
            identity=IDENTITY,
            symbol=symbol,
            session=session.value,
            window_start=window_start.isoformat(),
            window_end_exclusive=window_end.isoformat(),
            h1_bias_events=sum(
                1 for item in bias_events if window_start <= item.confirmed_at < window_end
            ),
            h1_states=counters["H1_STATES"],
            m15_setups=counters["M15_SETUPS"],
            m1_triggers=counters["M1_TRIGGERS"],
            target_witnesses=counters["TARGET_WITNESSES"],
            source_complete_opportunities=len(ordered),
            by_trigger_family=tuple(sorted(trigger_families.items())),
        ),
        ordered,
    )


def write_market(
    report: V49MarketCapacity,
    opportunities: tuple[V49Opportunity, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-v49-hf-capacity"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-opportunities.jsonl").open("w", encoding="utf-8") as handle:
        for item in opportunities:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def _read_market_reports(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-v49-hf-capacity.json"))
    if len(paths) != 9:
        raise ValueError(f"V49 matrix requires nine market reports, got {len(paths)}")
    return tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)


def _read_opportunities(root: Path) -> tuple[V49Opportunity, ...]:
    rows: list[V49Opportunity] = []
    for path in sorted(root.rglob("capitalizer-*-v49-hf-capacity-opportunities.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V49Opportunity(**json.loads(line)))
    return tuple(sorted(rows, key=lambda item: item.m1_trigger_confirmed_at))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _read_market_reports(root)
    opportunities = _read_opportunities(root)
    by_session: Counter[str] = Counter()
    for row in reports:
        by_session[str(row["session"])] += int(row["source_complete_opportunities"])

    annual_total = sum(by_session.values())
    density = assess_v49_density(
        annual_total=annual_total,
        asia_total=by_session["ASIA"],
        london_total=by_session["LONDON"],
        new_york_total=by_session["NEW_YORK"],
    )
    selected = _portfolio_max3(opportunities)

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": DEV_WINDOW_START.isoformat(),
        "window_end_exclusive": DEV_WINDOW_END.isoformat(),
        "decision_timeframes": ["H1", "M15", "M1"],
        "daily_used": False,
        "h4_used": False,
        "source_complete_opportunities": annual_total,
        "by_session": dict(sorted(by_session.items())),
        "density_decision": density.decision.value,
        "minimum_annual_required": 500,
        "minimum_per_session_required": 100,
        "portfolio_max3_chronological_selected": len(selected),
        "market_reports": sorted(reports, key=lambda row: str(row["symbol"])),
        "outcome_used": False,
        "economics_used": False,
        "fresh_holdout_used": False,
        "trader_certified": False,
        "live_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v49-nine-market-high-frequency-capacity.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )
    market.add_argument("--window-start")
    market.add_argument("--window-end")

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        window_start = (
            datetime.fromisoformat(args.window_start)
            if args.window_start
            else DEV_WINDOW_START
        )
        window_end = (
            datetime.fromisoformat(args.window_end)
            if args.window_end
            else DEV_WINDOW_END
        )
        report, opportunities = build_market_capacity(
            args.m1_root,
            session=CapitalizerSession(args.session),
            window_start=window_start,
            window_end=window_end,
        )
        write_market(report, opportunities, args.output)
        print(json.dumps(asdict(report), sort_keys=True))
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
