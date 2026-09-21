"""Consumed-evidence causal forensics for QORE Capitalizer native-M1 losses.

This lab does not change, filter, score, or re-run the strategy contract. It joins the
already-consumed 5Y native-M1 holdout ledger to the immutable 10Y provider-native M1
clone and the frozen higher-level candidate ledger, then measures what happened around
accepted entries.

The output is forensic evidence only. It may generate hypotheses, but never promotes a
rule, economic candidate, certification state, or execution authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_FAILURE_MATRIX_V1"
EXPECTED_REPLAY_IDENTITY = "QORE_CAPITALIZER_NATIVE_M1_ENTRY_REPLAY_V1"
EXPECTED_M1_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
EXPECTED_M1_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
PRICE_SCALE = Decimal(100_000)
NEW_YORK = ZoneInfo("America/New_York")

FEATURES = (
    "setup_age_minutes",
    "retest_delay_minutes",
    "planned_reward_r",
    "fvg_width_r",
    "order_block_width_r",
    "ob_fvg_overlap_r",
    "distance_ob_to_mss_r",
    "displacement_body_ratio",
    "displacement_range_vs_prior20",
    "displacement_body_vs_prior20",
    "entry_adverse_excursion_upper_bound_r",
    "entry_range_r",
    "session_elapsed_minutes",
    "session_remaining_minutes",
    "planned_r_per_session_hour_remaining",
    "order_block_candle_count",
)


@dataclass(frozen=True, slots=True)
class M1Bar:
    symbol: str
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @property
    def closed_at(self) -> datetime:
        return self.opened_at + timedelta(minutes=1)

    @property
    def range(self) -> Decimal:
        return self.high - self.low

    @property
    def body(self) -> Decimal:
        return abs(self.close - self.open)



def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("forensic timestamps must be timezone-aware")
    return parsed.astimezone(UTC)



def _price(row: dict[str, Any], field: str, *, digits: int) -> Decimal:
    value = row.get(field)
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be positive provider-relative int")
    return (Decimal(value) / PRICE_SCALE).quantize(Decimal(1).scaleb(-digits))



def _bar(row: dict[str, Any]) -> M1Bar:
    if row.get("schema") != EXPECTED_M1_SCHEMA:
        raise ValueError("unexpected M1 schema")
    if row.get("identity") != EXPECTED_M1_IDENTITY:
        raise ValueError("unexpected M1 identity")
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
    )



def _utc_minute(moment: datetime) -> int:
    return int(moment.timestamp()) // 60


def _row_utc_minute(line: str) -> int:
    marker = '"utc_timestamp_in_minutes": '
    start = line.find(marker)
    if start < 0:
        raise ValueError("raw M1 row missing utc_timestamp_in_minutes")
    start += len(marker)
    comma = line.find(',', start)
    brace = line.find('}', start)
    ends = [position for position in (comma, brace) if position >= 0]
    if not ends:
        raise ValueError("raw M1 row has invalid utc_timestamp_in_minutes")
    return int(line[start:min(ends)])


def _iter_relevant_m1(
    root: Path,
    session_intervals: list[tuple[datetime, datetime]],
) -> Iterable[tuple[M1Bar, bool]]:
    """Stream only M1 bars from sessions that actually contain accepted trades.

    The immutable 10Y clone is large. A cheap minute-key prefilter avoids JSON-decoding
    bars outside the consumed trade sessions while preserving the exact provider-native
    rows used by the replay. `new_interval` is true for the first retained bar of each
    session so rolling M1 context can be reset exactly as the source replay did.
    """

    intervals = sorted(
        (_utc_minute(start), _utc_minute(end))
        for start, end in set(session_intervals)
    )
    if not intervals:
        raise ValueError("M1 forensics require at least one trade session interval")
    for start_minute, end_minute in intervals:
        if end_minute <= start_minute:
            raise ValueError("invalid M1 forensic session interval")

    ledger = root / "RAW_M1_LEDGER"
    paths = sorted(ledger.glob("*.jsonl"))
    if not paths:
        raise ValueError("RAW_M1_LEDGER partitions not found")

    interval_index = 0
    previous: datetime | None = None
    previous_symbol: str | None = None
    last_emitted_interval: int | None = None
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                minute = _row_utc_minute(line)
                while (
                    interval_index < len(intervals)
                    and minute >= intervals[interval_index][1]
                ):
                    interval_index += 1
                if interval_index >= len(intervals):
                    return
                start_minute, end_minute = intervals[interval_index]
                if minute < start_minute or minute >= end_minute:
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("raw M1 row must be object")
                current = _bar(raw)
                if _utc_minute(current.opened_at) != minute:
                    raise ValueError("native-M1 minute key disagrees with opened_at")
                if previous is not None and current.opened_at <= previous:
                    raise ValueError("M1 chronology must be strictly increasing")
                if previous_symbol is not None and current.symbol != previous_symbol:
                    raise ValueError("one M1 forensic root must contain one symbol")
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



def _load_replay(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary_path = _one_path(root, "capitalizer-*-native-m1-entry-replay-v1.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("identity") != EXPECTED_REPLAY_IDENTITY:
        raise ValueError("unexpected native-M1 replay identity")
    if summary.get("entry_timeframe") != "M1_NATIVE":
        raise ValueError("forensics require native M1 entry replay")
    if summary.get("methodology_changed") is not False:
        raise ValueError("forensics require unchanged methodology")
    if summary.get("m1_mss_required") is not True:
        raise ValueError("M1 MSS invariant missing")
    if summary.get("m1_fvg_required") is not True:
        raise ValueError("M1 FVG invariant missing")
    if summary.get("m1_order_block_required") is not True:
        raise ValueError("M1 Order Block invariant missing")
    if summary.get("outcome_aware_selection") is not False:
        raise ValueError("selected replay cannot be outcome-aware")

    trades_path = _one_path(root, "capitalizer-*-native-m1-entry-replay-v1-trades.jsonl")
    trades: list[dict[str, Any]] = []
    with trades_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("trade row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("forensics reject outcome-selected trade rows")
            trades.append(raw)
    if len(trades) != int(summary.get("m1_entries", -1)):
        raise ValueError("replay summary/trade count mismatch")
    if not trades:
        raise ValueError("forensics require accepted native-M1 trades")
    return summary, trades



def _load_higher_source(root: Path) -> dict[str, dict[str, Any]]:
    path = _one_path(root, "capitalizer-*-three-session-replay-cell-v1-trades.jsonl")
    result: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("higher-source row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("higher-source row cannot be outcome-selected")
            signal_at = raw.get("signal_at")
            if not isinstance(signal_at, str):
                raise ValueError("higher-source row missing signal_at")
            if signal_at in result:
                raise ValueError("higher-source signal_at must be unique per market cell")
            result[signal_at] = raw
    if not result:
        raise ValueError("higher-source candidate ledger is empty")
    return result



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
        raise ValueError(f"unsupported Capitalizer session: {session}")
    return start.astimezone(UTC), end.astimezone(UTC)



def _ratio(value: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        raise ValueError("ratio denominator must be positive")
    return value / denominator



def _median(values: list[Decimal]) -> Decimal | None:
    return None if not values else median(values)



def _quantile(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = int((Decimal(len(ordered) - 1) * fraction).to_integral_value(rounding=ROUND_FLOOR))
    return ordered[index]



def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "profit_factor": None,
            "total_r": "0",
            "mean_r": None,
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    ordered = sorted(rows, key=lambda item: _aware(str(item["entry_at"])))
    values = [Decimal(str(item["realized_gross_r"])) for item in ordered]
    gross_profit = sum((value for value in values if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in values if value < 0), Decimal("0"))
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
    return {
        "trades": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "profit_factor": None if gross_loss == 0 else str(gross_profit / gross_loss),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_streak,
    }



def _reconstruct_ob(prior: deque[M1Bar], side: str) -> tuple[int, Decimal | None, Decimal | None]:
    selected: list[M1Bar] = []
    for bar in reversed(prior):
        opposing = bar.close < bar.open if side == "LONG" else bar.close > bar.open
        if not opposing:
            break
        selected.append(bar)
    if not selected:
        return 0, None, None
    return (
        len(selected),
        min(bar.low for bar in selected),
        max(bar.high for bar in selected),
    )



def _decimal_field(row: dict[str, Any], key: str) -> Decimal:
    return Decimal(str(row[key]))



def _prepare_trade(raw: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    entry_at = _aware(str(raw["entry_at"]))
    exit_at = _aware(str(raw["exit_at"]))
    signal_at = _aware(str(raw["higher_setup_signal_at"]))
    displacement_closed_at = _aware(str(raw["m1_displacement_at"]))
    fvg_confirmed_at = _aware(str(raw["m1_fvg_confirmed_at"]))
    session = str(raw["session"])
    session_start, session_end = _session_bounds(entry_at, session)
    entry = _decimal_field(raw, "entry_price")
    stop = _decimal_field(raw, "stop_price")
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("forensic trade requires positive initial risk")
    ob_low = _decimal_field(raw, "m1_order_block_low")
    ob_high = _decimal_field(raw, "m1_order_block_high")
    fvg_low = _decimal_field(raw, "m1_fvg_low")
    fvg_high = _decimal_field(raw, "m1_fvg_high")
    mss = _decimal_field(raw, "m1_mss_level")
    ob_width = ob_high - ob_low
    fvg_width = fvg_high - fvg_low
    overlap = max(Decimal("0"), min(ob_high, fvg_high) - max(ob_low, fvg_low))
    if ob_width <= 0 or fvg_width <= 0:
        raise ValueError("accepted M1 trade must have positive OB/FVG width")
    if str(raw["side"]) == "LONG":
        depth = (ob_high - entry) / ob_width
        ob_proximal = ob_high
    else:
        depth = (entry - ob_low) / ob_width
        ob_proximal = ob_low
    planned = _decimal_field(raw, "planned_reward_r")
    remaining_minutes = Decimal(str((session_end - entry_at).total_seconds() / 60))
    if remaining_minutes <= 0:
        raise ValueError("entry must occur before session end")
    event_labels = source.get("event_labels", [])
    if not isinstance(event_labels, list) or not all(isinstance(item, str) for item in event_labels):
        raise ValueError("higher-source event_labels must be string list")
    return {
        **raw,
        "entry_at": entry_at.isoformat(),
        "exit_at": exit_at.isoformat(),
        "higher_setup_signal_at": signal_at.isoformat(),
        "m1_displacement_at": displacement_closed_at.isoformat(),
        "m1_fvg_confirmed_at": fvg_confirmed_at.isoformat(),
        "setup_age_minutes": int((entry_at - signal_at).total_seconds() // 60),
        "retest_delay_minutes": int((entry_at - fvg_confirmed_at).total_seconds() // 60),
        "displacement_to_entry_minutes": int((entry_at - displacement_closed_at).total_seconds() // 60),
        "risk_price": str(risk),
        "fvg_width_r": str(fvg_width / risk),
        "order_block_width_r": str(ob_width / risk),
        "ob_fvg_overlap_r": str(overlap / risk),
        "entry_depth_within_ob": str(depth),
        "distance_ob_to_mss_r": str(abs(mss - ob_proximal) / risk),
        "session_elapsed_minutes": int((entry_at - session_start).total_seconds() // 60),
        "session_remaining_minutes": int((session_end - entry_at).total_seconds() // 60),
        "planned_r_per_session_hour_remaining": str(planned / (remaining_minutes / Decimal("60"))),
        "source_event_labels": tuple(event_labels),
        "source_strategy_status": source.get("source_strategy_status"),
        "source_entry_probe": source.get("entry_probe"),
        "source_stop_probe": source.get("stop_probe"),
        "source_target_probe": source.get("target_probe"),
        "mfe_r_before_exit": "0",
        "mae_r_before_exit": "0",
        "mfe_target_fraction_before_exit": "0",
        "target_25pct_reached_before_exit": False,
        "target_50pct_reached_before_exit": False,
        "target_75pct_reached_before_exit": False,
        "target_100pct_reached_before_exit": False,
        "displacement_body_ratio": None,
        "displacement_range_vs_prior20": None,
        "displacement_body_vs_prior20": None,
        "displacement_range_r": None,
        "displacement_body_r": None,
        "order_block_candle_count": None,
        "order_block_reconstruction_matches_ledger": None,
        "entry_adverse_excursion_upper_bound_r": None,
        "entry_range_r": None,
        "entry_body_ratio": None,
        "target_reached_after_stop_same_session": False,
        "minutes_stop_to_target_recovery": None,
        "extra_stop_r_needed_for_same_session_target_recovery": None,
        "post_stop_max_favorable_r_before_session_end": None,
        "post_stop_max_adverse_r_before_session_end": None,
        "loss_classification": None,
    }



def _enrich_with_m1(rows: list[dict[str, Any]], m1_root: Path) -> None:
    by_displacement: dict[datetime, list[int]] = defaultdict(list)
    by_entry: dict[datetime, list[int]] = defaultdict(list)
    by_exit: dict[datetime, list[int]] = defaultdict(list)
    by_session_end: dict[datetime, list[int]] = defaultdict(list)
    session_intervals: list[tuple[datetime, datetime]] = []
    for index, row in enumerate(rows):
        trade_entry_at = _aware(str(row["entry_at"]))
        exit_at = _aware(str(row["exit_at"]))
        displacement_open = _aware(str(row["m1_displacement_at"])) - timedelta(minutes=1)
        session_start, session_end = _session_bounds(trade_entry_at, str(row["session"]))
        session_intervals.append((session_start, session_end))
        by_displacement[displacement_open].append(index)
        by_entry[trade_entry_at].append(index)
        if str(row["exit_reason"]) == "STOP":
            by_exit[exit_at].append(index)
            by_session_end[session_end].append(index)


    active: set[int] = set()
    post_stop_active: set[int] = set()
    prior: deque[M1Bar] = deque(maxlen=20)
    lifecycle_starts = by_entry
    lifecycle_ends: dict[datetime, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        lifecycle_ends[_aware(str(row["exit_at"]))].append(index)

    for bar, new_interval in _iter_relevant_m1(m1_root, session_intervals):
        if new_interval:
            prior.clear()
            active.clear()
            post_stop_active.clear()
        at = bar.opened_at
        closed_at = bar.closed_at
        if at in lifecycle_starts:
            active.update(lifecycle_starts[at])
        if at in by_exit:
            post_stop_active.update(by_exit[at])
        if at in by_session_end:
            for index in by_session_end[at]:
                post_stop_active.discard(index)

        if at in by_displacement:
            prior_ranges = [item.range for item in prior if item.range > 0]
            prior_bodies = [item.body for item in prior if item.body > 0]
            med_range = _median(prior_ranges)
            med_body = _median(prior_bodies)
            for index in by_displacement[at]:
                row = rows[index]
                risk = _decimal_field(row, "risk_price")
                body_ratio = Decimal("0") if bar.range == 0 else bar.body / bar.range
                count, ob_low, ob_high = _reconstruct_ob(prior, str(row["side"]))
                row["displacement_body_ratio"] = str(body_ratio)
                row["displacement_range_vs_prior20"] = (
                    None
                    if med_range is None or med_range == Decimal("0")
                    else str(bar.range / med_range)
                )
                row["displacement_body_vs_prior20"] = (
                    None
                    if med_body is None or med_body == Decimal("0")
                    else str(bar.body / med_body)
                )
                row["displacement_range_r"] = str(bar.range / risk)
                row["displacement_body_r"] = str(bar.body / risk)
                row["order_block_candle_count"] = count
                if ob_low is None or ob_high is None:
                    row["order_block_reconstruction_matches_ledger"] = False
                else:
                    row["order_block_reconstruction_matches_ledger"] = (
                        ob_low == _decimal_field(row, "m1_order_block_low")
                        and ob_high == _decimal_field(row, "m1_order_block_high")
                    )

        if at in by_entry:
            for index in by_entry[at]:
                row = rows[index]
                risk = _decimal_field(row, "risk_price")
                entry = _decimal_field(row, "entry_price")
                if str(row["side"]) == "LONG":
                    adverse = max(Decimal("0"), entry - bar.low)
                else:
                    adverse = max(Decimal("0"), bar.high - entry)
                row["entry_adverse_excursion_upper_bound_r"] = str(adverse / risk)
                row["entry_range_r"] = str(bar.range / risk)
                row["entry_body_ratio"] = str(Decimal("0") if bar.range == 0 else bar.body / bar.range)

        for index in tuple(active):
            row = rows[index]
            entry_at = _aware(str(row["entry_at"]))
            exit_at = _aware(str(row["exit_at"]))
            if not (entry_at <= at < exit_at):
                continue
            risk = _decimal_field(row, "risk_price")
            entry = _decimal_field(row, "entry_price")
            if str(row["side"]) == "LONG":
                favorable = max(Decimal("0"), bar.high - entry) / risk
                adverse = max(Decimal("0"), entry - bar.low) / risk
            else:
                favorable = max(Decimal("0"), entry - bar.low) / risk
                adverse = max(Decimal("0"), bar.high - entry) / risk
            row["mfe_r_before_exit"] = str(max(_decimal_field(row, "mfe_r_before_exit"), favorable))
            row["mae_r_before_exit"] = str(max(_decimal_field(row, "mae_r_before_exit"), adverse))

        for index in tuple(post_stop_active):
            row = rows[index]
            _, session_end = _session_bounds(_aware(str(row["entry_at"])), str(row["session"]))
            if not (_aware(str(row["exit_at"])) <= at < session_end):
                continue
            risk = _decimal_field(row, "risk_price")
            entry = _decimal_field(row, "entry_price")
            target = _decimal_field(row, "target_price")
            if str(row["side"]) == "LONG":
                favorable = max(Decimal("0"), bar.high - entry) / risk
                adverse = max(Decimal("0"), entry - bar.low) / risk
                target_hit = bar.high >= target
            else:
                favorable = max(Decimal("0"), entry - bar.low) / risk
                adverse = max(Decimal("0"), bar.high - entry) / risk
                target_hit = bar.low <= target
            prev_fav = row["post_stop_max_favorable_r_before_session_end"]
            prev_adv = row["post_stop_max_adverse_r_before_session_end"]
            max_fav = favorable if prev_fav is None else max(Decimal(str(prev_fav)), favorable)
            max_adv = adverse if prev_adv is None else max(Decimal(str(prev_adv)), adverse)
            row["post_stop_max_favorable_r_before_session_end"] = str(max_fav)
            row["post_stop_max_adverse_r_before_session_end"] = str(max_adv)
            if target_hit and row["target_reached_after_stop_same_session"] is False:
                row["target_reached_after_stop_same_session"] = True
                row["minutes_stop_to_target_recovery"] = int(
                    (bar.closed_at - _aware(str(row["exit_at"]))).total_seconds() // 60
                )
                path_mae = max(_decimal_field(row, "mae_r_before_exit"), max_adv)
                row["extra_stop_r_needed_for_same_session_target_recovery"] = str(
                    max(Decimal("0"), path_mae - Decimal("1"))
                )

        prior.append(bar)
        if closed_at in lifecycle_ends:
            for index in lifecycle_ends[closed_at]:
                active.discard(index)

    for row in rows:
        planned = _decimal_field(row, "planned_reward_r")
        mfe = _decimal_field(row, "mfe_r_before_exit")
        fraction = Decimal("0") if planned <= 0 else mfe / planned
        row["mfe_target_fraction_before_exit"] = str(fraction)
        row["target_25pct_reached_before_exit"] = fraction >= Decimal("0.25")
        row["target_50pct_reached_before_exit"] = fraction >= Decimal("0.50")
        row["target_75pct_reached_before_exit"] = fraction >= Decimal("0.75")
        row["target_100pct_reached_before_exit"] = fraction >= Decimal("1.00")
        realized = _decimal_field(row, "realized_gross_r")
        if realized >= 0:
            row["loss_classification"] = None
        elif bool(row.get("same_minute_stop_target_ambiguity")):
            row["loss_classification"] = "SAME_MINUTE_PRECEDENCE_AMBIGUITY"
        elif str(row["exit_reason"]) == "SESSION_EXIT":
            row["loss_classification"] = "SESSION_LIFECYCLE_CONFLICT"
        elif str(row["exit_reason"]) == "STOP" and bool(row["target_reached_after_stop_same_session"]):
            row["loss_classification"] = "PREMATURE_STOP_EVIDENCE"
        elif str(row["exit_reason"]) == "STOP":
            row["loss_classification"] = "THESIS_INVALIDATED_NO_SAME_SESSION_TARGET_RECOVERY"
        else:
            row["loss_classification"] = "OTHER_CAUSAL_EXIT_FAILURE"



def _cohort_quintiles(rows: list[dict[str, Any]], feature: str) -> list[dict[str, Any]]:
    available = [
        Decimal(str(row[feature]))
        for row in rows
        if row.get(feature) is not None
    ]
    if len(available) < 5:
        return []
    cutoffs = [
        _quantile(available, Decimal("0")),
        _quantile(available, Decimal("0.2")),
        _quantile(available, Decimal("0.4")),
        _quantile(available, Decimal("0.6")),
        _quantile(available, Decimal("0.8")),
        _quantile(available, Decimal("1")),
    ]
    assert all(item is not None for item in cutoffs)
    bounds = [item for item in cutoffs if item is not None]
    result: list[dict[str, Any]] = []
    for index in range(5):
        low = bounds[index]
        high = bounds[index + 1]
        if index < 4:
            cohort = [
                row for row in rows
                if row.get(feature) is not None
                and low <= Decimal(str(row[feature])) < high
            ]
        else:
            cohort = [
                row for row in rows
                if row.get(feature) is not None
                and low <= Decimal(str(row[feature])) <= high
            ]
        if not cohort:
            continue
        result.append(
            {
                "quintile": index + 1,
                "low_inclusive": str(low),
                "high": str(high),
                "high_inclusive": index == 4,
                "metrics": _metrics(cohort),
            }
        )
    return result



def _winner_loser_feature_medians(rows: list[dict[str, Any]]) -> dict[str, Any]:
    winners = [row for row in rows if _decimal_field(row, "realized_gross_r") > 0]
    losers = [row for row in rows if _decimal_field(row, "realized_gross_r") < 0]
    result: dict[str, Any] = {}
    for feature in FEATURES:
        win_values = [Decimal(str(row[feature])) for row in winners if row.get(feature) is not None]
        loss_values = [Decimal(str(row[feature])) for row in losers if row.get(feature) is not None]
        win_median = _median(win_values)
        loss_median = _median(loss_values)
        if win_median is None or loss_median is None:
            direction = "INSUFFICIENT_EVIDENCE"
        elif loss_median > win_median:
            direction = "LOSS_HIGHER"
        elif loss_median < win_median:
            direction = "LOSS_LOWER"
        else:
            direction = "EQUAL_MEDIAN"
        result[feature] = {
            "winner_median": None if win_median is None else str(win_median),
            "loser_median": None if loss_median is None else str(loss_median),
            "direction": direction,
        }
    return result



def _source_label_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        labels = row.get("source_event_labels", ())
        if not isinstance(labels, (list, tuple)):
            raise ValueError("source_event_labels must be list/tuple")
        for label in labels:
            grouped[str(label)].append(row)
    return [
        {"label": label, "metrics": _metrics(grouped[label])}
        for label in sorted(grouped, key=lambda item: (-len(grouped[item]), item))
    ]



def _ny_hour_key(moment: datetime) -> str:
    local = moment.astimezone(NEW_YORK)
    return f"{local.hour:02d}:00"


def _hourly_stop_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe entry and STOP timing in New York local time.

    This is descriptive consumed evidence only. The native-M1 clone contains OHLC
    bars but no historical bid/ask spread series, so timing concentration can support
    a spread/liquidity hypothesis but cannot prove spread causality by itself.
    """

    entry_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stop_entry_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stop_exit_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        entry_at = _aware(str(row["entry_at"]))
        entry_key = _ny_hour_key(entry_at)
        entry_groups[entry_key].append(row)
        if str(row["exit_reason"]) == "STOP":
            stop_entry_groups[entry_key].append(row)
            stop_exit_at = _aware(str(row["exit_at"]))
            stop_exit_groups[_ny_hour_key(stop_exit_at)].append(row)

    hourly: list[dict[str, Any]] = []
    keys = sorted(
        set(entry_groups) | set(stop_entry_groups) | set(stop_exit_groups),
        key=lambda value: int(value[:2]),
    )
    for key in keys:
        trades = entry_groups.get(key, [])
        stopped_entries = stop_entry_groups.get(key, [])
        stop_exits = stop_exit_groups.get(key, [])
        hourly.append(
            {
                "ny_hour": key,
                "entries": len(trades),
                "entries_that_stopped": len(stopped_entries),
                "entry_stop_rate": (
                    None
                    if not trades
                    else str(Decimal(len(stopped_entries)) / Decimal(len(trades)))
                ),
                "stop_exits": len(stop_exits),
            }
        )

    def _window(
        *,
        start_hour: int,
        end_hour_exclusive: int,
        label: str,
    ) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []
        stopped_entries: list[dict[str, Any]] = []
        stop_exits: list[dict[str, Any]] = []
        for row in rows:
            entry_local = _aware(str(row["entry_at"])).astimezone(NEW_YORK)
            entry_hour = entry_local.hour
            if start_hour <= entry_hour < end_hour_exclusive:
                entries.append(row)
                if str(row["exit_reason"]) == "STOP":
                    stopped_entries.append(row)
            if str(row["exit_reason"]) == "STOP":
                exit_local = _aware(str(row["exit_at"])).astimezone(NEW_YORK)
                if start_hour <= exit_local.hour < end_hour_exclusive:
                    stop_exits.append(row)
        return {
            "label": label,
            "start_hour_ny": start_hour,
            "end_hour_exclusive_ny": end_hour_exclusive,
            "entries": len(entries),
            "entries_that_stopped": len(stopped_entries),
            "entry_stop_rate": (
                None
                if not entries
                else str(Decimal(len(stopped_entries)) / Decimal(len(entries)))
            ),
            "stop_exits": len(stop_exits),
        }

    session = str(rows[0]["session"]) if rows else ""
    windows: list[dict[str, Any]] = []
    if session == "ASIA":
        windows.extend(
            [
                _window(start_hour=20, end_hour_exclusive=21, label="ASIA_OPEN_FIRST_HOUR"),
                _window(start_hour=20, end_hour_exclusive=22, label="ASIA_OPEN_FIRST_TWO_HOURS"),
            ]
        )
    elif session == "NEW_YORK":
        windows.extend(
            [
                _window(start_hour=14, end_hour_exclusive=16, label="NEW_YORK_AFTER_14"),
                _window(start_hour=15, end_hour_exclusive=16, label="NEW_YORK_LAST_HOUR"),
            ]
        )

    return {
        "timezone": "America/New_York",
        "hourly": hourly,
        "hypothesis_windows": windows,
        "historical_spread_series_present": False,
        "spread_causality_proven": False,
    }



