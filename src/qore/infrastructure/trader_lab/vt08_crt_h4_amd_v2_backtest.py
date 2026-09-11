"""Source-bound two-year backtest for VT-08 CRT / H4 PO3 AMD V2.

Unlike VT-08 V1 this runner does not impose the generic M5-FVG/24-bar model.
It derives the exact New-York-local source H4 windows from retained M15 bars,
waits for the V2 evaluator's lower-timeframe CISD, enters at that confirming
M15 close, keeps the manipulation extreme as invalidation, and measures the
remainder of the source H4 body.  If the stop is touched first the trade is -1R;
otherwise the source H4 close is the terminal research observation.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    Vt08CrtH4AmdV2Bar,
    Vt08CrtH4AmdV2H4Candle,
    Vt08CrtH4AmdV2Input,
    Vt08CrtH4AmdV2Setup,
    evaluate_vt08_crt_h4_amd_v2,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt08_crt_h4_amd_v2_backtest.v1"
_EVIDENCE_SCHEMA = "qore.ctrader_demo.vt08_crt_h4_amd_v2_m15_evidence.v1"
_EXECUTION_MODEL = "source-m15-cisd-entry-h4-close-stop-first-v1"
_REQUIRED_COVERAGE_DAYS = 730
_NY = ZoneInfo("America/New_York")
_INDEX_MARKETS = frozenset({"NAS100", "SP500", "US30"})
_FOREX_ANCHORS = (1, 5, 9, 13, 17, 21)
_FUTURES_ANCHORS = (2, 6, 10, 14, 18, 22)


class Vt08CrtH4AmdV2BacktestError(InfrastructureError):
    """Source-bound VT-08 V2 historical research failed closed."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Trade:
    signal_at: datetime
    resolved_at: datetime
    side: str
    profile: str
    htf_closure: str
    entry_price: Decimal
    stop_loss: Decimal
    exit_price: Decimal
    outcome: str
    r_multiple: Decimal
    mfe_r: Decimal
    mae_r: Decimal
    h4_opened_at: datetime
    h4_closed_at: datetime

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": _iso(self.signal_at),
            "filled_at": _iso(self.signal_at),
            "resolved_at": _iso(self.resolved_at),
            "side": self.side,
            "profile": self.profile,
            "htf_closure": self.htf_closure,
            "entry_price": format(self.entry_price, "f"),
            "stop_loss": format(self.stop_loss, "f"),
            "exit_price": format(self.exit_price, "f"),
            "outcome": self.outcome,
            "r_multiple": format(self.r_multiple, "f"),
            "mfe_r": format(self.mfe_r, "f"),
            "mae_r": format(self.mae_r, "f"),
            "h4_opened_at": _iso(self.h4_opened_at),
            "h4_closed_at": _iso(self.h4_closed_at),
        }


@dataclass(frozen=True, slots=True)
class _SourceWindow:
    opened_at: datetime
    closed_at: datetime
    bars: tuple[Vt08CrtH4AmdV2Bar, ...]
    candle: Vt08CrtH4AmdV2H4Candle


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2BacktestReport:
    software_sha: str
    symbol: str
    provider_symbol_name: str
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    complete_h4_windows: int
    incomplete_h4_windows: int
    eligible_h4_windows: int
    trades: tuple[Vt08CrtH4AmdV2Trade, ...]

    def payload(self) -> dict[str, object]:
        values = tuple(item.r_multiple for item in self.trades)
        wins = sum(item.r_multiple > 0 for item in self.trades)
        expectancy = _mean(values)
        win_rate = Decimal(wins) / Decimal(len(values)) if values else Decimal(0)
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "trader_code": "vt-08",
            "trader_version": "v2",
            "methodology": "crt-h4-po3-amd-source-v2",
            "symbol": self.symbol,
            "provider_symbol_name": self.provider_symbol_name,
            "decision_timeframe": "M15",
            "higher_timeframe": "source-aligned-H4-derived-from-M15",
            "execution_model": _EXECUTION_MODEL,
            "software_sha": self.software_sha,
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": _iso(self.checked_at),
            "complete_h4_windows": self.complete_h4_windows,
            "incomplete_h4_windows": self.incomplete_h4_windows,
            "eligible_h4_windows": self.eligible_h4_windows,
            "setup_count": len(self.trades),
            "filled_count": len(self.trades),
            "terminal_sample_size": len(self.trades),
            "win_rate": format(win_rate, "f"),
            "expectancy_r": format(expectancy, "f"),
            "population_variance_r": format(_variance(values), "f"),
            "max_drawdown_r": format(_max_drawdown(values), "f"),
            "stop_count": sum(item.outcome == "stop" for item in self.trades),
            "h4_close_count": sum(item.outcome == "h4_close" for item in self.trades),
            "continuation_count": sum(
                item.profile == "continuation-expansion" for item in self.trades
            ),
            "reversal_count": sum(
                item.profile == "reversal-expansion" for item in self.trades
            ),
            "long_trade_count": sum(item.side == "long" for item in self.trades),
            "short_trade_count": sum(item.side == "short" for item in self.trades),
            "segment_metrics": {
                "long": _segment(self.trades, side="long"),
                "short": _segment(self.trades, side="short"),
                "continuation": _segment(
                    self.trades, profile="continuation-expansion"
                ),
                "reversal": _segment(self.trades, profile="reversal-expansion"),
            },
            "trades": [item.payload() for item in self.trades],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _object(value: object, *, field: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be object")
    return cast(dict[str, object], value)


def _array(value: object, *, field: str) -> list[object]:
    if type(value) is not list:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be array")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if type(value) is not str or not value:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be non-empty str")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be bool")
    return value


