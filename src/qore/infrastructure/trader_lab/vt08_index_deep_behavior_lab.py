"""Deep diagnostic laboratory for VT-08 Index.

This module is deliberately research-only. It never changes V7 admission,
execution, stop, target or governance. It instruments frozen V7 on consumed
evidence and produces a causal/behavioral feature ledger, opportunity funnel,
excursion analysis, target surface, drawdown anatomy and cross-index context.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _in_partition,
    _intrabar_exit,
    _load_candidate_market,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar
from qore.kernel.errors import InfrastructureError

SCHEMA = "qore.trader_lab.vt08_index_deep_behavior_lab.v1"
COMBINED_SCHEMA = "qore.trader_lab.vt08_index_deep_behavior_lab.combined.v1"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
TARGET_SURFACE_R = (
    Decimal("0.5"),
    Decimal("1.0"),
    Decimal("1.5"),
    Decimal("2.0"),
    Decimal("2.5"),
    Decimal("3.0"),
)
_NY = ZoneInfo("America/New_York")


class Vt08IndexDeepBehaviorError(InfrastructureError):
    __slots__ = ()


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _aligned(side: DemoTradingSetupSide, opened: Decimal, closed: Decimal) -> str:
    if closed == opened:
        return "flat"
    bullish = closed > opened
    if side is DemoTradingSetupSide.LONG:
        return "aligned" if bullish else "opposed"
    return "aligned" if not bullish else "opposed"


def _timing_bucket(minutes: int) -> str:
    if minutes <= 60:
        return "q1_0_60"
    if minutes <= 120:
        return "q2_61_120"
    if minutes <= 180:
        return "q3_121_180"
    return "q4_181_240"


def _range_regime(ratio: Decimal | None) -> str:
    if ratio is None:
        return "unknown"
    if ratio < Decimal("0.75"):
        return "compressed"
    if ratio > Decimal("1.25"):
        return "expanded"
    return "normal"


def _excursion_bucket(mfe_r: Decimal) -> str:
    if mfe_r < Decimal("0.5"):
        return "lt_0_5r"
    if mfe_r < Decimal("1"):
        return "0_5_to_1r"
    if mfe_r < Decimal("1.5"):
        return "1_to_1_5r"
    if mfe_r < Decimal("2"):
        return "1_5_to_2r"
    return "ge_2r_same_bar_or_gap"


def _duration_bucket(minutes: int) -> str:
    if minutes <= 120:
        return "le_2h"
    if minutes <= 240:
        return "2_to_4h"
    if minutes <= 480:
        return "4_to_8h"
    if minutes <= 1440:
        return "8_to_24h"
    return "gt_24h"


def _row_metrics(
    rows: Sequence[dict[str, object]], *, key: str = "primary_r"
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    values = tuple(_decimal(row[key]) for row in ordered)
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    max_dd = Decimal()
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
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": _fmt(total),
        "mean_r": _fmt(total / len(values)) if values else "0",
        "profit_factor": _fmt(gains / losses) if losses else None,
        "max_drawdown_r": _fmt(max_dd),
        "max_losing_streak": max_streak,
    }


def _cohort_cube(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    dimensions: dict[str, tuple[str, ...]] = {
        "symbol": ("symbol",),
        "side": ("side",),
        "anchor": ("anchor_hour_new_york",),
        "model": ("model_kind",),
        "poi": ("poi_kind",),
        "year": ("year",),
        "quarter": ("year_quarter",),
        "entry_timing": ("entry_timing_bucket",),
        "prior_h4_range_regime": ("prior_h4_range_regime",),
        "peer_alignment": ("peer_alignment_count",),
        "relative_strength_rank": ("side_adjusted_relative_strength_rank",),
        "current_source_body": ("current_source_body_alignment",),
        "previous_source_body": ("previous_source_body_alignment",),
        "symbol_anchor": ("symbol", "anchor_hour_new_york"),
        "symbol_model": ("symbol", "model_kind"),
        "symbol_side": ("symbol", "side"),
        "anchor_model": ("anchor_hour_new_york", "model_kind"),
        "symbol_range_regime": ("symbol", "prior_h4_range_regime"),
    }
    result: dict[str, object] = {}
    for name, keys in dimensions.items():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            label = "|".join(str(row.get(key, "unknown")) for key in keys)
            grouped[label].append(row)
        result[name] = {
            label: _row_metrics(items)
            for label, items in sorted(grouped.items())
        }
    return result


def _summarize_mix(
    rows: Sequence[dict[str, object]], key: str
) -> dict[str, object]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: Counter[str] = Counter()
    for row in rows:
        label = str(row.get(key, "unknown"))
        counts[label] += 1
        totals[label] += _decimal(row["primary_r"])
    return {
        label: {"sample": counts[label], "total_r": _fmt(totals[label])}
        for label in sorted(counts)
    }


def _drawdown_episodes(
    rows: Sequence[dict[str, object]], limit: int = 10
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    equity = Decimal()
    peak_equity = Decimal()
    peak_index = -1
    active_start: int | None = None
    trough_index: int | None = None
    max_depth = Decimal()
    episodes: list[dict[str, object]] = []

    def close_episode(end_index: int, recovered: bool) -> None:
        nonlocal active_start, trough_index, max_depth
        if active_start is None or trough_index is None:
            return
        subset = ordered[active_start : end_index + 1]
        episodes.append(
            {
                "started_at": subset[0]["signal_at"],
                "trough_at": ordered[trough_index]["signal_at"],
                "ended_at": ordered[end_index]["signal_at"],
                "recovered": recovered,
                "depth_r": _fmt(max_depth),
                "trade_count": len(subset),
                "symbol_mix": _summarize_mix(subset, "symbol"),
                "anchor_mix": _summarize_mix(subset, "anchor_hour_new_york"),
                "model_mix": _summarize_mix(subset, "model_kind"),
                "side_mix": _summarize_mix(subset, "side"),
            }
        )
        active_start = None
        trough_index = None
        max_depth = Decimal()

    for index, row in enumerate(ordered):
        equity += _decimal(row["primary_r"])
        if equity >= peak_equity:
            if active_start is not None:
                close_episode(index, True)
            peak_equity = equity
            peak_index = index
            continue
        if active_start is None:
            active_start = peak_index + 1
        depth = peak_equity - equity
        if depth > max_depth:
            max_depth = depth
            trough_index = index
    if active_start is not None:
        close_episode(len(ordered) - 1, False)
    episodes.sort(key=lambda item: _decimal(item["depth_r"]), reverse=True)
    return episodes[:limit]


def _loss_streaks(
    rows: Sequence[dict[str, object]], minimum: int = 3
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    result: list[dict[str, object]] = []
    streak: list[dict[str, object]] = []
    for row in [*ordered, {}]:
        if row and _decimal(row["primary_r"]) < 0:
            streak.append(row)
            continue
        if len(streak) >= minimum:
            result.append(
                {
                    "started_at": streak[0]["signal_at"],
                    "ended_at": streak[-1]["signal_at"],
                    "length": len(streak),
                    "total_r": _fmt(
                        sum(
                            (_decimal(item["primary_r"]) for item in streak),
                            Decimal(),
                        )
                    ),
                    "symbols": dict(
                        Counter(str(item["symbol"]) for item in streak)
                    ),
                    "anchors": dict(
                        Counter(
                            str(item["anchor_hour_new_york"]) for item in streak
                        )
                    ),
                    "models": dict(
                        Counter(str(item["model_kind"]) for item in streak)
                    ),
                }
            )
        streak = []
    result.sort(
        key=lambda item: (
            cast(int, item["length"]),
            -_decimal(item["total_r"]),
        ),
        reverse=True,
    )
    return result[:20]


def _correlated_loss_clusters(
    rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    losses = sorted(
        (row for row in rows if _decimal(row["primary_r"]) < 0),
        key=lambda row: str(row["signal_at"]),
    )
    clusters: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    last_time: datetime | None = None
    for row in losses:
        current_time = datetime.fromisoformat(str(row["signal_at"]))
        if last_time is None or current_time - last_time <= timedelta(hours=4):
            current.append(row)
        else:
            if current:
                clusters.append(current)
            current = [row]
        last_time = current_time
    if current:
        clusters.append(current)
    payloads: list[dict[str, object]] = []
    for cluster in clusters:
        markets = sorted({str(row["symbol"]) for row in cluster})
        if len(cluster) < 2 or len(markets) < 2:
            continue
        payloads.append(
            {
                "started_at": cluster[0]["signal_at"],
                "ended_at": cluster[-1]["signal_at"],
                "trade_count": len(cluster),
                "distinct_markets": markets,
                "total_r": _fmt(
                    sum(
                        (_decimal(row["primary_r"]) for row in cluster),
                        Decimal(),
                    )
                ),
                "anchors": dict(
                    Counter(
                        str(row["anchor_hour_new_york"]) for row in cluster
                    )
                ),
            }
        )
    payloads.sort(key=lambda item: _decimal(item["total_r"]))
    return payloads[:20]


def _funnel_slot(
    *,
    symbol: str,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    opened: datetime,
) -> dict[str, object]:
    local = opened.astimezone(_NY)
    base: dict[str, object] = {
        "symbol": symbol,
        "h4_opened_at": opened.astimezone(UTC).isoformat(),
        "anchor_hour_new_york": local.hour,
        "year_quarter": f"{local.year}-Q{((local.month - 1) // 3) + 1}",
    }
    side = v7._daily_bias(indexed, before=opened)
    if side is None:
        return {**base, "stage": "no-daily-bias"}
    base["side"] = side.value
    poi = v6._source_poi_for_h4(
        indexed,
        h4,
        h4_opened_at=opened,
        side=side,
    )
    if poi is None:
        return {**base, "stage": "no-poi"}
    base["poi_kind"] = poi.kind.value
    h4_bar = h4[opened.astimezone(UTC)]
    bars = v6._bars_between(indexed, start=opened, end=h4_bar.closed_at)
    touch_index = v6._poi_touch_index(bars, poi)
    if touch_index is None:
        return {**base, "stage": "poi-not-touched"}
    model = v6._completed_h4_model(
        indexed,
        h4,
        current_h4_open=opened,
        side=side,
    )
    if model is None:
        model = v6.H4ModelKind.SAME_C2
    base["model_kind"] = model.value
    cisd = v6._first_cisd(bars, side=side, start_index=touch_index)
    if cisd is None:
        return {**base, "stage": "no-cisd"}
    cisd_index, _, protected_swing = cisd
    base["cisd_latency_minutes"] = int(
        (bars[cisd_index].closed_at - opened).total_seconds() // 60
    )
    continuation_index = v6._first_continuation(
        bars,
        side=side,
        start_index=cisd_index + 1,
        protected_swing=protected_swing,
    )
    if continuation_index is None:
        return {**base, "stage": "no-continuation-or-ps-invalidated"}
    continuation = bars[continuation_index]
    entry = continuation.close
    if model is v6.H4ModelKind.SAME_C2:
        in_body = (
            entry > h4_bar.open
            if side is DemoTradingSetupSide.LONG
            else entry < h4_bar.open
        )
        if not in_body:
            return {**base, "stage": "same-c2-still-in-wick"}
    risk = (
        entry - protected_swing
        if side is DemoTradingSetupSide.LONG
        else protected_swing - entry
    )
    if risk <= 0:
        return {**base, "stage": "non-positive-risk"}
    base["entry_latency_minutes"] = int(
        (continuation.closed_at - opened).total_seconds() // 60
    )
    return {**base, "stage": "signal"}


def _funnel_summary(
    observations: Sequence[dict[str, object]],
) -> dict[str, object]:
    def summarize(items: Iterable[dict[str, object]]) -> dict[str, object]:
        rows = list(items)
        counts = Counter(str(row["stage"]) for row in rows)
        signals = counts.get("signal", 0)
        return {
            "opportunities": len(rows),
            "signals": signals,
            "conversion_rate": (
                _fmt(Decimal(signals) / Decimal(len(rows))) if rows else "0"
            ),
            "stages": dict(sorted(counts.items())),
        }

    symbols = sorted({str(row["symbol"]) for row in observations})
    anchors = sorted({str(row["anchor_hour_new_york"]) for row in observations})
    by_symbol = {
        symbol: summarize(
            row for row in observations if str(row["symbol"]) == symbol
        )
        for symbol in symbols
    }
    by_anchor = {
        anchor: summarize(
            row
            for row in observations
            if str(row["anchor_hour_new_york"]) == anchor
        )
        for anchor in anchors
    }
    by_symbol_anchor: dict[str, object] = {}
    for symbol in symbols:
        for anchor in anchors:
            items = [
                row
                for row in observations
                if str(row["symbol"]) == symbol
                and str(row["anchor_hour_new_york"]) == anchor
            ]
            if items:
                by_symbol_anchor[f"{symbol}|{anchor}"] = summarize(items)
    return {
        "overall": summarize(observations),
        "by_symbol": by_symbol,
        "by_anchor": by_anchor,
        "by_symbol_anchor": by_symbol_anchor,
    }


def _pre_exit_excursions(
    trade: v6.ModeledV6Trade,
    future_bars: Sequence[Vt08IndexC2R1Bar],
) -> tuple[Decimal, Decimal]:
    signal = trade.signal
    risk = abs(signal.entry - signal.stop)
    mfe = Decimal()
    mae = Decimal()
    for bar in future_bars:
        if bar.closed_at > trade.exited_at:
            break
        if bar.closed_at == trade.exited_at:
            if trade.exit_reason in {"target", "target-gap"}:
                mfe = max(mfe, max(trade.r_multiple, Decimal()))
            elif trade.exit_reason in {"stop", "stop-gap"}:
                mae = max(mae, max(-trade.r_multiple, Decimal("1")))
            else:
                favorable = (
                    bar.high - signal.entry
                    if signal.side is DemoTradingSetupSide.LONG
                    else signal.entry - bar.low
                )
                adverse = (
                    signal.entry - bar.low
                    if signal.side is DemoTradingSetupSide.LONG
                    else bar.high - signal.entry
                )
                mfe = max(mfe, favorable / risk)
                mae = max(mae, adverse / risk)
            break
        favorable = (
            bar.high - signal.entry
            if signal.side is DemoTradingSetupSide.LONG
            else signal.entry - bar.low
        )
        adverse = (
            signal.entry - bar.low
            if signal.side is DemoTradingSetupSide.LONG
            else bar.high - signal.entry
        )
        mfe = max(mfe, favorable / risk)
        mae = max(mae, adverse / risk)
    return max(mfe, Decimal()), max(mae, Decimal())


def _alternate_target_r(
    trade: v6.ModeledV6Trade,
    future_bars: Sequence[Vt08IndexC2R1Bar],
    target_r: Decimal,
) -> Decimal | None:
    signal = trade.signal
    risk = abs(signal.entry - signal.stop)
    target = (
        signal.entry + target_r * risk
        if signal.side is DemoTradingSetupSide.LONG
        else signal.entry - target_r * risk
    )
    last: Vt08IndexC2R1Bar | None = None
    for bar in future_bars:
        last = bar
        resolved = _gap_exit(
            side=signal.side,
            bar=bar,
            stop=signal.stop,
            target=target,
        )
        if resolved is None:
            resolved = _intrabar_exit(
                bar=bar,
                stop=signal.stop,
                target=target,
            )
        if resolved is None:
            continue
        exit_price, _ = resolved
        pnl = (
            exit_price - signal.entry
            if signal.side is DemoTradingSetupSide.LONG
            else signal.entry - exit_price
        )
        return pnl / risk
    if last is None:
        return None
    pnl = (
        last.close - signal.entry
        if signal.side is DemoTradingSetupSide.LONG
        else signal.entry - last.close
    )
    return pnl / risk


def _prior_context(
    signal: v6.CandidateSignal,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
) -> dict[str, object]:
    prior_keys = v6._prior_h4_keys(h4, before=signal.h4_opened_at, count=20)
    ratio: Decimal | None = None
    prior_alignment = "unknown"
    if prior_keys:
        last = h4[prior_keys[-1]]
        prior_alignment = _aligned(signal.side, last.open, last.close)
        ranges = [h4[key].high - h4[key].low for key in prior_keys]
        reference = median(ranges) if ranges else Decimal()
        if reference > 0:
            ratio = (last.high - last.low) / reference
    source_days = v7._latest_complete_source_days(
        indexed,
        before_local=signal.h4_opened_at,
    )
    current_alignment = "unknown"
    previous_alignment = "unknown"
    source_range_ratio: Decimal | None = None
    if source_days is not None:
        previous, current = source_days
        previous_alignment = _aligned(signal.side, previous.open, previous.close)
        current_alignment = _aligned(signal.side, current.open, current.close)
        previous_range = previous.high - previous.low
        if previous_range > 0:
            source_range_ratio = (current.high - current.low) / previous_range
    return {
        "prior_h4_body_alignment": prior_alignment,
        "prior_h4_range_ratio_20": _fmt(ratio) if ratio is not None else None,
        "prior_h4_range_regime": _range_regime(ratio),
        "current_source_body_alignment": current_alignment,
        "previous_source_body_alignment": previous_alignment,
        "source_day_range_ratio": (
            _fmt(source_range_ratio) if source_range_ratio is not None else None
        ),
    }


def _peer_context(
    signal: v6.CandidateSignal,
    states: dict[str, dict[str, object]],
) -> dict[str, object]:
    returns: dict[str, Decimal] = {}
    for symbol, state in states.items():
        h4 = cast(dict[datetime, Vt08IndexC2R1Bar], state["h4"])
        h4_bar = h4.get(signal.h4_opened_at.astimezone(UTC))
        if h4_bar is None or h4_bar.open <= 0:
            continue
        opened_times = cast(tuple[datetime, ...], state["opened_times"])
        ordered_bars = cast(tuple[Vt08IndexC2R1Bar, ...], state["ordered_bars"])
        start_index = bisect_left(
            opened_times,
            signal.h4_opened_at.astimezone(UTC),
        )
        end_index = bisect_left(
            opened_times,
            signal.signal_at.astimezone(UTC),
        )
        if end_index <= start_index:
            continue
        observed = ordered_bars[end_index - 1]
        returns[symbol] = (observed.close - h4_bar.open) / h4_bar.open
    side_sign = (
        Decimal("1")
        if signal.side is DemoTradingSetupSide.LONG
        else Decimal("-1")
    )
    peers = {
        symbol: value
        for symbol, value in returns.items()
        if symbol != signal.symbol
    }
    peer_alignment = sum(value * side_sign > 0 for value in peers.values())
    side_adjusted = sorted(
        ((symbol, value * side_sign) for symbol, value in returns.items()),
        key=lambda item: item[1],
    )
    rank = next(
        (
            index + 1
            for index, item in enumerate(side_adjusted)
            if item[0] == signal.symbol
        ),
        None,
    )
    return {
        "peer_alignment_count": peer_alignment,
        "side_adjusted_relative_strength_rank": rank,
        "contemporaneous_h4_returns": {
            symbol: _fmt(value) for symbol, value in sorted(returns.items())
        },
    }


def _future_bars_for_trade(
    trade: v6.ModeledV6Trade,
    *,
    opened_times: tuple[datetime, ...],
    ordered_bars: tuple[Vt08IndexC2R1Bar, ...],
    end_date_exclusive: date,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    boundary = v6._boundary_utc(end_date_exclusive)
    start_index = bisect_left(
        opened_times,
        trade.signal.signal_at.astimezone(UTC),
    )
    end_index = bisect_left(opened_times, boundary)
    return ordered_bars[start_index:end_index]


def _trade_row(
    trade: v6.ModeledV6Trade,
    *,
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    h4: dict[datetime, Vt08IndexC2R1Bar],
    opened_times: tuple[datetime, ...],
    ordered_bars: tuple[Vt08IndexC2R1Bar, ...],
    states: dict[str, dict[str, object]],
    end_date_exclusive: date,
) -> dict[str, object]:
    signal = trade.signal
    local = signal.signal_at.astimezone(_NY)
    risk = abs(signal.entry - signal.stop)
    entry_latency = int(
        (signal.signal_at - signal.h4_opened_at).total_seconds() // 60
    )
    cisd_latency = int(
        (signal.cisd_confirmed_at - signal.h4_opened_at).total_seconds() // 60
    )
    duration = int((trade.exited_at - signal.signal_at).total_seconds() // 60)
    future_bars = _future_bars_for_trade(
        trade,
        opened_times=opened_times,
        ordered_bars=ordered_bars,
        end_date_exclusive=end_date_exclusive,
    )
    mfe, mae = _pre_exit_excursions(trade, future_bars)
    target_outcomes: dict[str, object] = {}
    for target_r in TARGET_SURFACE_R:
        realized = _alternate_target_r(trade, future_bars, target_r)
        target_outcomes[_fmt(target_r)] = (
            _fmt(realized) if realized is not None else None
        )
    row: dict[str, object] = {
        "symbol": signal.symbol,
        "side": signal.side.value,
        "model_kind": signal.model_kind.value,
        "poi_kind": signal.poi.kind.value,
        "h4_opened_at": signal.h4_opened_at.astimezone(UTC).isoformat(),
        "signal_at": signal.signal_at.astimezone(UTC).isoformat(),
        "exited_at": trade.exited_at.astimezone(UTC).isoformat(),
        "anchor_hour_new_york": signal.h4_opened_at.astimezone(_NY).hour,
        "year": local.year,
        "year_quarter": f"{local.year}-Q{((local.month - 1) // 3) + 1}",
        "entry": _fmt(signal.entry),
        "stop": _fmt(signal.stop),
        "risk_points": _fmt(risk),
        "risk_fraction_of_entry": (
            _fmt(risk / signal.entry) if signal.entry > 0 else None
        ),
        "raw_r": _fmt(trade.r_multiple),
        "primary_r": _fmt(trade.r_multiple - PRIMARY_STRESS),
        "secondary_r": _fmt(trade.r_multiple - SECONDARY_STRESS),
        "exit_reason": trade.exit_reason,
        "entry_latency_minutes": entry_latency,
        "entry_timing_bucket": _timing_bucket(entry_latency),
        "cisd_latency_minutes": cisd_latency,
        "post_cisd_latency_minutes": entry_latency - cisd_latency,
        "trade_duration_minutes": duration,
        "duration_bucket": _duration_bucket(duration),
        "mfe_r_conservative": _fmt(mfe),
        "mae_r_conservative": _fmt(mae),
        "stop_excursion_bucket": (
            _excursion_bucket(mfe) if trade.r_multiple < 0 else "not-stop"
        ),
        "target_outcomes_raw_r": target_outcomes,
    }
    row.update(_prior_context(signal, indexed, h4))
    row.update(_peer_context(signal, states))
    return row


def _target_surface(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for target_r in TARGET_SURFACE_R:
        key = _fmt(target_r)
        derived: list[dict[str, object]] = []
        for row in rows:
            outcomes = cast(dict[str, object], row["target_outcomes_raw_r"])
            raw = outcomes.get(key)
            if raw is None:
                continue
            clone = dict(row)
            clone["primary_r"] = _fmt(_decimal(raw) - PRIMARY_STRESS)
            clone["secondary_r"] = _fmt(_decimal(raw) - SECONDARY_STRESS)
            derived.append(clone)
        result[key] = {
            "primary": _row_metrics(derived, key="primary_r"),
            "secondary": _row_metrics(derived, key="secondary_r"),
        }
    return result


def _stop_taxonomy(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    stops = [row for row in rows if _decimal(row["raw_r"]) < 0]
    by_bucket = Counter(str(row["stop_excursion_bucket"]) for row in stops)
    by_duration = Counter(str(row["duration_bucket"]) for row in stops)
    by_symbol: dict[str, object] = {}
    for symbol in sorted({str(row["symbol"]) for row in stops}):
        subset = [row for row in stops if str(row["symbol"]) == symbol]
        by_symbol[symbol] = {
            "sample": len(subset),
            "excursion_buckets": dict(
                Counter(str(row["stop_excursion_bucket"]) for row in subset)
            ),
            "duration_buckets": dict(
                Counter(str(row["duration_bucket"]) for row in subset)
            ),
            "mean_mfe_r": (
                _fmt(
                    sum(
                        (_decimal(row["mfe_r_conservative"]) for row in subset),
                        Decimal(),
                    )
                    / len(subset)
                )
                if subset
                else "0"
            ),
        }
    return {
        "sample": len(stops),
        "excursion_buckets": dict(by_bucket),
        "duration_buckets": dict(by_duration),
        "by_symbol": by_symbol,
    }


def analyze_window(
    *,
    nas100: Path,
    sp500: Path,
    us30: Path,
    start_date: date,
    end_date_exclusive: date,
    expected_software_sha: str,
    minimum_evidence_days: int,
    window_id: str,
) -> dict[str, object]:
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    states: dict[str, dict[str, object]] = {}
    provenance: dict[str, object] = {}
    for symbol in v7.AUTHORIZED_MARKETS:
        fingerprint, provider, checked_at, bars = _load_candidate_market(
            paths[symbol],
            expected_symbol=symbol,
            expected_software_sha=expected_software_sha,
            minimum_evidence_days=minimum_evidence_days,
        )
        indexed = {bar.opened_at.astimezone(UTC): bar for bar in bars}
        ordered_bars = tuple(sorted(bars, key=lambda bar: bar.opened_at))
        opened_times = tuple(bar.opened_at.astimezone(UTC) for bar in ordered_bars)
        states[symbol] = {
            "indexed": indexed,
            "h4": v6._build_h4(indexed),
            "bars": bars,
            "ordered_bars": ordered_bars,
            "opened_times": opened_times,
        }
        provenance[symbol] = {
            "provider_symbol": provider,
            "account_fingerprint": fingerprint,
            "checked_at": checked_at.astimezone(UTC).isoformat(),
            "software_sha": expected_software_sha,
            "m15_bars": len(bars),
        }

    rows: list[dict[str, object]] = []
    funnel: list[dict[str, object]] = []
    session_reconstruction: dict[str, object] = {}
    for symbol in v7.AUTHORIZED_MARKETS:
        state = states[symbol]
        indexed = cast(dict[datetime, Vt08IndexC2R1Bar], state["indexed"])
        h4 = cast(dict[datetime, Vt08IndexC2R1Bar], state["h4"])
        ordered_bars = cast(tuple[Vt08IndexC2R1Bar, ...], state["ordered_bars"])
        opened_times = cast(tuple[datetime, ...], state["opened_times"])
        market = v7._market_report(
            symbol=symbol,
            bars=cast(Sequence[Vt08IndexC2R1Bar], state["bars"]),
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
        )
        session_reconstruction[symbol] = market["session_reconstruction"]
        trades = cast(tuple[v6.ModeledV6Trade, ...], market["trades"])
        for trade in trades:
            rows.append(
                _trade_row(
                    trade,
                    indexed=indexed,
                    h4=h4,
                    opened_times=opened_times,
                    ordered_bars=ordered_bars,
                    states=states,
                    end_date_exclusive=end_date_exclusive,
                )
            )
        for opened in sorted(h4):
            if (
                opened.astimezone(_NY).hour
                not in v7.EXECUTABLE_H4_ANCHORS_NY
            ):
                continue
            if not _in_partition(
                opened,
                start_date=start_date,
                end_date_exclusive=end_date_exclusive,
            ):
                continue
            funnel.append(
                _funnel_slot(
                    symbol=symbol,
                    indexed=indexed,
                    h4=h4,
                    opened=opened,
                )
            )

    rows.sort(key=lambda row: (str(row["signal_at"]), str(row["symbol"])))
    return {
        "schema": SCHEMA,
        "window_id": window_id,
        "candidate_id": v7.CANDIDATE_ID,
        "rule_fingerprint": v7.RULE_FINGERPRINT,
        "partition": {
            "start_date": start_date.isoformat(),
            "end_date_exclusive": end_date_exclusive.isoformat(),
        },
        "provenance": provenance,
        "session_reconstruction": session_reconstruction,
        "metrics_raw": _row_metrics(rows, key="raw_r"),
        "metrics_primary": _row_metrics(rows, key="primary_r"),
        "metrics_secondary": _row_metrics(rows, key="secondary_r"),
        "opportunity_funnel": _funnel_summary(funnel),
        "cohort_cube": _cohort_cube(rows),
        "stop_taxonomy": _stop_taxonomy(rows),
        "target_surface": _target_surface(rows),
        "drawdown_episodes": _drawdown_episodes(rows),
        "loss_streaks": _loss_streaks(rows),
        "correlated_loss_clusters": _correlated_loss_clusters(rows),
        "trades": rows,
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "may_change_candidate_rules": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def combine_reports(reports: Sequence[dict[str, object]]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    windows: list[dict[str, object]] = []
    funnel_stages: Counter[str] = Counter()
    funnel_total = 0
    funnel_signals = 0
    for report in reports:
        report_rows = cast(list[dict[str, object]], report["trades"])
        rows.extend(report_rows)
        metrics = cast(dict[str, object], report["metrics_primary"])
        windows.append(
            {
                "window_id": report["window_id"],
                "partition": report["partition"],
                "sample": metrics["sample"],
                "mean_r": metrics["mean_r"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown_r": metrics["max_drawdown_r"],
            }
        )
        funnel = cast(dict[str, object], report["opportunity_funnel"])
        overall = cast(dict[str, object], funnel["overall"])
        funnel_total += cast(int, overall["opportunities"])
        funnel_signals += cast(int, overall["signals"])
        funnel_stages.update(cast(dict[str, int], overall["stages"]))
    rows.sort(key=lambda row: (str(row["signal_at"]), str(row["symbol"])))
    return {
        "schema": COMBINED_SCHEMA,
        "candidate_id": v7.CANDIDATE_ID,
        "rule_fingerprint": v7.RULE_FINGERPRINT,
        "windows": windows,
        "metrics_raw": _row_metrics(rows, key="raw_r"),
        "metrics_primary": _row_metrics(rows, key="primary_r"),
        "metrics_secondary": _row_metrics(rows, key="secondary_r"),
        "opportunity_funnel": {
            "opportunities": funnel_total,
            "signals": funnel_signals,
            "conversion_rate": (
                _fmt(Decimal(funnel_signals) / Decimal(funnel_total))
                if funnel_total
                else "0"
            ),
            "stages": dict(sorted(funnel_stages.items())),
        },
        "cohort_cube": _cohort_cube(rows),
        "stop_taxonomy": _stop_taxonomy(rows),
        "target_surface": _target_surface(rows),
        "drawdown_episodes": _drawdown_episodes(rows, limit=20),
        "loss_streaks": _loss_streaks(rows),
        "correlated_loss_clusters": _correlated_loss_clusters(rows),
        "trades": rows,
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "post_result_candidate_tuning_forbidden_without_new_identity": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    window = sub.add_parser("window")
    window.add_argument("--nas100", type=Path, required=True)
    window.add_argument("--sp500", type=Path, required=True)
    window.add_argument("--us30", type=Path, required=True)
    window.add_argument("--start-date", type=date.fromisoformat, required=True)
    window.add_argument("--end-date-exclusive", type=date.fromisoformat, required=True)
    window.add_argument("--expected-software-sha", required=True)
    window.add_argument("--minimum-evidence-days", type=int, required=True)
    window.add_argument("--window-id", required=True)
    window.add_argument("--out", type=Path, required=True)

    combine = sub.add_parser("combine")
    combine.add_argument("reports", nargs="+", type=Path)
    combine.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "window":
        payload = analyze_window(
            nas100=args.nas100,
            sp500=args.sp500,
            us30=args.us30,
            start_date=args.start_date,
            end_date_exclusive=args.end_date_exclusive,
            expected_software_sha=args.expected_software_sha,
            minimum_evidence_days=args.minimum_evidence_days,
            window_id=args.window_id,
        )
        _write(args.out, payload)
        print(
            json.dumps(
                {
                    "window_id": args.window_id,
                    "sample": cast(
                        dict[str, object], payload["metrics_primary"]
                    )["sample"],
                },
                sort_keys=True,
            )
        )
        return
    reports = [
        cast(
            dict[str, object],
            json.loads(path.read_text(encoding="utf-8")),
        )
        for path in args.reports
    ]
    payload = combine_reports(reports)
    _write(args.out, payload)
    print(
        json.dumps(
            {
                "windows": len(reports),
                "sample": cast(
                    dict[str, object], payload["metrics_primary"]
                )["sample"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
