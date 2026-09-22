"""Clean A/B Fibonacci entry variant of Capitalizer V3.

Everything upstream/downstream is imported from frozen V3:
H1 liquidity/sweep, M5 close-back, M3 MSS+CISD+body+ATR,
M3-swing stop + 5-pip buffer, fixed 2R / next-H1-open lifecycle,
same sessions and MAX3. Only the M1 entry trigger changes:
V3 causal OB+FVG retest/CE -> causal OB + OTE 0.62-0.79
with two-candle absorption and close-through-0.79 invalidation.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
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
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    WINDOW_END,
    WINDOW_START,
    ICTReplayMetrics,
    _aware,
)
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 import (
    ATR_MULTIPLIER,
    BODY_RATIO_MIN,
    BUFFER_PIPS,
    H1Swing,
    M3MssEvent,
    SweepCloseback,
    _build_h1_swings,
    _find_m3_mss,
    _find_sweep_closeback,
    _h1_windows,
    _lifecycle,
    _liquidity_levels,
    _previous_day_range,
    _stop_buffer,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    ReferenceLiquidity,
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_V3_FIBONACCI_AB_1Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_FIBONACCI_AB_1Y_V1"
ENTRY_IDENTITY = (
    "V3_IDENTICAL_UPSTREAM__M1_CAUSAL_OB__"
    "BODY_FIB_OTE_062_079__TWO_CANDLE_ABSORPTION"
)
STOP_IDENTITY = "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
TARGET_IDENTITY = "FIXED_2R_OR_NEXT_H1_OPEN"
LOOKBACK_START = WINDOW_START - timedelta(days=21)
FIB_062 = Decimal("0.62")
FIB_0705 = Decimal("0.705")
FIB_079 = Decimal("0.79")
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
class CausalOB:
    index: int
    opened_at: datetime
    low: Decimal
    high: Decimal


@dataclass(frozen=True, slots=True)
class OTEZone:
    impulse_start: Decimal
    impulse_end: Decimal
    level_062: Decimal
    level_0705: Decimal
    level_079: Decimal
    zone_low: Decimal
    zone_high: Decimal


@dataclass(frozen=True, slots=True)
class OTEReaction:
    index: int
    confirmed_at: datetime
    entry_price: Decimal
    bucket: str
    retracement: Decimal


@dataclass(frozen=True, slots=True)
class FibTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    liquidity_source: str
    liquidity_kind: str
    liquidity_price: str
    h1_sweep_at: str
    h1_sweep_extreme: str
    m5_closeback_at: str
    m3_mss_at: str
    m3_broken_swing_price: str
    m3_cisd_boundary: str
    m3_body_ratio: str
    m3_atr14: str
    m3_displacement_range: str
    m1_ob_opened_at: str
    m1_ob_low: str
    m1_ob_high: str
    fib_062: str
    fib_0705: str
    fib_079: str
    absorption_bucket: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    stop_buffer_price: str
    target_price: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    same_minute_stop_target_ambiguity: bool
    entry_definition: str = ENTRY_IDENTITY
    stop_definition: str = STOP_IDENTITY
    target_definition: str = TARGET_IDENTITY
    upstream_contract: str = "BYTE_EQUIVALENT_V3_HELPERS"
    fvg_entry_required: bool = False
    ote_entry_required: bool = True
    m3_cisd_required: bool = True
    m3_body_ratio_min: str = "0.60"
    m3_atr_multiplier: str = "1.2"
    max3_is_ceiling_not_quota: bool = True
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class FibMarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    operating_sessions_scanned: int
    h1_hours_scanned: int
    h1_hours_with_liquidity: int
    h1_sweeps_detected: int
    m5_closebacks_confirmed: int
    m3_mss_confirmed: int
    m1_ob_identified: int
    ote_zone_interactions: int
    absorptions_confirmed: int
    invalidated_close_through_79: int
    entries_executed: int
    raw_metrics: ICTReplayMetrics | None
    stage_counts: tuple[tuple[str, int], ...]
    architecture_predeclared: bool = True
    methodology_research_only: bool = True
    v3_upstream_unchanged: bool = True
    v3_stop_unchanged: bool = True
    v3_target_unchanged: bool = True
    entry_change_only: str = "FVG_RETEST_OR_CE_TO_OTE_ABSORPTION"
    m3_cisd_required: bool = True
    m3_body_ratio_min: str = "0.60"
    m3_atr_multiplier: str = "1.2"
    stop_buffer_pips: str = "5"
    max3_is_ceiling_not_quota: bool = True
    fresh_holdout_claimed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _metrics(trades: tuple[FibTrade, ...]) -> ICTReplayMetrics | None:
    if not trades:
        return None
    ordered = tuple(sorted(trades, key=lambda item: _aware(item.entry_at)))
    values = tuple(Decimal(item.realized_gross_r) for item in ordered)
    gp = sum((x for x in values if x > 0), Decimal("0"))
    gl = -sum((x for x in values if x < 0), Decimal("0"))
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
        wins=sum(x > 0 for x in values),
        losses=sum(x < 0 for x in values),
        flats=sum(x == 0 for x in values),
        total_r=str(total),
        mean_r=str(total / Decimal(len(values))),
        gross_profit_r=str(gp),
        gross_loss_r=str(gl),
        profit_factor=None if gl == 0 else str(gp / gl),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(x.exit_reason == "STOP" for x in ordered),
        target_exits=sum(x.exit_reason == "TARGET" for x in ordered),
        session_exits=sum(x.exit_reason == "SESSION_EXIT" for x in ordered),
        ambiguous_stop_first_exits=sum(
            x.same_minute_stop_target_ambiguity for x in ordered
        ),
    )


def _causal_ob(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: M3MssEvent,
) -> CausalOB | None:
    displacement_indices = [
        index
        for index, bar in enumerate(execution)
        if event.displacement_opened_at
        <= bar.opened_at
        < event.displacement_closed_at
    ]
    if not displacement_indices:
        return None
    first_index = displacement_indices[0]
    for index in range(first_index - 1, -1, -1):
        bar = execution[index]
        opposing = (
            bar.close < bar.open
            if event.side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            return CausalOB(index, bar.opened_at, bar.low, bar.high)
    return None


def _bar_at(
    execution: tuple[CapitalizerM1Bar, ...],
    opened_at: datetime,
) -> CapitalizerM1Bar | None:
    for bar in execution:
        if bar.opened_at == opened_at:
            return bar
    return None


def _ote_zone(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    closeback: SweepCloseback,
    event: M3MssEvent,
) -> OTEZone | None:
    sweep_bar = _bar_at(execution, closeback.sweep_at)
    displacement = tuple(
        bar
        for bar in execution
        if event.displacement_opened_at
        <= bar.opened_at
        < event.displacement_closed_at
    )
    if sweep_bar is None or not displacement:
        return None
    if event.side is CapitalizerSide.LONG:
        start = min(sweep_bar.open, sweep_bar.close)
        end = max(max(x.open, x.close) for x in displacement)
        if end <= start:
            return None
        span = end - start
        l62 = end - FIB_062 * span
        l705 = end - FIB_0705 * span
        l79 = end - FIB_079 * span
        low, high = l79, l62
    else:
        start = max(sweep_bar.open, sweep_bar.close)
        end = min(min(x.open, x.close) for x in displacement)
        if end >= start:
            return None
        span = start - end
        l62 = end + FIB_062 * span
        l705 = end + FIB_0705 * span
        l79 = end + FIB_079 * span
        low, high = l62, l79
    return OTEZone(start, end, l62, l705, l79, low, high)


def _absorption_depth(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    zone: OTEZone,
) -> Decimal:
    span = abs(zone.impulse_end - zone.impulse_start)
    raw = (
        (zone.impulse_end - bar.low) / span
        if side is CapitalizerSide.LONG
        else (bar.high - zone.impulse_end) / span
    )
    return min(FIB_079, max(FIB_062, raw))


def _find_ote_fill(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: M3MssEvent,
    zone: OTEZone,
    deadline: datetime,
) -> tuple[str, OTEReaction | None]:
    candidate: int | None = None
    interacted = False
    for index, bar in enumerate(execution):
        if bar.opened_at < event.confirmed_at:
            continue
        if bar.opened_at >= deadline:
            break
        if bar.low <= zone.zone_high and bar.high >= zone.zone_low:
            interacted = True

        adverse_close = (
            bar.close < zone.level_079
            if event.side is CapitalizerSide.LONG
            else bar.close > zone.level_079
        )
        if adverse_close:
            return "INVALIDATED_079", None

        if candidate is not None:
            first = execution[candidate]
            valid_second = (
                bar.close > bar.open and bar.close > first.close
                if event.side is CapitalizerSide.LONG
                else bar.close < bar.open and bar.close < first.close
            )
            if index == candidate + 1 and valid_second:
                depth = _absorption_depth(
                    first,
                    side=event.side,
                    zone=zone,
                )
                bucket = (
                    "0.62_TO_0.705"
                    if depth <= FIB_0705
                    else "0.705_TO_0.79"
                )
                return "ABSORPTION", OTEReaction(
                    index=index,
                    confirmed_at=bar.closed_at,
                    entry_price=bar.close,
                    bucket=bucket,
                    retracement=depth,
                )
            candidate = None

        touches = bar.low <= zone.zone_high and bar.high >= zone.zone_low
        if not touches:
            continue
        valid_first = (
            bar.close < bar.open and bar.close >= zone.level_079
            if event.side is CapitalizerSide.LONG
            else bar.close > bar.open and bar.close <= zone.level_079
        )
        if valid_first:
            candidate = index

    return ("INTERACTED_NO_FILL" if interacted else "NO_OTE_INTERACTION"), None


def _scan_day(
    *,
    symbol: str,
    session: CapitalizerSession,
    operating_day: date,
    prior_session: ReferenceLiquidity | None,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: tuple[H1Swing, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Any, ...],
    buffer_price: Decimal,
    stages: Counter[str],
) -> tuple[FibTrade, ...]:
    if len(execution) < 15:
        return ()
    previous_day = _previous_day_range(
        all_bars, operating_day=operating_day
    )
    results: list[FibTrade] = []
    for h1_open, h1_deadline, hour_bars in _h1_windows(execution):
        if len(results) >= MAX_EXECUTIONS_PER_SESSION:
            break
        stages["H1_HOUR_SCANNED"] += 1
        levels = _liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            continue
        stages["H1_HOUR_WITH_LIQUIDITY"] += 1
        sweep_seen, closeback = _find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=h1_deadline,
        )
        if sweep_seen:
            stages["H1_SWEEP_DETECTED"] += 1
        if closeback is None:
            continue
        stages["M5_CLOSEBACK_CONFIRMED"] += 1
        mss = _find_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            after=closeback.closeback_at,
            before=h1_deadline,
            side=closeback.side,
        )
        if mss is None:
            continue
        stages["M3_MSS_CONFIRMED"] += 1
        ob = _causal_ob(execution, event=mss)
        if ob is None:
            continue
        stages["M1_OB_IDENTIFIED"] += 1
        zone = _ote_zone(execution, closeback=closeback, event=mss)
        if zone is None:
            continue
        status, reaction = _find_ote_fill(
            execution,
            event=mss,
            zone=zone,
            deadline=h1_deadline,
        )
        if status != "NO_OTE_INTERACTION":
            stages["OTE_ZONE_INTERACTION"] += 1
        if status == "INVALIDATED_079":
            stages["OTE_INVALIDATED_079"] += 1
            continue
        if reaction is None:
            continue
        stages["OTE_ABSORPTION"] += 1
        stages[f"OTE_{reaction.bucket}"] += 1

        entry_index = reaction.index
        entry_price = reaction.entry_price
        stop_price = (
            mss.broken_swing_price - buffer_price
            if closeback.side is CapitalizerSide.LONG
            else mss.broken_swing_price + buffer_price
        )
        valid_stop = (
            stop_price < entry_price
            if closeback.side is CapitalizerSide.LONG
            else stop_price > entry_price
        )
        if not valid_stop:
            continue
        risk = abs(entry_price - stop_price)
        target_price = (
            entry_price + Decimal("2") * risk
            if closeback.side is CapitalizerSide.LONG
            else entry_price - Decimal("2") * risk
        )
        realized, reason, held, ambiguous, exit_at = _lifecycle(
            execution,
            entry_index=entry_index,
            side=closeback.side,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=h1_deadline,
        )
        stages["ENTRY_EXECUTED"] += 1
        results.append(
            FibTrade(
                symbol=symbol,
                session=session.value,
                operating_date=operating_day.isoformat(),
                side=closeback.side.value,
                h1_open=h1_open.isoformat(),
                h1_deadline=h1_deadline.isoformat(),
                liquidity_source=closeback.reference.source,
                liquidity_kind=closeback.reference.kind,
                liquidity_price=str(closeback.reference.price),
                h1_sweep_at=closeback.sweep_at.isoformat(),
                h1_sweep_extreme=str(closeback.sweep_extreme),
                m5_closeback_at=closeback.closeback_at.isoformat(),
                m3_mss_at=mss.confirmed_at.isoformat(),
                m3_broken_swing_price=str(mss.broken_swing_price),
                m3_cisd_boundary=str(mss.cisd_boundary),
                m3_body_ratio=str(mss.body_ratio),
                m3_atr14=str(mss.atr14),
                m3_displacement_range=str(mss.displacement_range),
                m1_ob_opened_at=ob.opened_at.isoformat(),
                m1_ob_low=str(ob.low),
                m1_ob_high=str(ob.high),
                fib_062=str(zone.level_062),
                fib_0705=str(zone.level_0705),
                fib_079=str(zone.level_079),
                absorption_bucket=reaction.bucket,
                entry_at=execution[entry_index].opened_at.isoformat(),
                exit_at=exit_at.isoformat(),
                entry_price=str(entry_price),
                stop_price=str(stop_price),
                stop_buffer_price=str(buffer_price),
                target_price=str(target_price),
                realized_gross_r=str(realized),
                exit_reason=reason,
                m1_bars_held=held,
                same_minute_stop_target_ambiguity=ambiguous,
            )
        )
    return tuple(results)


def build_market_report(
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[FibMarketReport, tuple[FibTrade, ...]]:
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("V3 Fibonacci A/B found no native M1")
    symbol = all_bars[0].symbol
    h1 = _aggregate_h1(all_bars)
    h1_swings = _build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_pivots = _pivots(m3)
    m5_closes = tuple(x.closed_at for x in m5)
    m3_closes = tuple(x.closed_at for x in m3)
    buffer_price = _stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars, session=session
    )
    grouped_dates = sorted(
        key
        for key in execution_by_day
        if WINDOW_START.date().isoformat()
        <= key
        < WINDOW_END.date().isoformat()
    )
    stages: Counter[str] = Counter()
    trades: list[FibTrade] = []
    for value in grouped_dates:
        day = date.fromisoformat(value)
        trades.extend(
            _scan_day(
                symbol=symbol,
                session=session,
                operating_day=day,
                prior_session=reference_by_day.get(value),
                execution=execution_by_day.get(value, ()),
                all_bars=all_bars,
                h1_swings=h1_swings,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
                stages=stages,
            )
        )
    ordered = tuple(sorted(trades, key=lambda x: _aware(x.entry_at)))
    return (
        FibMarketReport(
            identity=IDENTITY,
            symbol=symbol,
            session=session.value,
            window_start=WINDOW_START.isoformat(),
            window_end_exclusive=WINDOW_END.isoformat(),
            operating_sessions_scanned=len(grouped_dates),
            h1_hours_scanned=stages["H1_HOUR_SCANNED"],
            h1_hours_with_liquidity=stages["H1_HOUR_WITH_LIQUIDITY"],
            h1_sweeps_detected=stages["H1_SWEEP_DETECTED"],
            m5_closebacks_confirmed=stages["M5_CLOSEBACK_CONFIRMED"],
            m3_mss_confirmed=stages["M3_MSS_CONFIRMED"],
            m1_ob_identified=stages["M1_OB_IDENTIFIED"],
            ote_zone_interactions=stages["OTE_ZONE_INTERACTION"],
            absorptions_confirmed=stages["OTE_ABSORPTION"],
            invalidated_close_through_79=stages["OTE_INVALIDATED_079"],
            entries_executed=len(ordered),
            raw_metrics=_metrics(ordered),
            stage_counts=tuple(
                sorted(stages.items(), key=lambda x: (-x[1], x[0]))
            ),
        ),
        ordered,
    )


def write_market(
    report: FibMarketReport,
    trades: tuple[FibTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-v3-fibonacci-ab-1y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as h:
        for trade in trades:
            h.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-fibonacci-ab-1y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"V3 Fibonacci matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text()) for path in paths]
    if {str(x["symbol"]) for x in reports} != EXPECTED_SYMBOLS:
        raise ValueError("V3 Fibonacci universe mismatch")
    return reports


def _load_trades(root: Path) -> tuple[FibTrade, ...]:
    rows: list[FibTrade] = []
    for path in root.rglob("capitalizer-*-v3-fibonacci-ab-1y-v1-trades.jsonl"):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(FibTrade(**json.loads(line)))
    return tuple(sorted(rows, key=lambda x: (_aware(x.entry_at), x.symbol)))


def _portfolio_max3(trades: tuple[FibTrade, ...]) -> tuple[FibTrade, ...]:
    grouped: dict[str, list[FibTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[FibTrade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key], key=lambda x: (_aware(x.entry_at), x.symbol)
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda x: (_aware(x.entry_at), x.symbol)))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = _load_trades(root)
    max3 = _portfolio_max3(raw)
    per_session: dict[str, Any] = {}
    for session in CapitalizerSession:
        items = tuple(x for x in max3 if x.session == session.value)
        m = _metrics(items)
        per_session[session.value] = {
            "trades": len(items),
            "metrics": None if m is None else asdict(m),
        }
    return {
        "identity": MATRIX_IDENTITY,
        "architecture": "V3_EXACT_EXCEPT_M1_FVG_TO_FIBONACCI_OTE",
        "market_count": 9,
        "m3_mss_confirmed": sum(int(x["m3_mss_confirmed"]) for x in reports),
        "raw_trades": len(raw),
        "raw_metrics": None if _metrics(raw) is None else asdict(_metrics(raw)),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if _metrics(max3) is None else asdict(_metrics(max3)),
        "per_session": per_session,
        "entries_062_0705": sum(
            x.absorption_bucket == "0.62_TO_0.705" for x in max3
        ),
        "entries_0705_079": sum(
            x.absorption_bucket == "0.705_TO_0.79" for x in max3
        ),
        "v3_upstream_unchanged": True,
        "v3_stop_unchanged": True,
        "v3_target_unchanged": True,
        "entry_change_only": "FVG_RETEST_OR_CE_TO_OTE_ABSORPTION",
        "stop_identity": STOP_IDENTITY,
        "target_identity": TARGET_IDENTITY,
        "methodology_research_only": True,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-v3-fibonacci-ab-1y-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--session", required=True, choices=[x.value for x in CapitalizerSession])
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, trades = build_market_report(
            args.m1_root, session=CapitalizerSession(args.session)
        )
        write_market(report, trades, args.output)
        print(json.dumps(asdict(report), sort_keys=True))
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
