"""TTrades M1 CISD entry replay for QORE Capitalizer — 1Y research window.

Purpose
-------
Compare the TTrades lower-timeframe CISD entry route with the already-completed
ICT 2022 1Y entry replay while holding higher-level candidates, stop, target and
same-session lifecycle constant.

Frozen comparison window:
    [2025-09-17, 2026-09-17)

Frozen source-candidate boundary:
- same retained Capitalizer higher-level candidate ledger used by the ICT 1Y replay;
- same directional raid-rejection subset:
    LONG  -> LOW_RAID_REJECTION
    SHORT -> HIGH_RAID_REJECTION.

TTrades M1 entry route operationalized from reviewed source material:
- M1 liquidity sweep of a confirmed short-term pivot;
- causal opposing-candle series forms the sweep leg;
- CISD confirms when a candle closes through the opening price of the first candle
  in that opposing series;
- that closure validates the CISD/order-block structure;
- two source-supported entry expressions are predeclared BEFORE outcomes are read:
    CLOSE  -> enter at the CISD confirmation close;
    RETEST -> first causal retest of the validated opposing-candle series after CISD.

The two variants are both reported. The consumed 1Y outcomes do not choose between them.

Isolation controls:
- source stop remains SOURCE_M5_DIRECTIONAL_EXTREME;
- source target remains NEAREST_CAUSAL_TARGET_V2;
- lifecycle remains same session;
- same-minute ambiguity remains STOP_FIRST/fail-closed;
- no FVG requirement;
- no ICT MSS requirement;
- no Stop Intelligence / breathing quantile;
- no future-aware variant selection.

This is consumed historical research, not fresh validation or certification.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
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
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    ICTReplayMetrics,
    WINDOW_END,
    WINDOW_START,
    _aware,
    _is_directional_raid,
    _lifecycle,
    _metrics,
    _operating_date,
    _pivot_indices,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_TTRADES_CISD_M1_ENTRY_1Y_REPLAY_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_TTRADES_CISD_M1_ENTRY_1Y_MATRIX_V1"
COMPARE_IDENTITY = "QORE_CAPITALIZER_ICT_VS_TTRADES_ENTRY_1Y_COMPARISON_V1"
ENTRY_CLOSE = "TTRADES_M1_SWEEP_CISD_ENTRY_ON_CONFIRMATION_CLOSE"
ENTRY_RETEST = "TTRADES_M1_SWEEP_CISD_ENTRY_ON_FIRST_VALIDATED_SERIES_RETEST"
VARIANTS = ("CLOSE", "RETEST")
NEW_YORK = ZoneInfo("America/New_York")
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
class TTradesCISDSetup:
    sweep_index: int
    confirmation_index: int
    swept_level: Decimal
    series_open: Decimal
    order_block_low: Decimal
    order_block_high: Decimal
    series_start_index: int
    series_end_index: int


@dataclass(frozen=True, slots=True)
class TTradesM1Trade:
    symbol: str
    session: str
    side: str
    variant: str
    higher_setup_signal_at: str
    source_event_labels: tuple[str, ...]
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    planned_reward_r: str
    realized_gross_r: str
    exit_reason: str
    m1_bars_held: int
    m1_swept_level: str
    m1_cisd_series_open: str
    m1_order_block_low: str
    m1_order_block_high: str
    m1_sweep_at: str
    m1_cisd_confirmed_at: str
    same_minute_stop_target_ambiguity: bool
    entry_definition: str
    liquidity_sweep_required: bool = True
    cisd_required: bool = True
    opposing_candle_series_required: bool = True
    fvg_required: bool = False
    ict_mss_required: bool = False
    stop_definition: str = "UNCHANGED_SOURCE_M5_DIRECTIONAL_EXTREME"
    target_definition: str = "UNCHANGED_NEAREST_CAUSAL_TARGET_V2"
    outcome_used_for_selection: bool = False


@dataclass(frozen=True, slots=True)
class TTradesVariantReport:
    variant: str
    entry_definition: str
    entries: int
    entry_rate_vs_raid_candidates: str
    metrics: ICTReplayMetrics | None
    sessions_with_entry: int
    sessions_over_max3: int
    max_entries_one_session: int


@dataclass(frozen=True, slots=True)
class TTradesMarketReport:
    identity: str
    symbol: str
    session: str
    window_start: str
    window_end_exclusive: str
    source_candidates_in_window: int
    directional_raid_candidates: int
    non_raid_candidates_rejected: int
    close: TTradesVariantReport
    retest: TTradesVariantReport
    close_rejection_reasons: tuple[tuple[str, int], ...]
    retest_rejection_reasons: tuple[tuple[str, int], ...]
    variants_predeclared: bool = True
    outcome_selects_variant: bool = False
    higher_level_setup_changed: bool = False
    stop_changed: bool = False
    target_changed: bool = False
    lifecycle_changed: bool = False
    fvg_required: bool = False
    ict_mss_required: bool = False
    synthetic_m1_used: bool = False
    interpolated_m1_used: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _load_candidates(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"TTrades replay requires one source candidate ledger, got {len(paths)}")
    result: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("source candidate must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("TTrades replay rejects outcome-selected source candidates")
            signal = _aware(str(raw["signal_at"]))
            if WINDOW_START <= signal < WINDOW_END:
                result.append(raw)
    if not result:
        raise ValueError("TTrades 1Y source window is empty")
    return tuple(result)


def _opposing_series_ending_at(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    end_index: int,
    side: CapitalizerSide,
) -> tuple[int, ...]:
    """Return the causal opposing-candle series ending at end_index.

    Bullish CISD uses down-close candles. Bearish CISD uses up-close candles.
    """

    selected: list[int] = []
    index = end_index
    while index >= 0:
        bar = bars[index]
        opposing = (
            bar.close < bar.open
            if side is CapitalizerSide.LONG
            else bar.close > bar.open
        )
        if not opposing:
            break
        selected.append(index)
        index -= 1
    selected.reverse()
    return tuple(selected)


def _latest_pivot_before(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> int | None:
    pivots = _pivot_indices(
        bars,
        before_index=index - 1,
        high=side is CapitalizerSide.SHORT,
    )
    return None if not pivots else pivots[-1]


def _detect_cisd_after_signal(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    signal_at: datetime,
    side: CapitalizerSide,
    target: Decimal,
) -> tuple[TTradesCISDSetup, str] | tuple[None, str]:
    start_index = next(
        (index for index, bar in enumerate(bars) if bar.opened_at >= signal_at),
        None,
    )
    if start_index is None:
        return None, "NO_M1_AFTER_HIGHER_SIGNAL"

    saw_sweep = False
    saw_series = False
    for sweep_index in range(max(2, start_index), len(bars) - 1):
        pivot_index = _latest_pivot_before(
            bars,
            index=sweep_index,
            side=side,
        )
        if pivot_index is None:
            continue
        pivot = bars[pivot_index]
        sweep_bar = bars[sweep_index]
        swept_level = pivot.low if side is CapitalizerSide.LONG else pivot.high
        swept = (
            sweep_bar.low < swept_level
            if side is CapitalizerSide.LONG
            else sweep_bar.high > swept_level
        )
        if not swept:
            continue
        saw_sweep = True

        # The opposing series must include the candle that actually delivers into
        # the swept extreme or end immediately before the confirmation candle.
        series_indices = _opposing_series_ending_at(
            bars,
            end_index=sweep_index,
            side=side,
        )
        if not series_indices:
            # A sweep may finish on a neutral/same-direction candle. In that case
            # search forward only while the post-sweep opposing series is causal.
            probe = sweep_index + 1
            while probe < len(bars):
                bar = bars[probe]
                opposing = (
                    bar.close < bar.open
                    if side is CapitalizerSide.LONG
                    else bar.close > bar.open
                )
                if opposing:
                    series_indices = _opposing_series_ending_at(
                        bars,
                        end_index=probe,
                        side=side,
                    )
                    break
                probe += 1
        if not series_indices:
            continue
        saw_series = True
        series = tuple(bars[index] for index in series_indices)
        series_open = series[0].open
        ob_low = min(bar.low for bar in series)
        ob_high = max(bar.high for bar in series)

        confirmation_start = series_indices[-1] + 1
        for confirmation_index in range(confirmation_start, len(bars)):
            confirmation = bars[confirmation_index]
            if side is CapitalizerSide.LONG:
                if confirmation.close <= series_open:
                    continue
            else:
                if confirmation.close >= series_open:
                    continue

            # The original higher-level target cannot already be consumed before entry.
            for prior in bars[start_index : confirmation_index + 1]:
                if side is CapitalizerSide.LONG and prior.high >= target:
                    return None, "TARGET_CONSUMED_BEFORE_TTRADES_CISD"
                if side is CapitalizerSide.SHORT and prior.low <= target:
                    return None, "TARGET_CONSUMED_BEFORE_TTRADES_CISD"

            return (
                TTradesCISDSetup(
                    sweep_index=sweep_index,
                    confirmation_index=confirmation_index,
                    swept_level=swept_level,
                    series_open=series_open,
                    order_block_low=ob_low,
                    order_block_high=ob_high,
                    series_start_index=series_indices[0],
                    series_end_index=series_indices[-1],
                ),
                "TTRADES_CISD_CONFIRMED",
            )

    if not saw_sweep:
        return None, "M1_LIQUIDITY_SWEEP_NOT_CONFIRMED"
    if not saw_series:
        return None, "M1_OPPOSING_CANDLE_SERIES_NOT_CONFIRMED"
    return None, "M1_CISD_CLOSE_NOT_CONFIRMED"


def _retest_fill(
    bar: CapitalizerM1Bar,
    *,
    setup: TTradesCISDSetup,
    side: CapitalizerSide,
) -> Decimal | None:
    low = setup.order_block_low
    high = setup.order_block_high
    if bar.high < low or bar.low > high:
        return None
    if low <= bar.open <= high:
        return bar.open
    if side is CapitalizerSide.LONG:
        if bar.open > high and bar.low <= high:
            return high
        return None
    if bar.open < low and bar.high >= low:
        return low
    return None


def _target_touched(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    start_index: int,
    end_index: int,
    side: CapitalizerSide,
    target: Decimal,
) -> bool:
    for bar in bars[start_index:end_index]:
        if side is CapitalizerSide.LONG and bar.high >= target:
            return True
        if side is CapitalizerSide.SHORT and bar.low <= target:
            return True
    return False


def _entry_for_variant(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    setup: TTradesCISDSetup,
    side: CapitalizerSide,
    stop: Decimal,
    target: Decimal,
    variant: str,
) -> tuple[int, Decimal, str] | tuple[None, None, str]:
    if variant == "CLOSE":
        index = setup.confirmation_index
        price = bars[index].close
        valid = stop < price < target if side is CapitalizerSide.LONG else target < price < stop
        if not valid:
            return None, None, "TTRADES_CLOSE_ENTRY_GEOMETRY_INVALID"
        return index, price, "TTRADES_CLOSE_ENTRY_CONFIRMED"

    if variant != "RETEST":
        raise ValueError(f"unsupported TTrades variant: {variant}")

    start = setup.confirmation_index + 1
    for index in range(start, len(bars)):
        if _target_touched(
            bars,
            start_index=start,
            end_index=index,
            side=side,
            target=target,
        ):
            return None, None, "TARGET_CONSUMED_BEFORE_TTRADES_RETEST"
        fill = _retest_fill(
            bars[index],
            setup=setup,
            side=side,
        )
        if fill is None:
            continue
        valid = stop < fill < target if side is CapitalizerSide.LONG else target < fill < stop
        if not valid:
            return None, None, "TTRADES_RETEST_ENTRY_GEOMETRY_INVALID"
        return index, fill, "TTRADES_RETEST_ENTRY_CONFIRMED"
    return None, None, "TTRADES_VALIDATED_SERIES_RETEST_NOT_OBSERVED"


def _process_candidate(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    row: dict[str, Any],
    session: CapitalizerSession,
    variant: str,
) -> tuple[TTradesM1Trade, str] | tuple[None, str]:
    side = CapitalizerSide(str(row["side"]))
    signal_at = _aware(str(row["signal_at"]))
    target = Decimal(str(row["target_price"]))
    stop = Decimal(str(row["stop_price"]))
    setup, reason = _detect_cisd_after_signal(
        bars,
        signal_at=signal_at,
        side=side,
        target=target,
    )
    if setup is None:
        return None, reason

    entry_index, entry_price, reason = _entry_for_variant(
        bars,
        setup=setup,
        side=side,
        stop=stop,
        target=target,
        variant=variant,
    )
    if entry_index is None or entry_price is None:
        return None, reason

    realized, exit_reason, held, ambiguous, exit_at = _lifecycle(
        bars,
        entry_index=entry_index,
        side=side,
        entry_price=entry_price,
        stop_price=stop,
        target_price=target,
    )
    risk = abs(entry_price - stop)
    labels = row.get("event_labels")
    if not isinstance(labels, list):
        raise ValueError("event_labels must be list")
    return (
        TTradesM1Trade(
            symbol=str(row["symbol"]),
            session=session.value,
            side=side.value,
            variant=variant,
            higher_setup_signal_at=signal_at.isoformat(),
            source_event_labels=tuple(sorted(str(item) for item in labels)),
            entry_at=bars[entry_index].opened_at.isoformat(),
            exit_at=exit_at.isoformat(),
            entry_price=str(entry_price),
            stop_price=str(stop),
            target_price=str(target),
            planned_reward_r=str(abs(target - entry_price) / risk),
            realized_gross_r=str(realized),
            exit_reason=exit_reason,
            m1_bars_held=held,
            m1_swept_level=str(setup.swept_level),
            m1_cisd_series_open=str(setup.series_open),
            m1_order_block_low=str(setup.order_block_low),
            m1_order_block_high=str(setup.order_block_high),
            m1_sweep_at=bars[setup.sweep_index].closed_at.isoformat(),
            m1_cisd_confirmed_at=bars[setup.confirmation_index].closed_at.isoformat(),
            same_minute_stop_target_ambiguity=ambiguous,
            entry_definition=ENTRY_CLOSE if variant == "CLOSE" else ENTRY_RETEST,
        ),
        reason,
    )


def _variant_report(
    *,
    variant: str,
    trades: tuple[TTradesM1Trade, ...],
    raid_candidates: int,
    session_counts: Counter[str],
) -> TTradesVariantReport:
    return TTradesVariantReport(
        variant=variant,
        entry_definition=ENTRY_CLOSE if variant == "CLOSE" else ENTRY_RETEST,
        entries=len(trades),
        entry_rate_vs_raid_candidates=str(Decimal(len(trades)) / Decimal(raid_candidates)),
        metrics=_metrics(
            tuple(
                # _metrics consumes the structurally compatible fields on these dataclasses.
                trade  # type: ignore[arg-type]
                for trade in trades
            )
        ),
        sessions_with_entry=sum(count > 0 for count in session_counts.values()),
        sessions_over_max3=sum(count > MAX_EXECUTIONS_PER_SESSION for count in session_counts.values()),
        max_entries_one_session=max(session_counts.values(), default=0),
    )


def build_market_report(
    candidate_root: Path,
    m1_root: Path,
) -> tuple[TTradesMarketReport, dict[str, tuple[TTradesM1Trade, ...]]]:
    all_candidates = _load_candidates(candidate_root)
    symbols = {str(row["symbol"]) for row in all_candidates}
    sessions = {str(row["session"]) for row in all_candidates}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("TTrades market replay requires one symbol/session")
    symbol = next(iter(symbols))
    session = CapitalizerSession(next(iter(sessions)))
    raid_candidates = tuple(row for row in all_candidates if _is_directional_raid(row))
    if not raid_candidates:
        raise ValueError("TTrades market replay has no directional raid candidates")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raid_candidates:
        grouped[_operating_date(_aware(str(row["signal_at"])), session)].append(row)

    trades_by_variant: dict[str, list[TTradesM1Trade]] = {variant: [] for variant in VARIANTS}
    rejection_by_variant: dict[str, Counter[str]] = {
        variant: Counter() for variant in VARIANTS
    }
    session_counts: dict[str, Counter[str]] = {
        variant: Counter() for variant in VARIANTS
    }
    processed_keys: set[str] = set()
    buffer: list[CapitalizerM1Bar] = []
    active_key: str | None = None

    def flush() -> None:
        nonlocal buffer, active_key
        if active_key is None or not buffer:
            buffer = []
            return
        rows = tuple(grouped.get(active_key, ()))
        if rows:
            bars = tuple(buffer)
            for variant in VARIANTS:
                count = 0
                for row in rows:
                    trade, reason = _process_candidate(
                        bars,
                        row=row,
                        session=session,
                        variant=variant,
                    )
                    if trade is None:
                        rejection_by_variant[variant][reason] += 1
                    else:
                        trades_by_variant[variant].append(trade)
                        count += 1
                session_counts[variant][active_key] = count
            processed_keys.add(active_key)
        buffer = []

    for bar in iter_cibo_m1(m1_root):
        if bar.symbol != symbol:
            raise ValueError("native M1 clone symbol mismatch")
        if not (
            WINDOW_START - timedelta(days=1)
            <= bar.opened_at
            < WINDOW_END + timedelta(days=1)
        ):
            continue
        if capitalizer_session_at(bar.opened_at) is not session:
            if buffer:
                flush()
                active_key = None
            continue
        key = _operating_date(bar.opened_at, session)
        if active_key is None:
            active_key = key
        elif key != active_key:
            flush()
            active_key = key
        buffer.append(bar)
    flush()

    for key in set(grouped) - processed_keys:
        count = len(grouped[key])
        for variant in VARIANTS:
            rejection_by_variant[variant]["M1_SESSION_EVIDENCE_UNAVAILABLE"] += count

    frozen: dict[str, tuple[TTradesM1Trade, ...]] = {}
    for variant in VARIANTS:
        frozen[variant] = tuple(
            sorted(
                trades_by_variant[variant],
                key=lambda item: (_aware(item.entry_at), item.symbol),
            )
        )

    report = TTradesMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        window_start=WINDOW_START.isoformat(),
        window_end_exclusive=WINDOW_END.isoformat(),
        source_candidates_in_window=len(all_candidates),
        directional_raid_candidates=len(raid_candidates),
        non_raid_candidates_rejected=len(all_candidates) - len(raid_candidates),
        close=_variant_report(
            variant="CLOSE",
            trades=frozen["CLOSE"],
            raid_candidates=len(raid_candidates),
            session_counts=session_counts["CLOSE"],
        ),
        retest=_variant_report(
            variant="RETEST",
            trades=frozen["RETEST"],
            raid_candidates=len(raid_candidates),
            session_counts=session_counts["RETEST"],
        ),
        close_rejection_reasons=tuple(
            sorted(rejection_by_variant["CLOSE"].items(), key=lambda item: (-item[1], item[0]))
        ),
        retest_rejection_reasons=tuple(
            sorted(rejection_by_variant["RETEST"].items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    return report, frozen


def write_market(
    report: TTradesMarketReport,
    trades: dict[str, tuple[TTradesM1Trade, ...]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-ttrades-cisd-m1-entry-1y-replay-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for variant in VARIANTS:
        path = output / f"{stem}-{variant.lower()}-trades.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for trade in trades[variant]:
                handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-ttrades-cisd-m1-entry-1y-replay-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"TTrades matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if {str(item["symbol"]) for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("TTrades 1Y universe mismatch")
    return sorted(reports, key=lambda item: str(item["symbol"]))


def _load_variant_trades(root: Path, variant: str) -> tuple[TTradesM1Trade, ...]:
    rows: list[TTradesM1Trade] = []
    pattern = f"capitalizer-*-ttrades-cisd-m1-entry-1y-replay-v1-{variant.lower()}-trades.jsonl"
    for path in sorted(root.rglob(pattern)):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    raw["source_event_labels"] = tuple(raw["source_event_labels"])
                    rows.append(TTradesM1Trade(**raw))
    return tuple(sorted(rows, key=lambda item: (_aware(item.entry_at), item.symbol)))


def _apply_max3(trades: tuple[TTradesM1Trade, ...]) -> tuple[TTradesM1Trade, ...]:
    grouped: dict[str, list[TTradesM1Trade]] = defaultdict(list)
    for trade in trades:
        session = CapitalizerSession(trade.session)
        key = f"{trade.session}:{_operating_date(_aware(trade.entry_at), session)}"
        grouped[key].append(trade)
    selected: list[TTradesM1Trade] = []
    for key in sorted(grouped):
        ordered = sorted(grouped[key], key=lambda item: (_aware(item.entry_at), item.symbol))
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(sorted(selected, key=lambda item: (_aware(item.entry_at), item.symbol)))


def _pooled_variant(reports: list[dict[str, Any]], root: Path, variant: str) -> dict[str, Any]:
    key = variant.lower()
    gp = Decimal("0")
    gl = Decimal("0")
    total = Decimal("0")
    entries = 0
    for report in reports:
        data = report[key]
        entries += int(data["entries"])
        metrics = data.get("metrics")
        if isinstance(metrics, dict):
            gp += Decimal(str(metrics["gross_profit_r"]))
            gl += Decimal(str(metrics["gross_loss_r"]))
            total += Decimal(str(metrics["total_r"]))
    all_trades = _load_variant_trades(root, variant)
    max3 = _apply_max3(all_trades)
    max3_metrics = _metrics(
        tuple(trade for trade in max3)  # type: ignore[arg-type]
    )
    return {
        "variant": variant,
        "entry_definition": ENTRY_CLOSE if variant == "CLOSE" else ENTRY_RETEST,
        "entries": entries,
        "aggregate_profit_factor": None if gl == 0 else str(gp / gl),
        "total_r": str(total),
        "max3_selected_trades": len(max3),
        "max3_metrics": None if max3_metrics is None else asdict(max3_metrics),
    }


def _load_ict_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-nine-market-ict-2022-m1-entry-1y-matrix-v1.json"))
    if len(paths) != 1:
        raise ValueError(f"comparison requires one ICT matrix, got {len(paths)}")
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    if raw.get("identity") != "QORE_CAPITALIZER_NINE_MARKET_ICT_2022_M1_ENTRY_1Y_MATRIX_V1":
        raise ValueError("unexpected ICT comparison identity")
    return raw


def build_matrix(root: Path, ict_root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    close = _pooled_variant(reports, root, "CLOSE")
    retest = _pooled_variant(reports, root, "RETEST")
    ict = _load_ict_matrix(ict_root)
    ict_max3 = ict.get("max3_metrics")
    if not isinstance(ict_max3, dict):
        raise ValueError("ICT matrix missing MAX3 metrics")

    def delta(candidate: dict[str, Any], field: str) -> str:
        cm = candidate.get("max3_metrics")
        if not isinstance(cm, dict):
            raise ValueError("TTrades variant missing MAX3 metrics")
        return str(Decimal(str(cm[field])) - Decimal(str(ict_max3[field])))

    def pf_delta(candidate: dict[str, Any]) -> str | None:
        cm = candidate.get("max3_metrics")
        if not isinstance(cm, dict):
            raise ValueError("TTrades variant missing MAX3 metrics")
        a = cm.get("profit_factor")
        b = ict_max3.get("profit_factor")
        if a is None or b is None:
            return None
        return str(Decimal(str(a)) - Decimal(str(b)))

    comparison = {
        "identity": COMPARE_IDENTITY,
        "ict": {
            "entries": int(ict["ict_m1_entries"]),
            "aggregate_profit_factor": ict["aggregate_profit_factor"],
            "total_r": ict["total_r"],
            "max3_selected_trades": int(ict["max3_selected_trades"]),
            "max3_metrics": ict_max3,
        },
        "ttrades_close_minus_ict_max3": {
            "trade_delta": int(close["max3_selected_trades"]) - int(ict["max3_selected_trades"]),
            "profit_factor_delta": pf_delta(close),
            "total_r_delta": delta(close, "total_r"),
            "max_drawdown_r_delta": delta(close, "max_drawdown_r"),
            "max_losing_streak_delta": (
                int(close["max3_metrics"]["max_losing_streak"])
                - int(ict_max3["max_losing_streak"])
            ),
        },
        "ttrades_retest_minus_ict_max3": {
            "trade_delta": int(retest["max3_selected_trades"]) - int(ict["max3_selected_trades"]),
            "profit_factor_delta": pf_delta(retest),
            "total_r_delta": delta(retest, "total_r"),
            "max_drawdown_r_delta": delta(retest, "max_drawdown_r"),
            "max_losing_streak_delta": (
                int(retest["max3_metrics"]["max_losing_streak"])
                - int(ict_max3["max_losing_streak"])
            ),
        },
        "outcome_selects_ttrades_variant": False,
    }
    return {
        "identity": MATRIX_IDENTITY,
        "window_start": WINDOW_START.isoformat(),
        "window_end_exclusive": WINDOW_END.isoformat(),
        "market_count": 9,
        "source_candidates_in_window": sum(int(r["source_candidates_in_window"]) for r in reports),
        "directional_raid_candidates": sum(int(r["directional_raid_candidates"]) for r in reports),
        "variants_predeclared": list(VARIANTS),
        "close": close,
        "retest": retest,
        "markets": reports,
        "comparison_to_ict": comparison,
        "higher_level_setup_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "lifecycle_changed": False,
        "fvg_required": False,
        "ict_mss_required": False,
        "outcome_selects_variant": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-ttrades-cisd-m1-entry-1y-matrix-v1.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("candidate_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("ict_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, trades = build_market_report(args.candidate_root, args.m1_root)
        write_market(report, trades, args.output)
        print(
            json.dumps(
                {
                    "symbol": report.symbol,
                    "close_entries": report.close.entries,
                    "close_pf": (
                        None if report.close.metrics is None else report.close.metrics.profit_factor
                    ),
                    "retest_entries": report.retest.entries,
                    "retest_pf": (
                        None if report.retest.metrics is None else report.retest.metrics.profit_factor
                    ),
                },
                sort_keys=True,
            )
        )
        return

    matrix_report = build_matrix(args.input_root, args.ict_root)
    write_matrix(matrix_report, args.output)
    print(json.dumps(matrix_report, sort_keys=True))


if __name__ == "__main__":
    main()
