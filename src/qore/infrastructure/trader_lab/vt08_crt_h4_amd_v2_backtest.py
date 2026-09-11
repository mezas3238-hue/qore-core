"""Reconstructed source-bound backtest for VT-08 V2 TTrades 4H PO3.

This runner deliberately invalidates the prior all-H4-window campaign.  It
processes only the source's institutional 1-5-9 (FX) or 2-6-10 (futures-style)
sequence, requires a one-sided daily bias, and permits at most one setup per
market/day.  Target/stop are explicit; H4-close leftovers are censored.
"""

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
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    FUTURES_STYLE_MARKETS,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2Setup,
    daily_bias,
    evaluate_candle2_expansion,
    evaluate_candle3_continuation,
    methodology_fingerprint,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v2"
_EVIDENCE_SCHEMA = "qore.ctrader_demo.vt08_crt_h4_amd_v2_evidence.v2"
_EXECUTION_MODEL = "source-daily-bias-one-sequence-m15-cisd-target-stop-censor-v2"
_NY = ZoneInfo("America/New_York")


class Vt08CrtH4AmdV2BacktestError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def candle(self) -> Vt08CrtH4AmdV2Candle:
        return Vt08CrtH4AmdV2Candle(
            self.opened_at,
            self.closed_at,
            self.open,
            self.high,
            self.low,
            self.close,
        )


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Trade:
    signal_at: datetime
    resolved_at: datetime | None
    side: str
    scenario: str
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    outcome: str
    r_multiple: Decimal | None
    mark_to_market_r_at_h4_close: Decimal
    mfe_r: Decimal
    mae_r: Decimal
    cisd_level: Decimal
    manipulation_fraction_of_reference: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": _iso(self.signal_at),
            "filled_at": _iso(self.signal_at),
            "resolved_at": _iso(self.resolved_at) if self.resolved_at else None,
            "side": self.side,
            "scenario": self.scenario,
            "entry_price": format(self.entry_price, "f"),
            "stop_loss": format(self.stop_loss, "f"),
            "take_profit": format(self.take_profit, "f"),
            "outcome": self.outcome,
            "r_multiple": format(self.r_multiple, "f") if self.r_multiple is not None else None,
            "mark_to_market_r_at_h4_close": format(self.mark_to_market_r_at_h4_close, "f"),
            "mfe_r": format(self.mfe_r, "f"),
            "mae_r": format(self.mae_r, "f"),
            "cisd_level": format(self.cisd_level, "f"),
            "manipulation_fraction_of_reference": format(
                self.manipulation_fraction_of_reference, "f"
            ),
        }


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Report:
    software_sha: str
    symbol: str
    provider_symbol_name: str
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    decision_days: int
    daily_bias_pass: int
    candle2_setup_count: int
    candle3_candidate_count: int
    setups: tuple[Vt08CrtH4AmdV2Trade, ...]

    def payload(self) -> dict[str, object]:
        terminal = tuple(item for item in self.setups if item.r_multiple is not None)
        values = tuple(cast(Decimal, item.r_multiple) for item in terminal)
        wins = sum(item.outcome == "target" for item in terminal)
        mtm = tuple(item.mark_to_market_r_at_h4_close for item in self.setups)
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "invalidates_prior_campaign": True,
            "invalidated_prior_schema": "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v1",
            "trader_code": "vt-08",
            "trader_version": "v2",
            "methodology": "ttrades-h4-po3-source-v2.1-reconstructed",
            "methodology_fingerprint": methodology_fingerprint(),
            "symbol": self.symbol,
            "provider_symbol_name": self.provider_symbol_name,
            "decision_timeframe": "M15",
            "execution_model": _EXECUTION_MODEL,
            "software_sha": self.software_sha,
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": _iso(self.checked_at),
            "source_sequence_policy": (
                "02-06-10-NY" if self.symbol in FUTURES_STYLE_MARKETS else "01-05-09-NY"
            ),
            "maximum_setups_per_ny_day": 1,
            "decision_days": self.decision_days,
            "daily_bias_pass": self.daily_bias_pass,
            "candle2_setup_count": self.candle2_setup_count,
            "candle3_candidate_count": self.candle3_candidate_count,
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
            "candle2_expansion_count": sum(
                item.scenario == Vt08CrtH4AmdV2Scenario.CANDLE2_EXPANSION.value
                for item in self.setups
            ),
            "candle3_continuation_count": sum(
                item.scenario == Vt08CrtH4AmdV2Scenario.CANDLE3_CONTINUATION.value
                for item in self.setups
            ),
            "win_rate_terminal_only": format(
                Decimal(wins) / Decimal(len(terminal)) if terminal else Decimal(0), "f"
            ),
            "terminal_expectancy_r": format(_mean(values), "f"),
            "population_variance_terminal_r": format(_variance(values), "f"),
            "max_drawdown_terminal_r": format(_max_drawdown(values), "f"),
            "descriptive_mean_h4_close_mark_to_market_r": format(_mean(mtm), "f"),
            "trades": [item.payload() for item in self.setups],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _object(value: object, field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be non-empty str")
    return value


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be bool")
    return value


def _timestamp(value: object, field: str) -> datetime:
    raw = _text(value, field)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, field: str) -> Decimal:
    raw = _text(value, field)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be decimal") from error
    if not result.is_finite() or result <= 0:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be positive finite")
    return result