def build_market_forensics(
    replay_root: Path,
    m1_root: Path,
    higher_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary, raw_trades = _load_replay(replay_root)
    source_by_signal = _load_higher_source(higher_root)
    symbol = str(summary["symbol"])
    rows: list[dict[str, Any]] = []
    for raw in raw_trades:
        if str(raw["symbol"]) != symbol:
            raise ValueError("mixed symbols in native-M1 replay ledger")
        source = source_by_signal.get(str(raw["higher_setup_signal_at"]))
        if source is None:
            raise ValueError("native-M1 trade missing exact higher-source signal match")
        rows.append(_prepare_trade(raw, source))
    _enrich_with_m1(rows, m1_root)

    losses = [row for row in rows if _decimal_field(row, "realized_gross_r") < 0]
    stops = [row for row in rows if str(row["exit_reason"]) == "STOP"]
    recovered = [row for row in stops if bool(row["target_reached_after_stop_same_session"])]
    extra_needed = [
        Decimal(str(row["extra_stop_r_needed_for_same_session_target_recovery"]))
        for row in recovered
        if row.get("extra_stop_r_needed_for_same_session_target_recovery") is not None
    ]
    classifications = Counter(str(row["loss_classification"]) for row in losses)
    target_reach = {
        "reached_25pct_before_exit": sum(bool(row["target_25pct_reached_before_exit"]) for row in rows),
        "reached_50pct_before_exit": sum(bool(row["target_50pct_reached_before_exit"]) for row in rows),
        "reached_75pct_before_exit": sum(bool(row["target_75pct_reached_before_exit"]) for row in rows),
        "reached_100pct_before_exit": sum(bool(row["target_100pct_reached_before_exit"]) for row in rows),
    }
    stop_target_progress = {
        "stops": len(stops),
        "reached_25pct_before_stop": sum(bool(row["target_25pct_reached_before_exit"]) for row in stops),
        "reached_50pct_before_stop": sum(bool(row["target_50pct_reached_before_exit"]) for row in stops),
        "reached_75pct_before_stop": sum(bool(row["target_75pct_reached_before_exit"]) for row in stops),
        "reached_100pct_before_stop": sum(bool(row["target_100pct_reached_before_exit"]) for row in stops),
        "target_recovered_after_stop_same_session": len(recovered),
        "target_recovery_rate": None if not stops else str(Decimal(len(recovered)) / Decimal(len(stops))),
        "median_extra_stop_r_needed_for_recovered": None if not extra_needed else str(median(extra_needed)),
        "p75_extra_stop_r_needed_for_recovered": None if not extra_needed else str(_quantile(extra_needed, Decimal("0.75"))),
        "p90_extra_stop_r_needed_for_recovered": None if not extra_needed else str(_quantile(extra_needed, Decimal("0.90"))),
    }
    medians = _winner_loser_feature_medians(rows)
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": summary["session"],
        "source_replay_identity": summary["identity"],
        "source_trade_count": len(rows),
        "loss_count": len(losses),
        "baseline_metrics": summary["metrics"],
        "loss_classification_counts": sorted(classifications.items()),
        "winner_loser_feature_medians": medians,
        "feature_quintile_cohorts": {
            feature: _cohort_quintiles(rows, feature)
            for feature in FEATURES
        },
        "source_event_label_metrics": _source_label_metrics(rows),
        "stop_intelligence": stop_target_progress,
        "ny_time_stop_profile": _hourly_stop_profile(rows),
        "target_capacity": target_reach,
        "entry_forensics_complete": all(
            row.get("displacement_body_ratio") is not None
            and row.get("entry_adverse_excursion_upper_bound_r") is not None
            and row.get("order_block_candle_count") is not None
            for row in rows
        ),
        "ob_reconstruction_match_count": sum(
            row.get("order_block_reconstruction_matches_ledger") is True for row in rows
        ),
        "ob_reconstruction_mismatch_count": sum(
            row.get("order_block_reconstruction_matches_ledger") is False for row in rows
        ),
        "evidence_status": "CONSUMED_FORENSIC_EVIDENCE",
        "holdout_fresh_after_forensics": False,
        "methodology_changed": False,
        "entry_contract_changed": False,
        "stop_contract_changed": False,
        "target_contract_changed": False,
        "outcome_used_for_trade_selection": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, rows



def write_market(report: dict[str, Any], rows: list[dict[str, Any]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-m1-loss-causal-forensics-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-ledger.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        f"# QORE Capitalizer — {report['symbol']} M1 Loss Causal Forensics V1",
        "",
        "Consumed evidence only. No strategy rule is promoted by this report.",
        "",
        f"- Trades: {report['source_trade_count']}",
        f"- Losses: {report['loss_count']}",
        f"- Evidence: {report['evidence_status']}",
        f"- Holdout remains fresh: {report['holdout_fresh_after_forensics']}",
        "",
        "## Loss classifications",
    ]
    for label, count in report["loss_classification_counts"]:
        lines.append(f"- {label}: {count}")
    stop = report["stop_intelligence"]
    lines.extend(
        [
            "",
            "## Stop evidence",
            f"- Stops: {stop['stops']}",
            f"- Same-session original-target recovery after stop: {stop['target_recovered_after_stop_same_session']}",
            f"- Recovery rate: {stop['target_recovery_rate']}",
            f"- Median extra stop R needed among recovered cases: {stop['median_extra_stop_r_needed_for_recovered']}",
            "",
            "## New York time STOP profile",
        ]
    )
    for bucket in report["ny_time_stop_profile"]["hourly"]:
        lines.append(
            f"- {bucket['ny_hour']}: entries={bucket['entries']}, "
            f"entry_stops={bucket['entries_that_stopped']}, "
            f"entry_stop_rate={bucket['entry_stop_rate']}, "
            f"stop_exits={bucket['stop_exits']}"
        )
    for window in report["ny_time_stop_profile"]["hypothesis_windows"]:
        lines.append(
            f"- {window['label']}: entries={window['entries']}, "
            f"entry_stops={window['entries_that_stopped']}, "
            f"entry_stop_rate={window['entry_stop_rate']}, "
            f"stop_exits={window['stop_exits']}"
        )
    lines.extend(
        [
            "",
            "## Winner vs loser median directions",
        ]
    )
    for feature, data in report["winner_loser_feature_medians"].items():
        lines.append(
            f"- {feature}: winners={data['winner_median']} losers={data['loser_median']} ({data['direction']})"
        )
    (output / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")



def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-m1-loss-causal-forensics-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market failure matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    expected = {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "USDCAD", "USDJPY", "XAUUSD"}
    if {str(report["symbol"]) for report in reports} != expected:
        raise ValueError("nine-market forensic universe mismatch")
    directions: dict[str, Counter[str]] = {feature: Counter() for feature in FEATURES}
    for report in reports:
        for feature in FEATURES:
            directions[feature][str(report["winner_loser_feature_medians"][feature]["direction"])] += 1
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "total_trades": sum(int(report["source_trade_count"]) for report in reports),
        "total_losses": sum(int(report["loss_count"]) for report in reports),
        "feature_direction_counts": {
            feature: dict(sorted(counter.items()))
            for feature, counter in directions.items()
        },
        "markets": [
            {
                "symbol": report["symbol"],
                "session": report["session"],
                "baseline_metrics": report["baseline_metrics"],
                "loss_classification_counts": report["loss_classification_counts"],
                "stop_intelligence": report["stop_intelligence"],
                "ny_time_stop_profile": report["ny_time_stop_profile"],
                "winner_loser_feature_medians": report["winner_loser_feature_medians"],
            }
            for report in sorted(reports, key=lambda item: str(item["symbol"]))
        ],
        "evidence_status": "CONSUMED_FORENSIC_EVIDENCE",
        "holdout_fresh_after_forensics": False,
        "methodology_changed": False,
        "universal_rule_inferred": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
    }



def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-nine-market-failure-matrix-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# QORE Capitalizer — Nine-Market Failure Matrix V1",
        "",
        "Consumed forensic evidence. No universal rule is inferred or promoted.",
        "",
        f"- Trades: {report['total_trades']}",
        f"- Losses: {report['total_losses']}",
        "",
        "## Cross-market winner/loser median directions",
    ]
    for feature, counts in report["feature_direction_counts"].items():
        lines.append(f"- {feature}: {counts}")
    (output / "capitalizer-nine-market-failure-matrix-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )



def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("higher_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_forensics(
            args.replay_root,
            args.m1_root,
            args.higher_root,
        )
        write_market(report, rows, args.output)
        print(
            json.dumps(
                {
                    "identity": report["identity"],
                    "symbol": report["symbol"],
                    "trades": report["source_trade_count"],
                    "losses": report["loss_count"],
                    "stop_recovery_rate": report["stop_intelligence"]["target_recovery_rate"],
                    "evidence_status": report["evidence_status"],
                },
                sort_keys=True,
            )
        )
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