def _integer(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be int")
    return value


def _timestamp(value: object, *, field: str) -> datetime:
    raw = _text(value, field=field)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, field: str) -> Decimal:
    raw = _text(value, field=field)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be decimal") from error
    if not result.is_finite() or result <= 0:
        raise Vt08CrtH4AmdV2BacktestError(f"{field} must be positive finite")
    return result


def _bar(raw: object) -> Vt08CrtH4AmdV2Bar:
    row = _object(raw, field="M15 bar")
    return Vt08CrtH4AmdV2Bar(
        opened_at=_timestamp(row.get("opened_at"), field="bar opened_at"),
        closed_at=_timestamp(row.get("closed_at"), field="bar closed_at"),
        open=_decimal(row.get("open"), field="bar open"),
        high=_decimal(row.get("high"), field="bar high"),
        low=_decimal(row.get("low"), field="bar low"),
        close=_decimal(row.get("close"), field="bar close"),
    )


def _source_window_bounds(symbol: str, instant: datetime) -> tuple[datetime, datetime]:
    local = instant.astimezone(_NY)
    anchors = _FUTURES_ANCHORS if symbol in _INDEX_MARKETS else _FOREX_ANCHORS
    candidates: list[datetime] = []
    for day_delta in (-1, 0, 1):
        candidate_date = local.date() + timedelta(days=day_delta)
        for hour in anchors:
            candidates.append(
                datetime.combine(candidate_date, time(hour, 0), tzinfo=_NY)
            )
    starts = sorted(item for item in candidates if item <= local)
    if not starts:
        raise Vt08CrtH4AmdV2BacktestError("cannot resolve source H4 window start")
    opened_local = starts[-1]
    closes = sorted(item for item in candidates if item > opened_local)
    if not closes:
        next_date = local.date() + timedelta(days=2)
        closes.extend(
            datetime.combine(next_date, time(hour, 0), tzinfo=_NY)
            for hour in anchors
        )
        closes.sort()
    return opened_local.astimezone(UTC), closes[0].astimezone(UTC)


def _build_windows(
    symbol: str,
    bars: tuple[Vt08CrtH4AmdV2Bar, ...],
) -> tuple[tuple[_SourceWindow, ...], int]:
    grouped: dict[datetime, list[Vt08CrtH4AmdV2Bar]] = defaultdict(list)
    bounds: dict[datetime, datetime] = {}
    for bar in bars:
        opened, closed = _source_window_bounds(symbol, bar.opened_at)
        if not opened <= bar.opened_at < closed:
            raise Vt08CrtH4AmdV2BacktestError("M15 bar escaped resolved H4 window")
        grouped[opened].append(bar)
        bounds[opened] = closed
    complete: list[_SourceWindow] = []
    incomplete = 0
    for opened in sorted(grouped):
        members = tuple(sorted(grouped[opened], key=lambda item: item.opened_at))
        closed = bounds[opened]
        contiguous = (
            len(members) == 16
            and members[0].opened_at == opened
            and members[-1].closed_at == closed
            and all(
                current.opened_at == previous.closed_at
                for previous, current in zip(members, members[1:], strict=False)
            )
        )
        if not contiguous:
            incomplete += 1
            continue
        candle = Vt08CrtH4AmdV2H4Candle(
            opened_at=opened,
            closed_at=closed,
            open=members[0].open,
            high=max(item.high for item in members),
            low=min(item.low for item in members),
            close=members[-1].close,
        )
        complete.append(_SourceWindow(opened, closed, members, candle))
    return tuple(complete), incomplete


