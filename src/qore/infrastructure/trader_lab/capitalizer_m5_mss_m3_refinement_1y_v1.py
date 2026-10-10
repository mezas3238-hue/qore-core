"""B-M3 1Y replay for QORE Capitalizer.

Owner-frozen experimental delta over B:
    latest completed H1 C2/C3 bias
    -> prior-session significant liquidity sweep
    -> M5 CISD
    -> M5 MSS / protected swing
    -> M3 directional displacement + MSS
    -> M3 FVG
    -> first causal touch of M3 FVG CE
    -> entry

Only two strategic deltas are tested versus the intended strategy contract:
MSS is explicit on M5 after CISD, and refinement/entry setup is M3.
Native M1 is retained only for exact first-touch and lifecycle precedence.
M1 cannot originate or authorize a trade.

Risk/lifecycle remain frozen:
    stop = M5 protected swing
    target = fixed 2R
    same-session lifecycle
    same-minute stop/target ambiguity = STOP_FIRST
    MAX3/session = ceiling, never quota

Window: [2025-09-17, 2026-09-17)
Research only. No certification, promotion, live, or real-capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
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
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
    HTFBiasEvent,
    _aggregate_h1,
    _build_htf_bias_events,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
    ICTReplayMetrics,
    _aware,
    _lifecycle,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    ReferenceLiquidity,
    StructureEvent,
    TFBar,
    _aggregate_tf,
    _find_structure_event,
    _immediate_h1_bias,
    _index_day_inputs,
    _pivots,
    _side_from_bias,
    _sweep_confirmed,
    _sweep_extreme,
    _sweep_level,
)

__all__ = ["TFBar"]

IDENTITY = "QORE_CAPITALIZER_M5_MSS_M3_REFINEMENT_1Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_M5_MSS_M3_REFINEMENT_1Y_MATRIX_V1"
)
ENTRY_IDENTITY = "H1_C2C3__PRIOR_SESSION_SWEEP__M5_CISD_MSS__M3_MSS_FVG_CE"
STOP_IDENTITY = "M5_PROTECTED_SWING"
TARGET_IDENTITY = "FIXED_2R"
PARENT_STRUCTURE_TIMEFRAME = "M5"
LOOKBACK_START = WINDOW_START - timedelta(days=14)
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
}


@dataclass(frozen=True, slots=True)
class BM3Trade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_bias_confirmed_at: str
    h1_closure_kind: str
    h1_poi_kind: str
    reference_liquidity_source: str
    reference_high: str
    reference_low: str
    sweep_at: str
    sweep_level: str
    sweep_extreme: str
    m5_confirmed_at: str
    m5_break_price: str
    m5_protected_swing_price: str
    m5_cisd_confirmed_at: str
    m5_cisd_boundary: str
    m3_displacement_at: str
    m3_mss_level: str
    m3_fvg_confirmed_at: str
    m3_fvg_low: str
    m3_fvg_high: str
    m3_ce_price: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    same_minute_stop_target_ambiguity: bool
    entry_definition: str = ENTRY_IDENTITY
    stop_definition: str = STOP_IDENTITY
    target_definition: str = TARGET_IDENTITY
    parent_structure_timeframe: str = PARENT_STRUCTURE_TIMEFRAME
    m15_gate_required: bool = False
    entry_timeframe: str = "M3"
    m5_cisd_required: bool = True
    m5_mss_required: bool = True
    m1_intrabar_only: bool = True
    m1_originated_trade: bool = False
    daily_driver_used: bool = False
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class BM3MarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    sessions_with_reference_liquidity: int
    h1_gate_passes: int
    prior_session_sweeps: int
    m5_structure_passes: int
    m5_cisd_passes: int
    m5_mss_passes: int
    m3_mss_passes: int
    m3_fvg_passes: int
    raw_entries: int
    raw_metrics: ICTReplayMetrics | None
    raw_stop_exits: int
    raw_target_exits: int
    raw_session_exits: int
    sessions_with_entry: int
    max_entries_one_market_session: int
    stage_counts: tuple[tuple[str, int], ...]
    parent_structure_timeframe: str = PARENT_STRUCTURE_TIMEFRAME
    m15_gate_required: bool = False
    architecture_predeclared: bool = True
    max3_is_ceiling_not_quota: bool = True
    methodology_research_only: bool = True
    daily_driver_used: bool = False
    entry_timeframe: str = "M3"
    m5_cisd_required: bool = True
    m5_mss_required: bool = True
    m1_intrabar_only: bool = True
    m1_can_originate_trade: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _find_m5_parent_structure(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
    *,
    after: Any,
    before: Any,
    side: CapitalizerSide,
) -> StructureEvent | None:
    return _find_structure_event(
        bars,
        pivots,
        after=after,
        before=before,
        side=side,
        timeframe=PARENT_STRUCTURE_TIMEFRAME,
    )



@dataclass(frozen=True, slots=True)
class M5CisdEvent:
    confirmed_at: Any
    boundary: Decimal


def _find_m5_cisd(
    bars: tuple[TFBar, ...],
    *,
    after: Any,
    before: Any,
    side: CapitalizerSide,
) -> M5CisdEvent | None:
    boundary: Decimal | None = None
    for bar in bars:
        if not (after < bar.closed_at <= before):
            continue
        source = bar.source
        opposing = (
            source.close < source.open
            if side is CapitalizerSide.LONG
            else source.close > source.open
        )
        if opposing:
            if boundary is None:
                boundary = source.open
            elif side is CapitalizerSide.LONG:
                boundary = max(boundary, source.open)
            else:
                boundary = min(boundary, source.open)
            continue
        if boundary is None:
            continue
        confirmed = (
            source.close > boundary
            if side is CapitalizerSide.LONG
            else source.close < boundary
        )
        if confirmed:
            return M5CisdEvent(confirmed_at=bar.closed_at, boundary=boundary)
    return None


def _latest_tf_pivot(
    pivots: tuple[Pivot, ...],
    *,
    before: Any,
    side: CapitalizerSide,
) -> Pivot | None:
    kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    eligible = tuple(
        pivot
        for pivot in pivots
        if pivot.kind == kind and pivot.confirmed_at <= before
    )
    return None if not eligible else eligible[-1]


def _significant_tf_displacement(
    bar: TFBar,
    *,
    side: CapitalizerSide,
) -> bool:
    source = bar.source
    full_range = source.high - source.low
    body = abs(source.close - source.open)
    if full_range <= 0:
        return False
    directional = (
        source.close > source.open
        if side is CapitalizerSide.LONG
        else source.close < source.open
    )
    return directional and body > (full_range - body)


def _m3_entry_after_m5_mss(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    m3: tuple[TFBar, ...],
    m3_pivots: tuple[Pivot, ...],
    after: Any,
    before: Any,
    side: CapitalizerSide,
    stop_price: Decimal,
    stages: Counter[str],
) -> tuple[
    int,
    Decimal,
    Decimal,
    Decimal,
    Any,
    Decimal,
    Any,
] | None:
    eligible = tuple(
        (index, bar)
        for index, bar in enumerate(m3)
        if after < bar.closed_at <= before
    )
    if len(eligible) < 3:
        return None

    for pos in range(1, len(eligible) - 1):
        index, displacement = eligible[pos]
        if not _significant_tf_displacement(displacement, side=side):
            continue
        mss = _latest_tf_pivot(
            m3_pivots,
            before=displacement.opened_at,
            side=side,
        )
        if mss is None:
            continue
        closed_through = (
            displacement.source.close > mss.price
            if side is CapitalizerSide.LONG
            else displacement.source.close < mss.price
        )
        if not closed_through:
            continue
        stages["M3_MSS_AFTER_M5_MSS"] += 1

        if index <= 0 or index + 1 >= len(m3):
            continue
        first = m3[index - 1]
        third = m3[index + 1]
        if third.closed_at > before:
            continue
        if side is CapitalizerSide.LONG:
            valid_fvg = first.source.high < third.source.low
            fvg_low, fvg_high = first.source.high, third.source.low
        else:
            valid_fvg = first.source.low > third.source.high
            fvg_low, fvg_high = third.source.high, first.source.low
        if not valid_fvg:
            continue
        stages["M3_FVG_AFTER_M5_MSS"] += 1
        ce = (fvg_low + fvg_high) / Decimal("2")
        valid_stop = (
            stop_price < ce
            if side is CapitalizerSide.LONG
            else stop_price > ce
        )
        if not valid_stop:
            stages["M5_PROTECTED_SWING_INVALID_GEOMETRY"] += 1
            continue

        for entry_index, bar in enumerate(execution):
            if bar.opened_at < third.closed_at:
                continue
            if bar.opened_at >= before:
                break
            if bar.low <= ce <= bar.high:
                return (
                    entry_index,
                    ce,
                    fvg_low,
                    fvg_high,
                    third.closed_at,
                    mss.price,
                    displacement.closed_at,
                )
    return None


def _metrics(
    trades: tuple[BM3Trade, ...],
) -> ICTReplayMetrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    total = sum(values, Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return ICTReplayMetrics(
        trades=len(values),
        wins=sum(value > 0 for value in values),
        losses=sum(value < 0 for value in values),
        flats=sum(value == 0 for value in values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gp),
        gross_loss_r=str(gl),
        profit_factor=None if gl == 0 else str(gp / gl),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(item.exit_reason == "STOP" for item in ordered),
        target_exits=sum(item.exit_reason == "TARGET" for item in ordered),
        session_exits=sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        ambiguous_stop_first_exits=sum(
            item.same_minute_stop_target_ambiguity for item in ordered
        ),
    )


def _scan_operating_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    reference: ReferenceLiquidity | None,
    execution: tuple[CapitalizerM1Bar, ...],
    h1: tuple[AggregatedBar, ...],
    bias_events: tuple[HTFBiasEvent, ...],
    m5: tuple[TFBar, ...],
    m5_pivots: tuple[Pivot, ...],
    m3: tuple[TFBar, ...],
    m3_pivots: tuple[Pivot, ...],
    stages: Counter[str],
) -> tuple[BM3Trade, ...]:
    if reference is None:
        stages["REFERENCE_LIQUIDITY_UNAVAILABLE"] += 1
        return ()
    stages["REFERENCE_LIQUIDITY_AVAILABLE"] += 1

    if len(execution) < 15:
        stages["EXECUTION_WINDOW_TOO_SPARSE"] += 1
        return ()
    results: list[BM3Trade] = []
    cursor = 2
    while cursor < len(execution) and len(results) < MAX_EXECUTIONS_PER_SESSION:
        sweep_index: int | None = None
        bias: HTFBiasEvent | None = None
        side: CapitalizerSide | None = None

        for index in range(cursor, len(execution)):
            candidate_bias = _immediate_h1_bias(
                h1,
                bias_events,
                execution[index].opened_at,
            )
            if candidate_bias is None:
                continue
            stages["H1_GATE_PASS"] += 1
            candidate_side = _side_from_bias(candidate_bias)
            if _sweep_confirmed(
                execution[index],
                side=candidate_side,
                reference=reference,
            ):
                sweep_index = index
                bias = candidate_bias
                side = candidate_side
                break

        if sweep_index is None or bias is None or side is None:
            stages["NO_CAUSAL_SWEEP_AFTER_H1_GATE"] += 1
            break

        sweep_bar = execution[sweep_index]
        stages["PRIOR_SESSION_SWEEP"] += 1
        window_end = execution[-1].closed_at

        cisd = _find_m5_cisd(
            m5,
            after=sweep_bar.closed_at,
            before=window_end,
            side=side,
        )
        if cisd is None:
            stages["M5_CISD_MISSING"] += 1
            cursor = sweep_index + 1
            continue
        stages["M5_CISD_PASS"] += 1

        m5_event = _find_m5_parent_structure(
            m5,
            m5_pivots,
            after=cisd.confirmed_at,
            before=window_end,
            side=side,
        )
        if m5_event is None:
            stages["M5_MSS_MISSING"] += 1
            cursor = sweep_index + 1
            continue
        stages["M5_MSS_PASS"] += 1

        setup = _m3_entry_after_m5_mss(
            execution,
            m3=m3,
            m3_pivots=m3_pivots,
            after=m5_event.confirmed_at,
            before=window_end,
            side=side,
            stop_price=m5_event.protected_swing_price,
            stages=stages,
        )
        if setup is None:
            stages["M3_EXECUTION_MISSING"] += 1
            cursor = sweep_index + 1
            continue

        (
            entry_index,
            entry_price,
            fvg_low,
            fvg_high,
            fvg_confirmed_at,
            m3_mss_level,
            m3_displacement_at,
        ) = setup

        risk = abs(entry_price - m5_event.protected_swing_price)
        if risk <= 0:
            stages["NONPOSITIVE_RISK"] += 1
            cursor = entry_index + 1
            continue

        target = (
            entry_price + Decimal("2") * risk
            if side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = _lifecycle(
            execution,
            entry_index=entry_index,
            side=side,
            entry_price=entry_price,
            stop_price=m5_event.protected_swing_price,
            target_price=target,
        )
        stages["M3_CE_ENTRY"] += 1
        results.append(
            BM3Trade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=side.value,
                h1_bias_confirmed_at=bias.confirmed_at.isoformat(),
                h1_closure_kind=bias.closure_kind,
                h1_poi_kind=bias.poi_kind,
                reference_liquidity_source=reference.source,
                reference_high=str(reference.high),
                reference_low=str(reference.low),
                sweep_at=sweep_bar.opened_at.isoformat(),
                sweep_level=str(
                    _sweep_level(side=side, reference=reference)
                ),
                sweep_extreme=str(_sweep_extreme(sweep_bar, side=side)),
                m5_confirmed_at=m5_event.confirmed_at.isoformat(),
                m5_break_price=str(m5_event.break_price),
                m5_protected_swing_price=str(
                    m5_event.protected_swing_price
                ),
                m5_cisd_confirmed_at=cisd.confirmed_at.isoformat(),
                m5_cisd_boundary=str(cisd.boundary),
                m3_displacement_at=m3_displacement_at.isoformat(),
                m3_mss_level=str(m3_mss_level),
                m3_fvg_confirmed_at=fvg_confirmed_at.isoformat(),
                m3_fvg_low=str(fvg_low),
                m3_fvg_high=str(fvg_high),
                m3_ce_price=str(entry_price),
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(m5_event.protected_swing_price),
                target_price=str(target),
                planned_reward_r="2",
                realized_gross_r=str(realized),
                exit_reason=reason,
                m1_bars_held=held,
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )

        exit_index = next(
            (
                index
                for index in range(entry_index, len(execution))
                if execution[index].closed_at >= exit_at
            ),
            len(execution) - 1,
        )
        cursor = exit_index + 1

    return tuple(results)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[BM3MarketReport, tuple[BM3Trade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("m5-mss-m3-refinement replay found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("m5-mss-m3-refinement replay requires one symbol per M1 root")

    h1 = _aggregate_h1(all_bars)
    bias_events = _build_htf_bias_events(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_pivots = _pivots(m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)

    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )
    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )

    stages: Counter[str] = Counter()
    trades: list[BM3Trade] = []
    per_day: Counter[str] = Counter()

    for value in grouped_dates:
        operating_day = date.fromisoformat(value)
        produced = _scan_operating_day(
            symbol=symbol,
            session=session,
            operating_day=operating_day,
            reference=reference_by_day.get(value),
            execution=execution_by_day.get(value, ()),
            h1=h1,
            bias_events=bias_events,
            m5=m5,
            m5_pivots=m5_pivots,
            m3=m3,
            m3_pivots=m3_pivots,
            stages=stages,
        )
        trades.extend(produced)
        per_day[value] += len(produced)

    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    report = BM3MarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        operating_sessions_scanned=len(grouped_dates),
        sessions_with_reference_liquidity=stages[
            "REFERENCE_LIQUIDITY_AVAILABLE"
        ],
        h1_gate_passes=stages["H1_GATE_PASS"],
        prior_session_sweeps=stages["PRIOR_SESSION_SWEEP"],
        m5_structure_passes=stages["M5_MSS_PASS"],
        m5_cisd_passes=stages["M5_CISD_PASS"],
        m5_mss_passes=stages["M5_MSS_PASS"],
        m3_mss_passes=stages["M3_MSS_AFTER_M5_MSS"],
        m3_fvg_passes=stages["M3_FVG_AFTER_M5_MSS"],
        raw_entries=len(ordered),
        raw_metrics=_metrics(ordered),
        raw_stop_exits=sum(
            item.exit_reason == "STOP" for item in ordered
        ),
        raw_target_exits=sum(
            item.exit_reason == "TARGET" for item in ordered
        ),
        raw_session_exits=sum(
            item.exit_reason == "SESSION_EXIT" for item in ordered
        ),
        sessions_with_entry=sum(count > 0 for count in per_day.values()),
        max_entries_one_market_session=max(per_day.values(), default=0),
        stage_counts=tuple(
            sorted(stages.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, ordered


def write_market(
    report: BM3MarketReport,
    trades: tuple[BM3Trade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = (
        f"capitalizer-{report.symbol.lower()}-m5-mss-m3-refinement-1y-v1"
    )
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-m5-mss-m3-refinement-1y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(
            f"m5-mss-m3-refinement matrix requires 9 reports, got {len(paths)}"
        )
    reports: list[dict[str, Any]] = []
    for path in paths:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("identity") != IDENTITY:
            raise ValueError("unexpected m5-mss-m3-refinement market report")
        reports.append(dict(raw))
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("m5-mss-m3-refinement universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_trades(root: Path) -> tuple[BM3Trade, ...]:
    rows: list[BM3Trade] = []
    pattern = "capitalizer-*-m5-mss-m3-refinement-1y-v1-trades.jsonl"
    for path in sorted(root.rglob(pattern)):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(BM3Trade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _portfolio_max3(
    trades: tuple[BM3Trade, ...],
) -> tuple[BM3Trade, ...]:
    grouped: dict[str, list[BM3Trade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)

    selected: list[BM3Trade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol))
    )


def _monthly_counts(
    trades: tuple[BM3Trade, ...],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for trade in trades:
        counts[trade.operating_date[:7]] += 1
    return dict(sorted(counts.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = _portfolio_max3(raw)

    per_session: dict[str, dict[str, Any]] = {}
    for session in CapitalizerSession:
        session_raw = tuple(
            item for item in raw if item.session == session.value
        )
        session_max3 = tuple(
            item for item in max3 if item.session == session.value
        )
        per_session[session.value] = {
            "raw_trades": len(session_raw),
            "raw_metrics": (
                None
                if (value := _metrics(session_raw)) is None
                else asdict(value)
            ),
            "max3_trades": len(session_max3),
            "max3_metrics": (
                None
                if (value := _metrics(session_max3)) is None
                else asdict(value)
            ),
        }

    raw_metrics = _metrics(raw)
    max3_metrics = _metrics(max3)
    distinct_days = len({item.operating_date for item in max3})
    calendar_days = (WINDOW_END.date() - WINDOW_START.date()).days

    return {
        "identity": MATRIX_IDENTITY,
        "architecture": "H1_TO_M5_CISD_MSS_TO_M3",
        "architecture_predeclared": True,
        "parent_structure_timeframe": PARENT_STRUCTURE_TIMEFRAME,
        "m15_gate_required": False,
        "entry_identity": ENTRY_IDENTITY,
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "raw_trades": len(raw),
        "raw_metrics": None if raw_metrics is None else asdict(raw_metrics),
        "raw_stop_exits": sum(
            item.exit_reason == "STOP" for item in raw
        ),
        "raw_target_exits": sum(
            item.exit_reason == "TARGET" for item in raw
        ),
        "raw_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in raw
        ),
        "max3_selected_trades": len(max3),
        "max3_metrics": (
            None if max3_metrics is None else asdict(max3_metrics)
        ),
        "max3_stop_exits": sum(
            item.exit_reason == "STOP" for item in max3
        ),
        "max3_target_exits": sum(
            item.exit_reason == "TARGET" for item in max3
        ),
        "max3_session_exits": sum(
            item.exit_reason == "SESSION_EXIT" for item in max3
        ),
        "h1_gate_passes": sum(
            int(item["h1_gate_passes"]) for item in reports
        ),
        "prior_session_sweeps": sum(
            int(item["prior_session_sweeps"]) for item in reports
        ),
        "m5_structure_passes": sum(
            int(item["m5_structure_passes"]) for item in reports
        ),
        "m5_cisd_passes": sum(
            int(item["m5_cisd_passes"]) for item in reports
        ),
        "m5_mss_passes": sum(
            int(item["m5_mss_passes"]) for item in reports
        ),
        "m3_mss_passes": sum(
            int(item["m3_mss_passes"]) for item in reports
        ),
        "m3_fvg_passes": sum(
            int(item["m3_fvg_passes"]) for item in reports
        ),
        "monthly_max3_trades": _monthly_counts(max3),
        "days_with_any_trade": distinct_days,
        "calendar_days": calendar_days,
        "max3_trades_per_calendar_day": (
            0.0 if calendar_days == 0 else len(max3) / calendar_days
        ),
        "annualized_max3_trades": len(max3),
        "per_session": per_session,
        "markets": reports,
        "max3_is_ceiling_not_quota": True,
        "methodology_research_only": True,
        "daily_driver_used": False,
        "entry_timeframe": "M3",
        "m5_cisd_required": True,
        "m5_mss_required": True,
        "m1_intrabar_only": True,
        "m1_can_originate_trade": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-m5-mss-m3-refinement-1y-matrix-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
        report, trades = build_market_report(
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, trades, args.output)
        print(
            json.dumps(
                {
                    "symbol": report.symbol,
                    "session": report.session,
                    "trades": report.raw_entries,
                    "pf": (
                        None
                        if report.raw_metrics is None
                        else report.raw_metrics.profit_factor
                    ),
                    "stops": report.raw_stop_exits,
                    "targets": report.raw_target_exits,
                    "session_exits": report.raw_session_exits,
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
