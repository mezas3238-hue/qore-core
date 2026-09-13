"""Retained VT-08 evidence and conservative CIBO trade replay for R3.16."""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

CHALLENGE_RUN_ID = 34759027136
LONG_RUN_ID = 34693803930
CHALLENGE_SHA = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
LONG_SHA = "b65d32ea03d3b471997d7955db37cf9a2d41ddaa"
CHALLENGE_START = date(2020, 7, 1)
CHALLENGE_END = date(2022, 7, 1)
LONG_START = date(2024, 8, 13)
LONG_END = date(2026, 9, 12)
PRIMARY_COST_BPS = 0.50
REQUIRED_SYMBOLS = ("AUDJPY", "GBPUSD", "GBPJPY")
PORTFOLIOS = ("A_CORE", "GBPJPY_RETURN_ENHANCER", "B_COMBINED_PORTFOLIO")
_NY = ZoneInfo("America/New_York")


class CiboCapitalProtectionError(ValueError):
    """Raised when retained evidence or R3.16 invariants fail."""


@dataclass(frozen=True, slots=True)
class StopPolicy:
    name: str
    ratchets: tuple[tuple[float, float], ...]


STOP_POLICIES = (
    StopPolicy("off", ()),
    StopPolicy("soft", ((0.75, -0.50), (1.25, 0.00), (1.60, 0.50))),
    StopPolicy("be050-lock050-at100", ((0.50, 0.00), (1.00, 0.50))),
    StopPolicy("aggressive", ((0.50, 0.00), (1.00, 0.50), (1.50, 1.00))),
)


@dataclass(frozen=True, slots=True)
class Bar:
    opened_at: datetime
    closed_at: datetime
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    side: str
    signal_at: datetime
    entry: float
    stop: float
    target: float
    exit_price: float
    exit_reason: str

    @property
    def risk_price(self) -> float:
        return abs(self.entry - self.stop)

    @property
    def signal_key(self) -> tuple[str, str, str]:
        return (self.signal_at.isoformat(), self.symbol, self.side)


@dataclass(frozen=True, slots=True)
class ReplayTrade:
    signal_key: tuple[str, str, str]
    day: date
    anchor: int
    symbol: str
    side: str
    sleeve: str
    gross_r: float
    net_r: float
    exit_reason: str
    baseline_exit_reason: str


def _read_json(path: Path) -> dict[str, object]:
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if type(decoded) is not dict:
        raise CiboCapitalProtectionError(f"{path} must contain one JSON object")
    return cast(dict[str, object], decoded)


def _timestamp(value: object) -> datetime:
    if type(value) is not str:
        raise CiboCapitalProtectionError("timestamp must be text")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalProtectionError("timestamp must be timezone-aware")
    return result.astimezone(UTC)


def _float(value: object, *, name: str) -> float:
    if type(value) not in (str, int, float):
        raise CiboCapitalProtectionError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CiboCapitalProtectionError(f"{name} must be finite")
    return result


def load_period(
    root: Path,
    *,
    expected_sha: str,
) -> tuple[list[Trade], dict[str, dict[datetime, Bar]]]:
    trades: list[Trade] = []
    bars: dict[str, dict[datetime, Bar]] = {}
    seen: set[str] = set()
    for backtest_path in sorted(root.rglob("b01-backtest.json")):
        payload = _read_json(backtest_path)
        symbol = str(payload.get("symbol", ""))
        if symbol not in REQUIRED_SYMBOLS:
            continue
        if symbol in seen:
            raise CiboCapitalProtectionError(f"duplicate retained artifact for {symbol}")
        seen.add(symbol)
        if payload.get("trader_code") != "vt-08":
            raise CiboCapitalProtectionError("retained backtest does not belong to VT-08")
        if payload.get("software_sha") != expected_sha:
            raise CiboCapitalProtectionError(f"unexpected retained SHA for {symbol}")
        evidence_path = backtest_path.with_name("market-evidence.json")
        if not evidence_path.exists():
            raise CiboCapitalProtectionError(f"missing market evidence for {symbol}")
        evidence = _read_json(evidence_path)
        if evidence.get("environment") != "demo" or evidence.get("read_only") is not True:
            raise CiboCapitalProtectionError("R3.16 accepts only retained read-only DEMO evidence")
        if evidence.get("account_is_live") is not False:
            raise CiboCapitalProtectionError("LIVE market evidence is prohibited")
        periods = evidence.get("periods")
        if not isinstance(periods, Mapping) or not isinstance(periods.get("M15"), list):
            raise CiboCapitalProtectionError("market evidence missing M15 bars")
        symbol_bars: dict[datetime, Bar] = {}
        for raw in cast(list[object], periods["M15"]):
            if not isinstance(raw, Mapping):
                raise CiboCapitalProtectionError("M15 row must be an object")
            opened_at = _timestamp(raw.get("opened_at"))
            symbol_bars[opened_at] = Bar(
                opened_at=opened_at,
                closed_at=_timestamp(raw.get("closed_at")),
                high=_float(raw.get("high"), name="high"),
                low=_float(raw.get("low"), name="low"),
                close=_float(raw.get("close"), name="close"),
            )
        bars[symbol] = symbol_bars
        raw_trades = payload.get("trades")
        if not isinstance(raw_trades, list):
            raise CiboCapitalProtectionError("retained backtest missing trades")
        for raw in raw_trades:
            if not isinstance(raw, Mapping):
                raise CiboCapitalProtectionError("trade row must be an object")
            trades.append(
                Trade(
                    symbol=symbol,
                    side=str(raw.get("side")),
                    signal_at=_timestamp(raw.get("signal_at")),
                    entry=_float(raw.get("entry"), name="entry"),
                    stop=_float(raw.get("stop"), name="stop"),
                    target=_float(raw.get("target"), name="target"),
                    exit_price=_float(raw.get("exit_price"), name="exit_price"),
                    exit_reason=str(raw.get("exit_reason")),
                )
            )
    if seen != set(REQUIRED_SYMBOLS):
        raise CiboCapitalProtectionError(
            f"retained evidence must contain exactly A/GBPJPY symbols: {sorted(seen)}"
        )
    return sorted(trades, key=lambda item: item.signal_key), bars


