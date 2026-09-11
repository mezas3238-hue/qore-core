"""Broker-backed historical research runner for VT-08 CRT 1-5-9 V3."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_159_v3 import (
    Vt08Crt159V3Candle,
    Vt08Crt159V3Input,
    crt_direction,
    evaluate_vt08_crt_159_v3,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_crt_159_v3_backtest.v1"
_EVIDENCE_SCHEMA = "qore.ctrader_demo.vt08_crt_159_v3_evidence.v1"
_EXECUTION_MODEL = "nested-crt-market-entry-1130-ny-h4-target-stop-first-censor-v1"
_NY = ZoneInfo("America/New_York")


class Vt08Crt159V3BacktestError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class Vt08Crt159V3Trade:
    signal_at: datetime
    resolved_at: datetime | None
    side: str
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    daily_target: Decimal
    outcome: str
    r_multiple: Decimal | None
    mfe_r: Decimal
    mae_r: Decimal
    daily_target_touched: bool

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": _iso(self.signal_at),
            "filled_at": _iso(self.signal_at),
            "resolved_at": _iso(self.resolved_at) if self.resolved_at else None,
            "side": self.side,
            "entry_price": format(self.entry_price, "f"),
            "stop_loss": format(self.stop_loss, "f"),
            "take_profit": format(self.take_profit, "f"),
            "daily_target": format(self.daily_target, "f"),
            "outcome": self.outcome,
            "r_multiple": format(self.r_multiple, "f") if self.r_multiple is not None else None,
            "mfe_r": format(self.mfe_r, "f"),
            "mae_r": format(self.mae_r, "f"),
            "daily_target_touched": self.daily_target_touched,
        }


@dataclass(frozen=True, slots=True)
class Vt08Crt159V3Report:
    software_sha: str
    symbol: str
    provider_symbol_name: str
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    decision_days: int
    daily_context_pass: int
    h4_159_pass: int
    h1_nested_pass: int
    m15_nested_pass: int
    direction_agreement_pass: int
    setups: tuple[Vt08Crt159V3Trade, ...]

    def payload(self) -> dict[str, object]:
        terminal = tuple(item for item in self.setups if item.r_multiple is not None)
        values = tuple(cast(Decimal, item.r_multiple) for item in terminal)
        wins = sum(item.outcome == "target" for item in terminal)
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "trader_code": "vt-08",
            "trader_version": "v3",
            "methodology": "crt-159-fractal-nested-v3",
            "symbol": self.symbol,
            "provider_symbol_name": self.provider_symbol_name,
            "decision_timeframe": "M15",
            "execution_model": _EXECUTION_MODEL,
            "software_sha": self.software_sha,
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": _iso(self.checked_at),
            "decision_days": self.decision_days,
            "daily_context_pass": self.daily_context_pass,
            "h4_159_pass": self.h4_159_pass,
            "h1_nested_pass": self.h1_nested_pass,
            "m15_nested_pass": self.m15_nested_pass,
            "direction_agreement_pass": self.direction_agreement_pass,
            "setup_count": len(self.setups),
            "filled_count": len(self.setups),
            "terminal_sample_size": len(terminal),
            "target_count": sum(item.outcome == "target" for item in terminal),
            "stop_count": sum(item.outcome == "stop" for item in terminal),
            "h4_close_censored_count": sum(
                item.outcome == "h4_close_censored" for item in self.setups
            ),
            "gap_censored_count": sum(item.outcome == "gap_censored" for item in self.setups),
            "long_trade_count": sum(item.side == "long" for item in self.setups),
            "short_trade_count": sum(item.side == "short" for item in self.setups),
            "win_rate": format(Decimal(wins) / Decimal(len(terminal)) if terminal else Decimal(0), "f"),
            "expectancy_r": format(_mean(values), "f"),
            "population_variance_r": format(_variance(values), "f"),
            "max_drawdown_r": format(_max_drawdown(values), "f"),
            "daily_target_touch_count": sum(item.daily_target_touched for item in self.setups),
            "trades": [item.payload() for item in self.setups],
        }

    def to_json(self) -> str:
        return json.dumps(self.payload(), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _object(value: object, *, field: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08Crt159V3BacktestError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, *, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08Crt159V3BacktestError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08Crt159V3BacktestError(f"{field} must be non-empty str")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise Vt08Crt159V3BacktestError(f"{field} must be bool")
    return value


def _timestamp(value: object, *, field: str) -> datetime:
    raw = _text(value, field=field)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08Crt159V3BacktestError(f"{field} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08Crt159V3BacktestError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, field: str) -> Decimal:
    raw = _text(value, field=field)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08Crt159V3BacktestError(f"{field} must be decimal") from error
    if not result.is_finite() or result <= 0:
        raise Vt08Crt159V3BacktestError(f"{field} must be positive finite")
    return result


def _bar(raw: object) -> _Bar:
    row = _object(raw, field="bar")
    return _Bar(
        opened_at=_timestamp(row.get("opened_at"), field="opened_at"),
        closed_at=_timestamp(row.get("closed_at"), field="closed_at"),
        open=_decimal(row.get("open"), field="open"),
        high=_decimal(row.get("high"), field="high"),
        low=_decimal(row.get("low"), field="low"),
        close=_decimal(row.get("close"), field="close"),
    )


def _candle(bars: tuple[_Bar, ...]) -> Vt08Crt159V3Candle:
    if not bars:
        raise Vt08Crt159V3BacktestError("cannot aggregate empty candle")
    return Vt08Crt159V3Candle(
        opened_at=bars[0].opened_at,
        closed_at=bars[-1].closed_at,
        open=bars[0].open,
        high=max(item.high for item in bars),
        low=min(item.low for item in bars),
        close=bars[-1].close,
    )


def _exact_window(
    by_local_open: dict[datetime, _Bar],
    local_day: date,
    hour: int,
    minute: int,
    count: int,
) -> tuple[_Bar, ...] | None:
    start = datetime.combine(local_day, time(hour, minute), tzinfo=_NY)
    result: list[_Bar] = []
    for offset in range(count):
        local_open = start + timedelta(minutes=15 * offset)
        item = by_local_open.get(local_open)
        if item is None:
            return None
        result.append(item)
    for previous, current in zip(result, result[1:], strict=False):
        if current.opened_at != previous.closed_at:
            return None
    return tuple(result)


def _load(path: Path) -> tuple[str, str, str, str, datetime, tuple[_Bar, ...], tuple[_Bar, ...], str]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08Crt159V3BacktestError("cannot read VT-08 V3 market evidence") from error
    payload = _object(decoded, field="market evidence")
    if _text(payload.get("schema"), field="schema") != _EVIDENCE_SCHEMA:
        raise Vt08Crt159V3BacktestError("unexpected VT-08 V3 evidence schema")
    if _text(payload.get("environment"), field="environment") != "demo":
        raise Vt08Crt159V3BacktestError("VT-08 V3 evidence must be DEMO")
    if not _boolean(payload.get("read_only"), field="read_only"):
        raise Vt08Crt159V3BacktestError("VT-08 V3 evidence must be read-only")
    if _boolean(payload.get("account_is_live"), field="account_is_live"):
        raise Vt08Crt159V3BacktestError("LIVE evidence is prohibited")
    symbol = _text(payload.get("canonical_symbol"), field="canonical_symbol")
    provider = _text(payload.get("provider_symbol_name"), field="provider_symbol_name")
    account = _text(payload.get("account_fingerprint"), field="account_fingerprint")
    if re.fullmatch(r"[0-9a-f]{64}", account) is None:
        raise Vt08Crt159V3BacktestError("account_fingerprint must be SHA-256")
    software_sha = _text(payload.get("software_sha"), field="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt08Crt159V3BacktestError("software_sha must be exact Git SHA")
    periods = _object(payload.get("periods"), field="periods")
    if set(periods) != {"M15", "D1"}:
        raise Vt08Crt159V3BacktestError("VT-08 V3 evidence requires exact M15 and D1")
    m15 = tuple(_bar(item) for item in _array(periods.get("M15"), field="M15"))
    d1 = tuple(_bar(item) for item in _array(periods.get("D1"), field="D1"))
    if m15 != tuple(sorted(m15, key=lambda item: item.opened_at)):
        raise Vt08Crt159V3BacktestError("M15 evidence must be chronological")
    if d1 != tuple(sorted(d1, key=lambda item: item.opened_at)):
        raise Vt08Crt159V3BacktestError("D1 evidence must be chronological")
    fingerprint = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return software_sha, symbol, provider, account, _timestamp(payload.get("checked_at"), field="checked_at"), m15, d1, fingerprint


def _terminal_trade(
    setup: object,
    path: tuple[_Bar, ...],
) -> Vt08Crt159V3Trade:
    side = setup.side
    entry = setup.entry_price
    stop = setup.stop_loss
    target = setup.take_profit
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        raise Vt08Crt159V3BacktestError("risk geometry must be positive")
    expected_path = 6
    gap = len(path) != expected_path
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    daily_touched = False
    resolved_at: datetime | None = None
    outcome = "gap_censored" if gap else "h4_close_censored"
    r_multiple: Decimal | None = None
    for bar in path:
        if side is DemoTradingSetupSide.LONG:
            max_favorable = max(max_favorable, (bar.high - entry) / risk)
            max_adverse = max(max_adverse, (entry - bar.low) / risk)
            daily_touched = daily_touched or bar.high >= setup.daily_target
            stop_hit = bar.low <= stop
            target_hit = bar.high >= target
        else:
            max_favorable = max(max_favorable, (entry - bar.low) / risk)
            max_adverse = max(max_adverse, (bar.high - entry) / risk)
            daily_touched = daily_touched or bar.low <= setup.daily_target
            stop_hit = bar.high >= stop
            target_hit = bar.low <= target
        if stop_hit:
            outcome = "stop"
            r_multiple = Decimal(-1)
            resolved_at = bar.closed_at
            break
        if target_hit:
            outcome = "target"
            r_multiple = abs(target - entry) / risk
            resolved_at = bar.closed_at
            break
    return Vt08Crt159V3Trade(
        signal_at=setup.signal_at,
        resolved_at=resolved_at,
        side=side.value,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        daily_target=setup.daily_target,
        outcome=outcome,
        r_multiple=r_multiple,
        mfe_r=max_favorable,
        mae_r=max_adverse,
        daily_target_touched=daily_touched,
    )


def run_vt08_v3_backtest(path: Path) -> Vt08Crt159V3Report:
    software_sha, symbol, provider, account, checked_at, m15, d1, fingerprint = _load(path)
    by_local_open = {item.opened_at.astimezone(_NY): item for item in m15}
    local_days = sorted({item.opened_at.astimezone(_NY).date() for item in m15})
    decision_days = 0
    daily_pass = 0
    h4_pass = 0
    h1_pass = 0
    m15_pass = 0
    direction_pass = 0
    trades: list[Vt08Crt159V3Trade] = []
    for local_day in local_days:
        h4_ref_bars = _exact_window(by_local_open, local_day, 1, 0, 16)
        h4_man_bars = _exact_window(by_local_open, local_day, 5, 0, 16)
        h1_ref_bars = _exact_window(by_local_open, local_day, 9, 0, 4)
        h1_man_bars = _exact_window(by_local_open, local_day, 10, 0, 4)
        m15_ref_bars = _exact_window(by_local_open, local_day, 11, 0, 1)
        m15_man_bars = _exact_window(by_local_open, local_day, 11, 15, 1)
        entry_bars = _exact_window(by_local_open, local_day, 11, 30, 1)
        if any(
            item is None
            for item in (
                h4_ref_bars,
                h4_man_bars,
                h1_ref_bars,
                h1_man_bars,
                m15_ref_bars,
                m15_man_bars,
                entry_bars,
            )
        ):
            continue
        decision_days += 1
        h4_ref = _candle(cast(tuple[_Bar, ...], h4_ref_bars))
        prior_daily = tuple(item for item in d1 if item.closed_at <= h4_ref.opened_at)
        if len(prior_daily) < 2:
            continue
        daily_ref = _candle((prior_daily[-2],))
        daily_man = _candle((prior_daily[-1],))
        daily_side = crt_direction(daily_ref, daily_man)
        if daily_side is None:
            continue
        daily_pass += 1
        h4_man = _candle(cast(tuple[_Bar, ...], h4_man_bars))
        h4_side = crt_direction(h4_ref, h4_man)
        if h4_side is None:
            continue
        h4_pass += 1
        h1_ref = _candle(cast(tuple[_Bar, ...], h1_ref_bars))
        h1_man = _candle(cast(tuple[_Bar, ...], h1_man_bars))
        h1_side = crt_direction(h1_ref, h1_man)
        if h1_side is None:
            continue
        h1_pass += 1
        m15_ref = _candle(cast(tuple[_Bar, ...], m15_ref_bars))
        m15_man = _candle(cast(tuple[_Bar, ...], m15_man_bars))
        m15_side = crt_direction(m15_ref, m15_man)
        if m15_side is None:
            continue
        m15_pass += 1
        if len({daily_side, h4_side, h1_side, m15_side}) != 1:
            continue
        direction_pass += 1
        entry_bar = _candle(cast(tuple[_Bar, ...], entry_bars))
        expiry_local = datetime.combine(local_day, time(13, 0), tzinfo=_NY)
        evaluation = evaluate_vt08_crt_159_v3(
            Vt08Crt159V3Input(
                symbol=symbol,
                as_of=entry_bar.opened_at,
                daily_reference=daily_ref,
                daily_manipulation=daily_man,
                h4_reference_01=h4_ref,
                h4_manipulation_05=h4_man,
                h1_reference_09=h1_ref,
                h1_manipulation_10=h1_man,
                m15_reference_1100=m15_ref,
                m15_manipulation_1115=m15_man,
                entry_bar_1130=entry_bar,
                h4_distribution_closes_at=expiry_local.astimezone(UTC),
            )
        )
        if evaluation.decision is not DemoTradingDecision.SETUP or evaluation.setup is None:
            continue
        path = _exact_window(by_local_open, local_day, 11, 30, 6)
        trades.append(_terminal_trade(evaluation.setup, path or ()))
    return Vt08Crt159V3Report(
        software_sha=software_sha,
        symbol=symbol,
        provider_symbol_name=provider,
        account_fingerprint=account,
        evidence_fingerprint=fingerprint,
        checked_at=checked_at,
        decision_days=decision_days,
        daily_context_pass=daily_pass,
        h4_159_pass=h4_pass,
        h1_nested_pass=h1_pass,
        m15_nested_pass=m15_pass,
        direction_agreement_pass=direction_pass,
        setups=tuple(trades),
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values)) if values else Decimal(0)


def _variance(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        return Decimal(0)
    mean = _mean(values)
    return sum(((item - mean) ** 2 for item in values), Decimal(0)) / Decimal(len(values))


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: vt08_crt_159_v3_backtest <market-evidence.json>")
    print(run_vt08_v3_backtest(Path(args[0])).to_json())


if __name__ == "__main__":
    main()