def _load(
    path: Path,
) -> tuple[
    str,
    str,
    str,
    str,
    datetime,
    tuple[Vt08CrtH4AmdV2Bar, ...],
    str,
]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08CrtH4AmdV2BacktestError("cannot read VT-08 V2 evidence") from error
    payload = _object(decoded, field="market evidence")
    if _text(payload.get("schema"), field="schema") != _EVIDENCE_SCHEMA:
        raise Vt08CrtH4AmdV2BacktestError("unexpected VT-08 V2 evidence schema")
    if _text(payload.get("environment"), field="environment") != "demo":
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence must be DEMO")
    if not _boolean(payload.get("read_only"), field="read_only"):
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence must be read-only")
    if _boolean(payload.get("account_is_live"), field="account_is_live"):
        raise Vt08CrtH4AmdV2BacktestError("LIVE evidence is prohibited")
    if _integer(payload.get("required_coverage_days"), field="coverage") < _REQUIRED_COVERAGE_DAYS:
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence requires >=730 days")
    symbol = _text(payload.get("canonical_symbol"), field="canonical_symbol")
    symbol_object = _object(payload.get("symbol"), field="symbol")
    if _text(symbol_object.get("symbol_name"), field="symbol_name") != symbol:
        raise Vt08CrtH4AmdV2BacktestError("canonical symbol identity mismatch")
    provider = _text(payload.get("provider_symbol_name"), field="provider_symbol_name")
    account = _text(payload.get("account_fingerprint"), field="account_fingerprint")
    if re.fullmatch(r"[0-9a-f]{64}", account) is None:
        raise Vt08CrtH4AmdV2BacktestError("account fingerprint must be SHA-256")
    software_sha = _text(payload.get("software_sha"), field="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt08CrtH4AmdV2BacktestError("software_sha must be exact Git SHA")
    periods = _object(payload.get("periods"), field="periods")
    if set(periods) != {"M15"}:
        raise Vt08CrtH4AmdV2BacktestError("VT-08 V2 evidence must contain only M15")
    bars = tuple(_bar(item) for item in _array(periods.get("M15"), field="M15"))
    if not bars or bars != tuple(sorted(bars, key=lambda item: item.opened_at)):
        raise Vt08CrtH4AmdV2BacktestError("M15 evidence must be non-empty chronological")
    evidence_fingerprint = sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return (
        software_sha,
        symbol,
        provider,
        account,
        _timestamp(payload.get("checked_at"), field="checked_at"),
        bars,
        evidence_fingerprint,
    )


def _trade_from_setup(
    window: _SourceWindow,
    setup: Vt08CrtH4AmdV2Setup,
) -> Vt08CrtH4AmdV2Trade:
    signal_index = next(
        (
            index
            for index, bar in enumerate(window.bars)
            if bar.closed_at.astimezone(UTC) == setup.signal_at.astimezone(UTC)
        ),
        None,
    )
    if signal_index is None:
        raise Vt08CrtH4AmdV2BacktestError("setup signal does not bind a source M15 close")
    risk = (
        setup.entry_price - setup.invalidation_price
        if setup.side is DemoTradingSetupSide.LONG
        else setup.invalidation_price - setup.entry_price
    )
    if risk <= 0:
        raise Vt08CrtH4AmdV2BacktestError("setup risk must be positive")
    path = window.bars[signal_index + 1 :]
    if not path:
        raise Vt08CrtH4AmdV2BacktestError("CISD at H4 terminal boundary is not tradable")
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)
    for bar in path:
        if setup.side is DemoTradingSetupSide.LONG:
            max_favorable = max(max_favorable, (bar.high - setup.entry_price) / risk)
            max_adverse = max(max_adverse, (setup.entry_price - bar.low) / risk)
            stopped = bar.low <= setup.invalidation_price
        else:
            max_favorable = max(max_favorable, (setup.entry_price - bar.low) / risk)
            max_adverse = max(max_adverse, (bar.high - setup.entry_price) / risk)
            stopped = bar.high >= setup.invalidation_price
        if stopped:
            return Vt08CrtH4AmdV2Trade(
                signal_at=setup.signal_at,
                resolved_at=bar.closed_at,
                side=setup.side.value,
                profile=setup.profile.value,
                htf_closure=setup.htf_closure.value,
                entry_price=setup.entry_price,
                stop_loss=setup.invalidation_price,
                exit_price=setup.invalidation_price,
                outcome="stop",
                r_multiple=Decimal(-1),
                mfe_r=max_favorable,
                mae_r=max(max_adverse, Decimal(1)),
                h4_opened_at=window.opened_at,
                h4_closed_at=window.closed_at,
            )
    exit_price = path[-1].close
    r_value = (
        (exit_price - setup.entry_price) / risk
        if setup.side is DemoTradingSetupSide.LONG
        else (setup.entry_price - exit_price) / risk
    )
    return Vt08CrtH4AmdV2Trade(
        signal_at=setup.signal_at,
        resolved_at=window.closed_at,
        side=setup.side.value,
        profile=setup.profile.value,
        htf_closure=setup.htf_closure.value,
        entry_price=setup.entry_price,
        stop_loss=setup.invalidation_price,
        exit_price=exit_price,
        outcome="h4_close",
        r_multiple=r_value,
        mfe_r=max_favorable,
        mae_r=max_adverse,
        h4_opened_at=window.opened_at,
        h4_closed_at=window.closed_at,
    )