def _stop_price(trade: Trade, stop_r: float) -> float:
    if trade.side == "long":
        return trade.entry + stop_r * trade.risk_price
    return trade.entry - stop_r * trade.risk_price


def _stop_touched(trade: Trade, price: float, bar: Bar) -> bool:
    return bar.low <= price if trade.side == "long" else bar.high >= price


def _target_touched(trade: Trade, bar: Bar) -> bool:
    return bar.high >= trade.target if trade.side == "long" else bar.low <= trade.target


def _favorable_r(trade: Trade, bar: Bar) -> float:
    if trade.side == "long":
        return (bar.high - trade.entry) / trade.risk_price
    return (trade.entry - bar.low) / trade.risk_price


def _close_r(trade: Trade, close: float) -> float:
    if trade.side == "long":
        return (close - trade.entry) / trade.risk_price
    return (trade.entry - close) / trade.risk_price


def replay_trade(
    trade: Trade,
    bars: Mapping[datetime, Bar],
    stop_policy: StopPolicy,
) -> tuple[float, str]:
    if trade.risk_price <= 0:
        raise CiboCapitalProtectionError("trade risk distance must be positive")
    current_stop_r = -1.0
    cursor = trade.signal_at
    end = cursor + timedelta(hours=4)
    last: Bar | None = None
    while cursor < end:
        bar = bars.get(cursor)
        if bar is None:
            raise CiboCapitalProtectionError(
                f"missing M15 bar for {trade.symbol} at {cursor.isoformat()}"
            )
        last = bar
        # Conservative: the stop active at bar open is evaluated before target.
        # A threshold reached inside this bar can protect only later bars.
        if _stop_touched(trade, _stop_price(trade, current_stop_r), bar):
            reason = "stop" if current_stop_r <= -0.999999 else "cibo_protected_stop"
            return current_stop_r, reason
        if _target_touched(trade, bar):
            return 2.0, "target"
        favorable = _favorable_r(trade, bar)
        for trigger_r, lock_r in stop_policy.ratchets:
            if favorable >= trigger_r and lock_r > current_stop_r:
                current_stop_r = lock_r
        cursor += timedelta(minutes=15)
    if last is None:
        raise CiboCapitalProtectionError("trade replay has no retained bars")
    return _close_r(trade, last.close), "h4_containment_exit"


def _cost_r(trade: Trade) -> float:
    return trade.entry * (PRIMARY_COST_BPS / 10_000.0) / trade.risk_price


def build_records(
    trades: Sequence[Trade],
    bars: Mapping[str, Mapping[datetime, Bar]],
    stop_policy: StopPolicy,
    *,
    opened: date,
    closed: date,
) -> list[ReplayTrade]:
    result: list[ReplayTrade] = []
    for trade in trades:
        local = trade.signal_at.astimezone(_NY)
        if not opened <= local.date() < closed:
            continue
        gross_r, reason = replay_trade(trade, bars[trade.symbol], stop_policy)
        result.append(
            ReplayTrade(
                signal_key=trade.signal_key,
                day=local.date(),
                anchor=local.hour,
                symbol=trade.symbol,
                side=trade.side,
                sleeve="G" if trade.symbol == "GBPJPY" else "A",
                gross_r=gross_r,
                net_r=gross_r - _cost_r(trade),
                exit_reason=reason,
                baseline_exit_reason=trade.exit_reason,
            )
        )
    return result


def portfolio_record(record: ReplayTrade, portfolio: str) -> bool:
    if portfolio == "A_CORE":
        return record.sleeve == "A" and record.side == "short"
    if portfolio == "GBPJPY_RETURN_ENHANCER":
        return record.sleeve == "G"
    if portfolio == "B_COMBINED_PORTFOLIO":
        return record.sleeve == "G" or (record.sleeve == "A" and record.side == "short")
    raise CiboCapitalProtectionError(f"unknown portfolio {portfolio}")


def signal_identity(
    records: Iterable[ReplayTrade],
    portfolio: str,
) -> tuple[tuple[str, str, str], ...]:
    return tuple(sorted(item.signal_key for item in records if portfolio_record(item, portfolio)))
