"""Two-year economic characterization replay for VT08 CRT PURE.

Research only.  This replay freezes one source-first baseline:
- C1 is the scheduled H4 reference range.
- C2 must make a one-sided Turtle Soup penetration and close back inside C1.
- Entry is the first M5 open of C3, after C2 has closed.
- Stop is the C2 manipulation extreme.
- TP1 is the 50% midpoint of C1.
- If neither stop nor TP1 is reached during C3, exit at the final C3 M5 close.
- Same-M5 stop/target ambiguity is resolved STOP-first.

The NY/DST mapping of RomeoTPT's compact timing notation remains an explicit
engineering policy and is not mislabeled as source authority.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_consumer import (
    _credentials,
    _provider_bar,
    _selected_symbol,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_windowed_runtime import (
    read_windowed_chunk,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
    candidate_direction_from_turtle_soup,
    classify_range_outcome,
)
from qore.infrastructure.traders.crt_pure_timing_policy import (
    NY,
    utc_triplet_windows_for_local_date,
)
from qore.kernel.result import Failure

IDENTITY = "VT08_CRT_PURE_2Y_BASELINE_REPLAY_001"
SCHEMA = "qore.vt08.crt_pure.2y_baseline_replay.v1"
START = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
END_EXCLUSIVE = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FOLD_1_END = datetime(2025, 9, 21, 0, 0, tzinfo=UTC)
PERIOD_MINUTES = 5
CHUNK_DAYS = 7


@dataclass(frozen=True, slots=True)
class ReplayBar:
    opened_at: datetime
    open_price: int
    high_price: int
    low_price: int
    close_price: int

    def payload(self) -> tuple[int, int, int, int]:
        return (
            self.open_price,
            self.high_price,
            self.low_price,
            self.close_price,
        )


@dataclass(frozen=True, slots=True)
class AggregatedCandle:
    opened_at: datetime
    closed_at: datetime
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    m5_count: int


@dataclass(frozen=True, slots=True)
class ReplayTrade:
    schema: str
    identity: str
    market: str
    c3_opened_at: str
    local_date: str
    timing_triplet: str
    direction: str
    entry_price_relative: int
    stop_price_relative: int
    target_price_relative: str
    exit_price_relative: str
    exit_reason: str
    r_multiple: float
    risk_distance_relative: int
    reward_to_midpoint_r: float
    c1_high_relative: int
    c1_low_relative: int
    c2_high_relative: int
    c2_low_relative: int
    c2_close_relative: int
    same_m5_stop_first: bool
    engineering_timezone_policy: str
    research_only: bool = True
    demo_eligible: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False


def _partition_windows(start: datetime, end: datetime) -> tuple[tuple[datetime, datetime], ...]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        closed = min(cursor + timedelta(days=CHUNK_DAYS), end)
        windows.append((cursor, closed))
        cursor = closed
    return tuple(windows)


def _to_replay_bar(native: object, *, market: CrtPureMarket, provider_symbol: str,
                   provider_symbol_id: int, digits: int, pip_position: int | None) -> ReplayBar:
    row = _provider_bar(
        native,
        canonical_symbol=market.value,
        provider_symbol=provider_symbol,
        provider_symbol_id=provider_symbol_id,
        digits=digits,
        pip_position=pip_position,
    )
    return ReplayBar(
        opened_at=datetime.fromisoformat(row.opened_at),
        open_price=row.open_relative,
        high_price=row.high_relative,
        low_price=row.low_relative,
        close_price=row.close_relative,
    )


def load_two_year_m5(market: CrtPureMarket) -> tuple[ReplayBar, ...]:
    """Load the exact replay window plus one-day boundary margins, fail-closed."""

    fetch_start = START - timedelta(days=1)
    fetch_end = END_EXCLUSIVE + timedelta(days=1)
    client = SpotwareCTraderOpenApiClient(credentials=_credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits, pip_position = _selected_symbol(
            client,
            canonical_symbol=market.value,
        )
        by_time: dict[datetime, ReplayBar] = {}
        for index, (opened, closed) in enumerate(_partition_windows(fetch_start, fetch_end)):
            native_bars = read_windowed_chunk(
                client,
                account_id=client.account_id,
                symbol_id=symbol_id,
                opened_at=opened,
                closed_at=closed,
                client_msg_id=f"crt-pure-2y:{market.value}:{index}",
            )
            for native in native_bars:
                bar = _to_replay_bar(
                    native,
                    market=market,
                    provider_symbol=provider_symbol,
                    provider_symbol_id=symbol_id,
                    digits=digits,
                    pip_position=pip_position,
                )
                if not fetch_start <= bar.opened_at < fetch_end:
                    raise RuntimeError("provider returned M5 outside strict replay fetch window")
                existing = by_time.get(bar.opened_at)
                if existing is None:
                    by_time[bar.opened_at] = bar
                elif existing.payload() != bar.payload():
                    raise RuntimeError("contradictory duplicate M5 payload in replay evidence")
        return tuple(by_time[key] for key in sorted(by_time))
    finally:
        client.close()


def _segment(
    by_time: dict[datetime, ReplayBar],
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[ReplayBar, ...] | None:
    expected: list[ReplayBar] = []
    cursor = opened_at
    while cursor < closed_at:
        bar = by_time.get(cursor)
        if bar is None:
            return None
        expected.append(bar)
        cursor += timedelta(minutes=PERIOD_MINUTES)
    return tuple(expected)


def _aggregate(segment: tuple[ReplayBar, ...], opened_at: datetime, closed_at: datetime) -> AggregatedCandle:
    if not segment:
        raise ValueError("cannot aggregate an empty segment")
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=closed_at,
        open_price=segment[0].open_price,
        high_price=max(item.high_price for item in segment),
        low_price=min(item.low_price for item in segment),
        close_price=segment[-1].close_price,
        m5_count=len(segment),
    )


def _days(start_day: date, end_day: date) -> Iterable[date]:
    cursor = start_day
    while cursor <= end_day:
        yield cursor
        cursor += timedelta(days=1)


def _midpoint(high: int, low: int) -> Decimal:
    return (Decimal(high) + Decimal(low)) / Decimal(2)


def _trade_from_window(
    *,
    market: CrtPureMarket,
    timing_index: int,
    c1: AggregatedCandle,
    c2: AggregatedCandle,
    c3_m5: tuple[ReplayBar, ...],
) -> ReplayTrade | None:
    outcome = classify_range_outcome(
        reference_high=float(c1.high_price),
        reference_low=float(c1.low_price),
        observed_high=float(c2.high_price),
        observed_low=float(c2.low_price),
        observed_close=float(c2.close_price),
    )
    if outcome.value != "TURTLE_SOUP":
        return None

    direction = candidate_direction_from_turtle_soup(
        reference_high=float(c1.high_price),
        reference_low=float(c1.low_price),
        observed_high=float(c2.high_price),
        observed_low=float(c2.low_price),
        observed_close=float(c2.close_price),
    )
    if direction is None:
        return None

    entry = c3_m5[0].open_price
    target = _midpoint(c1.high_price, c1.low_price)

    if direction is CrtPureCandidateDirection.BULLISH:
        stop = c2.low_price
        if stop >= entry or target <= Decimal(entry):
            return None
        risk = entry - stop
        reward_r = float((target - Decimal(entry)) / Decimal(risk))
    else:
        stop = c2.high_price
        if stop <= entry or target >= Decimal(entry):
            return None
        risk = stop - entry
        reward_r = float((Decimal(entry) - target) / Decimal(risk))

    exit_reason = "C3_CLOSE"
    exit_price = Decimal(c3_m5[-1].close_price)
    r_value: Decimal | None = None

    for bar in c3_m5:
        if direction is CrtPureCandidateDirection.BULLISH:
            stop_hit = bar.low_price <= stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = bar.high_price >= stop
            target_hit = Decimal(bar.low_price) <= target

        if stop_hit:
            exit_reason = "STOP"
            exit_price = Decimal(stop)
            r_value = Decimal("-1")
            break
        if target_hit:
            exit_reason = "TARGET_50"
            exit_price = target
            r_value = Decimal(str(reward_r))
            break

    if r_value is None:
        if direction is CrtPureCandidateDirection.BULLISH:
            r_value = (exit_price - Decimal(entry)) / Decimal(risk)
        else:
            r_value = (Decimal(entry) - exit_price) / Decimal(risk)

    local = c3_m5[0].opened_at.astimezone(NY)
    return ReplayTrade(
        schema=SCHEMA,
        identity=IDENTITY,
        market=market.value,
        c3_opened_at=c3_m5[0].opened_at.isoformat(),
        local_date=local.date().isoformat(),
        timing_triplet=str(timing_index + 1),
        direction=direction.value,
        entry_price_relative=entry,
        stop_price_relative=stop,
        target_price_relative=str(target),
        exit_price_relative=str(exit_price),
        exit_reason=exit_reason,
        r_multiple=round(float(r_value), 8),
        risk_distance_relative=risk,
        reward_to_midpoint_r=round(reward_r, 8),
        c1_high_relative=c1.high_price,
        c1_low_relative=c1.low_price,
        c2_high_relative=c2.high_price,
        c2_low_relative=c2.low_price,
        c2_close_relative=c2.close_price,
        same_m5_stop_first=True,
        engineering_timezone_policy="America/New_York",
    )


def run_market_replay(market: CrtPureMarket, bars: tuple[ReplayBar, ...]) -> tuple[ReplayTrade, ...]:
    by_time = {bar.opened_at: bar for bar in bars}
    start_day = (START - timedelta(days=1)).astimezone(NY).date()
    end_day = END_EXCLUSIVE.astimezone(NY).date()
    trades: list[ReplayTrade] = []

    for day in _days(start_day, end_day):
        local_noon = datetime(day.year, day.month, day.day, 12, tzinfo=NY)
        windows = utc_triplet_windows_for_local_date(market, local_noon)
        for timing_index, window in enumerate(windows):
            if not START <= window.candle_3_open < END_EXCLUSIVE:
                continue
            c1_m5 = _segment(by_time, window.candle_1_open, window.candle_2_open)
            c2_m5 = _segment(by_time, window.candle_2_open, window.candle_3_open)
            c3_m5 = _segment(by_time, window.candle_3_open, window.window_close)
            if c1_m5 is None or c2_m5 is None or c3_m5 is None:
                continue
            trade = _trade_from_window(
                market=market,
                timing_index=timing_index,
                c1=_aggregate(c1_m5, window.candle_1_open, window.candle_2_open),
                c2=_aggregate(c2_m5, window.candle_2_open, window.candle_3_open),
                c3_m5=c3_m5,
            )
            if trade is not None:
                trades.append(trade)
    return tuple(trades)


def _max_drawdown(values: tuple[float, ...]) -> float:
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _losing_streak(values: tuple[float, ...]) -> int:
    current = 0
    worst = 0
    for value in values:
        if value < 0:
            current += 1
            worst = max(worst, current)
        else:
            current = 0
    return worst


def summarize(trades: tuple[ReplayTrade, ...]) -> dict[str, Any]:
    ordered = tuple(sorted(trades, key=lambda item: item.c3_opened_at))
    values = tuple(item.r_multiple for item in ordered)
    positive = tuple(value for value in values if value > 0)
    negative = tuple(value for value in values if value < 0)
    gross_profit = sum(positive)
    gross_loss = -sum(negative)
    return {
        "trades": len(values),
        "wins": len(positive),
        "losses": len(negative),
        "flat": sum(value == 0 for value in values),
        "win_rate": None if not values else round(len(positive) / len(values), 8),
        "profit_factor": None if gross_loss == 0 else round(gross_profit / gross_loss, 8),
        "total_r": round(sum(values), 8),
        "mean_r": None if not values else round(sum(values) / len(values), 8),
        "max_drawdown_r": round(_max_drawdown(values), 8),
        "longest_losing_streak": _losing_streak(values),
        "target_50_exits": sum(item.exit_reason == "TARGET_50" for item in ordered),
        "stop_exits": sum(item.exit_reason == "STOP" for item in ordered),
        "c3_close_exits": sum(item.exit_reason == "C3_CLOSE" for item in ordered),
        "longs": sum(item.direction == "BULLISH" for item in ordered),
        "shorts": sum(item.direction == "BEARISH" for item in ordered),
    }


def _fold(trades: tuple[ReplayTrade, ...], opened: datetime, closed: datetime) -> tuple[ReplayTrade, ...]:
    return tuple(
        item
        for item in trades
        if opened <= datetime.fromisoformat(item.c3_opened_at) < closed
    )


def build_report(per_market: dict[CrtPureMarket, tuple[ReplayTrade, ...]]) -> dict[str, Any]:
    combined = tuple(
        sorted(
            (trade for rows in per_market.values() for trade in rows),
            key=lambda item: item.c3_opened_at,
        )
    )
    market_payload: dict[str, Any] = {}
    for market, trades in per_market.items():
        market_payload[market.value] = {
            "full_2y": summarize(trades),
            "year_1": summarize(_fold(trades, START, FOLD_1_END)),
            "year_2": summarize(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        }

    return {
        "schema": f"{SCHEMA}.report",
        "identity": IDENTITY,
        "window": {
            "start": START.isoformat(),
            "end_exclusive": END_EXCLUSIVE.isoformat(),
            "fold_1_end": FOLD_1_END.isoformat(),
        },
        "baseline_contract": {
            "reference": "scheduled H4 C1 range",
            "manipulation": "C2 one-sided penetration plus close-back-inside",
            "entry": "C3 first M5 open after C2 close",
            "stop": "C2 manipulation extreme",
            "target": "C1 50 percent midpoint",
            "lifecycle": "C3 window; unresolved exits at C3 close",
            "same_m5_ambiguity": "STOP_FIRST",
            "timing_timezone": "America/New_York",
            "timing_timezone_authority": "ENGINEERING_POLICY",
        },
        "markets": market_payload,
        "combined": {
            "full_2y": summarize(combined),
            "year_1": summarize(_fold(combined, START, FOLD_1_END)),
            "year_2": summarize(_fold(combined, FOLD_1_END, END_EXCLUSIVE)),
        },
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[market.value for market in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    bars = load_two_year_m5(market)
    trades = run_market_replay(market, bars)
    args.output.mkdir(parents=True, exist_ok=True)
    ledger = args.output / "trades.jsonl"
    with ledger.open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    summary = {
        "schema": f"{SCHEMA}.market",
        "identity": IDENTITY,
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END_EXCLUSIVE.isoformat(),
        "m5_bars_loaded": len(bars),
        "summary": summarize(trades),
        "research_only": True,
        "candidate_certified": False,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
