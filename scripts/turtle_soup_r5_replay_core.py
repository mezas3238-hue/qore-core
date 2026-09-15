"""Causal evidence resolver for the Turtle Soup Classic R5 research replay."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

OOS_START = datetime(2026, 3, 1, tzinfo=UTC)
MARKETS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "GBPJPY", "AUDJPY")


def decimal(value: object) -> Decimal:
    return Decimal(str(value))


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(slots=True)
class State:
    swept: bool = False
    extreme: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Fill:
    side: str
    entry: Decimal
    trigger: Decimal
    stop: Decimal
    fill_at: datetime
    source_session: datetime
    resolution: str


@dataclass(frozen=True, slots=True)
class Evaluation:
    market: str
    session: datetime
    side: str
    status: str
    fill: Fill | None
    context: tuple[object, ...] | None


def _bar(row: dict[str, object]) -> Bar:
    return Bar(
        timestamp(row["opened_at"]),
        timestamp(row["closed_at"]),
        decimal(row["open"]),
        decimal(row["high"]),
        decimal(row["low"]),
        decimal(row["close"]),
    )


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    if value.get("fresh_oos_consumed") is not False:
        raise ValueError(f"fresh OOS governance violation: {path}")
    return value


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{key} must be a list of objects")
    return value


class Market:
    def __init__(self, root: Path, symbol: str) -> None:
        self.symbol = symbol
        d1 = _read(root / "d1" / symbol / "d1-evidence.json")
        self.tick_size = Decimal(10) ** -int(d1["symbol_digits"])
        self.d1 = tuple(
            _bar(row)
            for row in _rows(d1, "bars")
            if timestamp(row["opened_at"]) < OOS_START
        )
        m15 = _read(root / "m15" / symbol / "m15-evidence.json")
        self.m15 = tuple(
            _bar(row)
            for row in _rows(m15, "bars")
            if timestamp(row["opened_at"]) < OOS_START
        )
        self.m15_by_open = {bar.opened_at: bar for bar in self.m15}
        self.m1 = self._m1(root / "m1" / symbol / "m1-evidence.json")
        self.ticks, self.tick_counts, self.provenance = self._ticks(root / "ticks", symbol)

    @staticmethod
    def _m1(path: Path) -> dict[datetime, tuple[Bar, ...]]:
        payload = _read(path)
        result: dict[datetime, tuple[Bar, ...]] = {}
        for session in _rows(payload, "sessions"):
            opened_at = timestamp(session["opened_at"])
            if opened_at >= OOS_START:
                continue
            bars = session.get("bars")
            if not isinstance(bars, list) or not all(isinstance(item, dict) for item in bars):
                raise ValueError("M1 bars must be objects")
            result[opened_at] = tuple(_bar(item) for item in bars)
        return result

    @staticmethod
    def _ticks(
        root: Path, symbol: str
    ) -> tuple[
        dict[tuple[datetime, str], tuple[str, dict[str, object]]],
        Counter[str],
        dict[str, dict[str, object]],
    ]:
        result: dict[tuple[datetime, str], tuple[str, dict[str, object]]] = {}
        counts: Counter[str] = Counter()
        provenance: dict[str, dict[str, object]] = {}
        for wave in ("wave1", "wave1b", "wave2"):
            path = root / wave / symbol / "tick-evidence.json"
            if not path.exists():
                continue
            payload = _read(path)
            if payload.get("research_identity") != "turtle-soup-candidate-r5":
                raise ValueError("unexpected R5 identity")
            if payload.get("quote_type") != "BID":
                raise ValueError("R5 replay requires BID ticks")
            provenance[wave] = {
                "software_sha": payload.get("software_sha"),
                "manifest_digest": payload.get("target_manifest_digest_sha256"),
                "evidence_digest": payload.get("evidence_digest_sha256"),
            }
            for row in _rows(payload, "minutes"):
                side = row.get("side")
                if side not in {"long", "short"}:
                    raise ValueError("invalid tick side")
                key = (timestamp(row["minute_opened_at"]), side)
                if key in result:
                    raise ValueError(f"duplicate tick target {symbol} {key}")
                result[key] = (wave, row)
                counts[wave] += 1
        return result, counts, provenance

    def m15_session(self, source: Bar) -> tuple[Bar, ...] | None:
        current = source.opened_at
        bars: list[Bar] = []
        while current < source.closed_at:
            bar = self.m15_by_open.get(current)
            if bar is None:
                break
            bars.append(bar)
            current = bar.closed_at
        if not bars:
            return None
        aggregate = (
            bars[0].open,
            max(x.high for x in bars),
            min(x.low for x in bars),
            bars[-1].close,
        )
        expected = (source.open, source.high, source.low, source.close)
        return tuple(bars) if aggregate == expected else None

    def m1_subbars(self, session: datetime, source: Bar) -> tuple[Bar, ...] | None:
        bars = self.m1.get(session)
        if bars is None:
            return None
        by_open = {bar.opened_at: bar for bar in bars}
        current = source.opened_at
        output: list[Bar] = []
        while current < source.closed_at:
            bar = by_open.get(current)
            if bar is None:
                return None
            output.append(bar)
            current = bar.closed_at
        if current != source.closed_at or not output:
            return None
        aggregate = (
            output[0].open,
            max(x.high for x in output),
            min(x.low for x in output),
            output[-1].close,
        )
        expected = (source.open, source.high, source.low, source.close)
        return tuple(output) if aggregate == expected else None


def _reference(history: tuple[Bar, ...], side: str) -> tuple[Decimal | None, int | None]:
    window = history[-20:]
    prices = tuple(x.low if side == "long" else x.high for x in window)
    reference = min(prices) if side == "long" else max(prices)
    matches = tuple(index for index, price in enumerate(prices) if price == reference)
    if len(matches) != 1:
        return None, None
    absolute_index = len(history) - 20 + matches[0]
    return reference, len(history) - absolute_index


def process_bar(
    bar: Bar,
    side: str,
    reference: Decimal,
    trigger: Decimal,
    state: State,
    tick_size: Decimal,
) -> tuple[str, State, tuple[Decimal, Decimal, datetime, str] | None]:
    current = State(state.swept, state.extreme)
    if side == "long":
        sweep = bar.low < reference
        if not current.swept and sweep and bar.high >= trigger:
            return "ambiguous", current, None
        if not current.swept and sweep:
            return "continue", State(True, bar.low), None
        if current.swept:
            if current.extreme is None:
                raise AssertionError("lost LONG extreme")
            if bar.open >= trigger:
                return (
                    "fill", current,
                    (bar.open, current.extreme - tick_size, bar.opened_at, "open"),
                )
            if bar.high >= trigger:
                if bar.low < current.extreme:
                    return "ambiguous", current, None
                return (
                    "fill", current,
                    (trigger, current.extreme - tick_size, bar.opened_at, "trigger"),
                )
            current.extreme = min(current.extreme, bar.low)
        return "continue", current, None
    sweep = bar.high > reference
    if not current.swept and sweep and bar.low <= trigger:
        return "ambiguous", current, None
    if not current.swept and sweep:
        return "continue", State(True, bar.high), None
    if current.swept:
        if current.extreme is None:
            raise AssertionError("lost SHORT extreme")
        if bar.open <= trigger:
            return (
                "fill", current,
                (bar.open, current.extreme + tick_size, bar.opened_at, "open"),
            )
        if bar.low <= trigger:
            if bar.high > current.extreme:
                return "ambiguous", current, None
            return (
                "fill", current,
                (trigger, current.extreme + tick_size, bar.opened_at, "trigger"),
            )
        current.extreme = max(current.extreme, bar.high)
    return "continue", current, None


def tick_rows(record: dict[str, object]) -> list[dict[str, object]]:
    value = record.get("ticks")
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("tick rows must be objects")
    return value


def process_ticks(
    bar: Bar,
    record: dict[str, object],
    side: str,
    reference: Decimal,
    trigger: Decimal,
    state: State,
    tick_size: Decimal,
) -> tuple[str, State, tuple[Decimal, Decimal, datetime, str] | None]:
    rows = tick_rows(record)
    if not rows:
        return "irreconcilable", state, None
    prices = [bar.open, *(decimal(row["price"]) for row in rows)]
    if max(prices) != bar.high or min(prices) != bar.low or prices[-1] != bar.close:
        return "irreconcilable", state, None
    previous: int | None = None
    for row in rows:
        current_timestamp = row.get("timestamp_ms")
        if not isinstance(current_timestamp, int):
            return "irreconcilable", state, None
        if previous is not None and current_timestamp <= previous:
            status = "equal-timestamp" if current_timestamp == previous else "irreconcilable"
            return status, state, None
        previous = current_timestamp
    current = State(state.swept, state.extreme)
    sequence = [(bar.opened_at, bar.open, "open")]
    sequence.extend((timestamp(row["timestamp"]), decimal(row["price"]), "tick") for row in rows)
    for observed_at, price, kind in sequence:
        if side == "long":
            if not current.swept:
                if price < reference:
                    current = State(True, price)
                continue
            if current.extreme is None:
                raise AssertionError("lost LONG tick extreme")
            current.extreme = min(current.extreme, price)
            if price >= trigger:
                return "fill", current, (price, current.extreme - tick_size, observed_at, kind)
        else:
            if not current.swept:
                if price > reference:
                    current = State(True, price)
                continue
            if current.extreme is None:
                raise AssertionError("lost SHORT tick extreme")
            current.extreme = max(current.extreme, price)
            if price <= trigger:
                return "fill", current, (price, current.extreme + tick_size, observed_at, kind)
    return "continue", current, None


def evaluate(market: Market, index: int, side: str, use_ticks: bool) -> Evaluation:
    session = market.d1[index]
    history = market.d1[:index]
    if len(history) < 20:
        return Evaluation(market.symbol, session.opened_at, side, "insufficient", None, None)
    reference, age = _reference(history, side)
    if reference is None or age is None:
        return Evaluation(market.symbol, session.opened_at, side, "reference-tie", None, None)
    if age < 4:
        return Evaluation(
            market.symbol, session.opened_at, side, "reference-too-recent", None, None
        )
    path = market.m15_session(session)
    if path is None:
        return Evaluation(
            market.symbol, session.opened_at, side, "m15-data-unavailable", None, None
        )
    trigger = (
        reference + 5 * market.tick_size
        if side == "long"
        else reference - 5 * market.tick_size
    )
    state = State()
    for m15_index, m15_bar in enumerate(path):
        status, next_state, fill_data = process_bar(
            m15_bar, side, reference, trigger, state, market.tick_size
        )
        if status == "continue":
            state = next_state
            continue
        if status == "fill" and fill_data is not None:
            fill = Fill(
                side, fill_data[0], trigger, fill_data[1], fill_data[2],
                session.opened_at, "M15",
            )
            return Evaluation(
                market.symbol, session.opened_at, side, "fill", fill,
                (path, m15_index, m15_bar, fill_data[3]),
            )
        subbars = market.m1_subbars(session.opened_at, m15_bar)
        if subbars is None:
            return Evaluation(
                market.symbol, session.opened_at, side, "m1-data-unavailable", None, (m15_bar,)
            )
        local = State(state.swept, state.extreme)
        for m1_index, m1_bar in enumerate(subbars):
            m1_status, m1_state, m1_fill = process_bar(
                m1_bar, side, reference, trigger, local, market.tick_size
            )
            if m1_status == "continue":
                local = m1_state
                continue
            if m1_status == "fill" and m1_fill is not None:
                fill = Fill(
                    side, m1_fill[0], trigger, m1_fill[1], m1_fill[2],
                    session.opened_at, "M1",
                )
                return Evaluation(
                    market.symbol, session.opened_at, side, "fill", fill,
                    (path, m15_index, m15_bar, m1_fill[3], subbars, m1_index, m1_bar),
                )
            if not use_ticks:
                return Evaluation(
                    market.symbol, session.opened_at, side, "m1-ambiguous", None, (m15_bar, m1_bar)
                )
            target = market.ticks.get((m1_bar.opened_at, side))
            if target is None:
                return Evaluation(
                    market.symbol, session.opened_at, side, "tick-missing-wave", None,
                    (m15_bar, m1_bar),
                )
            wave, record = target
            tick_status, tick_state, tick_fill = process_ticks(
                m1_bar, record, side, reference, trigger, local, market.tick_size
            )
            if tick_status == "continue":
                local = tick_state
                continue
            if tick_status == "fill" and tick_fill is not None:
                fill = Fill(
                    side, tick_fill[0], trigger, tick_fill[1], tick_fill[2],
                    session.opened_at, f"TICK:{wave}",
                )
                return Evaluation(
                    market.symbol, session.opened_at, side, "fill", fill,
                    (path, m15_index, m15_bar, tick_fill[3], subbars, m1_index, m1_bar, record),
                )
            return Evaluation(
                market.symbol, session.opened_at, side, f"tick-{tick_status}", None,
                (m15_bar, m1_bar, record),
            )
        state = local
    status = "no-entry" if state.swept else "no-breakout"
    return Evaluation(market.symbol, session.opened_at, side, status, None, None)


def run_census(
    markets: dict[str, Market], use_ticks: bool
) -> tuple[list[Evaluation], list[tuple[Evaluation, Market, int]]]:
    evaluations: list[Evaluation] = []
    fills: list[tuple[Evaluation, Market, int]] = []
    for symbol in MARKETS:
        market = markets[symbol]
        for index, session in enumerate(market.d1):
            if session.opened_at >= OOS_START:
                continue
            for side in ("long", "short"):
                result = evaluate(market, index, side, use_ticks)
                evaluations.append(result)
                if result.fill is not None:
                    fills.append((result, market, index))
    return evaluations, fills
