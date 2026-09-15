"""Frozen experimental Classic re-entry replay for Turtle Soup R6.

R6 deliberately layers one preregistered QORE_EXPERIMENTAL_REENTRY mechanic on
R5.  It does not claim that underdetermined re-entry state mechanics are canonical
Connors/Raschke rules and it never opens fresh OOS.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from turtle_soup_r5_economics import (
    POLICIES,
    Trade,
    bar_stop,
    metrics,
    policy_report,
    replay,
)
from turtle_soup_r5_replay_core import (
    MARKETS,
    OOS_START,
    Bar,
    Evaluation,
    Fill,
    Market,
    State,
    decimal,
    process_bar,
    run_census,
    tick_rows,
    timestamp,
)

R6_IDENTITY = "turtle-soup-candidate-r6-reentry-exp1"


@dataclass(frozen=True, slots=True)
class StopPoint:
    day_offset: int
    level: str
    m15_index: int
    m1_index: int | None
    tick_index: int | None
    stop_price: Decimal
    reason: str
    bar: Bar
    record: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class ReentryResolution:
    status: str
    evaluation: Evaluation | None
    source_index: int | None
    stop_day_offset: int | None


def serialize(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def digest(value: object) -> str:
    raw = json.dumps(
        value,
        default=serialize,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return sha256(raw).hexdigest()


def stop_hit(side: str, stop: Decimal, price: Decimal) -> bool:
    return price <= stop if side == "long" else price >= stop


def trigger_hit(side: str, trigger: Decimal, bar: Bar) -> bool:
    return bar.high >= trigger if side == "long" else bar.low <= trigger


def adverse_extreme(side: str, current: Decimal, bar: Bar) -> Decimal:
    return min(current, bar.low) if side == "long" else max(current, bar.high)


def exact_m1(market: Market, session: datetime, m15: Bar) -> tuple[Bar, ...] | None:
    return market.m1_subbars(session, m15)


def tick_record(market: Market, minute: datetime, side: str) -> dict[str, object] | None:
    target = market.ticks.get((minute, side))
    return None if target is None else target[1]


def tick_sequence(bar: Bar, record: dict[str, object]) -> list[tuple[datetime, Decimal]] | None:
    rows = tick_rows(record)
    if not rows:
        return None
    prices = [bar.open, *(decimal(row["price"]) for row in rows)]
    if max(prices) != bar.high or min(prices) != bar.low or prices[-1] != bar.close:
        return None
    previous: int | None = None
    output = [(bar.opened_at, bar.open)]
    for row in rows:
        stamp = row.get("timestamp_ms")
        if not isinstance(stamp, int):
            return None
        if previous is not None and stamp <= previous:
            return None
        previous = stamp
        output.append((timestamp(row["timestamp"]), decimal(row["price"])))
    return output


def fill_from_data(
    *,
    original: Fill,
    source_session: datetime,
    resolution: str,
    fill_data: tuple[Decimal, Decimal, datetime, str],
+) -> Fill:
    return Fill(
        original.side,
        fill_data[0],
        original.trigger,
        fill_data[1],
        fill_data[2],
        source_session,
        resolution,
    )


def locate_day1_stop(result: Evaluation) -> StopPoint | None:
    if result.fill is None or result.context is None:
        raise ValueError("R6 requires deterministic R5 fill context")
    fill = result.fill
    context = result.context
    path, m15_index, current_m15, mode = context[:4]
    if not isinstance(path, tuple) or not isinstance(m15_index, int) or not isinstance(current_m15, Bar):
        raise ValueError("invalid R5 context")
    if not isinstance(mode, str):
        raise ValueError("invalid R5 fill mode")

    if fill.resolution.startswith("TICK:"):
        subbars, m1_index, m1_bar, record = context[4:8]
        if not isinstance(subbars, tuple) or not isinstance(m1_index, int):
            raise ValueError("invalid tick context")
        if not isinstance(m1_bar, Bar) or not isinstance(record, dict):
            raise ValueError("invalid tick evidence")
        rows = tick_rows(record)
        started = fill.fill_at == m1_bar.opened_at
        for tick_index, row in enumerate(rows):
            observed_at = timestamp(row["timestamp"])
            price = decimal(row["price"])
            if not started:
                if observed_at < fill.fill_at:
                    continue
                started = True
                if observed_at == fill.fill_at and price == fill.entry:
                    continue
            if stop_hit(fill.side, fill.stop, price):
                return StopPoint(
                    0,
                    "tick",
                    m15_index,
                    m1_index,
                    tick_index,
                    price,
                    "gap-stop" if price != fill.stop else "stop",
                    m1_bar,
                    record,
                )
        for local_index, bar in enumerate(subbars[m1_index + 1 :], start=m1_index + 1):
            if not isinstance(bar, Bar):
                raise ValueError("invalid M1 bar")
            price, reason = bar_stop(fill.side, fill.stop, bar)
            if price is not None and reason is not None:
                return StopPoint(0, "m1", m15_index, local_index, None, price, reason, bar, None)
        start_m15 = m15_index + 1
    elif fill.resolution == "M1":
        subbars, m1_index, m1_bar = context[4:7]
        if not isinstance(subbars, tuple) or not isinstance(m1_index, int) or not isinstance(m1_bar, Bar):
            raise ValueError("invalid M1 context")
        if mode == "open":
            price, reason = bar_stop(fill.side, fill.stop, m1_bar)
            if price is not None and reason is not None:
                return StopPoint(0, "m1", m15_index, m1_index, None, price, reason, m1_bar, None)
        for local_index, bar in enumerate(subbars[m1_index + 1 :], start=m1_index + 1):
            if not isinstance(bar, Bar):
                raise ValueError("invalid M1 bar")
            price, reason = bar_stop(fill.side, fill.stop, bar)
            if price is not None and reason is not None:
                return StopPoint(0, "m1", m15_index, local_index, None, price, reason, bar, None)
        start_m15 = m15_index + 1
    else:
        if mode == "open":
            price, reason = bar_stop(fill.side, fill.stop, current_m15)
            if price is not None and reason is not None:
                return StopPoint(0, "m15", m15_index, None, None, price, reason, current_m15, None)
        start_m15 = m15_index + 1

    for local_index, bar in enumerate(path[start_m15:], start=start_m15):
        if not isinstance(bar, Bar):
            raise ValueError("invalid M15 bar")
        price, reason = bar_stop(fill.side, fill.stop, bar)
        if price is not None and reason is not None:
            return StopPoint(0, "m15", local_index, None, None, price, reason, bar, None)
    return None


def locate_day2_stop(market: Market, source_index: int, fill: Fill) -> StopPoint | None:
    day2_index = source_index + 1
    if day2_index >= len(market.d1):
        return None
    day2 = market.d1[day2_index]
    if day2.opened_at >= OOS_START:
        return None
    path = market.m15_session(day2)
    if path is None:
        return None
    for m15_index, bar in enumerate(path):
        price, reason = bar_stop(fill.side, fill.stop, bar)
        if price is not None and reason is not None:
            return StopPoint(1, "m15", m15_index, None, None, price, reason, bar, None)
    return None


def ticks_stop_then_reentry(
    *,
    market: Market,
    session: Bar,
    m15_path: tuple[Bar, ...],
    m15_index: int,
    m1_path: tuple[Bar, ...],
    m1_index: int,
    bar: Bar,
    record: dict[str, object],
    original: Fill,
    initial_after_stop: State | None,
+) -> tuple[str, State | None, Evaluation | None]:
    sequence = tick_sequence(bar, record)
    if sequence is None:
        return "tick-irreconcilable", initial_after_stop, None
    after_stop = initial_after_stop
    for observed_at, price in sequence:
        if after_stop is None:
            if not stop_hit(original.side, original.stop, price):
                continue
            after_stop = State(True, price)
            continue
        if after_stop.extreme is None:
            raise AssertionError("lost R6 adverse extreme")
        if original.side == "long":
            after_stop.extreme = min(after_stop.extreme, price)
            if price >= original.trigger:
                fill_data = (price, after_stop.extreme - market.tick_size, observed_at, "tick")
                fill = fill_from_data(
                    original=original,
                    source_session=session.opened_at,
                    resolution="TICK:R6",
                    fill_data=fill_data,
                )
                context = (m15_path, m15_index, m15_path[m15_index], "tick", m1_path, m1_index, bar, record)
                return "fill", after_stop, Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context)
        else:
            after_stop.extreme = max(after_stop.extreme, price)
            if price <= original.trigger:
                fill_data = (price, after_stop.extreme + market.tick_size, observed_at, "tick")
                fill = fill_from_data(
                    original=original,
                    source_session=session.opened_at,
                    resolution="TICK:R6",
                    fill_data=fill_data,
                )
                context = (m15_path, m15_index, m15_path[m15_index], "tick", m1_path, m1_index, bar, record)
                return "fill", after_stop, Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context)
    return ("continue" if after_stop is not None else "stop-not-reproduced"), after_stop, None


def m1_stop_then_reentry(
    *,
    market: Market,
    session: Bar,
    m15_path: tuple[Bar, ...],
    m15_index: int,
    m1_path: tuple[Bar, ...],
    original: Fill,
    state: State | None,
    start_m1: int = 0,
+) -> tuple[str, State | None, Evaluation | None]:
    current = state
    for m1_index, bar in enumerate(m1_path[start_m1:], start=start_m1):
        if current is None:
            stop_price, stop_reason = bar_stop(original.side, original.stop, bar)
            if stop_price is None or stop_reason is None:
                continue
            if trigger_hit(original.side, original.trigger, bar) and stop_reason == "stop":
                record = tick_record(market, bar.opened_at, original.side)
                if record is None:
                    return "reentry-ambiguous", None, None
                return ticks_stop_then_reentry(
                    market=market,
                    session=session,
                    m15_path=m15_path,
                    m15_index=m15_index,
                    m1_path=m1_path,
                    m1_index=m1_index,
                    bar=bar,
                    record=record,
                    original=original,
                    initial_after_stop=None,
                )
            current = State(True, stop_price)
            if stop_reason == "stop":
                current.extreme = adverse_extreme(original.side, stop_price, bar)
                continue
        if current is None:
            raise AssertionError("R6 stop state lost")
        status, next_state, fill_data = process_bar(
            bar,
            original.side,
            original.trigger,
            original.trigger,
            current,
            market.tick_size,
        )
        if status == "continue":
            current = next_state
            continue
        if status == "ambiguous":
            record = tick_record(market, bar.opened_at, original.side)
            if record is None:
                return "reentry-ambiguous", current, None
            return ticks_stop_then_reentry(
                market=market,
                session=session,
                m15_path=m15_path,
                m15_index=m15_index,
                m1_path=m1_path,
                m1_index=m1_index,
                bar=bar,
                record=record,
                original=original,
                initial_after_stop=current,
            )
        if status == "fill" and fill_data is not None:
            fill = fill_from_data(
                original=original,
                source_session=session.opened_at,
                resolution="M1:R6",
                fill_data=fill_data,
            )
            context = (m15_path, m15_index, m15_path[m15_index], fill_data[3], m1_path, m1_index, bar)
            return "fill", next_state, Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context)
        raise AssertionError(f"unexpected M1 R6 state {status}")
    return "continue", current, None


def m15_after_stop(
    *,
    market: Market,
    session: Bar,
    path: tuple[Bar, ...],
    original: Fill,
    state: State,
    start_m15: int,
+) -> tuple[str, State, Evaluation | None]:
    current = state
    for m15_index, bar in enumerate(path[start_m15:], start=start_m15):
        status, next_state, fill_data = process_bar(
            bar,
            original.side,
            original.trigger,
            original.trigger,
            current,
            market.tick_size,
        )
        if status == "continue":
            current = next_state
            continue
        if status == "ambiguous":
            subbars = exact_m1(market, session.opened_at, bar)
            if subbars is None:
                return "reentry-ambiguous", current, None
            refined_status, refined_state, evaluation = m1_stop_then_reentry(
                market=market,
                session=session,
                m15_path=path,
                m15_index=m15_index,
                m1_path=subbars,
                original=original,
                state=current,
            )
            if refined_status == "continue" and refined_state is not None:
                current = refined_state
                continue
            return refined_status, refined_state or current, evaluation
        if status == "fill" and fill_data is not None:
            fill = fill_from_data(
                original=original,
                source_session=session.opened_at,
                resolution="M15:R6",
                fill_data=fill_data,
            )
            context = (path, m15_index, bar, fill_data[3])
            return "fill", next_state, Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context)
        raise AssertionError(f"unexpected M15 R6 state {status}")
    return "continue", current, None


def day2_from_state(
    market: Market,
    source_index: int,
    original: Fill,
    state: State,
+) -> tuple[str, State, Evaluation | None, int | None]:
    day2_index = source_index + 1
    if day2_index >= len(market.d1):
        return "reentry-data-unavailable", state, None, None
    session = market.d1[day2_index]
    if session.opened_at >= OOS_START:
        return "reentry-oos-embargo", state, None, None
    path = market.m15_session(session)
    if path is None:
        return "reentry-data-unavailable", state, None, None
    status, next_state, evaluation = m15_after_stop(
        market=market,
        session=session,
        path=path,
        original=original,
        state=state,
        start_m15=0,
    )
    return status, next_state, evaluation, day2_index


def resolve_from_day2_stop(
    market: Market,
    source_index: int,
    original: Fill,
    point: StopPoint,
+) -> ReentryResolution:
    day2_index = source_index + 1
    session = market.d1[day2_index]
    path = market.m15_session(session)
    if path is None:
        return ReentryResolution("reentry-data-unavailable", None, None, 1)
    bar = path[point.m15_index]
    state = State(True, point.stop_price)
    if point.reason == "stop" and trigger_hit(original.side, original.trigger, bar):
        subbars = exact_m1(market, session.opened_at, bar)
        if subbars is None:
            return ReentryResolution("reentry-ambiguous", None, None, 1)
        status, next_state, evaluation = m1_stop_then_reentry(
            market=market,
            session=session,
            m15_path=path,
            m15_index=point.m15_index,
            m1_path=subbars,
            original=original,
            state=None,
        )
        if status == "fill":
            return ReentryResolution(status, evaluation, day2_index, 1)
        if status != "continue" or next_state is None:
            return ReentryResolution(status, None, None, 1)
        state = next_state
    elif point.reason == "stop":
        state.extreme = adverse_extreme(original.side, point.stop_price, bar)
    else:
        status, next_state, evaluation = m15_after_stop(
            market=market,
            session=session,
            path=(bar,),
            original=original,
            state=state,
            start_m15=0,
        )
        if status == "fill":
            return ReentryResolution(status, evaluation, day2_index, 1)
        if status != "continue":
            return ReentryResolution(status, None, None, 1)
        state = next_state
    status, _, evaluation = m15_after_stop(
        market=market,
        session=session,
        path=path,
        original=original,
        state=state,
        start_m15=point.m15_index + 1,
    )
    return ReentryResolution(
        "expired" if status == "continue" else status,
        evaluation,
        day2_index if evaluation is not None else None,
        1,
    )


def resolve_reentry(market: Market, result: Evaluation, source_index: int) -> ReentryResolution:
    if result.fill is None:
        raise ValueError("R6 requires R5 source fill")
    original = result.fill
    day1_stop = locate_day1_stop(result)
    if day1_stop is None:
        day2_stop = locate_day2_stop(market, source_index, original)
        if day2_stop is None:
            return ReentryResolution("not-eligible-no-day1-day2-stop", None, None, None)
        return resolve_from_day2_stop(market, source_index, original, day2_stop)

    session = market.d1[source_index]
    path = market.m15_session(session)
    if path is None:
        return ReentryResolution("reentry-data-unavailable", None, None, 0)
    state = State(True, day1_stop.stop_price)

    if day1_stop.level == "tick":
        if day1_stop.record is None or day1_stop.tick_index is None or day1_stop.m1_index is None:
            raise ValueError("invalid tick stop point")
        subbars = exact_m1(market, session.opened_at, path[day1_stop.m15_index])
        if subbars is None:
            return ReentryResolution("reentry-data-unavailable", None, None, 0)
        sequence = tick_sequence(day1_stop.bar, day1_stop.record)
        if sequence is None:
            return ReentryResolution("tick-irreconcilable", None, None, 0)
        stop_seen = False
        for observed_at, price in sequence:
            if not stop_seen:
                if observed_at < day1_stop.bar.opened_at:
                    continue
                if stop_hit(original.side, original.stop, price):
                    stop_seen = True
                    state = State(True, price)
                continue
            if state.extreme is None:
                raise AssertionError("lost R6 tick state")
            state.extreme = min(state.extreme, price) if original.side == "long" else max(state.extreme, price)
            if (original.side == "long" and price >= original.trigger) or (
                original.side == "short" and price <= original.trigger
            ):
                stop = state.extreme - market.tick_size if original.side == "long" else state.extreme + market.tick_size
                fill = Fill(original.side, price, original.trigger, stop, observed_at, session.opened_at, "TICK:R6")
                context = (
                    path,
                    day1_stop.m15_index,
                    path[day1_stop.m15_index],
                    "tick",
                    subbars,
                    day1_stop.m1_index,
                    day1_stop.bar,
                    day1_stop.record,
                )
                evaluation = Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context)
                return ReentryResolution("fill", evaluation, source_index, 0)
        status, next_state, evaluation = m1_stop_then_reentry(
            market=market,
            session=session,
            m15_path=path,
            m15_index=day1_stop.m15_index,
            m1_path=subbars,
            original=original,
            state=state,
            start_m1=day1_stop.m1_index + 1,
        )
        if status == "fill":
            return ReentryResolution(status, evaluation, source_index, 0)
        if status != "continue" or next_state is None:
            return ReentryResolution(status, None, None, 0)
        state = next_state
        start_m15 = day1_stop.m15_index + 1
    elif day1_stop.level == "m1":
        subbars = exact_m1(market, session.opened_at, path[day1_stop.m15_index])
        if subbars is None or day1_stop.m1_index is None:
            return ReentryResolution("reentry-data-unavailable", None, None, 0)
        bar = subbars[day1_stop.m1_index]
        if day1_stop.reason == "stop" and trigger_hit(original.side, original.trigger, bar):
            record = tick_record(market, bar.opened_at, original.side)
            if record is None:
                return ReentryResolution("reentry-ambiguous", None, None, 0)
            status, next_state, evaluation = ticks_stop_then_reentry(
                market=market,
                session=session,
                m15_path=path,
                m15_index=day1_stop.m15_index,
                m1_path=subbars,
                m1_index=day1_stop.m1_index,
                bar=bar,
                record=record,
                original=original,
                initial_after_stop=None,
            )
            if status == "fill":
                return ReentryResolution(status, evaluation, source_index, 0)
            if status != "continue" or next_state is None:
                return ReentryResolution(status, None, None, 0)
            state = next_state
        elif day1_stop.reason == "stop":
            state.extreme = adverse_extreme(original.side, day1_stop.stop_price, bar)
        else:
            status, next_state, evaluation = m1_stop_then_reentry(
                market=market,
                session=session,
                m15_path=path,
                m15_index=day1_stop.m15_index,
                m1_path=(bar,),
                original=original,
                state=state,
            )
            if status == "fill":
                return ReentryResolution(status, evaluation, source_index, 0)
            if status != "continue" or next_state is None:
                return ReentryResolution(status, None, None, 0)
            state = next_state
        status, next_state, evaluation = m1_stop_then_reentry(
            market=market,
            session=session,
            m15_path=path,
            m15_index=day1_stop.m15_index,
            m1_path=subbars,
            original=original,
            state=state,
            start_m1=day1_stop.m1_index + 1,
        )
        if status == "fill":
            return ReentryResolution(status, evaluation, source_index, 0)
        if status != "continue" or next_state is None:
            return ReentryResolution(status, None, None, 0)
        state = next_state
        start_m15 = day1_stop.m15_index + 1
    else:
        bar = path[day1_stop.m15_index]
        if day1_stop.reason == "stop" and trigger_hit(original.side, original.trigger, bar):
            subbars = exact_m1(market, session.opened_at, bar)
            if subbars is None:
                return ReentryResolution("reentry-ambiguous", None, None, 0)
            status, next_state, evaluation = m1_stop_then_reentry(
                market=market,
                session=session,
                m15_path=path,
                m15_index=day1_stop.m15_index,
                m1_path=subbars,
                original=original,
                state=None,
            )
            if status == "fill":
                return ReentryResolution(status, evaluation, source_index, 0)
            if status != "continue" or next_state is None:
                return ReentryResolution(status, None, None, 0)
            state = next_state
        elif day1_stop.reason == "stop":
            state.extreme = adverse_extreme(original.side, day1_stop.stop_price, bar)
        else:
            status, next_state, evaluation = m15_after_stop(
                market=market,
                session=session,
                path=(bar,),
                original=original,
                state=state,
                start_m15=0,
            )
            if status == "fill":
                return ReentryResolution(status, evaluation, source_index, 0)
            if status != "continue":
                return ReentryResolution(status, None, None, 0)
            state = next_state
        start_m15 = day1_stop.m15_index + 1

    status, next_state, evaluation = m15_after_stop(
        market=market,
        session=session,
        path=path,
        original=original,
        state=state,
        start_m15=start_m15,
    )
    if status == "fill":
        return ReentryResolution(status, evaluation, source_index, 0)
    if status != "continue":
        return ReentryResolution(status, None, None, 0)
    status, _, evaluation, reentry_source_index = day2_from_state(
        market, source_index, original, next_state
    )
    return ReentryResolution(
        "expired" if status == "continue" else status,
        evaluation,
        reentry_source_index if evaluation is not None else None,
        0,
    )


def opportunity_metrics(
    first: list[Trade],
    second: list[Trade],
) -> dict[str, object]:
    values: list[Decimal] = []
    by_key: dict[tuple[str, str, datetime], Decimal] = {}
    for trade in first + second:
        if not isinstance(trade.net_1bp_r, Decimal):
            continue
        key = (trade.market, trade.side, trade.fill_at.replace(hour=0, minute=0, second=0, microsecond=0))
        by_key[key] = by_key.get(key, Decimal(0)) + trade.net_1bp_r
    values = list(by_key.values())
    return {
        "realized_opportunities": len(values),
        "total_r": sum(values, Decimal(0)),
        "mean_r": sum(values, Decimal(0)) / len(values) if values else None,
        "positive": sum(value > 0 for value in values),
        "negative": sum(value < 0 for value in values),
    }


def build_report(root: Path, software_sha: str) -> tuple[dict[str, object], dict[str, list[Trade]]]:
    markets = {symbol: Market(root, symbol) for symbol in MARKETS}
    evaluations, fills = run_census(markets, True)
    if len(fills) != 290:
        raise AssertionError(f"R5 source fill census drifted: {len(fills)}")
    unresolved = Counter(item.status for item in evaluations if item.status.startswith("tick-"))
    if unresolved:
        raise AssertionError(f"R5 causal base drifted: {unresolved}")

    resolutions: list[tuple[Evaluation, Market, int, ReentryResolution]] = []
    census: Counter[str] = Counter()
    stop_day: Counter[str] = Counter()
    for evaluation, market, source_index in fills:
        resolved = resolve_reentry(market, evaluation, source_index)
        resolutions.append((evaluation, market, source_index, resolved))
        census[resolved.status] += 1
        if resolved.stop_day_offset is not None:
            stop_day[f"day{resolved.stop_day_offset + 1}"] += 1

    trades_by_policy: dict[str, list[Trade]] = {}
    policies: dict[str, object] = {}
    for policy in POLICIES:
        first_trades: list[Trade] = []
        second_trades: list[Trade] = []
        for evaluation, market, source_index, resolved in resolutions:
            first_trades.append(replay(market, evaluation, source_index, policy))
            if resolved.evaluation is not None and resolved.source_index is not None:
                second_trades.append(
                    replay(market, resolved.evaluation, resolved.source_index, policy)
                )
        attempts = first_trades + second_trades
        trades_by_policy[policy] = attempts
        report = policy_report(attempts)
        report["attempt1"] = metrics(first_trades)
        report["attempt2"] = metrics(second_trades)
        report["opportunity_view"] = opportunity_metrics(first_trades, second_trades)
        report["reentry_fills"] = len(second_trades)
        policies[policy] = report

    passing = [
        policy for policy, report in policies.items()
        if isinstance(report, dict) and report.get("passes_advancement_gate") is True
    ]
    final_verdict = "R6_DEVELOPMENT_GATE_PASS" if passing else "R6_REENTRY_EXPERIMENT_REJECTED"
    report: dict[str, object] = {
        "schema": "qore.trader_lab.turtle_soup_candidate_r6.experimental_reentry.v1",
        "research_identity_root": "turtle-soup-candidate-r1",
        "research_round_identity": R6_IDENTITY,
        "canonical_trader_code": "CODE_UNASSIGNED",
        "source_adjudication": "R6_REENTRY_SOURCE_UNDERDETERMINED",
        "reentry_provenance": "QORE_EXPERIMENTAL_REENTRY",
        "software_sha": software_sha,
        "fresh_oos_consumed": False,
        "fresh_oos_authorized": bool(passing),
        "fresh_oos_embargo_start": OOS_START,
        "r5_source_fills": len(fills),
        "reentry_resolution_census": census,
        "eligible_stop_day_census": stop_day,
        "policies": policies,
        "passing_policies": passing,
        "candidate_freeze": None,
        "final_verdict": final_verdict,
    }
    report["report_digest_sha256"] = digest(report)
    return report, trades_by_policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    args = parser.parse_args()
    report, trades = build_report(args.input_root, args.software_sha)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, default=serialize, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.trades.write_text(
        json.dumps(
            {policy: [asdict(trade) for trade in rows] for policy, rows in trades.items()},
            default=serialize,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "final_verdict": report["final_verdict"],
                "passing_policies": report["passing_policies"],
                "reentry_resolution_census": report["reentry_resolution_census"],
                "report_digest_sha256": report["report_digest_sha256"],
            },
            default=serialize,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