def run_vt08_v2_backtest(path: Path) -> Vt08CrtH4AmdV2BacktestReport:
    loaded = _load(path)
    software_sha, symbol, provider, account, checked_at, bars, evidence_fingerprint = loaded
    windows, incomplete = _build_windows(symbol, bars)
    trades: list[Vt08CrtH4AmdV2Trade] = []
    eligible = 0
    for index in range(2, len(windows)):
        base, signal, current = windows[index - 2], windows[index - 1], windows[index]
        if base.closed_at != signal.opened_at or signal.closed_at != current.opened_at:
            continue
        eligible += 1
        setup: Vt08CrtH4AmdV2Setup | None = None
        for prefix_end in range(2, len(current.bars) + 1):
            prefix = current.bars[:prefix_end]
            evaluation = evaluate_vt08_crt_h4_amd_v2(
                Vt08CrtH4AmdV2Input(
                    symbol=symbol,
                    as_of=prefix[-1].closed_at,
                    previous_h4=(base.candle, signal.candle),
                    current_h4_opened_at=current.opened_at,
                    current_h4_closes_at=current.closed_at,
                    current_m15=prefix,
                )
            )
            if evaluation.decision is DemoTradingDecision.SETUP:
                setup = evaluation.setup
                break
        if setup is None:
            continue
        if setup.signal_at >= current.bars[-1].opened_at:
            continue
        trades.append(_trade_from_setup(current, setup))
    return Vt08CrtH4AmdV2BacktestReport(
        software_sha=software_sha,
        symbol=symbol,
        provider_symbol_name=provider,
        account_fingerprint=account,
        evidence_fingerprint=evidence_fingerprint,
        checked_at=checked_at,
        complete_h4_windows=len(windows),
        incomplete_h4_windows=incomplete,
        eligible_h4_windows=eligible,
        trades=tuple(trades),
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


def _segment(
    trades: tuple[Vt08CrtH4AmdV2Trade, ...],
    *,
    side: str | None = None,
    profile: str | None = None,
) -> dict[str, object]:
    selected = tuple(
        item
        for item in trades
        if (side is None or item.side == side) and (profile is None or item.profile == profile)
    )
    values = tuple(item.r_multiple for item in selected)
    wins = sum(item.r_multiple > 0 for item in selected)
    return {
        "sample_size": len(selected),
        "win_rate": format(
            Decimal(wins) / Decimal(len(selected)) if selected else Decimal(0), "f"
        ),
        "expectancy_r": format(_mean(values), "f"),
        "population_variance_r": format(_variance(values), "f"),
        "stop_count": sum(item.outcome == "stop" for item in selected),
        "h4_close_count": sum(item.outcome == "h4_close" for item in selected),
        "mean_mfe_r": format(_mean(tuple(item.mfe_r for item in selected)), "f"),
        "mean_mae_r": format(_mean(tuple(item.mae_r for item in selected)), "f"),
    }


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("usage: vt08_crt_h4_amd_v2_backtest <market-evidence.json>")
    report = run_vt08_v2_backtest(Path(args[0]))
    print(report.to_json())


if __name__ == "__main__":
    main()
