"""Market journey and target atlas for VT-08 Index consumed evidence.

Research-only diagnostics. The atlas reconstructs what price did before and after
frozen V7 signals, including local liquidity sweeps, FVG context, pre-entry
balance/overlap, time-to-expansion, known-boundary interactions, weekday/source-day
range behavior, post-stop afterlife, and cross-index snapshots.

It never changes V7 rules and never treats descriptive structures as automatic
trading rules. Order-block and breaker-block labels remain unresolved until a
source definition is separately frozen.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast
from zoneinfo import ZoneInfo

SCHEMA = "qore.trader_lab.vt08_index_market_journey_atlas.v1"
COMBINED_SCHEMA = "qore.trader_lab.vt08_index_market_journey_atlas.combined.v1"
_NY = ZoneInfo("America/New_York")
R_LEVELS = tuple(
    Decimal(value) for value in ("0.5", "1", "1.5", "2", "2.5", "3", "4", "5")
)
HORIZONS_MINUTES = (240, 480, 1440)


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class SourceDay:
    key: date
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @property
    def range(self) -> Decimal:
        return self.high - self.low


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _median_decimal(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return Decimal(str(median(values)))


def _load_payload(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _load_bars(path: Path, expected_symbol: str) -> tuple[Bar, ...]:
    payload = _load_payload(path)
    symbol = str(payload.get("canonical_symbol", expected_symbol))
    if symbol != expected_symbol:
        raise ValueError(f"expected {expected_symbol}, got {symbol}")
    periods = cast(dict[str, object], payload["periods"])
    raw = cast(list[dict[str, object]], periods["M15"])
    bars = tuple(
        Bar(
            opened_at=_dt(item["opened_at"]),
            closed_at=_dt(item["closed_at"]),
            open=_decimal(item["open"]),
            high=_decimal(item["high"]),
            low=_decimal(item["low"]),
            close=_decimal(item["close"]),
        )
        for item in raw
    )
    return tuple(sorted(bars, key=lambda bar: bar.opened_at))


def _source_day_key(moment: datetime) -> date:
    local = moment.astimezone(_NY)
    return local.date() if local.hour >= 18 else (local.date() - timedelta(days=1))


def _build_source_days(bars: Sequence[Bar]) -> dict[date, SourceDay]:
    grouped: dict[date, list[Bar]] = defaultdict(list)
    for bar in bars:
        grouped[_source_day_key(bar.opened_at)].append(bar)
    result: dict[date, SourceDay] = {}
    for key, items in grouped.items():
        ordered = sorted(items, key=lambda bar: bar.opened_at)
        result[key] = SourceDay(
            key=key,
            opened_at=ordered[0].opened_at,
            closed_at=ordered[-1].closed_at,
            open=ordered[0].open,
            high=max(bar.high for bar in ordered),
            low=min(bar.low for bar in ordered),
            close=ordered[-1].close,
        )
    return result


def _previous_key(keys: Sequence[date], current: date) -> date | None:
    index = bisect_left(keys, current)
    return keys[index - 1] if index > 0 else None


def _bars_between(
    bars: Sequence[Bar],
    opened_times: Sequence[datetime],
    start: datetime,
    end: datetime,
) -> tuple[Bar, ...]:
    left = bisect_left(opened_times, start)
    right = bisect_left(opened_times, end)
    return tuple(bars[left:right])


def _bars_closed_before(
    bars: Sequence[Bar],
    closed_times: Sequence[datetime],
    before: datetime,
    count: int,
) -> tuple[Bar, ...]:
    right = bisect_right(closed_times, before)
    left = max(0, right - count)
    return tuple(bars[left:right])


def _favorable_r(side: str, price: Decimal, entry: Decimal, risk: Decimal) -> Decimal:
    return (price - entry) / risk if side == "long" else (entry - price) / risk


def _adverse_r(side: str, price: Decimal, entry: Decimal, risk: Decimal) -> Decimal:
    return (entry - price) / risk if side == "long" else (price - entry) / risk


def _bar_favorable_r(side: str, bar: Bar, entry: Decimal, risk: Decimal) -> Decimal:
    price = bar.high if side == "long" else bar.low
    return _favorable_r(side, price, entry, risk)


def _bar_adverse_r(side: str, bar: Bar, entry: Decimal, risk: Decimal) -> Decimal:
    price = bar.low if side == "long" else bar.high
    return _adverse_r(side, price, entry, risk)


def _local_sweep_events(
    bars: Sequence[Bar], lookback: int = 4
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index in range(lookback, len(bars)):
        previous = bars[index - lookback : index]
        bar = bars[index]
        prior_high = max(item.high for item in previous)
        prior_low = min(item.low for item in previous)
        if bar.high > prior_high and bar.close < prior_high:
            events.append(
                {
                    "kind": "high-sweep-close-back",
                    "observed_at": bar.closed_at.isoformat(),
                    "level": _fmt(prior_high),
                }
            )
        if bar.low < prior_low and bar.close > prior_low:
            events.append(
                {
                    "kind": "low-sweep-close-back",
                    "observed_at": bar.closed_at.isoformat(),
                    "level": _fmt(prior_low),
                }
            )
    return events


def _fvg_events(bars: Sequence[Bar]) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for index in range(2, len(bars)):
        first = bars[index - 2]
        third = bars[index]
        if third.low > first.high:
            events.append(
                {
                    "kind": "bullish-fvg",
                    "formed_at": third.closed_at.isoformat(),
                    "low": _fmt(first.high),
                    "high": _fmt(third.low),
                }
            )
        if third.high < first.low:
            events.append(
                {
                    "kind": "bearish-fvg",
                    "formed_at": third.closed_at.isoformat(),
                    "low": _fmt(third.high),
                    "high": _fmt(first.low),
                }
            )
    return events


def _pre_entry_behavior(bars: Sequence[Bar]) -> dict[str, object]:
    if not bars:
        return {
            "sample": 0,
            "range": None,
            "net_displacement": None,
            "efficiency": None,
            "balance_score": None,
            "body_flip_count": 0,
            "inside_bar_rate": None,
            "latest_local_sweep": None,
            "latest_fvg": None,
        }
    high = max(bar.high for bar in bars)
    low = min(bar.low for bar in bars)
    span = high - low
    displacement = abs(bars[-1].close - bars[0].open)
    efficiency = displacement / span if span > 0 else Decimal()
    directions = [
        1 if bar.close > bar.open else -1 if bar.close < bar.open else 0
        for bar in bars
    ]
    flips = sum(
        a != 0 and b != 0 and a != b
        for a, b in zip(directions, directions[1:], strict=False)
    )
    inside = 0
    for previous, current in zip(bars, bars[1:], strict=False):
        inside += current.high <= previous.high and current.low >= previous.low
    denominator = max(1, len(bars) - 1)
    sweeps = _local_sweep_events(bars)
    fvgs = _fvg_events(bars)
    return {
        "sample": len(bars),
        "range": _fmt(span),
        "net_displacement": _fmt(displacement),
        "efficiency": _fmt(efficiency),
        "balance_score": _fmt(Decimal(1) - efficiency),
        "body_flip_count": flips,
        "inside_bar_rate": _fmt(Decimal(inside) / Decimal(denominator)),
        "latest_local_sweep": sweeps[-1] if sweeps else None,
        "latest_fvg": fvgs[-1] if fvgs else None,
    }


def _time_to_levels(
    side: str,
    entry: Decimal,
    risk: Decimal,
    signal_at: datetime,
    bars: Sequence[Bar],
) -> dict[str, object]:
    hits: dict[str, object] = {}
    for level in R_LEVELS:
        key = _fmt(level)
        hit: dict[str, object] | None = None
        for bar in bars:
            if _bar_favorable_r(side, bar, entry, risk) >= level:
                hit = {
                    "hit": True,
                    "minutes": int((bar.closed_at - signal_at).total_seconds() // 60),
                    "at": bar.closed_at.isoformat(),
                }
                break
        hits[key] = hit or {"hit": False, "minutes": None, "at": None}
    return hits


def _horizon_excursions(
    side: str,
    entry: Decimal,
    risk: Decimal,
    signal_at: datetime,
    bars: Sequence[Bar],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for minutes in HORIZONS_MINUTES:
        horizon_end = signal_at + timedelta(minutes=minutes)
        subset = [bar for bar in bars if bar.opened_at < horizon_end]
        favorable = max(
            (_bar_favorable_r(side, bar, entry, risk) for bar in subset),
            default=Decimal(),
        )
        adverse = max(
            (_bar_adverse_r(side, bar, entry, risk) for bar in subset),
            default=Decimal(),
        )
        result[str(minutes)] = {
            "max_favorable_r": _fmt(favorable),
            "max_adverse_r": _fmt(adverse),
        }
    return result


def _reaction_before_one_r(
    side: str,
    entry: Decimal,
    risk: Decimal,
    signal_at: datetime,
    bars: Sequence[Bar],
) -> dict[str, object]:
    selected: list[Bar] = []
    reached = False
    for bar in bars:
        selected.append(bar)
        if _bar_favorable_r(side, bar, entry, risk) >= Decimal(1):
            reached = True
            break
        if bar.opened_at >= signal_at + timedelta(hours=4):
            break
    if not selected:
        return {
            "reached_1r": False,
            "max_adverse_r": "0",
            "extreme_at": None,
            "contexts": [],
        }
    extreme = max(
        selected, key=lambda bar: _bar_adverse_r(side, bar, entry, risk)
    )
    context_window = [
        bar
        for bar in selected
        if extreme.opened_at - timedelta(hours=1)
        <= bar.opened_at
        <= extreme.opened_at
    ]
    sweeps = _local_sweep_events(context_window)
    fvgs = _fvg_events(context_window)
    contexts: list[str] = []
    if sweeps:
        contexts.append("local-liquidity-sweep")
    if fvgs:
        contexts.append("fvg-near-reaction")
    if not contexts:
        contexts.append("no-mechanical-structure-detected")
    return {
        "reached_1r": reached,
        "max_adverse_r": _fmt(_bar_adverse_r(side, extreme, entry, risk)),
        "extreme_at": extreme.closed_at.isoformat(),
        "extreme_hour_new_york": extreme.closed_at.astimezone(_NY).hour,
        "contexts": contexts,
    }


def _boundary(
    *,
    name: str,
    level: Decimal | None,
    side: str,
    entry: Decimal,
    risk: Decimal,
    signal_at: datetime,
    bars: Sequence[Bar],
) -> dict[str, object]:
    if level is None:
        return {"name": name, "available": False}
    distance = _favorable_r(side, level, entry, risk)
    if distance <= 0:
        return {
            "name": name,
            "available": True,
            "level": _fmt(level),
            "distance_r": _fmt(distance),
            "directionally_ahead": False,
            "hit": None,
            "minutes": None,
        }
    for bar in bars:
        touched = bar.high >= level if side == "long" else bar.low <= level
        if touched:
            return {
                "name": name,
                "available": True,
                "level": _fmt(level),
                "distance_r": _fmt(distance),
                "directionally_ahead": True,
                "hit": True,
                "minutes": int((bar.closed_at - signal_at).total_seconds() // 60),
                "at": bar.closed_at.isoformat(),
            }
    return {
        "name": name,
        "available": True,
        "level": _fmt(level),
        "distance_r": _fmt(distance),
        "directionally_ahead": True,
        "hit": False,
        "minutes": None,
        "at": None,
    }


def _peer_snapshot(
    signal_at: datetime, states: dict[str, dict[str, object]]
) -> dict[str, object]:
    result: dict[str, object] = {}
    for symbol, state in states.items():
        bars = cast(tuple[Bar, ...], state["bars"])
        closed_times = cast(tuple[datetime, ...], state["closed_times"])
        recent = _bars_closed_before(bars, closed_times, signal_at, 16)
        if not recent:
            result[symbol] = {"available": False}
            continue
        last4 = recent[-4:]
        result[symbol] = {
            "available": True,
            "return_60m": (
                _fmt((last4[-1].close - last4[0].open) / last4[0].open)
                if last4[0].open
                else "0"
            ),
            "return_240m": (
                _fmt((recent[-1].close - recent[0].open) / recent[0].open)
                if recent[0].open
                else "0"
            ),
            "pre_entry_balance_score_4h": _pre_entry_behavior(recent)[
                "balance_score"
            ],
        }
    return result


def _post_stop_afterlife(
    row: dict[str, object],
    side: str,
    entry: Decimal,
    risk: Decimal,
    bars: Sequence[Bar],
    opened_times: Sequence[datetime],
) -> dict[str, object] | None:
    if str(row.get("exit_reason")) != "stop":
        return None
    exited_at = _dt(row["exited_at"])
    subset = _bars_between(
        bars, opened_times, exited_at, exited_at + timedelta(hours=24)
    )
    max_fav = max(
        (_bar_favorable_r(side, bar, entry, risk) for bar in subset),
        default=Decimal(),
    )
    levels: dict[str, object] = {}
    for level in (Decimal("0.5"), Decimal("1"), Decimal("2"), Decimal("3")):
        hit_at = None
        for bar in subset:
            if _bar_favorable_r(side, bar, entry, risk) >= level:
                hit_at = bar.closed_at
                break
        levels[_fmt(level)] = {
            "hit": hit_at is not None,
            "minutes_after_stop": (
                int((hit_at - exited_at).total_seconds() // 60) if hit_at else None
            ),
            "at": hit_at.isoformat() if hit_at else None,
        }
    return {
        "max_favorable_r_24h_from_original_entry": _fmt(max_fav),
        "levels": levels,
    }


def _journey_row(
    row: dict[str, object], states: dict[str, dict[str, object]]
) -> dict[str, object]:
    symbol = str(row["symbol"])
    state = states[symbol]
    bars = cast(tuple[Bar, ...], state["bars"])
    opened_times = cast(tuple[datetime, ...], state["opened_times"])
    closed_times = cast(tuple[datetime, ...], state["closed_times"])
    days = cast(dict[date, SourceDay], state["source_days"])
    day_keys = cast(tuple[date, ...], state["source_day_keys"])

    signal_at = _dt(row["signal_at"])
    entry = _decimal(row["entry"])
    risk = _decimal(row["risk_points"])
    side = str(row["side"]).lower()
    post = _bars_between(
        bars, opened_times, signal_at, signal_at + timedelta(hours=24)
    )
    pre = _bars_closed_before(bars, closed_times, signal_at, 16)
    current_day_key = _source_day_key(signal_at)
    previous_day_key = _previous_key(day_keys, current_day_key)
    previous_day = days.get(previous_day_key) if previous_day_key else None

    h4_opened_at = _dt(row["h4_opened_at"])
    previous_h4_bars = _bars_between(
        bars,
        opened_times,
        h4_opened_at - timedelta(hours=4),
        h4_opened_at,
    )
    previous_h4_high = max((bar.high for bar in previous_h4_bars), default=None)
    previous_h4_low = min((bar.low for bar in previous_h4_bars), default=None)
    directional_prev_h4 = previous_h4_high if side == "long" else previous_h4_low
    directional_prev_day = None
    if previous_day is not None:
        directional_prev_day = previous_day.high if side == "long" else previous_day.low

    local = signal_at.astimezone(_NY)
    return {
        "symbol": symbol,
        "signal_at": signal_at.isoformat(),
        "weekday_new_york": local.strftime("%A"),
        "signal_hour_new_york": local.hour,
        "side": side,
        "anchor_hour_new_york": row["anchor_hour_new_york"],
        "model_kind": row["model_kind"],
        "poi_kind": row["poi_kind"],
        "primary_r": row["primary_r"],
        "raw_r": row["raw_r"],
        "exit_reason": row["exit_reason"],
        "prior_h4_range_regime": row["prior_h4_range_regime"],
        "peer_alignment_count": row["peer_alignment_count"],
        "relative_strength_rank": row["side_adjusted_relative_strength_rank"],
        "pre_entry_4h": _pre_entry_behavior(pre),
        "reaction_before_1r": _reaction_before_one_r(
            side, entry, risk, signal_at, post
        ),
        "time_to_favorable_levels": _time_to_levels(
            side, entry, risk, signal_at, post
        ),
        "horizon_excursions": _horizon_excursions(
            side, entry, risk, signal_at, post
        ),
        "known_directional_boundaries": {
            "previous_h4": _boundary(
                name="previous_h4_directional_extreme",
                level=directional_prev_h4,
                side=side,
                entry=entry,
                risk=risk,
                signal_at=signal_at,
                bars=post,
            ),
            "previous_source_day": _boundary(
                name="previous_source_day_directional_extreme",
                level=directional_prev_day,
                side=side,
                entry=entry,
                risk=risk,
                signal_at=signal_at,
                bars=post,
            ),
        },
        "post_stop_afterlife": _post_stop_afterlife(
            row, side, entry, risk, bars, opened_times
        ),
        "peer_snapshot": _peer_snapshot(signal_at, states),
    }


def _source_day_ledger(
    symbol: str,
    source_days: dict[date, SourceDay],
    start: date,
    end: date,
) -> list[dict[str, object]]:
    keys = sorted(source_days)
    ledger: list[dict[str, object]] = []
    prior_ranges: list[Decimal] = []
    for key in keys:
        day = source_days[key]
        if key < start:
            if day.range > 0:
                prior_ranges.append(day.range)
            continue
        if key >= end:
            break
        baseline_values = prior_ranges[-20:]
        baseline = _median_decimal(baseline_values)
        ratio = day.range / baseline if baseline and baseline > 0 else None
        efficiency = abs(day.close - day.open) / day.range if day.range > 0 else Decimal()
        regime = "unknown"
        if ratio is not None:
            if ratio < Decimal("0.75"):
                regime = "compressed"
            elif ratio > Decimal("1.25"):
                regime = "expanded"
            else:
                regime = "normal"
        trading_day = key + timedelta(days=1)
        ledger.append(
            {
                "symbol": symbol,
                "source_day": key.isoformat(),
                "trading_day": trading_day.isoformat(),
                "weekday": trading_day.strftime("%A"),
                "range": _fmt(day.range),
                "range_ratio_20_median": _fmt(ratio) if ratio is not None else None,
                "directional_efficiency": _fmt(efficiency),
                "regime": regime,
            }
        )
        if day.range > 0:
            prior_ranges.append(day.range)
    return ledger


def _journey_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"sample": 0}
    hit_rates: dict[str, str] = {}
    median_minutes: dict[str, int | None] = {}
    for level in R_LEVELS:
        key = _fmt(level)
        hits = [
            cast(dict[str, object], row["time_to_favorable_levels"])[key]
            for row in rows
        ]
        hit_rates[key] = _fmt(
            Decimal(
                sum(bool(cast(dict[str, object], hit)["hit"]) for hit in hits)
            )
            / Decimal(len(rows))
        )
        minutes = [
            int(str(cast(dict[str, object], hit)["minutes"]))
            for hit in hits
            if cast(dict[str, object], hit)["minutes"] is not None
        ]
        median_minutes[key] = int(median(minutes)) if minutes else None
    stops = [row for row in rows if str(row["exit_reason"]) == "stop"]
    stopped_then_2r = 0
    for row in stops:
        afterlife = cast(dict[str, object] | None, row["post_stop_afterlife"])
        if afterlife is None:
            continue
        levels = cast(dict[str, object], afterlife["levels"])
        if bool(cast(dict[str, object], levels["2"])["hit"]):
            stopped_then_2r += 1
    balances = [
        _decimal(cast(dict[str, object], row["pre_entry_4h"])["balance_score"])
        for row in rows
        if cast(dict[str, object], row["pre_entry_4h"])["balance_score"]
        is not None
    ]
    return {
        "sample": len(rows),
        "stop_rate": _fmt(Decimal(len(stops)) / Decimal(len(rows))),
        "hit_rate_by_r": hit_rates,
        "median_minutes_to_r": median_minutes,
        "median_pre_entry_balance_score": _fmt(
            _median_decimal(balances) or Decimal()
        ),
        "stopped_then_2r_24h_rate": (
            _fmt(Decimal(stopped_then_2r) / Decimal(len(stops))) if stops else "0"
        ),
    }


def _context_summary(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        reaction = cast(dict[str, object], row["reaction_before_1r"])
        contexts = cast(list[str], reaction["contexts"])
        for context in contexts:
            grouped[context].append(row)
    return {
        name: _journey_summary(group) for name, group in sorted(grouped.items())
    }


def _categorical_summary(
    rows: Sequence[dict[str, object]], key: str
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key, "unknown"))].append(row)
    return {
        name: _journey_summary(group) for name, group in sorted(grouped.items())
    }


def _aggregate_rows(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    by_symbol: dict[str, object] = {}
    symbols = sorted({str(row["symbol"]) for row in rows})
    for symbol in symbols:
        items = [row for row in rows if str(row["symbol"]) == symbol]
        weekday: dict[str, object] = {}
        for name in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
            group = [
                row for row in items if str(row["weekday_new_york"]) == name
            ]
            if group:
                weekday[name] = _journey_summary(group)
        by_symbol[symbol] = {
            "overall": _journey_summary(items),
            "weekday": weekday,
            "reaction_context": _context_summary(items),
            "poi": _categorical_summary(items, "poi_kind"),
            "range_regime": _categorical_summary(items, "prior_h4_range_regime"),
        }
    return by_symbol


def _weekday_source_day_summary(
    days: Sequence[dict[str, object]],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in days:
        grouped[str(row["weekday"])].append(row)
    result: dict[str, object] = {}
    for weekday, items in sorted(grouped.items()):
        ratios = [
            _decimal(item["range_ratio_20_median"])
            for item in items
            if item["range_ratio_20_median"] is not None
        ]
        efficiency = [_decimal(item["directional_efficiency"]) for item in items]
        regimes = Counter(str(item["regime"]) for item in items)
        result[weekday] = {
            "sample": len(items),
            "median_range_ratio": _fmt(_median_decimal(ratios) or Decimal()),
            "median_directional_efficiency": _fmt(
                _median_decimal(efficiency) or Decimal()
            ),
            "regime_mix": dict(sorted(regimes.items())),
        }
    return result


def build_window(
    *,
    input_report: Path,
    nas100: Path,
    sp500: Path,
    us30: Path,
) -> dict[str, object]:
    report = _load_payload(input_report)
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    states: dict[str, dict[str, object]] = {}
    for symbol, path in paths.items():
        bars = _load_bars(path, symbol)
        source_days = _build_source_days(bars)
        states[symbol] = {
            "bars": bars,
            "opened_times": tuple(bar.opened_at for bar in bars),
            "closed_times": tuple(bar.closed_at for bar in bars),
            "source_days": source_days,
            "source_day_keys": tuple(sorted(source_days)),
        }
    rows = [
        _journey_row(row, states)
        for row in cast(list[dict[str, object]], report["trades"])
    ]
    partition = cast(dict[str, object], report["partition"])
    start = date.fromisoformat(str(partition["start_date"]))
    end = date.fromisoformat(str(partition["end_date_exclusive"]))
    day_ledger: list[dict[str, object]] = []
    for symbol in sorted(states):
        day_ledger.extend(
            _source_day_ledger(
                symbol,
                cast(dict[date, SourceDay], states[symbol]["source_days"]),
                start,
                end,
            )
        )
    return {
        "schema": SCHEMA,
        "candidate_id": report["candidate_id"],
        "rule_fingerprint": report["rule_fingerprint"],
        "window_id": report["window_id"],
        "partition": partition,
        "trade_count": len(rows),
        "trades": rows,
        "market_summary": _aggregate_rows(rows),
        "source_day_ledger": day_ledger,
        "source_day_weekday_summary": {
            symbol: _weekday_source_day_summary(
                [row for row in day_ledger if str(row["symbol"]) == symbol]
            )
            for symbol in sorted(states)
        },
        "structure_definition_status": {
            "fvg": "mechanically-observable-three-candle-gap-diagnostic",
            "local_liquidity_sweep": (
                "mechanically-observable-four-bar-extreme-run-close-back-diagnostic"
            ),
            "order_block": "UNRESOLVED_SOURCE_DEFINITION_NOT_AUTOMATED",
            "breaker_block": "UNRESOLVED_SOURCE_DEFINITION_NOT_AUTOMATED",
        },
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "changes_v7": False,
            "structures_are_descriptive_not_entry_rules": True,
            "target_atlas_is_descriptive_not_target_selection": True,
            "fresh_validation_required_for_any_new_rule": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def combine(payloads: Sequence[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(
        payloads,
        key=lambda payload: str(
            cast(dict[str, object], payload["partition"])["start_date"]
        ),
    )
    rows = [
        row
        for payload in ordered
        for row in cast(list[dict[str, object]], payload["trades"])
    ]
    days = [
        row
        for payload in ordered
        for row in cast(list[dict[str, object]], payload["source_day_ledger"])
    ]
    return {
        "schema": COMBINED_SCHEMA,
        "candidate_id": ordered[0]["candidate_id"] if ordered else None,
        "rule_fingerprint": ordered[0]["rule_fingerprint"] if ordered else None,
        "windows": [
            {
                "window_id": payload["window_id"],
                "partition": payload["partition"],
                "trade_count": payload["trade_count"],
            }
            for payload in ordered
        ],
        "trade_count": len(rows),
        "trades": rows,
        "market_summary": _aggregate_rows(rows),
        "source_day_weekday_summary": {
            symbol: _weekday_source_day_summary(
                [row for row in days if str(row["symbol"]) == symbol]
            )
            for symbol in sorted({str(row["symbol"]) for row in days})
        },
        "structure_definition_status": (
            ordered[0]["structure_definition_status"] if ordered else {}
        ),
        "governance": ordered[0]["governance"] if ordered else {},
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    window = sub.add_parser("window")
    window.add_argument("--input", type=Path, required=True)
    window.add_argument("--nas100", type=Path, required=True)
    window.add_argument("--sp500", type=Path, required=True)
    window.add_argument("--us30", type=Path, required=True)
    window.add_argument("--out", type=Path, required=True)
    merged = sub.add_parser("combine")
    merged.add_argument("inputs", type=Path, nargs="+")
    merged.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "window":
        result = build_window(
            input_report=args.input,
            nas100=args.nas100,
            sp500=args.sp500,
            us30=args.us30,
        )
    else:
        result = combine([_load_payload(path) for path in args.inputs])
    _write(args.out, result)
    print(
        json.dumps(
            {"schema": result["schema"], "trade_count": result["trade_count"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
