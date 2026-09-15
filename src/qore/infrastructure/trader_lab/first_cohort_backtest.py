"""Read-only historical replay for the exact first five cTrader DEMO Traders.

The engine consumes sanitized cTrader DEMO Lab OHLC, invokes the production
methodology evaluators only with candles closed at each explicit ``as_of``, and
uses one source-frozen conservative execution model.  It never promotes a
Trader, issues Risk authority, or mutates a broker account.

Execution model v1:
- LIMIT can fill in the next 3 contiguous execution candles;
- a filled position is modeled for at most 24 contiguous candles;
- if SL and TP are both touched in one OHLC candle, SL wins;
- a data gap closes at the last known close;
- modeled trades for one Trader never overlap.
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
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
_HISTORY_LIMIT = 64
_PERIOD_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "H4": 14_400}
_REQUIRED_RESEARCH_PERIODS = ("M5", "M15", "H4")
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_EXECUTION_PERIOD = {
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
    __slots__ = ()


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
        for field_name, timestamp_value in (
            ("signal_at", self.signal_at),
            ("filled_at", self.filled_at),
            ("exited_at", self.exited_at),
        ):
            if (
                type(timestamp_value) is not datetime
                or timestamp_value.tzinfo is None
                or timestamp_value.utcoffset() is None
            ):
                raise FirstCohortBacktestError(f"{field_name} must be timezone-aware")
        if not self.signal_at <= self.filled_at <= self.exited_at:
            raise FirstCohortBacktestError("trade timestamps must be monotonic")
        if not isinstance(self.side, DemoTradingSetupSide):
            raise FirstCohortBacktestError("trade side must be canonical")
        for field_name, decimal_value in (
            ("entry_price", self.entry_price),
            ("stop_loss", self.stop_loss),
            ("take_profit", self.take_profit),
            ("exit_price", self.exit_price),
            ("return_rate", self.return_rate),
        ):
            if type(decimal_value) is not Decimal or not decimal_value.is_finite():
                raise FirstCohortBacktestError(f"{field_name} must be finite Decimal")
        if min(self.entry_price, self.stop_loss, self.take_profit, self.exit_price) <= 0:
            raise FirstCohortBacktestError("trade prices must be positive")
        if self.exit_reason not in {"stop", "target", "time_exit", "gap_exit"}:
            raise FirstCohortBacktestError("unsupported trade exit reason")

    def payload(self) -> dict[str, object]:
        return {
            "trader_code": self.trader_code,
            "signal_at": self.signal_at.astimezone(UTC).isoformat(),
            "filled_at": self.filled_at.astimezone(UTC).isoformat(),
            "exited_at": self.exited_at.astimezone(UTC).isoformat(),
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
            "trades": [trade.payload() for trade in self.trades],
        }


@dataclass(frozen=True, slots=True)
class FirstCohortBacktestReport:
    account_fingerprint: str
    symbol: str
    checked_at: datetime
    software_sha: str
    results: tuple[FirstCohortBacktestResult, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "account_fingerprint": self.account_fingerprint,
            "symbol": self.symbol,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(),
            "software_sha": self.software_sha,
            "execution_model": _EXECUTION_MODEL,
            "results": [result.payload() for result in self.results],
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


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortBacktestError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortBacktestError(f"{field_name} must be bool")
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int:
        raise FirstCohortBacktestError(f"{field_name} must be an int")
    return value


def _timestamp(value: object, *, field_name: str) -> datetime:
    raw = _text(value, field_name=field_name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise FirstCohortBacktestError(f"{field_name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FirstCohortBacktestError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, field_name: str) -> Decimal:
    raw = _text(value, field_name=field_name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise FirstCohortBacktestError(f"{field_name} must be decimal") from error
    if not parsed.is_finite() or parsed <= 0:
        raise FirstCohortBacktestError(f"{field_name} must be positive finite decimal")
    return parsed


def _snapshot(item: object, *, period: str, instrument: Instrument) -> OhlcSnapshot:
    payload = _object(item, field_name=f"{period} bar")
    opened_at = _timestamp(payload.get("opened_at"), field_name="bar opened_at")
    closed_at = _timestamp(payload.get("closed_at"), field_name="bar closed_at")
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            uuid5(
                NAMESPACE_URL,
                f"qore:first-cohort:{instrument.symbol}:{period}:{opened_at.isoformat()}",
            )
        ),
        instrument=instrument,
        source=_SOURCE,
        timeframe=Timeframe(_PERIOD_SECONDS[period]),
        opened_at=opened_at,
        closed_at=closed_at,
        open=float(_decimal(payload.get("open"), field_name="bar open")),
        high=float(_decimal(payload.get("high"), field_name="bar high")),
        low=float(_decimal(payload.get("low"), field_name="bar low")),
        close=float(_decimal(payload.get("close"), field_name="bar close")),
    )


def _load(
    path: Path,
) -> tuple[dict[str, tuple[OhlcSnapshot, ...]], str, str, datetime, str]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortBacktestError("cannot read cTrader Lab evidence") from error
    payload = _object(decoded, field_name="market evidence")
    if _text(payload.get("environment"), field_name="environment") != "demo":
        raise FirstCohortBacktestError("market evidence must be DEMO")
    if not _strict_bool(payload.get("read_only"), field_name="read_only"):
        raise FirstCohortBacktestError("market evidence must be read-only")
    if _strict_bool(payload.get("account_is_live"), field_name="account_is_live"):
        raise FirstCohortBacktestError("LIVE account evidence is prohibited")
    if not _strict_bool(
        payload.get("trading_permission_verified"),
        field_name="trading_permission_verified",
    ):
        raise FirstCohortBacktestError("DEMO trading permission must be verified")
    fingerprint = _text(payload.get("account_fingerprint"), field_name="account_fingerprint")
    if len(fingerprint) != 64:
        raise FirstCohortBacktestError("account fingerprint must have SHA-256 length")
    symbol_payload = _object(payload.get("symbol"), field_name="symbol")
    symbol = _text(symbol_payload.get("symbol_name"), field_name="symbol_name")
    checked_at = _timestamp(payload.get("checked_at"), field_name="checked_at")
    software_sha = _text(payload.get("software_sha"), field_name="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise FirstCohortBacktestError("software_sha must be a lowercase Git SHA")
    required_coverage_days = _strict_int(
        payload.get("required_coverage_days"), field_name="required_coverage_days"
    )
    if required_coverage_days < 730:
        raise FirstCohortBacktestError(
            "market evidence requires at least 730 effective coverage days"
        )
    requested_lookback_days = _strict_int(
        payload.get("requested_lookback_days"), field_name="requested_lookback_days"
    )
    if requested_lookback_days < required_coverage_days:
        raise FirstCohortBacktestError(
            "requested lookback cannot be shorter than required effective coverage"
        )
    instrument = Instrument(symbol)
    periods = _object(payload.get("periods"), field_name="periods")
    if set(periods) != set(_PERIOD_SECONDS):
        raise FirstCohortBacktestError("evidence must contain M1/M5/M15/H4")
    series: dict[str, tuple[OhlcSnapshot, ...]] = {}
    for period in _PERIOD_SECONDS:
        rows = _array(periods.get(period), field_name=f"period {period}")
        snapshots = tuple(_snapshot(row, period=period, instrument=instrument) for row in rows)
        if period in _REQUIRED_RESEARCH_PERIODS and not snapshots:
            raise FirstCohortBacktestError(f"period {period} is empty")
        if snapshots != tuple(sorted(snapshots, key=lambda bar: bar.closed_at)):
            raise FirstCohortBacktestError(f"period {period} is not chronological")
        identities = tuple((bar.opened_at, bar.closed_at) for bar in snapshots)
        if len(set(identities)) != len(identities):
            raise FirstCohortBacktestError(f"period {period} contains duplicate bars")
        series[period] = snapshots
    coverage = _object(payload.get("coverage"), field_name="coverage")
    minimum_seconds = required_coverage_days * 86_400
    for period in _REQUIRED_RESEARCH_PERIODS:
        snapshots = series[period]
        actual_seconds = int(
            (snapshots[-1].closed_at - snapshots[0].opened_at).total_seconds()
        )
        if actual_seconds < minimum_seconds:
            raise FirstCohortBacktestError(
                f"period {period} has less than 730 effective calendar days"
            )
        declared = _object(coverage.get(period), field_name=f"coverage {period}")
        if _strict_int(declared.get("bar_count"), field_name="coverage bar_count") != len(
            snapshots
        ):
            raise FirstCohortBacktestError(f"period {period} coverage count mismatch")
        if _timestamp(
            declared.get("first_opened_at"), field_name="coverage first_opened_at"
        ) != snapshots[0].opened_at or _timestamp(
            declared.get("last_closed_at"), field_name="coverage last_closed_at"
        ) != snapshots[-1].closed_at:
            raise FirstCohortBacktestError(
                f"period {period} coverage boundaries mismatch"
            )
        if _strict_int(
            declared.get("span_seconds"), field_name="coverage span_seconds"
        ) != actual_seconds:
            raise FirstCohortBacktestError(f"period {period} coverage span mismatch")
    return series, fingerprint, symbol, checked_at, software_sha


def _history(
    series: tuple[OhlcSnapshot, ...], end_index: int, *, limit: int = _HISTORY_LIMIT
) -> tuple[OhlcSnapshot, ...]:
    start = end_index
    while start > 0 and end_index - start + 1 < limit:
        if series[start - 1].closed_at != series[start].opened_at:
            break
        start -= 1
    return series[start : end_index + 1]


def _h4_context(h4: tuple[OhlcSnapshot, ...], *, as_of: datetime) -> tuple[OhlcSnapshot, ...]:
    """Return the exact prior H4 context in O(log N) lookup time.

    ``h4`` is validated as chronological by ``_load``.  ``bisect_right`` with
    the closed-at key therefore finds the same final eligible index as the
    former full linear scan, including an H4 candle closing exactly at
    ``as_of``.  ``_history`` continues to enforce the original contiguous-tail
    semantics, so this is a performance change only.
    """

    insertion = bisect_right(h4, as_of, key=lambda bar: bar.closed_at)
    return () if insertion == 0 else _history(h4, insertion - 1, limit=32)


def _touches(bar: OhlcSnapshot, price: Decimal) -> bool:
    point = float(price)
    return bar.low <= point <= bar.high


def _return_rate(
    *, side: DemoTradingSetupSide, entry: Decimal, exit_price: Decimal
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
    last_fill = min(signal_index + _LIMIT_FILL_BARS, len(series) - 1)
    prior = series[signal_index]
    fill_index: int | None = None
    for index in range(signal_index + 1, last_fill + 1):
        bar = series[index]
        if bar.opened_at != prior.closed_at:
            return None, signal_index
        if _touches(bar, entry):
            fill_index = index
            break
        prior = bar
    if fill_index is None:
        return None, last_fill

    exit_index = fill_index
    exit_price = Decimal(str(series[fill_index].close))
    reason = "time_exit"
    prior = series[fill_index]
    last_exit = min(fill_index + _MAX_HOLD_BARS - 1, len(series) - 1)
    for index in range(fill_index, last_exit + 1):
        bar = series[index]
        if index > fill_index and bar.opened_at != prior.closed_at:
            exit_index = index - 1
            exit_price = Decimal(str(prior.close))
            reason = "gap_exit"
            break
        if _touches(bar, stop):
            exit_index, exit_price, reason = index, stop, "stop"
            break
        if _touches(bar, target):
            exit_index, exit_price, reason = index, target, "target"
            break
        exit_index = index
        exit_price = Decimal(str(bar.close))
        reason = "time_exit"
        prior = bar

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
        return_rate=_return_rate(side=side, entry=entry, exit_price=exit_price),
        exit_reason=reason,
    )
    return trade, exit_index


def _metrics(
    trades: tuple[FirstCohortBacktestTrade, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    if not trades:
        return Decimal(0), Decimal(0), Decimal(0)
    values = tuple(trade.return_rate for trade in trades)
    size = Decimal(len(values))
    mean = sum(values, Decimal(0)) / size
    wins = Decimal(sum(value > 0 for value in values)) / size
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / size
    return mean, wins, variance


def _backtest(
    evaluator: DemoTradingEvaluatorBoundary,
    *,
    trader_code: str,
    series: dict[str, tuple[OhlcSnapshot, ...]],
) -> FirstCohortBacktestResult:
    period = _EXECUTION_PERIOD[trader_code]
    execution = series[period]
    trades: list[FirstCohortBacktestTrade] = []
    setup_count = 0
    unfilled = 0
    index = 0
    while index < len(execution) - 1:
        as_of = execution[index].closed_at
        context = _h4_context(series["H4"], as_of=as_of) if trader_code == "vt-08" else ()
        if trader_code == "vt-08" and not context:
            index += 1
            continue
        bound = build_instrument_bound_demo_trading_input(
            execution_evidence=_history(execution, index),
            context_evidence=context,
            as_of=as_of,
        )
        evaluated = evaluate_instrument_bound_demo_trader(evaluator, bound)
        if isinstance(evaluated, Failure):
            index += 1
            continue
        output = evaluated.value.trader_output
        if output.decision is not DemoTradingDecision.SETUP or output.setup is None:
            index += 1
            continue
        setup_count += 1
        setup = output.setup
        trade, consumed = _model_trade(
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
            index = max(index + 1, consumed + 1)
        else:
            trades.append(trade)
            index = consumed + 1
    retained = tuple(trades)
    mean, win_rate, variance = _metrics(retained)
    return FirstCohortBacktestResult(
        trader_code=trader_code,
        execution_period=period,
        setup_count=setup_count,
        unfilled_setup_count=unfilled,
        trades=retained,
        mean_return=mean,
        win_rate=win_rate,
        population_variance=variance,
    )


def run_first_cohort_backtest(path: Path) -> FirstCohortBacktestReport:
    """Run all five production evaluators on one fresh sanitized DEMO evidence file."""
    series, fingerprint, symbol, checked_at, software_sha = _load(path)
    evaluators = cohort_evaluators()
    if tuple(evaluator.trader_code for evaluator in evaluators) != _CODES:
        raise FirstCohortBacktestError("production cohort identity/order changed")
    results = tuple(
        _backtest(
            cast(DemoTradingEvaluatorBoundary, evaluator),
            trader_code=code,
            series=series,
        )
        for code, evaluator in zip(_CODES, evaluators, strict=True)
    )
    return FirstCohortBacktestReport(
        account_fingerprint=fingerprint,
        symbol=symbol,
        checked_at=checked_at,
        software_sha=software_sha,
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
