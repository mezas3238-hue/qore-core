"""Deep CIBO failure attribution for the consumed ICT Turtle Soup R5 holdout.

This module never changes R5. It reconstructs each of the 12 consumed trades from
its original read-only M5 artifact, verifies entry/stop/target mechanics, then
separates contract correctness from observed market-state and post-exit behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo.contracts import CiboFunctionalAuthority
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    Side,
    SourceCandle,
    build_daily,
    build_h4,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r5_authentic_ideal import (
    authentic_ideal_c2,
    load_evidence,
)

IDENTITY = "ICT_TS_CIBO_HOLDOUT_FAILURE_ATTRIBUTION_V1"
PARENT_IDENTITY = "ICT_TS_CIBO_DIAGNOSTICS_V1"
HOLDOUT_ID = "ICT_TS_R5_FRESH_2016_2018"
R5_RUN = 35118222306
R5_SHA = "9beb2f8147db2b9fb780bc4cc28e2cdb05b7851e"
LAB_RUN = 35125861002
LAB_SHA = "4d09a43aa5795624b4a7cb29bb2503ae586c5a4f"
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
}
STOP_REASONS = {"stop", "gap-stop", "stop-first"}
TARGET_REASONS = {"target", "gap-target-capped"}


@dataclass(frozen=True, slots=True)
class TargetCandidate:
    level: Decimal
    pivot_opened_at: datetime
    confirmed_at: datetime


@dataclass(frozen=True, slots=True)
class LabEvent:
    raid_at: datetime
    opposite_reference_hit_24h: bool
    opposite_reference_hit_minutes: int | None


@dataclass(frozen=True, slots=True)
class MarketContext:
    evidence: Evidence
    h4: tuple[SourceCandle, ...]
    daily: tuple[SourceCandle, ...]
    h4_index: dict[datetime, int]
    daily_index: dict[datetime, int]


@dataclass(frozen=True, slots=True)
class TradeAttribution:
    trade_id: int
    symbol: str
    side: str
    entry_at: str
    exit_at: str
    exit_reason: str
    gross_r: float
    entry_contract_assessment: str
    entry_market_state_assessment: str
    stop_contract_assessment: str
    stop_behavior_assessment: str
    target_contract_assessment: str
    target_behavior_assessment: str
    failure_zone: str
    failure_evidence_tier: str
    d1_full_c1_traverse_pre_entry: bool
    h4_full_c1_traverse_pre_entry: bool
    daily_c3_minutes_spent_before_entry: int
    daily_pre_entry_favorable_r: float
    daily_pre_entry_adverse_r: float
    daily_pre_entry_progress_to_target: float
    final_15m_directional_net_r: float
    final_30m_directional_net_r: float
    final_60m_directional_net_r: float
    h4_c2_body_fraction: float
    h4_c2_directional_close_location: float
    risk_ticks: float
    projected_r: float
    time_to_stop_minutes: int | None
    mfe_before_stop_r: float | None
    max_stop_penetration_ticks: float | None
    entry_recovered_after_stop: bool | None
    target_reached_after_stop: bool | None
    post_stop_max_recovery_r: float | None
    daily_close_beyond_stop: bool | None
    valid_dol_count_at_entry: int
    next_farther_dol: str | None
    target_reached_after_exit: bool
    target_additional_favorable_r: float | None
    next_farther_dol_reached_after_target: bool | None
    max_favorable_fraction_of_target: float
    diagnostic_codes: tuple[str, ...]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _side(value: str) -> Side:
    normalized = value.strip().lower()
    if normalized == Side.LONG.value:
        return Side.LONG
    if normalized == Side.SHORT.value:
        return Side.SHORT
    raise ValueError(f"unknown side: {value}")


def _required_row(row: dict[str, str | None], key: str) -> str:
    value = row.get(key)
    if value is None:
        raise ValueError(f"missing CSV field: {key}")
    return value


def _tick_size(digits: int) -> Decimal:
    if digits <= 0:
        raise ValueError("digits must be positive")
    return Decimal(1).scaleb(-digits)


def _bars_between(
    bars: tuple[Bar, ...], start: datetime, end: datetime
) -> tuple[Bar, ...]:
    return tuple(bar for bar in bars if start <= bar.opened_at < end)


def _directional_delta(start: Decimal, end: Decimal, side: Side) -> Decimal:
    return end - start if side is Side.LONG else start - end


def _favorable_excursion(
    bars: tuple[Bar, ...], anchor: Decimal, side: Side
) -> Decimal:
    if not bars:
        return Decimal(0)
    if side is Side.LONG:
        return max(Decimal(0), max(bar.high for bar in bars) - anchor)
    return max(Decimal(0), anchor - min(bar.low for bar in bars))


def _adverse_excursion(
    bars: tuple[Bar, ...], anchor: Decimal, side: Side
) -> Decimal:
    if not bars:
        return Decimal(0)
    if side is Side.LONG:
        return max(Decimal(0), anchor - min(bar.low for bar in bars))
    return max(Decimal(0), max(bar.high for bar in bars) - anchor)


def _hit_level(bars: tuple[Bar, ...], level: Decimal, side: Side) -> bool:
    if side is Side.LONG:
        return any(bar.high >= level for bar in bars)
    return any(bar.low <= level for bar in bars)


def _recover_entry(bars: tuple[Bar, ...], entry: Decimal, side: Side) -> bool:
    if side is Side.LONG:
        return any(bar.high >= entry for bar in bars)
    return any(bar.low <= entry for bar in bars)


def _enumerate_daily_targets(
    daily: tuple[SourceCandle, ...],
    m5: tuple[Bar, ...],
    *,
    side: Side,
    entry: Decimal,
    entry_at: datetime,
) -> tuple[TargetCandidate, ...]:
    by_level: dict[Decimal, TargetCandidate] = {}
    for index in range(1, len(daily) - 1):
        left, pivot, right = daily[index - 1], daily[index], daily[index + 1]
        if right.closed_at > entry_at:
            continue
        if side is Side.LONG:
            level = pivot.high
            if not (pivot.high > left.high and pivot.high > right.high and level > entry):
                continue
            taken = any(
                bar.high >= level
                for bar in m5
                if right.closed_at <= bar.opened_at < entry_at
            )
        else:
            level = pivot.low
            if not (pivot.low < left.low and pivot.low < right.low and level < entry):
                continue
            taken = any(
                bar.low <= level
                for bar in m5
                if right.closed_at <= bar.opened_at < entry_at
            )
        if taken:
            continue
        candidate = TargetCandidate(level, pivot.opened_at, right.closed_at)
        existing = by_level.get(level)
        if existing is None or candidate.pivot_opened_at < existing.pivot_opened_at:
            by_level[level] = candidate
    ordered = sorted(
        by_level.values(),
        key=lambda item: item.level,
        reverse=side is Side.SHORT,
    )
    return tuple(ordered)


def _load_market_contexts(root: Path) -> dict[str, MarketContext]:
    result: dict[str, MarketContext] = {}
    for path in root.rglob("market-evidence.json"):
        evidence = load_evidence(path)
        if evidence.symbol in result:
            raise ValueError(f"duplicate market evidence for {evidence.symbol}")
        h4 = build_h4(evidence.bars)
        daily = build_daily(h4)
        result[evidence.symbol] = MarketContext(
            evidence=evidence,
            h4=h4,
            daily=daily,
            h4_index={item.opened_at: idx for idx, item in enumerate(h4)},
            daily_index={item.opened_at: idx for idx, item in enumerate(daily)},
        )
    if set(result) != EXPECTED_SYMBOLS:
        raise ValueError(f"expected exact seven R5 market artifacts, got {sorted(result)}")
    return result


def _load_lab_events(path: Path) -> dict[tuple[str, str, str, datetime], LabEvent]:
    result: dict[tuple[str, str, str, datetime], LabEvent] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            reference_type = _required_row(row, "reference_type")
            if reference_type != "prior-candle":
                continue
            timeframe = _required_row(row, "timeframe")
            if timeframe not in {"D1", "H4"}:
                continue
            raw_minutes = _required_row(row, "opposite_reference_hit_minutes")
            minutes = (
                None
                if raw_minutes.strip().lower() in {"", "nan", "none"}
                else int(float(raw_minutes))
            )
            key = (
                _required_row(row, "symbol"),
                timeframe,
                _required_row(row, "side"),
                _dt(_required_row(row, "source_opened_at")),
            )
            result[key] = LabEvent(
                raid_at=_dt(_required_row(row, "raid_at")),
                opposite_reference_hit_24h=_required_row(
                    row, "opposite_reference_hit_24h"
                ).strip().lower()
                == "true",
                opposite_reference_hit_minutes=minutes,
            )
    return result


def _full_c1_pre_entry(event: LabEvent, entry_at: datetime) -> bool:
    if not event.opposite_reference_hit_24h or event.opposite_reference_hit_minutes is None:
        return False
    return event.raid_at + timedelta(minutes=event.opposite_reference_hit_minutes) <= entry_at


def _daily_close_bar(path: tuple[Bar, ...]) -> Bar | None:
    return path[-1] if path else None


def _window_directional_net_r(
    bars: tuple[Bar, ...], entry_at: datetime, minutes: int, side: Side, risk: Decimal
) -> float:
    window = _bars_between(bars, entry_at - timedelta(minutes=minutes), entry_at)
    if not window:
        return 0.0
    return float(_directional_delta(window[0].open, window[-1].close, side) / risk)


def _is_stop_reason(reason: str) -> bool:
    return reason in STOP_REASONS


def _is_target_reason(reason: str) -> bool:
    return reason in TARGET_REASONS


def _stop_behavior(
    *,
    trade: dict[str, Any],
    evidence: Evidence,
    daily_close: datetime,
    side: Side,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
    risk: Decimal,
    tick: Decimal,
) -> tuple[str, dict[str, Any]]:
    if not _is_stop_reason(str(trade["exit_reason"])):
        return "STOP_NOT_TESTED", {
            "time_to_stop_minutes": None,
            "mfe_before_stop_r": None,
            "max_stop_penetration_ticks": None,
            "entry_recovered_after_stop": None,
            "target_reached_after_stop": None,
            "post_stop_max_recovery_r": None,
            "daily_close_beyond_stop": None,
        }
    entry_at = _dt(str(trade["entry_at"]))
    exit_at = _dt(str(trade["exit_at"]))
    before = _bars_between(evidence.bars, entry_at, exit_at)
    after = _bars_between(evidence.bars, exit_at, daily_close)
    mfe = _favorable_excursion(before, entry, side) / risk
    recovered = _recover_entry(after, entry, side)
    target_after = _hit_level(after, target, side)
    if side is Side.LONG:
        penetration = max(
            Decimal(0), stop - min((bar.low for bar in after), default=stop)
        ) / tick
        recovery = (max((bar.high for bar in after), default=stop) - stop) / risk
    else:
        penetration = max(
            Decimal(0), max((bar.high for bar in after), default=stop) - stop
        ) / tick
        recovery = (stop - min((bar.low for bar in after), default=stop)) / risk
    close_bar = _daily_close_bar(after)
    beyond_stop = False
    if close_bar is not None:
        beyond_stop = (
            close_bar.close < stop if side is Side.LONG else close_bar.close > stop
        )
    if target_after:
        assessment = "POST_STOP_TARGET_REACHED"
    elif recovered:
        assessment = "POST_STOP_ENTRY_RECOVERED_ONLY"
    else:
        assessment = "POST_STOP_NO_ENTRY_RECOVERY"
    return assessment, {
        "time_to_stop_minutes": int((exit_at - entry_at).total_seconds() // 60),
        "mfe_before_stop_r": float(mfe),
        "max_stop_penetration_ticks": float(penetration),
        "entry_recovered_after_stop": recovered,
        "target_reached_after_stop": target_after,
        "post_stop_max_recovery_r": float(recovery),
        "daily_close_beyond_stop": beyond_stop,
    }


def _failure_zone(
    *,
    exit_reason: str,
    gross_r: float,
    d1_full: bool,
    entry_contract_ok: bool,
    stop_contract_ok: bool,
    target_contract_ok: bool,
    stop_behavior: str,
) -> tuple[str, str]:
    if _is_target_reason(exit_reason):
        return "NO_FAILURE_TARGET_EXIT", "E0_OBSERVATION"
    if gross_r > 0:
        return "NO_FAILURE_PROFITABLE_EXIT", "E0_OBSERVATION"
    if not target_contract_ok:
        return "TARGET_SELECTION", "E0_OBSERVATION"
    if not entry_contract_ok or not stop_contract_ok:
        return "MIXED", "E0_OBSERVATION"
    if stop_behavior in {"POST_STOP_TARGET_REACHED", "POST_STOP_ENTRY_RECOVERED_ONLY"}:
        return "STOP_INVALIDATION", "E1_DIAGNOSTIC_TRAJECTORY"
    if not d1_full:
        return "ENTRY_STATE", "E1_ASSOCIATION"
    return "UNRESOLVED", "E0_OBSERVATION"


def _diagnose_trade(
    trade_id: int,
    trade: dict[str, Any],
    context: MarketContext,
    lab_events: dict[tuple[str, str, str, datetime], LabEvent],
) -> TradeAttribution:
    side_text = str(trade["side"])
    side = _side(side_text)
    entry_at = _dt(str(trade["entry_at"]))
    exit_at = _dt(str(trade["exit_at"]))
    daily_c2_at = _dt(str(trade["daily_c2_opened_at"]))
    daily_c3_at = _dt(str(trade["daily_c3_opened_at"]))
    h4_c2_at = _dt(str(trade["h4_c2_opened_at"]))
    if daily_c2_at not in context.daily_index or h4_c2_at not in context.h4_index:
        raise ValueError("trade source candle missing from reconstructed evidence")
    day_idx = context.daily_index[daily_c2_at]
    h4_idx = context.h4_index[h4_c2_at]
    if day_idx + 1 >= len(context.daily) or h4_idx + 1 >= len(context.h4):
        raise ValueError("trade requires missing C3 candle")
    daily_c3 = context.daily[day_idx + 1]
    h4_c2 = context.h4[h4_idx]
    h4_c3 = context.h4[h4_idx + 1]
    daily_ideal = authentic_ideal_c2(context.daily, day_idx)
    h4_ideal = authentic_ideal_c2(context.h4, h4_idx)
    if daily_ideal is None or h4_ideal is None:
        raise ValueError("R5 trade does not reconstruct authentic Ideal C2")
    if daily_ideal.side is not side or h4_ideal.side is not side:
        raise ValueError("R5 side drift against reconstructed Ideal C2")

    entry = Decimal(str(trade["entry"]))
    stop = Decimal(str(trade["stop"]))
    target = Decimal(str(trade["target"]))
    protected = Decimal(str(trade["protected_swing"]))
    tick = _tick_size(context.evidence.digits)
    expected_stop = protected - tick if side is Side.LONG else protected + tick
    entry_contract_ok = (
        entry_at == h4_c3.opened_at
        and entry == h4_c3.open
        and daily_c3_at == daily_c3.opened_at
        and h4_ideal.protected_swing == protected
        and daily_c3.opened_at <= entry_at < daily_c3.closed_at
    )
    stop_contract_ok = stop == expected_stop
    entry_contract = (
        "ENTRY_CONTRACT_CORRECT" if entry_contract_ok else "ENTRY_CONTRACT_INVALID"
    )
    stop_contract = (
        "STOP_CONTRACT_CORRECT_ONE_NATIVE_TICK_BEYOND_PS"
        if stop_contract_ok
        else "STOP_CONTRACT_INVALID"
    )
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    if risk <= 0 or reward <= 0:
        raise ValueError("non-positive reconstructed R5 risk/reward")

    candidates = _enumerate_daily_targets(
        context.daily,
        context.evidence.bars,
        side=side,
        entry=entry,
        entry_at=entry_at,
    )
    target_opened_at = _dt(str(trade["primary_dol_opened_at"]))
    nearest = candidates[0] if candidates else None
    target_contract_ok = (
        nearest is not None
        and nearest.level == target
        and nearest.pivot_opened_at == target_opened_at
    )
    if not target_contract_ok:
        target_contract = "TARGET_CONTRACT_INVALID"
    elif len(candidates) == 1:
        target_contract = "TARGET_CONTRACT_CORRECT_SINGLE_DOL"
    else:
        target_contract = "TARGET_CONTRACT_CORRECT_NEAREST_OF_MULTIPLE"
    next_dol = candidates[1].level if len(candidates) > 1 else None

    d1_key = (str(trade["symbol"]), "D1", side_text, daily_c2_at)
    h4_key = (str(trade["symbol"]), "H4", side_text, h4_c2_at)
    if d1_key not in lab_events or h4_key not in lab_events:
        raise ValueError("exact Behavior Lab linkage missing")
    d1_full = _full_c1_pre_entry(lab_events[d1_key], entry_at)
    h4_full = _full_c1_pre_entry(lab_events[h4_key], entry_at)

    daily_pre = _bars_between(context.evidence.bars, daily_c3.opened_at, entry_at)
    daily_open = daily_c3.open
    favorable_pre = _favorable_excursion(daily_pre, daily_open, side)
    adverse_pre = _adverse_excursion(daily_pre, daily_open, side)
    progress_denominator = abs(target - daily_open)
    progress_to_target = (
        favorable_pre / progress_denominator
        if progress_denominator > 0
        else Decimal(0)
    )
    c2_range = h4_c2.high - h4_c2.low
    body_fraction = (
        abs(h4_c2.close - h4_c2.open) / c2_range
        if c2_range > 0
        else Decimal(0)
    )
    directional_close = (
        (
            (h4_c2.close - h4_c2.low) / c2_range
            if side is Side.LONG
            else (h4_c2.high - h4_c2.close) / c2_range
        )
        if c2_range > 0
        else Decimal(0)
    )

    if not entry_contract_ok:
        entry_market_state = "ENTRY_STATE_FAIL_CLOSED_CONTRACT_MISMATCH"
    elif not d1_full:
        entry_market_state = "E1_WARNING_D1_INCOMPLETE_FULL_RANGE_REPRICING"
    else:
        entry_market_state = "NO_E1_ENTRY_CONTRADICTION_OBSERVED"

    stop_behavior, stop_metrics = _stop_behavior(
        trade=trade,
        evidence=context.evidence,
        daily_close=daily_c3.closed_at,
        side=side,
        entry=entry,
        stop=stop,
        target=target,
        risk=risk,
        tick=tick,
    )

    after_exit = _bars_between(context.evidence.bars, exit_at, daily_c3.closed_at)
    target_after_exit = _hit_level(after_exit, target, side)
    whole_trade_path = _bars_between(context.evidence.bars, entry_at, daily_c3.closed_at)
    max_favorable = _favorable_excursion(whole_trade_path, entry, side)
    max_favorable_fraction = max_favorable / reward
    additional_after_target: float | None = None
    next_dol_after_target: bool | None = None
    exit_reason = str(trade["exit_reason"])
    if _is_target_reason(exit_reason):
        after_target = _bars_between(context.evidence.bars, exit_at, daily_c3.closed_at)
        additional_after_target = float(
            _favorable_excursion(after_target, target, side) / risk
        )
        next_dol_after_target = (
            None if next_dol is None else _hit_level(after_target, next_dol, side)
        )
        target_behavior = (
            "TARGET_REACHED_AND_DELIVERY_CONTINUED"
            if additional_after_target > 0
            else "TARGET_REACHED_NO_ADDITIONAL_DELIVERY"
        )
    elif target_after_exit:
        target_behavior = "TARGET_REACHED_ONLY_AFTER_RECORDED_EXIT"
    else:
        target_behavior = "TARGET_NOT_REACHED_BY_DAILY_C3_CLOSE"

    failure_zone, failure_tier = _failure_zone(
        exit_reason=exit_reason,
        gross_r=float(trade["gross_r"]),
        d1_full=d1_full,
        entry_contract_ok=entry_contract_ok,
        stop_contract_ok=stop_contract_ok,
        target_contract_ok=target_contract_ok,
        stop_behavior=stop_behavior,
    )
    codes: set[str] = {
        "entry.contract-correct" if entry_contract_ok else "entry.contract-invalid",
        "stop.contract-correct" if stop_contract_ok else "stop.contract-invalid",
        "target.contract-correct" if target_contract_ok else "target.contract-invalid",
        "d1.full-c1-traverse" if d1_full else "d1.incomplete-full-c1-traverse",
        "h4.full-c1-traverse" if h4_full else "h4.incomplete-full-c1-traverse",
        f"stop.{stop_behavior.lower()}",
        f"target.{target_behavior.lower()}",
    }
    if len(candidates) > 1:
        codes.add("target.multiple-valid-r5-dols-at-entry")

    return TradeAttribution(
        trade_id=trade_id,
        symbol=str(trade["symbol"]),
        side=side_text,
        entry_at=entry_at.isoformat(),
        exit_at=exit_at.isoformat(),
        exit_reason=exit_reason,
        gross_r=float(trade["gross_r"]),
        entry_contract_assessment=entry_contract,
        entry_market_state_assessment=entry_market_state,
        stop_contract_assessment=stop_contract,
        stop_behavior_assessment=stop_behavior,
        target_contract_assessment=target_contract,
        target_behavior_assessment=target_behavior,
        failure_zone=failure_zone,
        failure_evidence_tier=failure_tier,
        d1_full_c1_traverse_pre_entry=d1_full,
        h4_full_c1_traverse_pre_entry=h4_full,
        daily_c3_minutes_spent_before_entry=int(
            (entry_at - daily_c3.opened_at).total_seconds() // 60
        ),
        daily_pre_entry_favorable_r=float(favorable_pre / risk),
        daily_pre_entry_adverse_r=float(adverse_pre / risk),
        daily_pre_entry_progress_to_target=float(progress_to_target),
        final_15m_directional_net_r=_window_directional_net_r(
            context.evidence.bars, entry_at, 15, side, risk
        ),
        final_30m_directional_net_r=_window_directional_net_r(
            context.evidence.bars, entry_at, 30, side, risk
        ),
        final_60m_directional_net_r=_window_directional_net_r(
            context.evidence.bars, entry_at, 60, side, risk
        ),
        h4_c2_body_fraction=float(body_fraction),
        h4_c2_directional_close_location=float(directional_close),
        risk_ticks=float(risk / tick),
        projected_r=float(reward / risk),
        time_to_stop_minutes=stop_metrics["time_to_stop_minutes"],
        mfe_before_stop_r=stop_metrics["mfe_before_stop_r"],
        max_stop_penetration_ticks=stop_metrics["max_stop_penetration_ticks"],
        entry_recovered_after_stop=stop_metrics["entry_recovered_after_stop"],
        target_reached_after_stop=stop_metrics["target_reached_after_stop"],
        post_stop_max_recovery_r=stop_metrics["post_stop_max_recovery_r"],
        daily_close_beyond_stop=stop_metrics["daily_close_beyond_stop"],
        valid_dol_count_at_entry=len(candidates),
        next_farther_dol=None if next_dol is None else str(next_dol),
        target_reached_after_exit=target_after_exit,
        target_additional_favorable_r=additional_after_target,
        next_farther_dol_reached_after_target=next_dol_after_target,
        max_favorable_fraction_of_target=float(max_favorable_fraction),
        diagnostic_codes=tuple(sorted(codes)),
    )


def diagnose(
    trades_path: Path,
    events_path: Path,
    market_root: Path,
) -> list[TradeAttribution]:
    trades = json.loads(trades_path.read_text())
    if not isinstance(trades, list) or len(trades) != 12:
        raise ValueError("expected exact 12-trade R5 aggregate")
    contexts = _load_market_contexts(market_root)
    lab_events = _load_lab_events(events_path)
    return [
        _diagnose_trade(index, trade, contexts[str(trade["symbol"])], lab_events)
        for index, trade in enumerate(trades, start=1)
    ]


def _count(items: list[TradeAttribution], attr: str, value: str) -> int:
    return sum(getattr(item, attr) == value for item in items)


def write_outputs(items: list[TradeAttribution], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    rows = [asdict(item) for item in items]
    (output / "failure-attribution-ledger.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )
    with (output / "failure-attribution-ledger.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value) if isinstance(value, tuple) else value
                    for key, value in row.items()
                }
            )
    stops = [item for item in items if _is_stop_reason(item.exit_reason)]
    targets = [item for item in items if _is_target_reason(item.exit_reason)]
    summary: dict[str, Any] = {
        "schema": "qore.ict_ts_cibo_holdout_failure_attribution.v1",
        "identity": IDENTITY,
        "parent_identity": PARENT_IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "r5_run": R5_RUN,
        "r5_sha": R5_SHA,
        "behavior_lab_run": LAB_RUN,
        "behavior_lab_sha": LAB_SHA,
        "trade_count": len(items),
        "entry_contract_correct": _count(
            items, "entry_contract_assessment", "ENTRY_CONTRACT_CORRECT"
        ),
        "entry_e1_d1_incomplete_warning": _count(
            items,
            "entry_market_state_assessment",
            "E1_WARNING_D1_INCOMPLETE_FULL_RANGE_REPRICING",
        ),
        "stop_contract_correct": _count(
            items,
            "stop_contract_assessment",
            "STOP_CONTRACT_CORRECT_ONE_NATIVE_TICK_BEYOND_PS",
        ),
        "target_contract_correct": sum(
            item.target_contract_assessment.startswith("TARGET_CONTRACT_CORRECT")
            for item in items
        ),
        "multiple_valid_dol_at_entry": sum(
            item.valid_dol_count_at_entry > 1 for item in items
        ),
        "hard_stops": len(stops),
        "hard_stop_entry_recovered": sum(
            item.entry_recovered_after_stop is True for item in stops
        ),
        "hard_stop_target_reached_after_stop": sum(
            item.target_reached_after_stop is True for item in stops
        ),
        "hard_stop_no_entry_recovery": _count(
            stops, "stop_behavior_assessment", "POST_STOP_NO_ENTRY_RECOVERY"
        ),
        "target_exits": len(targets),
        "target_exits_with_additional_delivery": _count(
            targets,
            "target_behavior_assessment",
            "TARGET_REACHED_AND_DELIVERY_CONTINUED",
        ),
        "failure_zones": {
            name: sum(item.failure_zone == name for item in items)
            for name in sorted({item.failure_zone for item in items})
        },
        "evidence_status": "CONSUMED_DIAGNOSTIC_ONLY",
        "cibo_authority_ceiling": CiboFunctionalAuthority.OPINION.value,
        "governance": {
            "pnl_used_for_filter_selection": False,
            "candidate_rule_created": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    report_lines = [
        "# CIBO Turtle Soup R5 Holdout Failure Attribution V1",
        "",
        f"- Trades: {len(items)}",
        f"- Entry contract correct: {summary['entry_contract_correct']}/{len(items)}",
        f"- Stop contract correct: {summary['stop_contract_correct']}/{len(items)}",
        f"- Target contract correct: {summary['target_contract_correct']}/{len(items)}",
        f"- Entry E1 D1-incomplete warnings: {summary['entry_e1_d1_incomplete_warning']}/{len(items)}",
        f"- Hard stops: {len(stops)}",
        f"- Hard stops recovering entry: {summary['hard_stop_entry_recovered']}/{len(stops)}",
        f"- Hard stops later reaching original target: {summary['hard_stop_target_reached_after_stop']}/{len(stops)}",
        f"- Target exits with additional delivery: {summary['target_exits_with_additional_delivery']}/{len(targets)}",
        f"- Multiple valid R5 Daily DOLs at entry: {summary['multiple_valid_dol_at_entry']}/{len(items)}",
        "",
        "## Failure zones",
        json.dumps(summary["failure_zones"], sort_keys=True),
        "",
        "All findings are consumed diagnostic evidence only. No operating rule is authorized.",
    ]
    (output / "REPORT.md").write_text("\n".join(report_lines) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trades", type=Path)
    parser.add_argument("events", type=Path)
    parser.add_argument("market_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    items = diagnose(args.trades, args.events, args.market_root)
    summary = write_outputs(items, args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
