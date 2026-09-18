"""Source-exact ICT/TTrades Turtle Soup R4 fresh-holdout research implementation.

Frozen candidate:
Daily Ideal C2 + H1 causal CISD -> Daily C3 expansion bias ->
H4 Ideal C2 + M15 causal CISD -> protected swing -> H4 C3 positional entry ->
pre-entry untouched Daily liquidity target.

Sessions are diagnostic metadata only. No clock-time inclusion/exclusion filter exists.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from time import sleep
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.kernel.result import Failure

IDENTITY = (
    "ICT_TURTLE_SOUP_R4_D1_IDEAL_C2_H1_CISD__"
    "H4_IDEAL_C2_M15_CISD__POSITIONAL_DAILY_DOL"
)
HOLDOUT_ID = "ICT_TS_R4_FRESH_2018_2020"
NY = ZoneInfo("America/New_York")
ACQUISITION_OPEN = datetime(2018, 5, 1, 21, tzinfo=UTC)
EVAL_OPEN = datetime(2018, 7, 2, 21, tzinfo=UTC)
EVAL_CLOSE = datetime(2020, 7, 1, 21, tzinfo=UTC)
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
}
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
M5 = timedelta(minutes=5)
M15 = timedelta(minutes=15)
H1 = timedelta(hours=1)
H4 = timedelta(hours=4)
D1 = timedelta(hours=24)
H4_SOURCE_ANCHORS = (17, 21, 1, 5, 9, 13)
PRICE_SCALE = Decimal(100_000)
CHUNK_DAYS = 14
PAGE_COUNT = 5000
REQUEST_PAUSE_SECONDS = 0.22


class Side(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class Evidence:
    symbol: str
    digits: int
    bars: tuple[Bar, ...]


@dataclass(frozen=True, slots=True)
class SourceCandle:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    m5: tuple[Bar, ...]


@dataclass(frozen=True, slots=True)
class CISD:
    side: Side
    extreme_at: datetime
    series_opened_at: datetime
    confirmed_at: datetime
    threshold: Decimal
    protected_swing: Decimal


@dataclass(frozen=True, slots=True)
class DailyBias:
    side: Side
    c1_opened_at: datetime
    c2_opened_at: datetime
    c3_opened_at: datetime
    relevant_level: Decimal
    protected_swing: Decimal
    cisd_at: datetime


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    side: Side
    daily_c2_opened_at: datetime
    daily_c3_opened_at: datetime
    h4_c1_opened_at: datetime
    h4_c2_opened_at: datetime
    cisd_at: datetime
    entry_at: datetime
    exit_at: datetime
    protected_swing: Decimal
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    projected_r: Decimal
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    exit_reason: str
    session_bucket: str
    primary_dol_opened_at: datetime


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise RuntimeError(f"missing required environment input: {name}")


def _native_int(value: object, name: str) -> int:
    result = getattr(value, name, None)
    if type(result) is not int:
        raise RuntimeError(f"cTrader {name} must be int")
    return result


def _price(relative: int, digits: int) -> Decimal:
    if relative <= 0:
        raise RuntimeError("invalid cTrader relative price")
    return (Decimal(relative) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))


def _collect_m5(symbol_name: str) -> Evidence:
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise RuntimeError("cTrader DEMO authentication failed")
        account_id = client.account_id
        listed = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
            client_msg_id="qore-ict-ts-r4-symbol-list",
            timeout_seconds=30.0,
        )
        if isinstance(listed, Failure):
            raise RuntimeError("cTrader symbol list failed")
        native_symbols = tuple(
            cast(Iterable[object], getattr(listed.value, "symbol", ()))
        )
        selected = next(
            (
                item
                for item in native_symbols
                if getattr(item, "symbolName", None) == symbol_name
                and getattr(item, "enabled", None) is True
            ),
            None,
        )
        if selected is None:
            raise RuntimeError(f"symbol unavailable: {symbol_name}")
        symbol_id = _native_int(selected, "symbolId")
        details = client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
            client_msg_id=f"qore-ict-ts-r4-symbol:{symbol_id}",
            timeout_seconds=30.0,
        )
        if isinstance(details, Failure):
            raise RuntimeError("cTrader symbol details failed")
        detail = next(
            (
                item
                for item in cast(
                    Iterable[object], getattr(details.value, "symbol", ())
                )
                if getattr(item, "symbolId", None) == symbol_id
            ),
            None,
        )
        if detail is None:
            raise RuntimeError("exact symbol details missing")
        digits = _native_int(detail, "digits")

        retained: dict[datetime, Bar] = {}
        window_start = ACQUISITION_OPEN
        window_index = 0
        while window_start < EVAL_CLOSE:
            window_end = min(
                window_start + timedelta(days=CHUNK_DAYS), EVAL_CLOSE
            )
            sleep(REQUEST_PAUSE_SECONDS)
            response = client.request(
                "ProtoOAGetTrendbarsReq",
                {
                    "ctidTraderAccountId": account_id,
                    "count": PAGE_COUNT,
                    "fromTimestamp": int(window_start.timestamp() * 1000),
                    "period": 5,
                    "symbolId": symbol_id,
                    "toTimestamp": int(window_end.timestamp() * 1000),
                },
                client_msg_id=(
                    f"qore-ict-ts-r4-m5:{symbol_id}:{window_index}"
                ),
                timeout_seconds=45.0,
            )
            if isinstance(response, Failure):
                raise RuntimeError("cTrader M5 historical read failed")
            natives = tuple(
                cast(Iterable[object], getattr(response.value, "trendbar", ()))
            )
            if (
                len(natives) >= PAGE_COUNT
                and getattr(response.value, "hasMore", False)
            ):
                raise RuntimeError("cTrader M5 chunk exceeded safe page bound")
            for native in natives:
                low_rel = _native_int(native, "low")
                opened = datetime.fromtimestamp(
                    _native_int(native, "utcTimestampInMinutes") * 60,
                    tz=UTC,
                )
                if not ACQUISITION_OPEN <= opened < EVAL_CLOSE:
                    continue
                bar = Bar(
                    opened_at=opened,
                    closed_at=opened + M5,
                    open=_price(
                        low_rel + _native_int(native, "deltaOpen"), digits
                    ),
                    high=_price(
                        low_rel + _native_int(native, "deltaHigh"), digits
                    ),
                    low=_price(low_rel, digits),
                    close=_price(
                        low_rel + _native_int(native, "deltaClose"), digits
                    ),
                )
                existing = retained.get(opened)
                if existing is not None and existing != bar:
                    raise RuntimeError("contradictory historical M5 bar")
                retained[opened] = bar
            window_start = window_end
            window_index += 1
        bars = tuple(retained[key] for key in sorted(retained))
        if not bars:
            raise RuntimeError("no historical M5 evidence")
        if bars[0].opened_at > ACQUISITION_OPEN + timedelta(days=10):
            raise RuntimeError(
                "provider history does not reach frozen warm-up boundary"
            )
        if bars[-1].closed_at < EVAL_CLOSE - timedelta(days=10):
            raise RuntimeError("provider history is stale at frozen close boundary")
        return Evidence(symbol=symbol_name, digits=digits, bars=bars)
    finally:
        client.close()


def _evidence_payload(evidence: Evidence) -> dict[str, Any]:
    return {
        "schema": "qore.ict_turtle_soup_r4.fresh_evidence.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "fresh_relative_to_documented_repo_evidence": True,
        "acquisition_opened_at": ACQUISITION_OPEN.isoformat(),
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
        "source_time_zone": "America/New_York",
        "forex_daily_open_ny": "17:00",
        "forex_h4_opens_ny": list(H4_SOURCE_ANCHORS),
        "symbol": {"symbol_name": evidence.symbol, "digits": evidence.digits},
        "periods": {
            "M5": [
                {
                    "opened_at": bar.opened_at.isoformat(),
                    "closed_at": bar.closed_at.isoformat(),
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "close": str(bar.close),
                }
                for bar in evidence.bars
            ]
        },
        "read_only": True,
    }


def load_evidence(path: Path) -> Evidence:
    payload = json.loads(path.read_text())
    if payload.get("holdout_id") != HOLDOUT_ID:
        raise ValueError("unexpected holdout id")
    symbol = str(payload["symbol"]["symbol_name"])
    digits = int(payload["symbol"]["digits"])
    bars = tuple(
        Bar(
            opened_at=_dt(item["opened_at"]),
            closed_at=_dt(item["closed_at"]),
            open=Decimal(item["open"]),
            high=Decimal(item["high"]),
            low=Decimal(item["low"]),
            close=Decimal(item["close"]),
        )
        for item in payload["periods"]["M5"]
    )
    return Evidence(symbol=symbol, digits=digits, bars=bars)


def _contiguous(bars: tuple[Bar, ...], step: timedelta = M5) -> bool:
    return all(
        left.opened_at + step == right.opened_at
        for left, right in zip(bars, bars[1:], strict=False)
    )


def _source_day(moment: datetime) -> date:
    local = moment.astimezone(NY)
    wall = local.timetz().replace(tzinfo=None)
    if wall >= time(17, 0):
        return local.date()
    return local.date() - timedelta(days=1)


def _source_day_open(day: date) -> datetime:
    return datetime.combine(day, time(17, 0), tzinfo=NY).astimezone(UTC)


def _h4_open_for(moment: datetime) -> datetime:
    local = moment.astimezone(NY)
    day = _source_day(moment)
    base = datetime.combine(day, time(17, 0), tzinfo=NY)
    delta = local - base
    slot = int(delta.total_seconds() // H4.total_seconds())
    return (base + slot * H4).astimezone(UTC)


def _h1_open_for(moment: datetime) -> datetime:
    local = moment.astimezone(NY).replace(
        minute=0, second=0, microsecond=0
    )
    return local.astimezone(UTC)


def _m15_open_for(moment: datetime) -> datetime:
    local = moment.astimezone(NY)
    local = local.replace(
        minute=(local.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    return local.astimezone(UTC)


def _aggregate_complete(
    bars: tuple[Bar, ...],
    *,
    key_fn: Callable[[datetime], datetime],
    expected_count: int,
    duration: timedelta,
) -> tuple[SourceCandle, ...]:
    grouped: dict[datetime, list[Bar]] = defaultdict(list)
    for bar in bars:
        grouped[key_fn(bar.opened_at)].append(bar)
    result: list[SourceCandle] = []
    for opened, raw in sorted(grouped.items()):
        ordered = tuple(sorted(raw, key=lambda item: item.opened_at))
        if len(ordered) != expected_count or not _contiguous(ordered):
            continue
        if (
            ordered[0].opened_at != opened
            or ordered[-1].closed_at != opened + duration
        ):
            continue
        result.append(
            SourceCandle(
                opened_at=opened,
                closed_at=opened + duration,
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
                m5=ordered,
            )
        )
    return tuple(result)


def build_h4(bars: tuple[Bar, ...]) -> tuple[SourceCandle, ...]:
    return _aggregate_complete(
        bars,
        key_fn=_h4_open_for,
        expected_count=48,
        duration=H4,
    )


def build_h1(bars: tuple[Bar, ...]) -> tuple[SourceCandle, ...]:
    return _aggregate_complete(
        bars,
        key_fn=_h1_open_for,
        expected_count=12,
        duration=H1,
    )


def build_m15(bars: tuple[Bar, ...]) -> tuple[SourceCandle, ...]:
    return _aggregate_complete(
        bars,
        key_fn=_m15_open_for,
        expected_count=3,
        duration=M15,
    )


def build_daily(h4: tuple[SourceCandle, ...]) -> tuple[SourceCandle, ...]:
    grouped: dict[date, list[SourceCandle]] = defaultdict(list)
    for bar in h4:
        grouped[_source_day(bar.opened_at)].append(bar)
    result: list[SourceCandle] = []
    for day, raw in sorted(grouped.items()):
        opened = _source_day_open(day)
        ordered = tuple(sorted(raw, key=lambda item: item.opened_at))
        expected = tuple(opened + index * H4 for index in range(6))
        if tuple(item.opened_at for item in ordered) != expected:
            continue
        m5 = tuple(item for candle in ordered for item in candle.m5)
        if len(m5) != 288 or not _contiguous(m5):
            continue
        result.append(
            SourceCandle(
                opened_at=opened,
                closed_at=opened + D1,
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
                m5=m5,
            )
        )
    return tuple(result)


def _opposing(candle: SourceCandle, side: Side) -> bool:
    if candle.close == candle.open:
        return False
    if side is Side.LONG:
        return candle.close < candle.open
    return candle.close > candle.open


def _confirms(
    candle: SourceCandle,
    side: Side,
    threshold: Decimal,
) -> bool:
    if side is Side.LONG:
        return candle.close > threshold
    return candle.close < threshold


def causal_cisd(
    candles: tuple[SourceCandle, ...],
    *,
    side: Side,
    extreme: Decimal,
) -> CISD | None:
    matches = [
        index
        for index, candle in enumerate(candles)
        if (
            candle.low == extreme
            if side is Side.LONG
            else candle.high == extreme
        )
    ]
    if len(matches) != 1:
        return None
    extreme_index = matches[0]
    extreme_candle = candles[extreme_index]
    cursor = (
        extreme_index
        if _opposing(extreme_candle, side)
        else extreme_index - 1
    )
    if cursor < 0 or not _opposing(candles[cursor], side):
        return None
    while cursor > 0 and _opposing(candles[cursor - 1], side):
        cursor -= 1
    threshold = candles[cursor].open
    confirm_index = next(
        (
            index
            for index in range(extreme_index, len(candles))
            if _confirms(candles[index], side, threshold)
        ),
        None,
    )
    if confirm_index is None:
        return None
    return CISD(
        side=side,
        extreme_at=extreme_candle.opened_at,
        series_opened_at=candles[cursor].opened_at,
        confirmed_at=candles[confirm_index].closed_at,
        threshold=threshold,
        protected_swing=extreme,
    )


def daily_biases(
    daily: tuple[SourceCandle, ...],
    h1: tuple[SourceCandle, ...],
) -> tuple[DailyBias, ...]:
    by_day: dict[datetime, tuple[SourceCandle, ...]] = {}
    for d1 in daily:
        by_day[d1.opened_at] = tuple(
            item
            for item in h1
            if d1.opened_at <= item.opened_at < d1.closed_at
        )
    result: list[DailyBias] = []
    for index in range(1, len(daily) - 1):
        c1, c2, c3 = daily[index - 1], daily[index], daily[index + 1]
        if c2.opened_at - c1.opened_at > timedelta(days=4):
            continue
        if c3.opened_at - c2.opened_at > timedelta(days=4):
            continue
        if not EVAL_OPEN <= c3.opened_at < EVAL_CLOSE:
            continue
        bullish = c2.low < c1.low and c2.close > c1.low
        bearish = c2.high > c1.high and c2.close < c1.high
        if bullish == bearish:
            continue
        side = Side.LONG if bullish else Side.SHORT
        cisd = causal_cisd(
            by_day.get(c2.opened_at, ()),
            side=side,
            extreme=c2.low if side is Side.LONG else c2.high,
        )
        if cisd is None or cisd.confirmed_at > c2.closed_at:
            continue
        result.append(
            DailyBias(
                side=side,
                c1_opened_at=c1.opened_at,
                c2_opened_at=c2.opened_at,
                c3_opened_at=c3.opened_at,
                relevant_level=(
                    c1.low if side is Side.LONG else c1.high
                ),
                protected_swing=cisd.protected_swing,
                cisd_at=cisd.confirmed_at,
            )
        )
    return tuple(result)


def _session_bucket(moment: datetime) -> str:
    wall = moment.astimezone(NY).timetz().replace(tzinfo=None)
    if wall >= time(20, 0) or wall < time(2, 0):
        return "asia"
    if time(2, 0) <= wall < time(8, 30):
        return "london"
    if time(8, 30) <= wall < time(16, 0):
        return "new-york"
    return "other"


def _untouched_daily_dol(
    daily: tuple[SourceCandle, ...],
    m5: tuple[Bar, ...],
    *,
    side: Side,
    entry: Decimal,
    entry_at: datetime,
) -> tuple[Decimal, datetime] | None:
    candidates: list[tuple[Decimal, datetime]] = []
    for candle in daily:
        if candle.closed_at > entry_at:
            continue
        level = candle.high if side is Side.LONG else candle.low
        if side is Side.LONG and level <= entry:
            continue
        if side is Side.SHORT and level >= entry:
            continue
        taken = any(
            (
                bar.high >= level
                if side is Side.LONG
                else bar.low <= level
            )
            for bar in m5
            if candle.closed_at <= bar.opened_at < entry_at
        )
        if not taken:
            candidates.append((level, candle.opened_at))
    if not candidates:
        return None
    if side is Side.LONG:
        best_level = min(level for level, _ in candidates)
    else:
        best_level = max(level for level, _ in candidates)
    labels = [
        opened for level, opened in candidates if level == best_level
    ]
    return best_level, min(labels)


def _simulate_until_daily_close(
    bars: tuple[Bar, ...],
    *,
    side: Side,
    entry_at: datetime,
    daily_close: datetime,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[datetime, Decimal, str, Decimal]:
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    path = tuple(
        bar for bar in bars if entry_at <= bar.opened_at < daily_close
    )
    for bar in path:
        if side is Side.LONG:
            if bar.open <= stop:
                return (
                    bar.opened_at,
                    bar.open,
                    "gap-stop",
                    (bar.open - entry) / risk,
                )
            if bar.open >= target:
                return bar.opened_at, target, "gap-target-capped", reward / risk
            stop_touch = bar.low <= stop
            target_touch = bar.high >= target
        else:
            if bar.open >= stop:
                return (
                    bar.opened_at,
                    bar.open,
                    "gap-stop",
                    (entry - bar.open) / risk,
                )
            if bar.open <= target:
                return bar.opened_at, target, "gap-target-capped", reward / risk
            stop_touch = bar.high >= stop
            target_touch = bar.low <= target
        if stop_touch and target_touch:
            return bar.closed_at, stop, "stop-first", Decimal(-1)
        if stop_touch:
            return bar.closed_at, stop, "stop", Decimal(-1)
        if target_touch:
            return bar.closed_at, target, "target", reward / risk
    if not path:
        raise ValueError("empty execution path")
    final = path[-1]
    if side is Side.LONG:
        gross = (final.close - entry) / risk
    else:
        gross = (entry - final.close) / risk
    return final.closed_at, final.close, "daily-c3-close", gross


def replay_symbol(
    evidence: Evidence,
) -> tuple[list[Trade], Counter[str]]:
    h4 = build_h4(evidence.bars)
    h1 = build_h1(evidence.bars)
    m15 = build_m15(evidence.bars)
    daily = build_daily(h4)
    biases = daily_biases(daily, h1)
    h4_by_day: dict[datetime, tuple[SourceCandle, ...]] = {}
    m15_by_h4: dict[datetime, tuple[SourceCandle, ...]] = {}
    daily_by_open = {item.opened_at: item for item in daily}
    for d1 in daily:
        h4_by_day[d1.opened_at] = tuple(
            item
            for item in h4
            if d1.opened_at <= item.opened_at < d1.closed_at
        )
    for candle in h4:
        m15_by_h4[candle.opened_at] = tuple(
            item
            for item in m15
            if candle.opened_at <= item.opened_at < candle.closed_at
        )

    funnel: Counter[str] = Counter()
    trades: list[Trade] = []
    tick = Decimal(1).scaleb(-evidence.digits)
    for bias in biases:
        funnel["daily-ideal-c2"] += 1
        d3 = daily_by_open.get(bias.c3_opened_at)
        if d3 is None:
            funnel["missing-daily-c3"] += 1
            continue
        intraday = h4_by_day.get(d3.opened_at, ())
        traded = False
        for index in range(1, len(intraday) - 1):
            c1 = intraday[index - 1]
            c2 = intraday[index]
            c3 = intraday[index + 1]
            if bias.side is Side.LONG:
                running_extreme = min(
                    item.low for item in intraday[:index]
                )
                relevant = c1.low == running_extreme
                closure = (
                    c2.low < c1.low and c2.close > c1.low
                )
                extreme = c2.low
            else:
                running_extreme = max(
                    item.high for item in intraday[:index]
                )
                relevant = c1.high == running_extreme
                closure = (
                    c2.high > c1.high and c2.close < c1.high
                )
                extreme = c2.high
            if not relevant:
                funnel["h4-c1-not-relevant-current-extreme"] += 1
                continue
            if not closure:
                funnel["no-h4-c2-reversal"] += 1
                continue
            funnel["h4-c2-reversal"] += 1
            cisd = causal_cisd(
                m15_by_h4.get(c2.opened_at, ()),
                side=bias.side,
                extreme=extreme,
            )
            if cisd is None or cisd.confirmed_at > c2.closed_at:
                funnel["no-causal-m15-cisd"] += 1
                continue
            funnel["h4-ideal-c2"] += 1
            entry = c3.open
            if bias.side is Side.LONG:
                stop = cisd.protected_swing - tick
            else:
                stop = cisd.protected_swing + tick
            if bias.side is Side.LONG and entry <= stop:
                funnel["entry-through-protected-swing"] += 1
                continue
            if bias.side is Side.SHORT and entry >= stop:
                funnel["entry-through-protected-swing"] += 1
                continue
            dol = _untouched_daily_dol(
                daily,
                evidence.bars,
                side=bias.side,
                entry=entry,
                entry_at=c3.opened_at,
            )
            if dol is None:
                funnel["no-primary-daily-dol"] += 1
                continue
            target, target_opened_at = dol
            if bias.side is Side.LONG and entry >= target:
                funnel["entry-through-dol"] += 1
                continue
            if bias.side is Side.SHORT and entry <= target:
                funnel["entry-through-dol"] += 1
                continue
            risk = (
                entry - stop
                if bias.side is Side.LONG
                else stop - entry
            )
            reward = (
                target - entry
                if bias.side is Side.LONG
                else entry - target
            )
            if risk <= 0 or reward <= 0:
                funnel["invalid-geometry"] += 1
                continue
            exit_at, exit_price, reason, gross_r = (
                _simulate_until_daily_close(
                    evidence.bars,
                    side=bias.side,
                    entry_at=c3.opened_at,
                    daily_close=d3.closed_at,
                    entry=entry,
                    stop=stop,
                    target=target,
                )
            )
            trades.append(
                Trade(
                    symbol=evidence.symbol,
                    side=bias.side,
                    daily_c2_opened_at=bias.c2_opened_at,
                    daily_c3_opened_at=bias.c3_opened_at,
                    h4_c1_opened_at=c1.opened_at,
                    h4_c2_opened_at=c2.opened_at,
                    cisd_at=cisd.confirmed_at,
                    entry_at=c3.opened_at,
                    exit_at=exit_at,
                    protected_swing=cisd.protected_swing,
                    entry=entry,
                    stop=stop,
                    target=target,
                    exit_price=exit_price,
                    projected_r=reward / risk,
                    gross_r=gross_r,
                    primary_net_r=gross_r - PRIMARY_FRICTION_R,
                    stress_net_r=gross_r - STRESS_FRICTION_R,
                    exit_reason=reason,
                    session_bucket=_session_bucket(c2.opened_at),
                    primary_dol_opened_at=target_opened_at,
                )
            )
            funnel["trade"] += 1
            traded = True
            break
        if not traded:
            funnel["daily-c3-no-trade"] += 1
    return trades, funnel


def legacy_r3_comparator_count(evidence: Evidence) -> int:
    """Count legacy R3-like signals on the same fresh evidence; diagnostic only."""
    grouped: dict[tuple[date, int], list[Bar]] = defaultdict(list)
    for bar in evidence.bars:
        local = bar.opened_at.astimezone(NY)
        grouped[(local.date(), (local.hour // 4) * 4)].append(bar)
    old_h4: list[SourceCandle] = []
    for _, raw in sorted(grouped.items()):
        ordered = tuple(sorted(raw, key=lambda item: item.opened_at))
        if len(ordered) != 48 or not _contiguous(ordered):
            continue
        old_h4.append(
            SourceCandle(
                opened_at=ordered[0].opened_at,
                closed_at=ordered[-1].closed_at,
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
                m5=ordered,
            )
        )
    count = 0
    for index in range(3, len(old_h4) - 1):
        window = old_h4[index - 3 : index]
        c1 = old_h4[index - 1]
        c2 = old_h4[index]
        if not EVAL_OPEN <= c2.opened_at < EVAL_CLOSE:
            continue
        bullish = (
            c1.low == min(item.low for item in window)
            and c2.low < c1.low
            and c2.close > c1.low
        )
        bearish = (
            c1.high == max(item.high for item in window)
            and c2.high > c1.high
            and c2.close < c1.high
        )
        if bullish == bearish:
            continue
        side = Side.LONG if bullish else Side.SHORT
        m15s = _aggregate_complete(
            c2.m5,
            key_fn=_m15_open_for,
            expected_count=3,
            duration=M15,
        )
        cisd = causal_cisd(
            m15s,
            side=side,
            extreme=c2.low if side is Side.LONG else c2.high,
        )
        if cisd is not None:
            count += 1
    return count


def _profit_factor(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    if losses == 0:
        return None
    return gains / losses


def _max_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def _summary(trades: list[Trade]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: (item.entry_at, item.symbol))
    gross = [item.gross_r for item in ordered]
    primary = [item.primary_net_r for item in ordered]
    stress = [item.stress_net_r for item in ordered]
    gross_pf = _profit_factor(gross)
    primary_pf = _profit_factor(primary)
    stress_pf = _profit_factor(stress)
    return {
        "trades": len(ordered),
        "gross_wins": sum(item > 0 for item in gross),
        "gross_losses": sum(item < 0 for item in gross),
        "gross_total_r": str(sum(gross, Decimal(0))),
        "gross_mean_r": (
            None
            if not gross
            else str(sum(gross, Decimal(0)) / len(gross))
        ),
        "gross_pf": None if gross_pf is None else str(gross_pf),
        "primary_total_r": str(sum(primary, Decimal(0))),
        "primary_mean_r": (
            None
            if not primary
            else str(sum(primary, Decimal(0)) / len(primary))
        ),
        "primary_pf": None if primary_pf is None else str(primary_pf),
        "primary_max_drawdown_r": str(_max_drawdown(primary)),
        "stress_total_r": str(sum(stress, Decimal(0))),
        "stress_pf": None if stress_pf is None else str(stress_pf),
    }


def _json_trade(trade: Trade) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in asdict(trade).items():
        if isinstance(value, Decimal):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, StrEnum):
            result[key] = value.value
        else:
            result[key] = value
    return result


def replay_to_dir(evidence_path: Path, output: Path) -> dict[str, Any]:
    evidence = load_evidence(evidence_path)
    trades, funnel = replay_symbol(evidence)
    comparator = legacy_r3_comparator_count(evidence)
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "qore.ict_turtle_soup_r4.market_result.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "symbol": evidence.symbol,
        "evidence_status": "FRESH_RELATIVE_TO_DOCUMENTED_REPO_EVIDENCE",
        "fresh_window_open": EVAL_OPEN.isoformat(),
        "fresh_window_close": EVAL_CLOSE.isoformat(),
        "session_filter_applied": False,
        "asia_london_new_york_all_eligible": True,
        "minimum_projected_r_gate": None,
        "r4": _summary(trades),
        "legacy_r3_same_window_signal_count": comparator,
        "signal_count_difference_r4_minus_r3": len(trades) - comparator,
        "funnel": dict(sorted(funnel.items())),
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "trades.json").write_text(
        json.dumps(
            [_json_trade(trade) for trade in trades],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return payload


def aggregate_results(paths: list[Path], output: Path) -> dict[str, Any]:
    reports = [json.loads(path.read_text()) for path in paths]
    if {item["symbol"] for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("aggregate requires exact seven-symbol scope")
    all_trades: list[dict[str, Any]] = []
    r3_count = 0
    for path, report in zip(paths, reports, strict=True):
        r3_count += int(report["legacy_r3_same_window_signal_count"])
        all_trades.extend(
            json.loads((path.parent / "trades.json").read_text())
        )
    all_trades.sort(key=lambda item: (item["entry_at"], item["symbol"]))
    gross = [Decimal(item["gross_r"]) for item in all_trades]
    primary = [Decimal(item["primary_net_r"]) for item in all_trades]
    stress = [Decimal(item["stress_net_r"]) for item in all_trades]
    gross_pf = _profit_factor(gross)
    primary_pf = _profit_factor(primary)
    stress_pf = _profit_factor(stress)
    payload = {
        "schema": "qore.ict_turtle_soup_r4.aggregate.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "symbols": sorted(EXPECTED_SYMBOLS),
        "fresh_relative_to_documented_repo_evidence": True,
        "trade_count": len(all_trades),
        "legacy_r3_same_window_signal_count": r3_count,
        "signal_count_difference_r4_minus_r3": len(all_trades) - r3_count,
        "gross_total_r": str(sum(gross, Decimal(0))),
        "gross_mean_r": (
            None
            if not gross
            else str(sum(gross, Decimal(0)) / len(gross))
        ),
        "gross_pf": None if gross_pf is None else str(gross_pf),
        "primary_total_r": str(sum(primary, Decimal(0))),
        "primary_mean_r": (
            None
            if not primary
            else str(sum(primary, Decimal(0)) / len(primary))
        ),
        "primary_pf": None if primary_pf is None else str(primary_pf),
        "primary_max_drawdown_r": str(_max_drawdown(primary)),
        "stress_total_r": str(sum(stress, Decimal(0))),
        "stress_pf": None if stress_pf is None else str(stress_pf),
        "by_symbol": {
            report["symbol"]: report["r4"]
            for report in sorted(reports, key=lambda item: item["symbol"])
        },
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "aggregate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "trades.json").write_text(
        json.dumps(all_trades, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: module collect SYMBOL OUTPUT | replay EVIDENCE OUTPUT_DIR | "
            "aggregate OUTPUT_DIR REPORT..."
        )
    command = sys.argv[1]
    if command == "collect":
        if len(sys.argv) != 4:
            raise SystemExit("collect SYMBOL OUTPUT")
        symbol = sys.argv[2]
        if symbol not in EXPECTED_SYMBOLS:
            raise SystemExit("symbol outside frozen scope")
        evidence = _collect_m5(symbol)
        Path(sys.argv[3]).write_text(
            json.dumps(
                _evidence_payload(evidence),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        return
    if command == "replay":
        if len(sys.argv) != 4:
            raise SystemExit("replay EVIDENCE OUTPUT_DIR")
        result = replay_to_dir(Path(sys.argv[2]), Path(sys.argv[3]))
        print(json.dumps(result, sort_keys=True))
        return
    if command == "aggregate":
        if len(sys.argv) < 5:
            raise SystemExit("aggregate OUTPUT_DIR REPORT...")
        result = aggregate_results(
            [Path(item) for item in sys.argv[3:]],
            Path(sys.argv[2]),
        )
        print(json.dumps(result, sort_keys=True))
        return
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
