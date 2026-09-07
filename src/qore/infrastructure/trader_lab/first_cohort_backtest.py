"""Deterministic historical backtest for the first five cTrader DEMO Traders.

This module consumes only sanitized, read-only cTrader DEMO Lab market evidence.
It runs the production cohort evaluators over closed candles with no future
leakage and applies one explicit conservative execution model.  It does not
promote a Trader, issue Risk authority, or submit/cancel/amend broker orders.

Execution-model policy (v1), frozen in source before outcomes are inspected:

* evaluate only at the close of an execution-timeframe candle;
* the LIMIT entry may fill during at most the next three contiguous candles;
* a filled position may remain open for at most 24 contiguous candles;
* if stop and target are both touched in one OHLC candle, stop wins;
* a market-data gap terminates the modeled position at the last known close;
* only one modeled position per Trader may be open at a time.

The resulting closed-trade returns are research inputs for the governed Trader
Lab chain.  They are not DEMO eligibility by themselves.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingSetupSide,
)
from qore.infrastructure.traders.evaluators import cohort_evaluators
from qore.infrastructure.traders.instrument_binding import (
    DemoTradingEvaluatorBoundary,
    build_instrument_bound_demo_trading_input,
    evaluate_instrument_bound_demo_trader,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure

_SCHEMA = "qore.trader_lab.first_cohort_backtest.v1"
_EXECUTION_MODEL = "limit-3bar-fill-24bar-hold-stop-first-v1"
_LIMIT_FILL_BARS = 3
_MAX_HOLD_BARS = 24
_HISTORY_LIMIT = 256
_PERIOD_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H4": 14_400,
}
_EXECUTION_PERIOD: dict[str, str] = {
    "vt-01": "M5",
    "vt-08": "M5",
    "vt-09": "M15",
    "vt-17": "M5",
    "vt-31": "M5",
}
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("78a00000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("78a00000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo-first-cohort-backtest"),
)


class FirstCohortBacktestError(InfrastructureError):
    """Sanitized fail-closed backtest error."""

    __slots__ = ()


class _Evaluator(Protocol):
    @property
    def trader_code(self) -> str: ...

    @property
    def timeframe(self) -> str: ...

    def evaluate(self, inputs: object) -> object: ...


@dataclass(frozen=True, slots=True)
class FirstCohortBacktestTrade:
    trader_code: str
    signal_at: datetime
    filled_at: datetime
    exited_at: datetime
    side: DemoTradingSetupSide
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    exit_price: Decimal
    return_rate: Decimal
    exit_reason: str

    def __post_init__(self) -> None:
        if self.trader_code not in _EXECUTION_PERIOD:
            raise FirstCohortBacktestError("unknown first-cohort Trader code")
        for name, value in (
            ("signal_at", self.signal_at),
            ("filled_at", self.filled_at),
            ("exited_at", self.exited_at),
        ):
            if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
                raise FirstCohortBacktestError(f"{name} must be timezone-aware")
        if not self.signal_at <= self.filled_at <= self.exited_at:
            raise FirstCohortBacktestError("trade timestamps must be monotonic")
        if not isinstance(self.side, DemoTradingSetupSide):
            raise FirstCohortBacktestError("trade side must be canonical")
        for name, value in (
            ("entry_price", self.entry_price),
            ("stop_loss", self.stop_loss),
            ("take_profit", self.take_profit),
            ("exit_price", self.exit_price),
            ("return_rate", self.return_rate),
        ):
            if type(value) is not Decimal or not value.is_finite():
                raise FirstCohortBacktestError(f"{name} must be finite Decimal")
        if min(self.entry_price, self.stop_loss, self.take_profit, self.exit_price) <= 0:
            raise FirstCohortBacktestError("trade prices must be positive")
        if self.exit_reason not in {"stop", "target", "time_exit", "gap_exit"}:
            raise FirstCohortBacktestError("unsupported trade exit reason")

    def payload(self) -> dict[str, object]:
        return {
            "trader_code": self.trader_code,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "filled_at": self.filled_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "exited_at": self.exited_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "side": self.side.value,
            "entry_price": format(self.entry_price, "f"),
            "stop_loss": format(self.stop_loss, "f"),
            "take_profit": format(self.take_profit, "f"),
            "exit_price": format(self.exit_price, "f"),
            "return_rate": format(self.return_rate, "f"),
            "exit_reason": self.exit_reason,
        }


@dataclass(frozen=True, slots=True)
class FirstCohortBacktestResult:
    trader_code: str
    execution_period: str
    setup_count: int
    unfilled_setup_count: int
    trades: tuple[FirstCohortBacktestTrade, ...]
    mean_return: Decimal
    win_rate: Decimal
    population_variance: Decimal

    def __post_init__(self) -> None:
        if self.trader_code not in _EXECUTION_PERIOD:
            raise FirstCohortBacktestError("unknown result Trader code")
        if self.execution_period != _EXECUTION_PERIOD[self.trader_code]:
            raise FirstCohortBacktestError("result timeframe does not match Trader")
        if type(self.setup_count) is not int or self.setup_count < 0:
            raise FirstCohortBacktestError("setup_count must be non-negative int")
        if type(self.unfilled_setup_count) is not int or self.unfilled_setup_count < 0:
            raise FirstCohortBacktestError("unfilled_setup_count must be non-negative int")
        if type(self.trades) is not tuple or any(
            type(item) is not FirstCohortBacktestTrade for item in self.trades
        ):
            raise FirstCohortBacktestError("trades must be canonical tuple")
        if self.setup_count < len(self.trades) + self.unfilled_setup_count:
            raise FirstCohortBacktestError("setup accounting is inconsistent")
        for value in (self.mean_return, self.win_rate, self.population_variance):
            if type(value) is not Decimal or not value.is_finite():
                raise FirstCohortBacktestError("metrics must be finite Decimal")
        if not Decimal("0") <= self.win_rate <= Decimal("1"):
            raise FirstCohortBacktestError("win rate must be in [0,1]")
        if self.population_variance < 0:
            raise FirstCohortBacktestError("variance must be non-negative")

    @property
    def sample_size(self) -> int:
        return len(self.trades)

    def payload(self) -> dict[str, object]:
        return {
            "trader_code": self.trader_code,
            "execution_period": self.execution_period,
            "setup_count": self.setup_count,
            "unfilled_setup_count": self.unfilled_setup_count,
            "sample_size": self.sample_size,
            "mean_return": format(self.mean_return, "f"),
            "win_rate": format(self.win_rate, "f"),
            "population_variance": format(self.population_variance, "f"),
            "trades": [item.payload() for item in self.trades],
        }


@dataclass(frozen=True, slots=True)
class FirstCohortBacktestReport:
    environment: str
    read_only: bool
    account_fingerprint: str
    symbol: str
    checked_at: datetime
    execution_model: str
    results: tuple[FirstCohortBacktestResult, ...]

    def __post_init__(self) -> None:
        if self.environment != "demo" or self.read_only is not True:
            raise FirstCohortBacktestError("backtest input must be read-only DEMO evidence")
        if len(self.account_fingerprint) != 64:
            raise FirstCohortBacktestError("account fingerprint must be SHA-256 length")
        if not self.symbol:
            raise FirstCohortBacktestError("symbol must be non-empty")
        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise FirstCohortBacktestError("checked_at must be timezone-aware")
        if self.execution_model != _EXECUTION_MODEL:
            raise FirstCohortBacktestError("unexpected execution model")
        if tuple(item.trader_code for item in self.results) != (
            "vt-01",
            "vt-08",
            "vt-09",
            "vt-17",
            "vt-31",
        ):
            raise FirstCohortBacktestError("report requires canonical five-Trader order")

    def payload(self) -> dict[str, object]:
        return {
            "schema": _SCHEMA,
            "environment": self.environment,
            "read_only": self.read_only,
            "account_fingerprint": self.account_fingerprint,
            "symbol": self.symbol,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "execution_model": self.execution_model,
            "results": [item.payload() for item in self.results],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.payload(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortBacktestError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortBacktestError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortBacktestError(f"{field_name} must be a non-empty string")
    return value


def _bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortBacktestError(f"{field_name} must be a bool")
    return value


def _parse_time(value: object, *, field_name: str) -> datetime:
    raw = _string(value, field_name=field_name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise FirstCohortBacktestError(f"{field_name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FirstCohortBacktestError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _parse_snapshot(
    item: object,
    *,
    period: str,
    instrument: Instrument,
) -> OhlcSnapshot:
    payload = _object(item, field_name=f"{period} bar")
    opened_at = _parse_time(payload.get("opened_at"), field_name="bar opened_at")
    closed_at = _parse_time(payload.get("closed_at"), field_name="bar closed_at")
    prices: dict[str, Decimal] = {}
    for name in ("open", "high", "low", "close"):
        try:
            prices[name] = Decimal(_string(payload.get(name), field_name=f"bar {name}"))
        except Exception as error:
            if isinstance(error, FirstCohortBacktestError):
                raise
            raise FirstCohortBacktestError(f"bar {name} must be Decimal") from error
    timeframe_seconds = _PERIOD_SECONDS[period]
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            uuid5(
                NAMESPACE_URL,
                "qore:first-cohort-backtest:bar:"
                f"{instrument.symbol}:{period}:{opened_at.isoformat()}",
            )
        ),
        instrument=instrument,
        source=_SOURCE,
        timeframe=Timeframe(timeframe_seconds),
        opened_at=opened_at,
        closed_at=closed_at,
        open=float(prices["open"]),
        high=float(prices["high"]),
        low=float(prices["low"]),
        close=float(prices["close"]),
    )


def _load_market_evidence(
    path: Path,
) -> tuple[dict[str, tuple[OhlcSnapshot, ...]], str, str, datetime]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortBacktestError("cannot read cTrader Lab market evidence") from error
    payload = _object(decoded, field_name="market evidence")
    if _string(payload.get("environment"), field_name="environment") != "demo":
        raise FirstCohortBacktestError("market evidence must be DEMO")
    if not _bool(payload.get("read_only"), field_name="read_only"):
        raise FirstCohortBacktestError("market evidence must be read-only")
    if _bool(payload.get("account_is_live"), field_name="account_is_live"):
        raise FirstCohortBacktestError("LIVE account evidence is prohibited")
    if not _bool(
        payload.get("trading_permission_verified"),
        field_name="trading_permission_verified",
    ):
        raise FirstCohortBacktestError("DEMO trading permission must be verified")
    account_fingerprint = _string(
        payload.get("account_fingerprint"), field_name="account_fingerprint"
    )
    if len(account_fingerprint) != 64:
        raise FirstCohortBacktestError("account fingerprint must be SHA-256 length")
    symbol_payload = _object(payload.get("symbol"), field_name="symbol")
    symbol = _string(symbol_payload.get("symbol_name"), field_name="symbol_name")
    instrument = Instrument(symbol)
    checked_at = _parse_time(payload.get("checked_at"), field_name="checked_at")
    periods_payload = _object(payload.get("periods"), field_name="periods")
    if set(periods_payload) != set(_PERIOD_SECONDS):
        raise FirstCohortBacktestError("market evidence must contain M1/M5/M15/H4")
    series: dict[str, tuple[OhlcSnapshot, ...]] = {}
    for period in _PERIOD_SECONDS:
        rows = _array(periods_payload.get(period), field_name=f"period {period}")
        snapshots = tuple(
            _parse_snapshot(item, period=period, instrument=instrument) for item in rows
        )
        if not snapshots:
            raise FirstCohortBacktestError(f"period {period} contains no bars")
        if snapshots != tuple(sorted(snapshots, key=lambda item: item.closed_at)):
            raise FirstCohortBacktestError(f"period {period} bars are not chronological")
        series[period] = snapshots
    return series, account_fingerprint, symbol, checked_at


def _contiguous_history(
    series: tuple[OhlcSnapshot, ...],
    end_index: int,
    *,
    limit: int = _HISTORY_LIMIT,
) -> tuple[OhlcSnapshot, ...]:
    if end_index < 0 or end_index >= len(series):
        raise FirstCohortBacktestError("history end_index is out of range")
    start = end_index
    while start > 0 and end_index - start + 1 < limit:
        if series[start - 1].closed_at != series[start].opened_at:
            break
        start -= 1
    return series[start : end_index + 1]


def _context_history(
    h4: tuple[OhlcSnapshot, ...],
    *,
    as_of: datetime,
) -> tuple[OhlcSnapshot, ...]:
    eligible = [index for index, item in enumerate(h4) if item.closed_at <= as_of]
    if not eligible:
        return ()
    return _contiguous_history(h4, eligible[-1], limit=32)


def _touches(bar: OhlcSnapshot, price: Decimal) -> bool:
    value = float(price)
    return bar.low <= value <= bar.high


def _trade_return(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    exit_price: Decimal,
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return (exit_price - entry) / entry
    return (entry - exit_price) / entry


def _model_trade(
    *,
    trader_code: str,
    series: tuple[OhlcSnapshot, ...],
    signal_index: int,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[FirstCohortBacktestTrade | None, int]:
    last_fill_index = min(signal_index + _LIMIT_FILL_BARS, len(series) - 1)
    previous = series[signal_index]
    fill_index: int | None = None
    for index in range(signal_index + 1, last_fill_index + 1):
        bar = series[index]
        if bar.opened_at != previous.closed_at:
            return None, signal_index
        if _touches(bar, entry):
            fill_index = index
            break
        previous = bar
    if fill_index is None:
        return None, last_fill_index

    fill_bar = series[fill_index]
    exit_index = fill_index
    exit_price = Decimal(str(fill_bar.close))
    exit_reason = "time_exit"
    previous = fill_bar
    max_exit_index = min(fill_index + _MAX_HOLD_BARS - 1, len(series) - 1)
    for index in range(fill_index, max_exit_index + 1):
        bar = series[index]
        if index > fill_index and bar.opened_at != previous.closed_at:
            exit_index = index - 1
            exit_price = Decimal(str(previous.close))
            exit_reason = "gap_exit"
            break
        stop_touched = _touches(bar, stop)
        target_touched = _touches(bar, target)
        if stop_touched:
            exit_index = index
            exit_price = stop
            exit_reason = "stop"
            break
        if target_touched:
            exit_index = index
            exit_price = target
            exit_reason = "target"
            break
        exit_index = index
        exit_price = Decimal(str(bar.close))
        exit_reason = "time_exit"
        previous = bar

    trade = FirstCohortBacktestTrade(
        trader_code=trader_code,
        signal_at=series[signal_index].closed_at,
        filled_at=series[fill_index].closed_at,
        exited_at=series[exit_index].closed_at,
        side=side,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
        exit_price=exit_price,
        return_rate=_trade_return(side=side, entry=entry, exit_price=exit_price),
        exit_reason=exit_reason,
    )
    return trade, exit_index


def _metrics(
    trades: tuple[FirstCohortBacktestTrade, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    if not trades:
        return Decimal("0"), Decimal("0"), Decimal("0")
    values = tuple(item.return_rate for item in trades)
    denominator = Decimal(len(values))
    mean = sum(values, Decimal("0")) / denominator
    win_rate = Decimal(sum(value > 0 for value in values)) / denominator
    variance = (
        sum(((value - mean) * (value - mean) for value in values), Decimal("0"))
        / denominator
    )
    return mean, win_rate, variance


def _backtest_trader(
    evaluator: DemoTradingEvaluatorBoundary,
    *,
    trader_code: str,
    series: dict[str, tuple[OhlcSnapshot, ...]],
) -> FirstCohortBacktestResult:
    period = _EXECUTION_PERIOD[trader_code]
    execution = series[period]
    h4 = series["H4"]
    trades: list[FirstCohortBacktestTrade] = []
    setup_count = 0
    unfilled = 0
    index = 0
    while index < len(execution) - 1:
        history = _contiguous_history(execution, index)
        as_of = execution[index].closed_at
        context = _context_history(h4, as_of=as_of) if trader_code == "vt-08" else ()
        if trader_code == "vt-08" and not context:
            index += 1
            continue
        bound_input = build_instrument_bound_demo_trading_input(
            execution_evidence=history,
            context_evidence=context,
            as_of=as_of,
        )
        evaluated = evaluate_instrument_bound_demo_trader(evaluator, bound_input)
        if isinstance(evaluated, Failure):
            index += 1
            continue
        output = evaluated.value.trader_output
        if output.decision is not DemoTradingDecision.SETUP or output.setup is None:
            index += 1
            continue
        setup_count += 1
        setup = output.setup
        trade, consumed_index = _model_trade(
            trader_code=trader_code,
            series=execution,
            signal_index=index,
            side=setup.side,
            entry=setup.entry_price,
            stop=setup.invalidation_price,
            target=setup.take_profit_price,
        )
        if trade is None:
            unfilled += 1
            index = max(index + 1, consumed_index + 1)
            continue
        trades.append(trade)
        index = consumed_index + 1
    trade_tuple = tuple(trades)
    mean, win_rate, variance = _metrics(trade_tuple)
    return FirstCohortBacktestResult(
        trader_code=trader_code,
        execution_period=period,
        setup_count=setup_count,
        unfilled_setup_count=unfilled,
        trades=trade_tuple,
        mean_return=mean,
        win_rate=win_rate,
        population_variance=variance,
    )


def run_first_cohort_backtest(path: Path) -> FirstCohortBacktestReport:
    """Run all five production evaluators against one sanitized cTrader DEMO artifact."""
    series, account_fingerprint, symbol, checked_at = _load_market_evidence(path)
    evaluators = cohort_evaluators()
    codes = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
    if tuple(item.trader_code for item in evaluators) != codes:
        raise FirstCohortBacktestError("production cohort evaluator order changed")
    results = tuple(
        _backtest_trader(
            cast(DemoTradingEvaluatorBoundary, evaluator),
            trader_code=code,
            series=series,
        )
        for code, evaluator in zip(codes, evaluators, strict=True)
    )
    return FirstCohortBacktestReport(
        environment="demo",
        read_only=True,
        account_fingerprint=account_fingerprint,
        symbol=symbol,
        checked_at=checked_at,
        execution_model=_EXECUTION_MODEL,
        results=results,
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("usage: python -m qore.infrastructure.trader_lab.first_cohort_backtest PATH")
        return 2
    try:
        report = run_first_cohort_backtest(Path(arguments[0]))
    except FirstCohortBacktestError as error:
        print(f"first-cohort backtest failed: {error}", file=sys.stderr)
        return 1
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
