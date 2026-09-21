"""Order-Block penetration intelligence for QORE Capitalizer Stop Intelligence.

The purpose of this lab is to measure how far price penetrates the validated M1 Order Block
after entry, and specifically how far price travels beyond the distal Order Block extreme
before either reaching the unchanged target or exhausting the session.

This is offline diagnostic evidence. It does not select entries, move live stops, or authorize
a buffer. It separates four post-entry path classes:

- OB_HELD_TARGET: target reached without trading beyond the distal OB extreme.
- OB_OVERSHOOT_THEN_TARGET: price traded beyond the OB and later reached target.
  This is breathing evidence, not an automatic buffer authorization.
- OB_BREAK_NO_TARGET: price traded beyond the OB and target never arrived in-session.
  Widening is rejected as a default; entry/thesis failure remains a candidate explanation.
- OB_HELD_NO_TARGET: target failed without an OB break; stop is not isolated as root cause.

Provider-native M1 clones retain quote digits but not a historical broker tick-size series.
Therefore this lab reports:
- exact price distance;
- provider quote increments = 10^-digits;
- FX pips where the conventional pip size is unambiguous;
- R-normalized distance.

For NAS100 and XAUUSD, no synthetic "pip" or broker tick is invented.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_CAPITALIZER_OB_PENETRATION_INTELLIGENCE_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_OB_PENETRATION_MATRIX_V1"
SOURCE_REPLAY_IDENTITY = "QORE_CAPITALIZER_NATIVE_M1_ENTRY_REPLAY_V1"
EXPECTED_M1_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
EXPECTED_M1_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
PRICE_SCALE = Decimal(100_000)
NEW_YORK = ZoneInfo("America/New_York")
FX_SYMBOLS = frozenset(
    {
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "USDCAD",
        "USDJPY",
    }
)
OVERSHOOT_R_BANDS: tuple[tuple[str, Decimal, Decimal | None], ...] = (
    ("0_TO_0_25R", Decimal("0"), Decimal("0.25")),
    ("0_25_TO_0_50R", Decimal("0.25"), Decimal("0.50")),
    ("0_50_TO_0_75R", Decimal("0.50"), Decimal("0.75")),
    ("0_75_TO_1_00R", Decimal("0.75"), Decimal("1.00")),
    ("1_00_TO_1_50R", Decimal("1.00"), Decimal("1.50")),
    ("1_50_TO_2_00R", Decimal("1.50"), Decimal("2.00")),
    ("2_00_TO_3_00R", Decimal("2.00"), Decimal("3.00")),
    ("3R_PLUS", Decimal("3.00"), None),
)


@dataclass(frozen=True, slots=True)
class M1Bar:
    symbol: str
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    digits: int

    @property
    def closed_at(self) -> datetime:
        return self.opened_at + timedelta(minutes=1)

    @property
    def provider_increment(self) -> Decimal:
        return Decimal(1).scaleb(-self.digits)


@dataclass(slots=True)
class _PenetrationState:
    row_index: int
    entry_at: datetime
    session_end: datetime
    side: str
    entry: Decimal
    target: Decimal
    ob_low: Decimal
    ob_high: Decimal
    baseline_risk: Decimal
    deepest_adverse_price: Decimal
    max_close_adverse_price: Decimal
    bars_penetrating_ob: int = 0
    bars_beyond_ob: int = 0
    consecutive_bars_beyond_ob: int = 0
    max_consecutive_bars_beyond_ob: int = 0
    first_overshoot_at: datetime | None = None
    max_overshoot_at: datetime | None = None
    target_reached_at: datetime | None = None
    reclaimed_proximal_after_overshoot: bool = False
    same_bar_overshoot_target_ambiguity: bool = False
    completed: bool = False
    provider_increment: Decimal | None = None

    @property
    def proximal(self) -> Decimal:
        return self.ob_high if self.side == "LONG" else self.ob_low

    @property
    def distal(self) -> Decimal:
        return self.ob_low if self.side == "LONG" else self.ob_high

    @property
    def ob_width(self) -> Decimal:
        return self.ob_high - self.ob_low


@dataclass(frozen=True, slots=True)
class CapitalizerOBOvershootBand:
    label: str
    lower_r_inclusive: str
    upper_r_exclusive: str | None
    trades: int
    target_reached_same_session: int
    target_rate: str
    close_outside_ob: int
    close_outside_ob_rate: str
    same_bar_target_ambiguity: int


@dataclass(frozen=True, slots=True)
class CapitalizerOBPenetrationMarketReport:
    identity: str
    symbol: str
    session: str
    source_trade_count: int
    path_classification_counts: tuple[tuple[str, int], ...]
    overshoot_r_bands: tuple[CapitalizerOBOvershootBand, ...]
    overshoot_trades: int
    overshoot_then_target: int
    overshoot_no_target: int
    target_without_overshoot: int
    no_target_ob_held: int
    wick_only_overshoot_then_target: int
    close_outside_ob_then_target: int
    same_bar_overshoot_target_ambiguous: int
    breathing_evidence_rate_all_trades: str
    breathing_evidence_rate_target_trades: str
    no_target_after_overshoot_rate: str
    median_target_case_overshoot_price: str | None
    p75_target_case_overshoot_price: str | None
    p90_target_case_overshoot_price: str | None
    p95_target_case_overshoot_price: str | None
    median_target_case_overshoot_provider_increments: str | None
    p75_target_case_overshoot_provider_increments: str | None
    p90_target_case_overshoot_provider_increments: str | None
    p95_target_case_overshoot_provider_increments: str | None
    median_target_case_overshoot_pips: str | None
    p75_target_case_overshoot_pips: str | None
    p90_target_case_overshoot_pips: str | None
    p95_target_case_overshoot_pips: str | None
    median_target_case_overshoot_r: str | None
    p90_target_case_overshoot_r: str | None
    median_no_target_overshoot_r: str | None
    p90_no_target_overshoot_r: str | None
    provider_quote_increment_definition: str = "10^-digits"
    broker_historical_tick_size_present: bool = False
    fx_pip_definition_applied: bool = True
    buffer_authorized: bool = False
    entry_failure_proven: bool = False
    outcome_used_for_entry_selection: bool = False
    methodology_changed: bool = False
    entry_changed: bool = False
    target_changed: bool = False
    fresh_holdout_claimed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("penetration timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _session_bounds(moment: datetime, session: str) -> tuple[datetime, datetime]:
    local = moment.astimezone(NEW_YORK)
    date = local.date()
    if session == "ASIA":
        if local.timetz().replace(tzinfo=None) < time(2, 0):
            start_date = date - timedelta(days=1)
            end_date = date
        else:
            start_date = date
            end_date = date + timedelta(days=1)
        start = datetime.combine(start_date, time(20, 0), tzinfo=NEW_YORK)
        end = datetime.combine(end_date, time(2, 0), tzinfo=NEW_YORK)
    elif session == "LONDON":
        start = datetime.combine(date, time(2, 0), tzinfo=NEW_YORK)
        end = datetime.combine(date, time(8, 30), tzinfo=NEW_YORK)
    elif session == "NEW_YORK":
        start = datetime.combine(date, time(8, 30), tzinfo=NEW_YORK)
        end = datetime.combine(date, time(16, 0), tzinfo=NEW_YORK)
    else:
        raise ValueError(f"unsupported session: {session}")
    return start.astimezone(UTC), end.astimezone(UTC)


def _price(row: dict[str, Any], field: str, *, digits: int) -> Decimal:
    value = row.get(field)
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be positive provider-relative int")
    return (Decimal(value) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))


def _bar(row: dict[str, Any]) -> M1Bar:
    if row.get("schema") != EXPECTED_M1_SCHEMA:
        raise ValueError("unexpected native-M1 schema")
    if row.get("identity") != EXPECTED_M1_IDENTITY:
        raise ValueError("unexpected native-M1 identity")
    symbol = row.get("canonical_symbol")
    opened = row.get("opened_at")
    digits = row.get("digits")
    if not isinstance(symbol, str) or not isinstance(opened, str) or type(digits) is not int:
        raise ValueError("invalid native-M1 row")
    return M1Bar(
        symbol=symbol,
        opened_at=_aware(opened),
        open=_price(row, "open_relative", digits=digits),
        high=_price(row, "high_relative", digits=digits),
        low=_price(row, "low_relative", digits=digits),
        close=_price(row, "close_relative", digits=digits),
        digits=digits,
    )


def _utc_minute(moment: datetime) -> int:
    return int(moment.timestamp()) // 60


def _row_utc_minute(line: str) -> int:
    marker = '"utc_timestamp_in_minutes": '
    start = line.find(marker)
    if start < 0:
        raise ValueError("native-M1 row missing utc_timestamp_in_minutes")
    start += len(marker)
    comma = line.find(",", start)
    brace = line.find("}", start)
    ends = [position for position in (comma, brace) if position >= 0]
    if not ends:
        raise ValueError("invalid utc_timestamp_in_minutes")
    return int(line[start:min(ends)])


def _iter_relevant_m1(
    root: Path,
    session_intervals: list[tuple[datetime, datetime]],
) -> Iterable[tuple[M1Bar, bool]]:
    intervals = sorted(
        (_utc_minute(start), _utc_minute(end))
        for start, end in set(session_intervals)
    )
    if not intervals:
        raise ValueError("penetration intelligence requires session intervals")
    paths = sorted((root / "RAW_M1_LEDGER").glob("*.jsonl"))
    if not paths:
        raise ValueError("RAW_M1_LEDGER partitions not found")

    interval_index = 0
    last_emitted_interval: int | None = None
    previous: datetime | None = None
    previous_symbol: str | None = None
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                minute = _row_utc_minute(line)
                while interval_index < len(intervals) and minute >= intervals[interval_index][1]:
                    interval_index += 1
                if interval_index >= len(intervals):
                    return
                start_minute, end_minute = intervals[interval_index]
                if minute < start_minute or minute >= end_minute:
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("native-M1 row must be object")
                current = _bar(raw)
                if _utc_minute(current.opened_at) != minute:
                    raise ValueError("native-M1 minute key mismatch")
                if previous is not None and current.opened_at <= previous:
                    raise ValueError("native-M1 chronology must increase")
                if previous_symbol is not None and current.symbol != previous_symbol:
                    raise ValueError("one M1 root must contain one symbol")
                new_interval = last_emitted_interval != interval_index
                previous = current.opened_at
                previous_symbol = current.symbol
                last_emitted_interval = interval_index
                yield current, new_interval


def _one_path(root: Path, pattern: str) -> Path:
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(f"expected exactly one {pattern}, got {len(paths)}")
    return paths[0]


def _load_source(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary_path = _one_path(
        root,
        "capitalizer-*-native-m1-entry-replay-v1.json",
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("identity") != SOURCE_REPLAY_IDENTITY:
        raise ValueError("unexpected native-M1 replay identity")
    if summary.get("entry_timeframe") != "M1_NATIVE":
        raise ValueError("penetration lab requires native-M1 entries")
    if summary.get("methodology_changed") is not False:
        raise ValueError("penetration lab requires unchanged methodology")
    trades_path = _one_path(
        root,
        "capitalizer-*-native-m1-entry-replay-v1-trades.jsonl",
    )
    rows: list[dict[str, Any]] = []
    with trades_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("native-M1 trade row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("penetration lab rejects outcome-selected entries")
            rows.append(raw)
    if len(rows) != int(summary["m1_entries"]):
        raise ValueError("source native-M1 report/trade count mismatch")
    return summary, rows


def _fx_pip_size(symbol: str) -> Decimal | None:
    if symbol not in FX_SYMBOLS:
        return None
    return Decimal("0.01") if symbol.endswith("JPY") else Decimal("0.0001")


def _quantile(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = int(
        (Decimal(len(ordered) - 1) * fraction).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    return ordered[index]


def _decimal_stat(values: list[Decimal], statistic: str) -> str | None:
    if not values:
        return None
    if statistic == "median":
        return str(median(values))
    fractions = {
        "p75": Decimal("0.75"),
        "p90": Decimal("0.90"),
        "p95": Decimal("0.95"),
    }
    value = _quantile(values, fractions[statistic])
    return None if value is None else str(value)


def _adverse_extreme(state: _PenetrationState, bar: M1Bar) -> Decimal:
    return bar.low if state.side == "LONG" else bar.high


def _close_is_beyond_distal(state: _PenetrationState, bar: M1Bar) -> bool:
    if state.side == "LONG":
        return bar.close < state.distal
    return bar.close > state.distal


def _bar_penetrates_ob(state: _PenetrationState, bar: M1Bar) -> bool:
    adverse = _adverse_extreme(state, bar)
    if state.side == "LONG":
        return adverse < state.proximal
    return adverse > state.proximal


def _bar_beyond_ob(state: _PenetrationState, bar: M1Bar) -> bool:
    adverse = _adverse_extreme(state, bar)
    if state.side == "LONG":
        return adverse < state.distal
    return adverse > state.distal


def _target_hit(state: _PenetrationState, bar: M1Bar) -> bool:
    if state.side == "LONG":
        return bar.high >= state.target
    return bar.low <= state.target


def _reclaimed_proximal(state: _PenetrationState, bar: M1Bar) -> bool:
    if state.side == "LONG":
        return bar.close >= state.proximal
    return bar.close <= state.proximal


def _adverse_distance_from_proximal(state: _PenetrationState) -> Decimal:
    if state.side == "LONG":
        return max(Decimal("0"), state.proximal - state.deepest_adverse_price)
    return max(Decimal("0"), state.deepest_adverse_price - state.proximal)


def _close_overshoot_price(state: _PenetrationState) -> Decimal:
    if state.side == "LONG":
        return max(Decimal("0"), state.distal - state.max_close_adverse_price)
    return max(Decimal("0"), state.max_close_adverse_price - state.distal)


def _overshoot_price(state: _PenetrationState) -> Decimal:
    penetration = _adverse_distance_from_proximal(state)
    return max(Decimal("0"), penetration - state.ob_width)


def _update_state(state: _PenetrationState, bar: M1Bar) -> None:
    if state.provider_increment is None:
        state.provider_increment = bar.provider_increment
    elif state.provider_increment != bar.provider_increment:
        raise ValueError("provider quote increment changed inside one trade")

    adverse = _adverse_extreme(state, bar)
    if state.side == "LONG":
        if adverse < state.deepest_adverse_price:
            state.deepest_adverse_price = adverse
            if adverse < state.distal:
                state.max_overshoot_at = bar.closed_at
        state.max_close_adverse_price = min(state.max_close_adverse_price, bar.close)
    else:
        if adverse > state.deepest_adverse_price:
            state.deepest_adverse_price = adverse
            if adverse > state.distal:
                state.max_overshoot_at = bar.closed_at
        state.max_close_adverse_price = max(state.max_close_adverse_price, bar.close)

    if _bar_penetrates_ob(state, bar):
        state.bars_penetrating_ob += 1

    if _bar_beyond_ob(state, bar):
        state.bars_beyond_ob += 1
        state.consecutive_bars_beyond_ob += 1
        state.max_consecutive_bars_beyond_ob = max(
            state.max_consecutive_bars_beyond_ob,
            state.consecutive_bars_beyond_ob,
        )
        if state.first_overshoot_at is None:
            state.first_overshoot_at = bar.closed_at
    else:
        state.consecutive_bars_beyond_ob = 0

    if (
        state.first_overshoot_at is not None
        and not state.reclaimed_proximal_after_overshoot
        and _reclaimed_proximal(state, bar)
    ):
        state.reclaimed_proximal_after_overshoot = True

    if state.target_reached_at is None and _target_hit(state, bar):
        state.target_reached_at = bar.closed_at
        if (
            state.first_overshoot_at is not None
            and state.first_overshoot_at == bar.closed_at
        ):
            state.same_bar_overshoot_target_ambiguity = True
        state.completed = True
    elif bar.closed_at >= state.session_end:
        state.completed = True


def _classify(state: _PenetrationState) -> str:
    overshoot = _overshoot_price(state) > 0
    target = state.target_reached_at is not None
    if overshoot and target:
        if state.same_bar_overshoot_target_ambiguity:
            return "OB_OVERSHOOT_TARGET_SAME_BAR_AMBIGUOUS"
        return "OB_OVERSHOOT_THEN_TARGET"
    if overshoot:
        return "OB_BREAK_NO_TARGET"
    if target:
        return "OB_HELD_TARGET"
    return "OB_HELD_NO_TARGET"


def _enrich_rows(rows: list[dict[str, Any]], m1_root: Path) -> None:
    states: list[_PenetrationState] = []
    starts: dict[datetime, list[int]] = defaultdict(list)
    intervals: list[tuple[datetime, datetime]] = []
    for row_index, row in enumerate(rows):
        entry_at = _aware(str(row["entry_at"]))
        _, session_end = _session_bounds(entry_at, str(row["session"]))
        entry = Decimal(str(row["entry_price"]))
        target = Decimal(str(row["target_price"]))
        ob_low = Decimal(str(row["m1_order_block_low"]))
        ob_high = Decimal(str(row["m1_order_block_high"]))
        baseline_stop = Decimal(str(row["stop_price"]))
        risk = abs(entry - baseline_stop)
        if ob_low >= ob_high or risk <= 0:
            raise ValueError("penetration intelligence requires valid OB and baseline risk")
        state = _PenetrationState(
            row_index=row_index,
            entry_at=entry_at,
            session_end=session_end,
            side=str(row["side"]),
            entry=entry,
            target=target,
            ob_low=ob_low,
            ob_high=ob_high,
            baseline_risk=risk,
            deepest_adverse_price=entry,
            max_close_adverse_price=entry,
        )
        state_index = len(states)
        states.append(state)
        starts[entry_at].append(state_index)
        intervals.append(_session_bounds(entry_at, str(row["session"])))

    active: set[int] = set()
    for bar, new_interval in _iter_relevant_m1(m1_root, intervals):
        if new_interval:
            active.clear()
        for state_index in starts.get(bar.opened_at, ()):
            active.add(state_index)

        completed: list[int] = []
        for state_index in tuple(active):
            state = states[state_index]
            _update_state(state, bar)
            if state.completed:
                completed.append(state_index)
        for state_index in completed:
            active.discard(state_index)

    for state in states:
        if state.provider_increment is None:
            raise ValueError("accepted trade received no provider-native M1 bars")
        row = rows[state.row_index]
        symbol = str(row["symbol"])
        pip_size = _fx_pip_size(symbol)
        penetration_from_proximal = _adverse_distance_from_proximal(state)
        inside_penetration = min(state.ob_width, penetration_from_proximal)
        overshoot = _overshoot_price(state)
        close_overshoot = _close_overshoot_price(state)
        provider_increment = state.provider_increment
        row["ob_proximal_price"] = str(state.proximal)
        row["ob_distal_price"] = str(state.distal)
        row["ob_width_price"] = str(state.ob_width)
        row["provider_quote_increment"] = str(provider_increment)
        row["broker_historical_tick_size_present"] = False
        row["max_ob_penetration_from_proximal_price"] = str(
            penetration_from_proximal
        )
        row["max_ob_penetration_inside_price"] = str(inside_penetration)
        row["max_ob_overshoot_beyond_distal_price"] = str(overshoot)
        row["max_close_overshoot_beyond_distal_price"] = str(close_overshoot)
        row["max_ob_overshoot_provider_increments"] = str(
            overshoot / provider_increment
        )
        row["max_close_overshoot_provider_increments"] = str(
            close_overshoot / provider_increment
        )
        row["max_ob_overshoot_r"] = str(overshoot / state.baseline_risk)
        row["max_ob_penetration_from_proximal_r"] = str(
            penetration_from_proximal / state.baseline_risk
        )
        row["max_ob_overshoot_pips"] = (
            None if pip_size is None else str(overshoot / pip_size)
        )
        row["fx_pip_size"] = None if pip_size is None else str(pip_size)
        row["bars_penetrating_ob"] = state.bars_penetrating_ob
        row["bars_beyond_ob"] = state.bars_beyond_ob
        row["max_consecutive_bars_beyond_ob"] = (
            state.max_consecutive_bars_beyond_ob
        )
        row["first_ob_overshoot_at"] = (
            None
            if state.first_overshoot_at is None
            else state.first_overshoot_at.isoformat()
        )
        row["max_ob_overshoot_at"] = (
            None
            if state.max_overshoot_at is None
            else state.max_overshoot_at.isoformat()
        )
        row["target_reached_same_session"] = state.target_reached_at is not None
        row["target_reached_at_same_session"] = (
            None
            if state.target_reached_at is None
            else state.target_reached_at.isoformat()
        )
        row["target_reached_after_ob_overshoot"] = (
            state.target_reached_at is not None
            and state.first_overshoot_at is not None
            and state.target_reached_at >= state.first_overshoot_at
        )
        row["reclaimed_ob_proximal_after_overshoot"] = (
            state.reclaimed_proximal_after_overshoot
        )
        row["same_bar_overshoot_target_ambiguity"] = (
            state.same_bar_overshoot_target_ambiguity
        )
        row["ob_penetration_path_classification"] = _classify(state)
        row["breathing_buffer_authorized"] = False
        row["entry_failure_proven"] = False
        row["outcome_used_for_entry_selection"] = False


def _overshoot_r_bands(
    rows: list[dict[str, Any]],
) -> tuple[CapitalizerOBOvershootBand, ...]:
    result: list[CapitalizerOBOvershootBand] = []
    for label, lower, upper in OVERSHOOT_R_BANDS:
        selected = [
            row
            for row in rows
            if (value := Decimal(str(row["max_ob_overshoot_r"]))) > 0
            and value >= lower
            and (upper is None or value < upper)
        ]
        targets = sum(bool(row["target_reached_same_session"]) for row in selected)
        closes = sum(
            Decimal(str(row["max_close_overshoot_beyond_distal_price"])) > 0
            for row in selected
        )
        ambiguities = sum(
            bool(row["same_bar_overshoot_target_ambiguity"]) for row in selected
        )
        count = len(selected)
        result.append(
            CapitalizerOBOvershootBand(
                label=label,
                lower_r_inclusive=str(lower),
                upper_r_exclusive=None if upper is None else str(upper),
                trades=count,
                target_reached_same_session=targets,
                target_rate="0" if count == 0 else str(Decimal(targets) / Decimal(count)),
                close_outside_ob=closes,
                close_outside_ob_rate=(
                    "0" if count == 0 else str(Decimal(closes) / Decimal(count))
                ),
                same_bar_target_ambiguity=ambiguities,
            )
        )
    return tuple(result)


def build_market_report(
    source_root: Path,
    m1_root: Path,
) -> tuple[CapitalizerOBPenetrationMarketReport, list[dict[str, Any]]]:
    summary, rows = _load_source(source_root)
    _enrich_rows(rows, m1_root)
    symbol = str(summary["symbol"])
    session = str(summary["session"])
    classes = Counter(
        str(row["ob_penetration_path_classification"]) for row in rows
    )
    overshoot_target_rows = [
        row
        for row in rows
        if row["ob_penetration_path_classification"]
        == "OB_OVERSHOOT_THEN_TARGET"
    ]
    overshoot_no_target_rows = [
        row
        for row in rows
        if row["ob_penetration_path_classification"] == "OB_BREAK_NO_TARGET"
    ]
    ambiguous_rows = [
        row
        for row in rows
        if row["ob_penetration_path_classification"]
        == "OB_OVERSHOOT_TARGET_SAME_BAR_AMBIGUOUS"
    ]
    target_rows = [
        row for row in rows if bool(row["target_reached_same_session"])
    ]
    overshoot_rows = [
        row
        for row in rows
        if Decimal(str(row["max_ob_overshoot_beyond_distal_price"])) > 0
    ]

    target_price = [
        Decimal(str(row["max_ob_overshoot_beyond_distal_price"]))
        for row in overshoot_target_rows
    ]
    target_inc = [
        Decimal(str(row["max_ob_overshoot_provider_increments"]))
        for row in overshoot_target_rows
    ]
    target_pips = [
        Decimal(str(row["max_ob_overshoot_pips"]))
        for row in overshoot_target_rows
        if row["max_ob_overshoot_pips"] is not None
    ]
    target_r = [
        Decimal(str(row["max_ob_overshoot_r"]))
        for row in overshoot_target_rows
    ]
    failure_r = [
        Decimal(str(row["max_ob_overshoot_r"]))
        for row in overshoot_no_target_rows
    ]
    close_target = sum(
        Decimal(str(row["max_close_overshoot_beyond_distal_price"])) > 0
        for row in overshoot_target_rows
    )
    wick_target = len(overshoot_target_rows) - close_target

    report = CapitalizerOBPenetrationMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        source_trade_count=len(rows),
        path_classification_counts=tuple(sorted(classes.items())),
        overshoot_r_bands=_overshoot_r_bands(rows),
        overshoot_trades=len(overshoot_rows),
        overshoot_then_target=len(overshoot_target_rows),
        overshoot_no_target=len(overshoot_no_target_rows),
        target_without_overshoot=classes["OB_HELD_TARGET"],
        no_target_ob_held=classes["OB_HELD_NO_TARGET"],
        wick_only_overshoot_then_target=wick_target,
        close_outside_ob_then_target=close_target,
        same_bar_overshoot_target_ambiguous=len(ambiguous_rows),
        breathing_evidence_rate_all_trades=str(
            Decimal(len(overshoot_target_rows)) / Decimal(len(rows))
        ),
        breathing_evidence_rate_target_trades=(
            "0"
            if not target_rows
            else str(
                Decimal(len(overshoot_target_rows)) / Decimal(len(target_rows))
            )
        ),
        no_target_after_overshoot_rate=(
            "0"
            if not overshoot_rows
            else str(
                Decimal(len(overshoot_no_target_rows))
                / Decimal(len(overshoot_rows))
            )
        ),
        median_target_case_overshoot_price=_decimal_stat(target_price, "median"),
        p75_target_case_overshoot_price=_decimal_stat(target_price, "p75"),
        p90_target_case_overshoot_price=_decimal_stat(target_price, "p90"),
        p95_target_case_overshoot_price=_decimal_stat(target_price, "p95"),
        median_target_case_overshoot_provider_increments=_decimal_stat(
            target_inc,
            "median",
        ),
        p75_target_case_overshoot_provider_increments=_decimal_stat(
            target_inc,
            "p75",
        ),
        p90_target_case_overshoot_provider_increments=_decimal_stat(
            target_inc,
            "p90",
        ),
        p95_target_case_overshoot_provider_increments=_decimal_stat(
            target_inc,
            "p95",
        ),
        median_target_case_overshoot_pips=_decimal_stat(target_pips, "median"),
        p75_target_case_overshoot_pips=_decimal_stat(target_pips, "p75"),
        p90_target_case_overshoot_pips=_decimal_stat(target_pips, "p90"),
        p95_target_case_overshoot_pips=_decimal_stat(target_pips, "p95"),
        median_target_case_overshoot_r=_decimal_stat(target_r, "median"),
        p90_target_case_overshoot_r=_decimal_stat(target_r, "p90"),
        median_no_target_overshoot_r=_decimal_stat(failure_r, "median"),
        p90_no_target_overshoot_r=_decimal_stat(failure_r, "p90"),
    )
    return report, rows


def write_market(
    report: CapitalizerOBPenetrationMarketReport,
    rows: list[dict[str, Any]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = f"capitalizer-{report.symbol.lower()}-ob-penetration-intelligence-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trades.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-ob-penetration-intelligence-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market penetration matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    expected = {
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
    if {str(report["symbol"]) for report in reports} != expected:
        raise ValueError("penetration matrix universe mismatch")
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "source_trade_count": sum(int(report["source_trade_count"]) for report in reports),
        "overshoot_trades": sum(int(report["overshoot_trades"]) for report in reports),
        "overshoot_then_target": sum(
            int(report["overshoot_then_target"]) for report in reports
        ),
        "overshoot_no_target": sum(
            int(report["overshoot_no_target"]) for report in reports
        ),
        "same_bar_overshoot_target_ambiguous": sum(
            int(report["same_bar_overshoot_target_ambiguous"])
            for report in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "provider_quote_increment_definition": "10^-digits",
        "broker_historical_tick_size_present": False,
        "buffer_authorized": False,
        "entry_failure_proven": False,
        "outcome_used_for_entry_selection": False,
        "methodology_changed": False,
        "entry_changed": False,
        "target_changed": False,
        "fresh_holdout_claimed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-ob-penetration-matrix-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("source_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        market_report, rows = build_market_report(args.source_root, args.m1_root)
        write_market(market_report, rows, args.output)
        print(
            json.dumps(
                {
                    "identity": market_report.identity,
                    "symbol": market_report.symbol,
                    "overshoot_then_target": market_report.overshoot_then_target,
                    "overshoot_no_target": market_report.overshoot_no_target,
                    "p90_target_overshoot_increments": (
                        market_report.p90_target_case_overshoot_provider_increments
                    ),
                    "p90_target_overshoot_pips": (
                        market_report.p90_target_case_overshoot_pips
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