def _bar(raw: object) -> _Bar:
    row = _object(raw, "bar")
    return _Bar(
        opened_at=_timestamp(row.get("opened_at"), "opened_at"),
        closed_at=_timestamp(row.get("closed_at"), "closed_at"),
        open=_decimal(row.get("open"), "open"),
        high=_decimal(row.get("high"), "high"),
        low=_decimal(row.get("low"), "low"),
        close=_decimal(row.get("close"), "close"),
    )


def _aggregate(bars: tuple[_Bar, ...]) -> Vt08CrtH4AmdV2Candle:
    if not bars:
        raise Vt08CrtH4AmdV2BacktestError("cannot aggregate empty window")
    return Vt08CrtH4AmdV2Candle(
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
    count: int,
) -> tuple[_Bar, ...] | None:
    start = datetime.combine(local_day, time(hour, 0), tzinfo=_NY)
    result: list[_Bar] = []
    for offset in range(count):
        item = by_local_open.get(start + timedelta(minutes=15 * offset))
        if item is None:
            return None
        result.append(item)
    if any(
        current.opened_at != previous.closed_at
        for previous, current in zip(result, result[1:], strict=False)
    ):
        return None
    return tuple(result)


def _load(path: Path) -> tuple[
    str,
    str,
    str,
    str,
    datetime,
    tuple[_Bar, ...],
    tuple[_Bar, ...],
    str,
]:
    try:
        payload = _object(json.loads(path.read_text(encoding="utf-8")), "market evidence")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08CrtH4AmdV2BacktestError("cannot read VT-08 V2 evidence") from error
    if _text(payload.get("schema"), "schema") != _EVIDENCE_SCHEMA:
        raise Vt08CrtH4AmdV2BacktestError("unexpected VT-08 V2 evidence schema")
    if _text(payload.get("environment"), "environment") != "demo":
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence must be DEMO")
    if not _boolean(payload.get("read_only"), "read_only"):
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence must be read-only")
    if _boolean(payload.get("account_is_live"), "account_is_live"):
        raise Vt08CrtH4AmdV2BacktestError("LIVE evidence is prohibited")
    software_sha = _text(payload.get("software_sha"), "software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt08CrtH4AmdV2BacktestError("software_sha must be exact Git SHA")
    account = _text(payload.get("account_fingerprint"), "account_fingerprint")
    if re.fullmatch(r"[0-9a-f]{64}", account) is None:
        raise Vt08CrtH4AmdV2BacktestError("account fingerprint must be SHA-256")
    symbol = _text(payload.get("canonical_symbol"), "canonical_symbol")
    provider = _text(payload.get("provider_symbol_name"), "provider_symbol_name")
    periods = _object(payload.get("periods"), "periods")
    if set(periods) != {"M15", "D1"}:
        raise Vt08CrtH4AmdV2BacktestError("V2 rebuilt evidence requires M15 and D1")
    m15 = tuple(_bar(item) for item in _array(periods.get("M15"), "M15"))
    d1 = tuple(_bar(item) for item in _array(periods.get("D1"), "D1"))
    if not m15 or m15 != tuple(sorted(m15, key=lambda item: item.opened_at)):
        raise Vt08CrtH4AmdV2BacktestError("M15 evidence must be chronological")
    if len(d1) < 2 or d1 != tuple(sorted(d1, key=lambda item: item.opened_at)):
        raise Vt08CrtH4AmdV2BacktestError("D1 evidence must be chronological")
    material = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return (
        software_sha,
        symbol,
        provider,
        account,
        _timestamp(payload.get("checked_at"), "checked_at"),
        m15,
        d1,
        sha256(material).hexdigest(),
    )


def _terminal_trade(
    setup: Vt08CrtH4AmdV2Setup,
    path: tuple[_Bar, ...],
    *,
    expected_terminal: datetime,
) -> Vt08CrtH4AmdV2Trade:
    side = setup.side
    entry = setup.entry_price
    stop = setup.stop_loss
    target = setup.take_profit
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        raise Vt08CrtH4AmdV2BacktestError("risk must be positive")
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    resolved_at: datetime | None = None
    outcome = "h4_close_censored"
    r_multiple: Decimal | None = None
    gap = not path or path[-1].closed_at != expected_terminal
    if gap:
        outcome = "gap_censored"
    for bar in path:
        if side is DemoTradingSetupSide.LONG:
            max_favorable = max(max_favorable, (bar.high - entry) / risk)
            max_adverse = max(max_adverse, (entry - bar.low) / risk)
            stop_hit = bar.low <= stop
            target_hit = bar.high >= target
        else:
            max_favorable = max(max_favorable, (entry - bar.low) / risk)
            max_adverse = max(max_adverse, (bar.high - entry) / risk)
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
    terminal_close = path[-1].close if path else entry
    mark = (
        (terminal_close - entry) / risk
        if side is DemoTradingSetupSide.LONG
        else (entry - terminal_close) / risk
    )
    return Vt08CrtH4AmdV2Trade(
        signal_at=setup.signal_at,
        resolved_at=resolved_at,
        side=side.value,
        scenario=setup.scenario.value,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        outcome=outcome,
        r_multiple=r_multiple,
        mark_to_market_r_at_h4_close=mark,
        mfe_r=max_favorable,
        mae_r=max_adverse,
        cisd_level=setup.cisd_level,
        manipulation_fraction_of_reference=setup.manipulation_fraction_of_reference,
    )


def _find_setup_in_c2(
    *,
    symbol: str,
    daily_reference: Vt08CrtH4AmdV2Candle,
    daily_signal: Vt08CrtH4AmdV2Candle,
    h4_reference: Vt08CrtH4AmdV2Candle,
    bars: tuple[_Bar, ...],
) -> Vt08CrtH4AmdV2Setup | None:
    for end in range(2, len(bars) + 1):
        evaluation = evaluate_candle2_expansion(
            symbol=symbol,
            daily_reference=daily_reference,
            daily_signal=daily_signal,
            h4_reference=h4_reference,
            h4_candle2_open=bars[0].open,
            h4_candle2_closes_at=bars[-1].closed_at,
            observed_m15=tuple(item.candle() for item in bars[:end]),
        )
        if evaluation.decision is DemoTradingDecision.SETUP:
            return evaluation.setup
    return None


def _find_setup_in_c3(
    *,
    symbol: str,
    daily_reference: Vt08CrtH4AmdV2Candle,
    daily_signal: Vt08CrtH4AmdV2Candle,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2: Vt08CrtH4AmdV2Candle,
    bars: tuple[_Bar, ...],
) -> Vt08CrtH4AmdV2Setup | None:
    for end in range(2, len(bars) + 1):
        evaluation = evaluate_candle3_continuation(
            symbol=symbol,
            daily_reference=daily_reference,
            daily_signal=daily_signal,
            h4_reference=h4_reference,
            h4_candle2=h4_candle2,
            h4_candle3_open=bars[0].open,
            h4_candle3_closes_at=bars[-1].closed_at,
            observed_m15=tuple(item.candle() for item in bars[:end]),
        )
        if evaluation.decision is DemoTradingDecision.SETUP:
            return evaluation.setup
    return None


def _path_after_signal(bars: tuple[_Bar, ...], signal_at: datetime) -> tuple[_Bar, ...]:
    return tuple(item for item in bars if item.opened_at >= signal_at)


def run_vt08_v2_backtest(path: Path) -> Vt08CrtH4AmdV2Report:
    software_sha, symbol, provider, account, checked_at, m15, d1, fingerprint = _load(path)
    by_local_open = {item.opened_at.astimezone(_NY): item for item in m15}
    local_days = sorted({item.opened_at.astimezone(_NY).date() for item in m15})
    anchors = (2, 6, 10) if symbol in FUTURES_STYLE_MARKETS else (1, 5, 9)
    decision_days = 0
    bias_pass = 0
    c2_count = 0
    c3_candidates = 0
    trades: list[Vt08CrtH4AmdV2Trade] = []

    for local_day in local_days:
        c1_bars = _exact_window(by_local_open, local_day, anchors[0], 16)
        c2_bars = _exact_window(by_local_open, local_day, anchors[1], 16)
        c3_bars = _exact_window(by_local_open, local_day, anchors[2], 16)
        if c1_bars is None or c2_bars is None or c3_bars is None:
            continue
        c1 = _aggregate(c1_bars)
        prior_daily = tuple(item for item in d1 if item.closed_at <= c1.opened_at)
        if len(prior_daily) < 2:
            continue
        decision_days += 1
        daily_reference = _aggregate((prior_daily[-2],))
        daily_signal = _aggregate((prior_daily[-1],))
        bias = daily_bias(daily_reference, daily_signal)
        if bias is None:
            continue
        bias_pass += 1

        c2_setup = _find_setup_in_c2(
            symbol=symbol,
            daily_reference=daily_reference,
            daily_signal=daily_signal,
            h4_reference=c1,
            bars=c2_bars,
        )
        if c2_setup is not None:
            c2_count += 1
            path_bars = _path_after_signal(c2_bars, c2_setup.signal_at)
            trades.append(
                _terminal_trade(
                    c2_setup,
                    path_bars,
                    expected_terminal=c2_bars[-1].closed_at,
                )
            )
            continue

        c2 = _aggregate(c2_bars)
        c3_candidates += 1
        c3_setup = _find_setup_in_c3(
            symbol=symbol,
            daily_reference=daily_reference,
            daily_signal=daily_signal,
            h4_reference=c1,
            h4_candle2=c2,
            bars=c3_bars,
        )
        if c3_setup is None:
            continue
        path_bars = _path_after_signal(c3_bars, c3_setup.signal_at)
        trades.append(
            _terminal_trade(
                c3_setup,
                path_bars,
                expected_terminal=c3_bars[-1].closed_at,
            )
        )

    by_day: set[tuple[date, str]] = set()
    for trade in trades:
        key = (trade.signal_at.astimezone(_NY).date(), symbol)
        if key in by_day:
            raise Vt08CrtH4AmdV2BacktestError("source contract permits at most one setup/day")
        by_day.add(key)

    return Vt08CrtH4AmdV2Report(
        software_sha=software_sha,
        symbol=symbol,
        provider_symbol_name=provider,
        account_fingerprint=account,
        evidence_fingerprint=fingerprint,
        checked_at=checked_at,
        decision_days=decision_days,
        daily_bias_pass=bias_pass,
        candle2_setup_count=c2_count,
        candle3_candidate_count=c3_candidates,
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
        raise SystemExit("usage: vt08_crt_h4_amd_v2_backtest <market-evidence.json>")
    print(run_vt08_v2_backtest(Path(args[0])).to_json())


if __name__ == "__main__":
    main()
