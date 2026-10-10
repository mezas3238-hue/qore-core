"""V48 pre-economic H1 -> M15 -> M1 Scalping census.

Purpose
-------
Measure a source-faithful *lower bound* of Capitalizer opportunity density across the
frozen nine-market / three-session universe without reading trade outcomes.

Implemented source branch:
    H1 Candle-2/Candle-3 bias at causal POI
    -> M15 CISD confirms the wick/protected swing
    -> M1 local-liquidity sweep + CISD confirms continuation
    -> route-valid protected-swing invalidation is geometrically available
    -> at least one untouched prior H1 objective is available

The FVG + CISD continuation family is not yet included, so this census must never be
described as complete opportunity density. MAX3/session is reported as a chronological
ceiling only. No P&L, R, lifecycle, future outcomes, Fresh Holdout, capital or execution.
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
from zoneinfo import ZoneInfo

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
from qore.infrastructure.trader_lab.capitalizer_human_decision_graph_v48 import (
    V48Session,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
    bar_interacts_with_poi,
    detect_external_liquidity_swing,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_three_session_coverage_gate_v48 import (
    V48SessionMarketCoverage,
    assess_three_session_coverage,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    V48M1CISDStatus,
    observe_first_m1_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    observe_first_m1_fvg_cisd_continuation,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
    observe_first_structural_cisd,
)

IDENTITY = "QORE_CAPITALIZER_V48_GENERIC_SCALP_PRE_ECONOMIC_CENSUS"
MATRIX_IDENTITY = "QORE_CAPITALIZER_V48_NINE_MARKET_THREE_SESSION_SCALP_CENSUS"
WINDOW_START = datetime(2025, 9, 17, tzinfo=UTC)
WINDOW_END = datetime(2026, 9, 17, tzinfo=UTC)
LOOKBACK_START = WINDOW_START - timedelta(days=14)
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class V48AggregatedBar:
    opened_at: datetime
    closed_at: datetime
    source: CapitalizerSourceBar
    minute_count: int


@dataclass(frozen=True, slots=True)
class V48H1BiasEvent:
    confirmed_at: datetime
    direction: CapitalizerSourceDirection
    closure_kind: str
    poi_kind: str


@dataclass(frozen=True, slots=True)
class V48ScalpOpportunity:
    symbol: str
    session: str
    operating_date: str
    direction: str
    h1_bias_confirmed_at: str
    h1_closure_kind: str
    h1_poi_kind: str
    m15_cisd_confirmed_at: str
    m15_protected_swing_price: str
    m1_continuation_confirmed_at: str
    m1_continuation_family: str
    decision_reference_price: str
    structural_target_witness_price: str
    outcome_used: bool = False
    economics_calculated: bool = False
    exact_entry_selected: bool = False
    exact_target_selected: bool = False

    def __post_init__(self) -> None:
        if self.outcome_used or self.economics_calculated:
            raise ValueError("pre-economic census cannot read outcomes/economics")
        if self.exact_entry_selected or self.exact_target_selected:
            raise ValueError("census cannot select exact execution/target policy")


@dataclass(frozen=True, slots=True)
class V48ScalpMarketCensus:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    h1_bias_events: int
    m15_cisd_protected_swings: int
    m1_sweep_cisd_continuations: int
    m1_fvg_cisd_continuations: int
    m1_source_valid_continuations: int
    session_matched_continuations: int
    structural_stop_available: int
    structural_target_available: int
    source_complete_opportunities: int
    max3_chronological_selected: int
    by_year: tuple[tuple[int, int], ...]
    stage_counts: tuple[tuple[str, int], ...]
    continuation_families_implemented: tuple[str, ...] = (
        "LIQUIDITY_SWEEP_CISD",
        "FVG_RETRACE_CISD",
    )
    fvg_cisd_continuation_implemented: bool = True
    census_is_lower_bound: bool = True
    outcome_used: bool = False
    economics_calculated: bool = False
    fresh_holdout_used: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V48 scalp census identity")
        if not self.fvg_cisd_continuation_implemented:
            raise ValueError("this census requires both documented continuation families")
        if not self.census_is_lower_bound:
            raise ValueError("partial continuation coverage must remain lower-bound evidence")
        if (
            self.outcome_used
            or self.economics_calculated
            or self.fresh_holdout_used
            or self.trader_certified
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise ValueError("V48 census cannot claim economic/certification authority")


def _aggregate(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    minutes: int,
) -> tuple[V48AggregatedBar, ...]:
    if minutes not in {15, 60}:
        raise ValueError("V48 generic scalp census only supports source-safe M15/H1 aggregation")

    seconds = minutes * 60
    grouped: dict[int, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        bucket = int(bar.opened_at.timestamp()) // seconds
        grouped[bucket].append(bar)

    minimum = minutes * 3 // 4
    result: list[V48AggregatedBar] = []
    for bucket in sorted(grouped):
        chunk = sorted(grouped[bucket], key=lambda item: item.opened_at)
        if len(chunk) < minimum:
            continue
        result.append(
            V48AggregatedBar(
                opened_at=chunk[0].opened_at,
                closed_at=chunk[-1].closed_at,
                source=CapitalizerSourceBar(
                    open=chunk[0].open,
                    high=max(item.high for item in chunk),
                    low=min(item.low for item in chunk),
                    close=chunk[-1].close,
                ),
                minute_count=len(chunk),
            )
        )
    return tuple(result)


def _poi_direction_compatible(
    poi: CapitalizerSourcePOI,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return poi.kind in {
            CapitalizerSourcePOIKind.BULLISH_FVG,
            CapitalizerSourcePOIKind.SWING_LOW,
        }
    return poi.kind in {
        CapitalizerSourcePOIKind.BEARISH_FVG,
        CapitalizerSourcePOIKind.SWING_HIGH,
    }


def _build_h1_bias_events(
    h1: tuple[V48AggregatedBar, ...],
) -> tuple[V48H1BiasEvent, ...]:
    if len(h1) < 4:
        return ()

    pois_by_confirm_index: dict[int, list[CapitalizerSourcePOI]] = defaultdict(list)
    for center in range(1, len(h1) - 1):
        left, mid, right = h1[center - 1], h1[center], h1[center + 1]
        fvg = detect_fair_value_gap(
            candle1=left.source,
            candle2=mid.source,
            candle3=right.source,
        )
        if fvg is not None:
            pois_by_confirm_index[center + 1].append(fvg)
        swing = detect_external_liquidity_swing(
            left=left.source,
            center=mid.source,
            right=right.source,
        )
        if swing is not None:
            pois_by_confirm_index[center + 1].append(swing)

    active_pois: list[CapitalizerSourcePOI] = []
    events: list[V48H1BiasEvent] = []
    previous_interacted: tuple[CapitalizerSourcePOI, ...] = ()
    previous_c2_confirmed = False

    for index in range(1, len(h1)):
        active_pois.extend(pois_by_confirm_index.get(index - 1, ()))
        current = h1[index].source
        previous = h1[index - 1].source

        if index >= 2:
            c3 = detect_candle3_confirmation(
                candle2=previous,
                candle3=current,
                point_of_interest_present=bool(previous_interacted),
                candle2_reversal_already_confirmed=previous_c2_confirmed,
            )
            if c3 is not None and c3.source_rule_satisfied:
                compatible = tuple(
                    poi
                    for poi in previous_interacted
                    if _poi_direction_compatible(poi, c3.direction)
                )
                if compatible:
                    events.append(
                        V48H1BiasEvent(
                            confirmed_at=h1[index].closed_at,
                            direction=c3.direction,
                            closure_kind=c3.kind.value,
                            poi_kind=compatible[0].kind.value,
                        )
                    )

        interacted_bullish = tuple(
            poi
            for poi in active_pois
            if _poi_direction_compatible(poi, CapitalizerSourceDirection.BULLISH)
            and bar_interacts_with_poi(bar=current, poi=poi)
        )
        interacted_bearish = tuple(
            poi
            for poi in active_pois
            if _poi_direction_compatible(poi, CapitalizerSourceDirection.BEARISH)
            and bar_interacts_with_poi(bar=current, poi=poi)
        )
        interacted = interacted_bullish + interacted_bearish

        c2 = detect_candle2_reversal_closure(
            previous=previous,
            candle2=current,
            point_of_interest_present=bool(interacted),
        )
        current_c2_confirmed = False
        if c2 is not None and c2.source_rule_satisfied:
            compatible = (
                interacted_bullish
                if c2.direction is CapitalizerSourceDirection.BULLISH
                else interacted_bearish
            )
            current_c2_confirmed = bool(compatible)
            if compatible:
                events.append(
                    V48H1BiasEvent(
                        confirmed_at=h1[index].closed_at,
                        direction=c2.direction,
                        closure_kind=c2.kind.value,
                        poi_kind=compatible[0].kind.value,
                    )
                )

        previous_interacted = interacted
        previous_c2_confirmed = current_c2_confirmed

    return tuple(sorted(events, key=lambda item: item.confirmed_at))


def _timed_m15(
    bars: tuple[V48AggregatedBar, ...],
) -> tuple[V48TimedSourceBar, ...]:
    return tuple(
        V48TimedSourceBar(
            opened_at=bar.opened_at,
            closed_at=bar.closed_at,
            source=bar.source,
        )
        for bar in bars
    )


def _slice_around(
    bars: tuple[Any, ...],
    opened_times: tuple[datetime, ...],
    *,
    start: datetime,
    end: datetime,
    context_items: int = 3,
) -> tuple[Any, ...]:
    left = max(0, bisect.bisect_left(opened_times, start) - context_items)
    right = bisect.bisect_left(opened_times, end)
    return bars[left:right]


def _operating_date(moment: datetime, session: CapitalizerSession) -> str:
    local = moment.astimezone(NEW_YORK)
    value = local.date()
    if session is CapitalizerSession.ASIA and local.hour < 2:
        value -= timedelta(days=1)
    return value.isoformat()


def _side(direction: CapitalizerSourceDirection) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSide.SHORT
    )


def _untouched_h1_target(
    h1: tuple[V48AggregatedBar, ...],
    m1: tuple[CapitalizerM1Bar, ...],
    *,
    decision_at: datetime,
    decision_price: Decimal,
    direction: CapitalizerSourceDirection,
) -> Decimal | None:
    eligible_h1 = tuple(bar for bar in h1 if bar.closed_at <= decision_at)
    for candidate in reversed(eligible_h1[-24:]):
        target = (
            candidate.source.high
            if direction is CapitalizerSourceDirection.BULLISH
            else candidate.source.low
        )
        directionally_ahead = (
            target > decision_price
            if direction is CapitalizerSourceDirection.BULLISH
            else target < decision_price
        )
        if not directionally_ahead:
            continue

        touched = any(
            (
                bar.high >= target
                if direction is CapitalizerSourceDirection.BULLISH
                else bar.low <= target
            )
            for bar in m1
            if candidate.closed_at < bar.closed_at <= decision_at
        )
        if not touched:
            return target
    return None


def _chronological_max3(
    opportunities: tuple[V48ScalpOpportunity, ...],
) -> tuple[V48ScalpOpportunity, ...]:
    grouped: dict[str, list[V48ScalpOpportunity]] = defaultdict(list)
    for item in opportunities:
        grouped[f"{item.session}:{item.operating_date}"].append(item)

    selected: list[V48ScalpOpportunity] = []
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=lambda item: item.m1_continuation_confirmed_at)
        selected.extend(rows[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda item: item.m1_continuation_confirmed_at))


def build_market_census(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[V48ScalpMarketCensus, tuple[V48ScalpOpportunity, ...]]:
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END
    )
    if not bars:
        raise ValueError("V48 scalp census found no retained native M1")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("one census root must contain one symbol")
    if symbol not in allowed_markets(session):
        raise ValueError("symbol/session outside frozen Capitalizer identity")

    h1 = _aggregate(bars, minutes=60)
    m15 = _timed_m15(_aggregate(bars, minutes=15))
    h1_bias = tuple(
        item
        for item in _build_h1_bias_events(h1)
        if WINDOW_START <= item.confirmed_at < WINDOW_END
    )

    m15_opened = tuple(item.opened_at for item in m15)
    m1_opened = tuple(item.opened_at for item in bars)
    stages: Counter[str] = Counter()
    stages["H1_BIAS_EVENT"] = len(h1_bias)
    opportunities: list[V48ScalpOpportunity] = []

    for bias in h1_bias:
        deadline = min(bias.confirmed_at + timedelta(hours=1), WINDOW_END)
        m15_window = _slice_around(
            m15,
            m15_opened,
            start=bias.confirmed_at,
            end=deadline,
        )
        m15_cisd = observe_first_structural_cisd(
            m15_window,
            direction=bias.direction,
            after=bias.confirmed_at,
            before=deadline,
            higher_timeframe_closure_confirmed=True,
        )
        if not m15_cisd.source_valid or m15_cisd.confirmed_at is None:
            stages["M15_CISD_PROTECTED_SWING_MISSING"] += 1
            continue
        stages["M15_CISD_PROTECTED_SWING"] += 1

        m1_window = _slice_around(
            bars,
            m1_opened,
            start=m15_cisd.confirmed_at,
            end=deadline,
            context_items=0,
        )
        if len(m1_window) < 4:
            stages["M1_CONTINUATION_WINDOW_TOO_SPARSE"] += 1
            continue
        sweep_cisd = observe_first_m1_cisd(
            m1_window,
            thesis_at=m15_cisd.confirmed_at,
            deadline_at=deadline,
            side=_side(bias.direction),
        )
        fvg_cisd = observe_first_m1_fvg_cisd_continuation(
            m1_window,
            thesis_at=m15_cisd.confirmed_at,
            deadline_at=deadline,
            direction=bias.direction,
        )

        continuation_candidates: list[tuple[datetime, str, Decimal]] = []
        if (
            sweep_cisd.status is V48M1CISDStatus.CONFIRMED
            and sweep_cisd.confirmed_at is not None
            and sweep_cisd.confirmation_close is not None
        ):
            stages["M1_SWEEP_CISD_CONTINUATION"] += 1
            continuation_candidates.append(
                (
                    sweep_cisd.confirmed_at,
                    "LIQUIDITY_SWEEP_CISD",
                    sweep_cisd.confirmation_close,
                )
            )
        else:
            stages["M1_SWEEP_CISD_CONTINUATION_MISSING"] += 1

        if fvg_cisd.confirmed and fvg_cisd.cisd_confirmed_at is not None:
            fvg_confirmation_bar = next(
                (
                    bar
                    for bar in m1_window
                    if bar.closed_at == fvg_cisd.cisd_confirmed_at
                ),
                None,
            )
            if fvg_confirmation_bar is None:
                raise ValueError("FVG+CISD confirmation bar must exist in causal window")
            stages["M1_FVG_CISD_CONTINUATION"] += 1
            continuation_candidates.append(
                (
                    fvg_cisd.cisd_confirmed_at,
                    "FVG_RETRACE_CISD",
                    fvg_confirmation_bar.close,
                )
            )
        else:
            stages["M1_FVG_CISD_CONTINUATION_MISSING"] += 1

        if not continuation_candidates:
            stages["M1_SOURCE_VALID_CONTINUATION_MISSING"] += 1
            continue

        continuation_at, continuation_family, decision_price = min(
            continuation_candidates,
            key=lambda item: (item[0], item[1]),
        )
        stages["M1_SOURCE_VALID_CONTINUATION"] += 1

        observed_session = capitalizer_session_at(continuation_at)
        if observed_session is not session:
            stages["CONTINUATION_OUTSIDE_ASSIGNED_SESSION"] += 1
            continue
        stages["SESSION_MATCHED_CONTINUATION"] += 1

        if m15_cisd.swing_price is None:
            raise ValueError("source-valid M15 CISD requires protected swing")
        stop_valid = (
            m15_cisd.swing_price < decision_price
            if bias.direction is CapitalizerSourceDirection.BULLISH
            else m15_cisd.swing_price > decision_price
        )
        if not stop_valid:
            stages["STRUCTURAL_STOP_INVALID_GEOMETRY"] += 1
            continue
        stages["STRUCTURAL_STOP_AVAILABLE"] += 1

        target = _untouched_h1_target(
            h1,
            bars,
            decision_at=continuation_at,
            decision_price=decision_price,
            direction=bias.direction,
        )
        if target is None:
            stages["STRUCTURAL_TARGET_UNAVAILABLE"] += 1
            continue
        stages["STRUCTURAL_TARGET_AVAILABLE"] += 1

        opportunity = V48ScalpOpportunity(
            symbol=symbol,
            session=session.value,
            operating_date=_operating_date(continuation_at, session),
            direction=bias.direction.value,
            h1_bias_confirmed_at=bias.confirmed_at.isoformat(),
            h1_closure_kind=bias.closure_kind,
            h1_poi_kind=bias.poi_kind,
            m15_cisd_confirmed_at=m15_cisd.confirmed_at.isoformat(),
            m15_protected_swing_price=str(m15_cisd.swing_price),
            m1_continuation_confirmed_at=continuation_at.isoformat(),
            m1_continuation_family=continuation_family,
            decision_reference_price=str(decision_price),
            structural_target_witness_price=str(target),
        )
        opportunities.append(opportunity)
        stages["SOURCE_COMPLETE_OPPORTUNITY"] += 1

    ordered = tuple(
        sorted(opportunities, key=lambda item: item.m1_continuation_confirmed_at)
    )
    max3 = _chronological_max3(ordered)
    by_year: Counter[int] = Counter(
        datetime.fromisoformat(item.m1_continuation_confirmed_at).year
        for item in ordered
    )
    report = V48ScalpMarketCensus(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        h1_bias_events=stages["H1_BIAS_EVENT"],
        m15_cisd_protected_swings=stages["M15_CISD_PROTECTED_SWING"],
        m1_sweep_cisd_continuations=stages["M1_SWEEP_CISD_CONTINUATION"],
        m1_fvg_cisd_continuations=stages["M1_FVG_CISD_CONTINUATION"],
        m1_source_valid_continuations=stages["M1_SOURCE_VALID_CONTINUATION"],
        session_matched_continuations=stages["SESSION_MATCHED_CONTINUATION"],
        structural_stop_available=stages["STRUCTURAL_STOP_AVAILABLE"],
        structural_target_available=stages["STRUCTURAL_TARGET_AVAILABLE"],
        source_complete_opportunities=len(ordered),
        max3_chronological_selected=len(max3),
        by_year=tuple(sorted(by_year.items())),
        stage_counts=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, ordered


def write_market_census(
    report: V48ScalpMarketCensus,
    opportunities: tuple[V48ScalpOpportunity, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-v48-scalp-pre-economic-census"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-opportunities.jsonl").open("w", encoding="utf-8") as handle:
        for item in opportunities:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")


def _read_reports(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-v48-scalp-pre-economic-census.json"))
    if len(paths) != 9:
        raise ValueError(f"V48 matrix requires exactly nine market reports, got {len(paths)}")
    rows = tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)
    if any(row.get("identity") != IDENTITY for row in rows):
        raise ValueError("unexpected V48 market census identity")
    return rows


def _read_opportunities(root: Path) -> tuple[V48ScalpOpportunity, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v48-scalp-pre-economic-census-opportunities.jsonl")
    )
    rows: list[V48ScalpOpportunity] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(V48ScalpOpportunity(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: item.m1_continuation_confirmed_at)
    )


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _read_reports(root)
    expected = {
        (session.value, symbol)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    observed = {(str(row["session"]), str(row["symbol"])) for row in reports}
    if observed != expected:
        raise ValueError("V48 census market/session universe mismatch")

    session_map = {
        CapitalizerSession.ASIA.value: V48Session.ASIA,
        CapitalizerSession.LONDON.value: V48Session.LONDON,
        CapitalizerSession.NEW_YORK.value: V48Session.NEW_YORK,
    }
    coverage_rows = tuple(
        V48SessionMarketCoverage(
            session=session_map[str(row["session"])],
            market=str(row["symbol"]),
            source_complete_opportunities=int(row["source_complete_opportunities"]),
        )
        for row in reports
    )
    coverage = assess_three_session_coverage(coverage_rows)

    by_session: dict[str, int] = Counter()
    total = 0
    market_local_max3_sum = 0
    for row in reports:
        count = int(row["source_complete_opportunities"])
        total += count
        market_local_max3_sum += int(row["max3_chronological_selected"])
        by_session[str(row["session"])] += count

    all_opportunities = _read_opportunities(root)
    if len(all_opportunities) != total:
        raise ValueError("V48 opportunity ledgers do not reconcile with market reports")
    portfolio_max3 = _chronological_max3(all_opportunities)
    max3_by_session: Counter[str] = Counter(item.session for item in portfolio_max3)

    return {
        "identity": MATRIX_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "session_count": 3,
        "source_complete_opportunities": total,
        "market_local_max3_selected_sum": market_local_max3_sum,
        "portfolio_max3_chronological_selected": len(portfolio_max3),
        "portfolio_max3_by_session": dict(sorted(max3_by_session.items())),
        "by_session": dict(sorted(by_session.items())),
        "coverage_decision": coverage.decision.value,
        "missing_market_rows": list(coverage.missing_market_rows),
        "empty_sessions": [item.value for item in coverage.empty_sessions],
        "markets": sorted(reports, key=lambda row: str(row["symbol"])),
        "continuation_families_implemented": [
            "LIQUIDITY_SWEEP_CISD",
            "FVG_RETRACE_CISD",
        ],
        "fvg_cisd_continuation_implemented": True,
        "census_is_lower_bound": True,
        "h4_routes_included": False,
        "outcome_used": False,
        "economics_calculated": False,
        "fresh_holdout_used": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-v48-nine-market-three-session-scalp-census.json"
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

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        market_report, opportunities = build_market_census(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market_census(market_report, opportunities, args.output)
        print(
            json.dumps(
                {
                    "symbol": market_report.symbol,
                    "session": market_report.session,
                    "h1_bias_events": market_report.h1_bias_events,
                    "source_complete_opportunities": (
                        market_report.source_complete_opportunities
                    ),
                    "max3_chronological_selected": (
                        market_report.max3_chronological_selected
                    ),
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
