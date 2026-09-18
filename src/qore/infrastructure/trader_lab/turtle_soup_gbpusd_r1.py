"""Frozen GBPUSD Turtle Soup R1 and one-year sealed-holdout replay.

The candidate is deliberately narrower than the CIBO association matrix.  E1
features such as FVG-after-raid and prior-body alignment remain diagnostics and
are not promoted to entry filters.  R1 uses only source-defined mechanics that
are causal and known before execution: prior-candle liquidity, exact C2
reversal closure, causal CISD, protected-swing invalidation, and the still-
untouched opposite boundary of C1 as structural DOL.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as atlas
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    Side,
    SourceCandle,
    _max_drawdown,
    _price,
    _profit_factor,
    _session_bucket,
    build_h1,
    build_h4,
    build_m15,
    causal_cisd,
)
from qore.kernel.result import Failure

IDENTITY = "TURTLE_SOUP_GBPUSD_R1"
HOLDOUT_ID = "TURTLE_SOUP_GBPUSD_DEVELOPMENT_10Y_CONSUMED"
SYMBOL = "GBPUSD"
EVIDENCE_TIER = "E1_CONSUMED_DEVELOPMENT"
ACQUISITION_OPEN = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
EVAL_OPEN = datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
MAX_LIFETIME = timedelta(hours=24)
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
MIN_HOLDOUT_TRADES = 30
MAX_PRIMARY_DRAWDOWN_R = Decimal("20")
MIN_POSITIVE_QUARTERS = 3
TIMEFRAME_PRIORITY = {"H4": 0, "H1": 1}


@dataclass(frozen=True, slots=True)
class Signal:
    timeframe: str
    side: Side
    c1_opened_at: datetime
    c2_opened_at: datetime
    raid_at: datetime
    cisd_at: datetime
    entry_at: datetime
    entry: Decimal
    protected_swing: Decimal
    target: Decimal
    projected_r: Decimal
    session_bucket: str
    prior_body_alignment: str


@dataclass(frozen=True, slots=True)
class Trade:
    timeframe: str
    side: Side
    c1_opened_at: datetime
    c2_opened_at: datetime
    raid_at: datetime
    cisd_at: datetime
    entry_at: datetime
    exit_at: datetime
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
    prior_body_alignment: str


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _tick_size(digits: int) -> Decimal:
    if digits <= 0:
        raise ValueError("digits must be positive")
    return Decimal(1).scaleb(-digits)


def _collect_m5() -> Evidence:
    """Read the preregistered GBPUSD interval without probing another window."""
    client = SpotwareCTraderOpenApiClient(credentials=atlas._credentials())
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader DEMO authentication failed: {ready.error}")
        provider, symbol_id, digits, pip_position = atlas._selected_symbol(
            client, canonical_symbol=SYMBOL
        )
        retained: dict[datetime, Bar] = {}
        cursor = ACQUISITION_OPEN
        chunk_index = 0
        while cursor < EVAL_CLOSE:
            closed_at = min(cursor + timedelta(days=atlas.CHUNK_DAYS), EVAL_CLOSE)
            natives = atlas._read_chunk(
                client,
                account_id=client.account_id,
                symbol_id=symbol_id,
                opened_at=cursor,
                closed_at=closed_at,
                client_msg_id=f"ts-xau-r1:{symbol_id}:{chunk_index}",
            )
            for native in natives:
                raw = atlas._provider_bar(
                    native,
                    canonical_symbol=SYMBOL,
                    provider_symbol=provider,
                    provider_symbol_id=symbol_id,
                    digits=digits,
                    pip_position=pip_position,
                )
                opened = _dt(raw.opened_at)
                if not ACQUISITION_OPEN <= opened < EVAL_CLOSE:
                    continue
                bar = Bar(
                    opened_at=opened,
                    closed_at=opened + timedelta(minutes=5),
                    open=_price(raw.open_relative, digits),
                    high=_price(raw.high_relative, digits),
                    low=_price(raw.low_relative, digits),
                    close=_price(raw.close_relative, digits),
                )
                existing = retained.get(opened)
                if existing is not None and existing != bar:
                    raise RuntimeError("contradictory historical M5 bar")
                retained[opened] = bar
            cursor = closed_at
            chunk_index += 1
        bars = tuple(retained[key] for key in sorted(retained))
        if not bars:
            raise RuntimeError("no GBPUSD historical M5 evidence in frozen interval")
        if bars[0].opened_at > ACQUISITION_OPEN + timedelta(days=10):
            raise RuntimeError("provider history does not reach frozen warm-up boundary")
        if bars[-1].closed_at < EVAL_CLOSE - timedelta(days=10):
            raise RuntimeError("provider history does not reach frozen holdout close")
        return Evidence(symbol=SYMBOL, digits=digits, bars=bars)
    finally:
        client.close()


def evidence_payload(evidence: Evidence) -> dict[str, Any]:
    return {
        "schema": "qore.turtle_soup_gbpusd_r1.holdout_evidence.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "fresh_relative_to_documented_project_windows": False,
        "acquisition_opened_at": ACQUISITION_OPEN.isoformat(),
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
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
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def load_evidence(path: Path) -> Evidence:
    payload = json.loads(path.read_text())
    if payload.get("identity") != IDENTITY or payload.get("holdout_id") != HOLDOUT_ID:
        raise ValueError("unexpected GBPUSD R1 evidence identity")
    if payload.get("read_only") is not True:
        raise ValueError("holdout evidence must be read-only")
    if _dt(str(payload["evaluation_opened_at"])) != EVAL_OPEN:
        raise ValueError("holdout evaluation open drift")
    if _dt(str(payload["evaluation_closed_at"])) != EVAL_CLOSE:
        raise ValueError("holdout evaluation close drift")
    symbol = str(payload["symbol"]["symbol_name"])
    if symbol != SYMBOL:
        raise ValueError(f"expected {SYMBOL}, got {symbol}")
    digits = int(payload["symbol"]["digits"])
    bars = tuple(
        Bar(
            opened_at=_dt(str(item["opened_at"])),
            closed_at=_dt(str(item["closed_at"])),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
        )
        for item in payload["periods"]["M5"]
    )
    return Evidence(symbol=symbol, digits=digits, bars=bars)


def exact_c2_side(c1: SourceCandle, c2: SourceCandle) -> Side | None:
    bullish = c2.low < c1.low and c2.close > c1.low
    bearish = c2.high > c1.high and c2.close < c1.high
    if bullish == bearish:
        return None
    return Side.LONG if bullish else Side.SHORT


def _m5_sources(bars: Sequence[Bar]) -> tuple[SourceCandle, ...]:
    return tuple(
        SourceCandle(
            opened_at=bar.opened_at,
            closed_at=bar.closed_at,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            m5=(bar,),
        )
        for bar in bars
    )


def _prior_alignment(c1: SourceCandle, side: Side) -> str:
    if c1.close == c1.open:
        return "doji"
    aligned = c1.close > c1.open if side is Side.LONG else c1.close < c1.open
    return "aligned" if aligned else "opposed"


def _raid_at(c2: SourceCandle, c1: SourceCandle, side: Side) -> datetime | None:
    for bar in c2.m5:
        if side is Side.LONG and bar.low < c1.low:
            return bar.opened_at
        if side is Side.SHORT and bar.high > c1.high:
            return bar.opened_at
    return None


def _target_untouched(c2: SourceCandle, side: Side, target: Decimal) -> bool:
    if side is Side.LONG:
        return all(bar.high < target for bar in c2.m5)
    return all(bar.low > target for bar in c2.m5)


def _source_signals(
    candles: tuple[SourceCandle, ...], timeframe: str
) -> tuple[list[Signal], Counter[str]]:
    result: list[Signal] = []
    funnel: Counter[str] = Counter()
    for index in range(1, len(candles) - 1):
        c1, c2, next_source = candles[index - 1], candles[index], candles[index + 1]
        entry_at = next_source.opened_at
        if not EVAL_OPEN <= entry_at < EVAL_CLOSE:
            continue
        funnel[f"{timeframe}:source-cycles"] += 1
        side = exact_c2_side(c1, c2)
        if side is None:
            funnel[f"{timeframe}:no-exact-c2"] += 1
            continue
        funnel[f"{timeframe}:exact-c2"] += 1
        raid_at = _raid_at(c2, c1, side)
        if raid_at is None:
            funnel[f"{timeframe}:missing-causal-raid"] += 1
            continue
        lower = _m5_sources(c2.m5) if timeframe == "H1" else build_m15(c2.m5)
        extreme = c2.low if side is Side.LONG else c2.high
        cisd = causal_cisd(lower, side=side, extreme=extreme)
        if cisd is None or cisd.confirmed_at > c2.closed_at:
            funnel[f"{timeframe}:no-causal-cisd"] += 1
            continue
        funnel[f"{timeframe}:causal-cisd"] += 1
        entry = next_source.open
        stop = cisd.protected_swing
        target = c1.high if side is Side.LONG else c1.low
        risk = entry - stop if side is Side.LONG else stop - entry
        reward = target - entry if side is Side.LONG else entry - target
        if risk <= 0 or reward <= 0:
            funnel[f"{timeframe}:invalid-entry-geometry"] += 1
            continue
        if not _target_untouched(c2, side, target):
            funnel[f"{timeframe}:opposite-boundary-already-touched"] += 1
            continue
        result.append(
            Signal(
                timeframe=timeframe,
                side=side,
                c1_opened_at=c1.opened_at,
                c2_opened_at=c2.opened_at,
                raid_at=raid_at,
                cisd_at=cisd.confirmed_at,
                entry_at=entry_at,
                entry=entry,
                protected_swing=stop,
                target=target,
                projected_r=reward / risk,
                session_bucket=_session_bucket(raid_at),
                prior_body_alignment=_prior_alignment(c1, side),
            )
        )
        funnel[f"{timeframe}:signal"] += 1
    return result, funnel


def _simulate(evidence: Evidence, signal: Signal) -> Trade:
    stop = signal.protected_swing
    risk = signal.entry - stop if signal.side is Side.LONG else stop - signal.entry
    reward = (
        signal.target - signal.entry
        if signal.side is Side.LONG
        else signal.entry - signal.target
    )
    closed_at = min(signal.entry_at + MAX_LIFETIME, EVAL_CLOSE)
    path = tuple(
        bar
        for bar in evidence.bars
        if signal.entry_at <= bar.opened_at < closed_at
    )
    if not path:
        raise ValueError("empty execution path for frozen GBPUSD R1 signal")
    exit_at: datetime | None = None
    exit_price: Decimal | None = None
    exit_reason = "time-24h"
    gross_r: Decimal | None = None
    for bar in path:
        if signal.side is Side.LONG:
            if bar.open <= stop:
                exit_at, exit_price = bar.opened_at, bar.open
                exit_reason = "gap-stop"
                gross_r = (bar.open - signal.entry) / risk
                break
            if bar.open >= signal.target:
                exit_at, exit_price = bar.opened_at, signal.target
                exit_reason = "gap-target-capped"
                gross_r = reward / risk
                break
            stop_touch = bar.low <= stop
            target_touch = bar.high >= signal.target
        else:
            if bar.open >= stop:
                exit_at, exit_price = bar.opened_at, bar.open
                exit_reason = "gap-stop"
                gross_r = (signal.entry - bar.open) / risk
                break
            if bar.open <= signal.target:
                exit_at, exit_price = bar.opened_at, signal.target
                exit_reason = "gap-target-capped"
                gross_r = reward / risk
                break
            stop_touch = bar.high >= stop
            target_touch = bar.low <= signal.target
        if stop_touch and target_touch:
            exit_at, exit_price, exit_reason, gross_r = (
                bar.closed_at,
                stop,
                "stop-first",
                Decimal(-1),
            )
            break
        if stop_touch:
            exit_at, exit_price, exit_reason, gross_r = (
                bar.closed_at,
                stop,
                "stop",
                Decimal(-1),
            )
            break
        if target_touch:
            exit_at, exit_price, exit_reason, gross_r = (
                bar.closed_at,
                signal.target,
                "target",
                reward / risk,
            )
            break
    if gross_r is None or exit_at is None or exit_price is None:
        final = path[-1]
        exit_at = final.closed_at
        exit_price = final.close
        gross_r = (
            (final.close - signal.entry) / risk
            if signal.side is Side.LONG
            else (signal.entry - final.close) / risk
        )
    return Trade(
        timeframe=signal.timeframe,
        side=signal.side,
        c1_opened_at=signal.c1_opened_at,
        c2_opened_at=signal.c2_opened_at,
        raid_at=signal.raid_at,
        cisd_at=signal.cisd_at,
        entry_at=signal.entry_at,
        exit_at=exit_at,
        entry=signal.entry,
        stop=stop,
        target=signal.target,
        exit_price=exit_price,
        projected_r=signal.projected_r,
        gross_r=gross_r,
        primary_net_r=gross_r - PRIMARY_FRICTION_R,
        stress_net_r=gross_r - STRESS_FRICTION_R,
        exit_reason=exit_reason,
        session_bucket=signal.session_bucket,
        prior_body_alignment=signal.prior_body_alignment,
    )


def replay(evidence: Evidence) -> tuple[list[Trade], Counter[str]]:
    if evidence.symbol != SYMBOL:
        raise ValueError(f"expected {SYMBOL}")
    h1_signals, h1_funnel = _source_signals(build_h1(evidence.bars), "H1")
    h4_signals, h4_funnel = _source_signals(build_h4(evidence.bars), "H4")
    funnel = h1_funnel + h4_funnel
    signals = sorted(
        h1_signals + h4_signals,
        key=lambda item: (item.entry_at, TIMEFRAME_PRIORITY[item.timeframe]),
    )
    trades: list[Trade] = []
    busy_until = EVAL_OPEN
    for signal in signals:
        if signal.entry_at < busy_until:
            funnel["overlap-skipped"] += 1
            continue
        trade = _simulate(evidence, signal)
        trades.append(trade)
        busy_until = trade.exit_at
        funnel["trade"] += 1
    return trades, funnel


def _max_losing_streak(values: Sequence[Decimal]) -> int:
    best = current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _stat(values: Sequence[Decimal]) -> dict[str, Any]:
    total = sum(values, Decimal(0))
    pf = _profit_factor(list(values))
    return {
        "count": len(values),
        "total_r": str(total),
        "mean_r": None if not values else str(total / len(values)),
        "profit_factor": None if pf is None else str(pf),
        "max_drawdown_r": str(_max_drawdown(list(values))),
        "max_losing_streak": _max_losing_streak(values),
    }


def _group_summary(trades: Sequence[Trade], attr: str) -> dict[str, Any]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for trade in trades:
        value = getattr(trade, attr)
        key = value.value if isinstance(value, StrEnum) else str(value)
        groups[key].append(trade.primary_net_r)
    return {key: _stat(values) for key, values in sorted(groups.items())}


def _quarter(moment: datetime) -> str:
    return f"{moment.year}-Q{((moment.month - 1) // 3) + 1}"


def _quarter_summary(trades: Sequence[Trade]) -> dict[str, Any]:
    groups: dict[str, list[Decimal]] = defaultdict(list)
    for trade in trades:
        groups[_quarter(trade.entry_at)].append(trade.primary_net_r)
    return {key: _stat(values) for key, values in sorted(groups.items())}


def _research_outcome(trades: Sequence[Trade]) -> tuple[str, dict[str, bool]]:
    primary = [item.primary_net_r for item in trades]
    stress = [item.stress_net_r for item in trades]
    primary_pf = _profit_factor(primary)
    stress_pf = _profit_factor(stress)
    midpoint = len(primary) // 2
    second_half = primary[midpoint:]
    quarters: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for trade in trades:
        quarters[_quarter(trade.entry_at)] += trade.primary_net_r
    positive_quarters = sum(value > 0 for value in quarters.values())
    checks = {
        "sample_at_least_30": len(trades) >= MIN_HOLDOUT_TRADES,
        "primary_total_r_positive": sum(primary, Decimal(0)) > 0,
        "primary_pf_above_one": primary_pf is not None and primary_pf > 1,
        "stress_total_r_positive": sum(stress, Decimal(0)) > 0,
        "stress_pf_above_one": stress_pf is not None and stress_pf > 1,
        "primary_max_drawdown_at_most_20r": _max_drawdown(primary)
        <= MAX_PRIMARY_DRAWDOWN_R,
        "second_half_primary_mean_positive": bool(second_half)
        and sum(second_half, Decimal(0)) / len(second_half) > 0,
        "positive_quarters_at_least_3": positive_quarters >= MIN_POSITIVE_QUARTERS,
    }
    if all(checks.values()):
        return "OOS_SURVIVED_RESEARCH_GATE_NOT_CERTIFIED", checks
    return "R1_REJECTED_FOR_PROMOTION", checks


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


def report(evidence: Evidence, output: Path) -> dict[str, Any]:
    trades, funnel = replay(evidence)
    ordered = sorted(trades, key=lambda item: item.entry_at)
    gross = [item.gross_r for item in ordered]
    primary = [item.primary_net_r for item in ordered]
    stress = [item.stress_net_r for item in ordered]
    outcome, checks = _research_outcome(ordered)
    midpoint = len(primary) // 2
    payload: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpusd_r1.holdout_result.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "symbol": SYMBOL,
        "evidence_status": "FRESH_HOLDOUT_CONSUMED_ON_EXECUTION",
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
        "candidate_contract": {
            "source_timeframes": ["H1", "H4"],
            "sides": ["long", "short"],
            "reference": "PRIOR_CANDLE_BOUNDARY",
            "closure": "EXACT_C2_REVERSAL",
            "confirmation": "CAUSAL_CISD_WITHIN_C2",
            "entry": "NEXT_SOURCE_OPEN",
            "stop": "PROTECTED_SWING_EXACT_NO_OFFSET",
            "target": "UNTOUCHED_C1_OPPOSITE_BOUNDARY",
            "maximum_lifetime_hours": 24,
            "single_position": True,
            "same_m5_bar_tie": "STOP_FIRST",
            "session_filter": None,
            "prior_body_filter": None,
            "fvg_filter": None,
            "equal_liquidity_filter": None,
            "minimum_projected_r": None,
            "c3_contract": "UNRESOLVED_NO_FROZEN_C3_CONTRACT",
        },
        "trades": len(ordered),
        "gross_wins": sum(value > 0 for value in gross),
        "gross_losses": sum(value < 0 for value in gross),
        "gross_flats": sum(value == 0 for value in gross),
        "gross": _stat(gross),
        "primary_005r_friction": _stat(primary),
        "stress_010r_friction": _stat(stress),
        "first_half_primary": _stat(primary[:midpoint]),
        "second_half_primary": _stat(primary[midpoint:]),
        "by_side_primary": _group_summary(ordered, "side"),
        "by_timeframe_primary": _group_summary(ordered, "timeframe"),
        "by_session_primary": _group_summary(ordered, "session_bucket"),
        "by_prior_body_alignment_primary": _group_summary(
            ordered, "prior_body_alignment"
        ),
        "by_quarter_primary": _quarter_summary(ordered),
        "funnel": dict(sorted(funnel.items())),
        "pre_registered_research_checks": checks,
        "research_outcome": outcome,
        "automatic_certification_allowed": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "canonical_trader_code": "CODE_UNASSIGNED",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "trades.json").write_text(
        json.dumps([_json_trade(item) for item in ordered], indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: module collect OUTPUT | replay EVIDENCE OUTPUT_DIR")
    command = sys.argv[1]
    if command == "collect":
        if len(sys.argv) != 3:
            raise SystemExit("collect OUTPUT")
        evidence = _collect_m5()
        Path(sys.argv[2]).write_text(
            json.dumps(evidence_payload(evidence), sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        return
    if command == "replay":
        if len(sys.argv) != 4:
            raise SystemExit("replay EVIDENCE OUTPUT_DIR")
        evidence = load_evidence(Path(sys.argv[2]))
        print(json.dumps(report(evidence, Path(sys.argv[3])), sort_keys=True))
        return
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
