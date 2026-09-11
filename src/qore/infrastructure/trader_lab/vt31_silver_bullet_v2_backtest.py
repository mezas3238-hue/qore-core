"""Source-bound historical research runner for VT-31 Silver Bullet V2.

The runner consumes retained NAS100 M1 evidence and the actual V2 evaluator.
Pending LIMIT entries expire at 11:00 New York. Filled positions are allowed to
remain open after 11:00. The source-explicit 3R -> breakeven transition is
modeled causally and never inferred from future bars.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

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
from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_v2 import (
    Vt31SilverBulletV2Input,
    Vt31SilverBulletV2Setup,
    evaluate_vt31_silver_bullet_v2,
)
from qore.kernel.errors import InfrastructureError

_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1"
_EVIDENCE_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
_EXECUTION_MODEL = "source-limit-11et-3r-breakeven-stop-first-gap-censor-v2"
_SYMBOL = "NAS100"
_M1_SECONDS = 60
_REQUIRED_COVERAGE_DAYS = 730
_NY = ZoneInfo("America/New_York")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(uuid5(NAMESPACE_URL, "qore:vt31-v2:research-adapter")),
    source_id=SourceId(uuid5(NAMESPACE_URL, "qore:vt31-v2:research-source")),
    port_name=PortName("market-data.vt31-v2-research"),
)


class Vt31SilverBulletV2BacktestError(InfrastructureError):
    """VT-31 V2 historical research failed closed."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Trade:
    signal_at: datetime
    filled_at: datetime
    fill_interval_opened_at: datetime
    fill_interval_closed_at: datetime
    resolved_at: datetime | None
    side: DemoTradingSetupSide
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    three_r_price: Decimal
    breakeven_armed_at: datetime | None
    entry_model: str
    entry_models: tuple[str, ...]
    exit_price: Decimal | None
    outcome: str
    r_multiple: Decimal | None

    def __post_init__(self) -> None:
        supported = {
            "target",
            "stop",
            "breakeven",
            "gap_censored",
            "data_end_censored",
        }
        if self.outcome not in supported:
            raise Vt31SilverBulletV2BacktestError("unsupported VT-31 V2 trade outcome")
        if not self.signal_at <= self.filled_at:
            raise Vt31SilverBulletV2BacktestError("fill cannot precede signal")
        if not self.fill_interval_opened_at < self.fill_interval_closed_at:
            raise Vt31SilverBulletV2BacktestError("fill evidence interval must be half-open")
        if self.filled_at != self.fill_interval_closed_at:
            raise Vt31SilverBulletV2BacktestError(
                "filled_at is the M1 evidence-availability timestamp"
            )
        if self.resolved_at is not None and self.resolved_at < self.filled_at:
            raise Vt31SilverBulletV2BacktestError("resolution cannot precede fill")
        terminal = self.outcome in {"target", "stop", "breakeven"}
        if terminal != (self.exit_price is not None and self.r_multiple is not None):
            raise Vt31SilverBulletV2BacktestError(
                "terminal outcome must bind exit_price and r_multiple"
            )
        if self.outcome == "breakeven" and (
            self.exit_price != self.entry_price or self.r_multiple != Decimal(0)
        ):
            raise Vt31SilverBulletV2BacktestError(
                "breakeven terminal state must exit at entry with zero R"
            )
        if self.breakeven_armed_at is not None:
            if self.breakeven_armed_at < self.filled_at:
                raise Vt31SilverBulletV2BacktestError(
                    "breakeven cannot arm before the position fills"
                )
        if type(self.entry_model) is not str or not self.entry_model:
            raise Vt31SilverBulletV2BacktestError("entry_model must be retained")
        if (
            type(self.entry_models) is not tuple
            or not self.entry_models
            or self.entry_model not in self.entry_models
        ):
            raise Vt31SilverBulletV2BacktestError(
                "entry model confluence must retain the selected model"
            )

    def payload(self) -> dict[str, object]:
        return {
            "signal_at": self.signal_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "filled_at": self.filled_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "fill_interval_opened_at": self.fill_interval_opened_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "fill_interval_closed_at": self.fill_interval_closed_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "fill_time_precision": "M1-half-open-interval",
            "resolved_at": (
                self.resolved_at.astimezone(UTC).isoformat(timespec="microseconds")
                if self.resolved_at is not None
                else None
            ),
            "side": self.side.value,
            "entry_price": format(self.entry_price, "f"),
            "stop_loss": format(self.stop_loss, "f"),
            "take_profit": format(self.take_profit, "f"),
            "three_r_price": format(self.three_r_price, "f"),
            "breakeven_armed_at": (
                self.breakeven_armed_at.astimezone(UTC).isoformat(timespec="microseconds")
                if self.breakeven_armed_at is not None
                else None
            ),
            "entry_model": self.entry_model,
            "entry_models": list(self.entry_models),
            "exit_price": format(self.exit_price, "f") if self.exit_price is not None else None,
            "outcome": self.outcome,
            "r_multiple": (
                format(self.r_multiple, "f") if self.r_multiple is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2BacktestReport:
    software_sha: str
    account_fingerprint: str
    evidence_fingerprint: str
    checked_at: datetime
    decision_days: int
    setup_count: int
    unfilled_setup_count: int
    pending_gap_count: int
    abstain_evaluation_counts: tuple[tuple[str, int], ...]
    session_abstain_counts: tuple[tuple[str, int], ...]
    trades: tuple[Vt31SilverBulletV2Trade, ...]

    @property
    def filled_count(self) -> int:
        return len(self.trades)

    @property
    def terminal_trades(self) -> tuple[Vt31SilverBulletV2Trade, ...]:
        return tuple(item for item in self.trades if item.r_multiple is not None)

    def payload(self) -> dict[str, object]:
        terminal = self.terminal_trades
        r_values = tuple(cast(Decimal, item.r_multiple) for item in terminal)
        target_count = sum(item.outcome == "target" for item in terminal)
        stop_count = sum(item.outcome == "stop" for item in terminal)
        breakeven_count = sum(item.outcome == "breakeven" for item in terminal)
        fill_rate = (
            Decimal(self.filled_count) / Decimal(self.setup_count)
            if self.setup_count
            else Decimal(0)
        )
        win_rate = (
            Decimal(target_count) / Decimal(len(terminal)) if terminal else Decimal(0)
        )
        expectancy = (
            sum(r_values, Decimal(0)) / Decimal(len(r_values))
            if r_values
            else Decimal(0)
        )
        drawdown = _max_drawdown_r(r_values)
        losing_streak, winning_streak = _streaks(terminal)
        return {
            "schema": _SCHEMA,
            "environment": "demo",
            "read_only": True,
            "research_only": True,
            "trader_code": "vt-31",
            "trader_version": "v2",
            "methodology": "silver-bullet-am-nq-v2",
            "methodology_version": "v2.1-source-complete",
            "symbol": _SYMBOL,
            "source_authorized_market": _SYMBOL,
            "decision_timeframe": "M1",
            "execution_model": _EXECUTION_MODEL,
            "position_management": "source-3r-to-breakeven-v1",
            "same_bar_policy": "stop-first-before-be-be-first-after-be-v1",
            "one_fill_per_session": True,
            "software_sha": self.software_sha,
            "account_fingerprint": self.account_fingerprint,
            "evidence_fingerprint": self.evidence_fingerprint,
            "checked_at": self.checked_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "decision_days": self.decision_days,
            "setup_count": self.setup_count,
            "filled_count": self.filled_count,
            "unfilled_setup_count": self.unfilled_setup_count,
            "pending_gap_count": self.pending_gap_count,
            "fill_rate": format(fill_rate, "f"),
            "terminal_sample_size": len(terminal),
            "win_rate": format(win_rate, "f"),
            "expectancy_r": format(expectancy, "f"),
            "max_drawdown_r": format(drawdown, "f"),
            "winning_streak": winning_streak,
            "losing_streak": losing_streak,
            "target_count": target_count,
            "stop_count": stop_count,
            "breakeven_count": breakeven_count,
            "gap_censored_count": sum(item.outcome == "gap_censored" for item in self.trades),
            "data_end_censored_count": sum(
                item.outcome == "data_end_censored" for item in self.trades
            ),
            "abstain_evaluation_counts": dict(self.abstain_evaluation_counts),
            "session_abstain_counts": dict(self.session_abstain_counts),
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


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be bool")
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be int")
    return value


def _timestamp(value: object, *, field_name: str) -> datetime:
    raw = _text(value, field_name=field_name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, field_name: str) -> Decimal:
    raw = _text(value, field_name=field_name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise Vt31SilverBulletV2BacktestError(f"{field_name} must be decimal") from error
    if not parsed.is_finite() or parsed <= 0:
        raise Vt31SilverBulletV2BacktestError(
            f"{field_name} must be positive finite decimal"
        )
    return parsed


def _snapshot(item: object, *, instrument: Instrument) -> OhlcSnapshot:
    payload = _object(item, field_name="M1 bar")
    opened_at = _timestamp(payload.get("opened_at"), field_name="bar opened_at")
    closed_at = _timestamp(payload.get("closed_at"), field_name="bar closed_at")
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            uuid5(NAMESPACE_URL, f"qore:vt31-v2:{instrument.symbol}:{opened_at.isoformat()}")
        ),
        instrument=instrument,
        source=_SOURCE,
        timeframe=Timeframe(_M1_SECONDS),
        opened_at=opened_at,
        closed_at=closed_at,
        open=float(_decimal(payload.get("open"), field_name="bar open")),
        high=float(_decimal(payload.get("high"), field_name="bar high")),
        low=float(_decimal(payload.get("low"), field_name="bar low")),
        close=float(_decimal(payload.get("close"), field_name="bar close")),
    )


def _canonical_evidence_fingerprint(payload: dict[str, object]) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(material).hexdigest()


def _load(
    path: Path,
) -> tuple[tuple[OhlcSnapshot, ...], str, str, datetime, str]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31SilverBulletV2BacktestError("cannot read VT-31 V2 evidence") from error
    payload = _object(decoded, field_name="VT-31 V2 evidence")
    if _text(payload.get("schema"), field_name="schema") != _EVIDENCE_SCHEMA:
        raise Vt31SilverBulletV2BacktestError("unexpected VT-31 V2 evidence schema")
    if _text(payload.get("environment"), field_name="environment") != "demo":
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 evidence must be DEMO")
    if not _strict_bool(payload.get("read_only"), field_name="read_only"):
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 evidence must be read-only")
    if _strict_bool(payload.get("account_is_live"), field_name="account_is_live"):
        raise Vt31SilverBulletV2BacktestError("LIVE evidence is prohibited")
    if not _strict_bool(
        payload.get("trading_permission_verified"),
        field_name="trading_permission_verified",
    ):
        raise Vt31SilverBulletV2BacktestError("DEMO permission must be verified")
    if _strict_int(
        payload.get("required_coverage_days"),
        field_name="required_coverage_days",
    ) < _REQUIRED_COVERAGE_DAYS:
        raise Vt31SilverBulletV2BacktestError("M1 evidence must require at least 730 days")
    source_market = _text(
        payload.get("source_authorized_market"),
        field_name="source_authorized_market",
    )
    if source_market != _SYMBOL:
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 source contract requires NAS100")
    symbol_payload = _object(payload.get("symbol"), field_name="symbol")
    symbol = _text(symbol_payload.get("symbol_name"), field_name="symbol_name")
    if symbol != _SYMBOL:
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 canonical evidence must bind NAS100")
    provider_symbol_name = _text(
        payload.get("provider_symbol_name"), field_name="provider_symbol_name"
    )
    if not provider_symbol_name.strip():
        raise Vt31SilverBulletV2BacktestError("provider symbol name must be retained")
    account_fingerprint = _text(
        payload.get("account_fingerprint"), field_name="account_fingerprint"
    )
    if re.fullmatch(r"[0-9a-f]{64}", account_fingerprint) is None:
        raise Vt31SilverBulletV2BacktestError("account fingerprint must be SHA-256")
    software_sha = _text(payload.get("software_sha"), field_name="software_sha")
    if re.fullmatch(r"[0-9a-f]{40}", software_sha) is None:
        raise Vt31SilverBulletV2BacktestError("software_sha must be exact Git SHA")
    checked_at = _timestamp(payload.get("checked_at"), field_name="checked_at")
    periods = _object(payload.get("periods"), field_name="periods")
    if set(periods) != {"M1"}:
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 evidence must contain only M1")
    rows = _array(periods.get("M1"), field_name="period M1")
    instrument = Instrument(symbol)
    snapshots = tuple(_snapshot(item, instrument=instrument) for item in rows)
    if not snapshots:
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 M1 evidence is empty")
    if snapshots != tuple(sorted(snapshots, key=lambda item: item.opened_at)):
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 M1 evidence is not chronological")
    identities = tuple((item.opened_at, item.closed_at) for item in snapshots)
    if len(set(identities)) != len(identities):
        raise Vt31SilverBulletV2BacktestError("VT-31 V2 M1 evidence contains duplicates")
    if any(item.closed_at > checked_at for item in snapshots):
        raise Vt31SilverBulletV2BacktestError("future M1 evidence is prohibited")
    coverage = _object(payload.get("coverage"), field_name="coverage")
    if _strict_int(coverage.get("bar_count"), field_name="coverage bar_count") != len(
        snapshots
    ):
        raise Vt31SilverBulletV2BacktestError("M1 coverage count mismatch")
    if snapshots[-1].closed_at - snapshots[0].opened_at < timedelta(
        days=_REQUIRED_COVERAGE_DAYS
    ):
        raise Vt31SilverBulletV2BacktestError("M1 evidence span is below 730 days")
    return (
        snapshots,
        account_fingerprint,
        _canonical_evidence_fingerprint(payload),
        checked_at,
        software_sha,
    )


def _ny_date(value: datetime) -> date:
    return value.astimezone(_NY).date()


def _ny_wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _touches(bar: OhlcSnapshot, price: Decimal) -> bool:
    return Decimal(str(bar.low)) <= price <= Decimal(str(bar.high))


def _expected_next(previous: OhlcSnapshot, current: OhlcSnapshot) -> bool:
    return current.opened_at == previous.closed_at


def _contiguous(bars: tuple[OhlcSnapshot, ...]) -> bool:
    return all(
        _expected_next(previous, current)
        for previous, current in zip(bars, bars[1:], strict=False)
    )


def _r_multiple(setup: Vt31SilverBulletV2Setup) -> Decimal:
    risk = setup.initial_risk
    reward = abs(setup.take_profit_price - setup.entry_price)
    if risk <= 0:
        raise Vt31SilverBulletV2BacktestError("setup risk must be positive")
    return reward / risk


def _trade(
    *,
    signal: OhlcSnapshot,
    fill_bar: OhlcSnapshot,
    setup: Vt31SilverBulletV2Setup,
    resolved_at: datetime | None,
    breakeven_armed_at: datetime | None,
    exit_price: Decimal | None,
    outcome: str,
    r_multiple: Decimal | None,
) -> Vt31SilverBulletV2Trade:
    return Vt31SilverBulletV2Trade(
        signal_at=signal.closed_at,
        filled_at=fill_bar.closed_at,
        fill_interval_opened_at=fill_bar.opened_at,
        fill_interval_closed_at=fill_bar.closed_at,
        resolved_at=resolved_at,
        side=setup.side,
        entry_price=setup.entry_price,
        stop_loss=setup.invalidation_price,
        take_profit=setup.take_profit_price,
        three_r_price=setup.three_r_price,
        breakeven_armed_at=breakeven_armed_at,
        entry_model=setup.entry_model.value,
        entry_models=tuple(item.value for item in setup.entry_models),
        exit_price=exit_price,
        outcome=outcome,
        r_multiple=r_multiple,
    )


def _model_trade(
    series: tuple[OhlcSnapshot, ...],
    *,
    signal_index: int,
    setup: Vt31SilverBulletV2Setup,
) -> tuple[Vt31SilverBulletV2Trade | None, int, str]:
    signal = series[signal_index]
    prior = signal
    fill_index: int | None = None
    index = signal_index + 1
    while index < len(series):
        bar = series[index]
        if _ny_date(bar.opened_at) != _ny_date(signal.opened_at) or _ny_wall(
            bar.opened_at
        ) >= (11, 0, 0):
            return None, max(signal_index, index - 1), "unfilled"
        if not _expected_next(prior, bar):
            return None, index - 1, "pending_gap"
        if _touches(bar, setup.entry_price):
            fill_index = index
            break
        prior = bar
        index += 1
    if fill_index is None:
        return None, len(series) - 1, "unfilled"

    fill_bar = series[fill_index]
    breakeven_armed_at: datetime | None = None
    for exit_index in range(fill_index, len(series)):
        bar = series[exit_index]
        if exit_index > fill_index and not _expected_next(series[exit_index - 1], bar):
            return (
                _trade(
                    signal=signal,
                    fill_bar=fill_bar,
                    setup=setup,
                    resolved_at=series[exit_index - 1].closed_at,
                    breakeven_armed_at=breakeven_armed_at,
                    exit_price=None,
                    outcome="gap_censored",
                    r_multiple=None,
                ),
                exit_index - 1,
                "filled",
            )

        if breakeven_armed_at is None:
            # The fill bar has unknown intrabar chronology. Adverse stop evidence is
            # honored conservatively, while favorable target/3R evidence is not
            # credited until a later bar. This prevents pre-fill favorable look-ahead.
            if exit_index == fill_index:
                if _touches(bar, setup.invalidation_price):
                    return (
                        _trade(
                            signal=signal,
                            fill_bar=fill_bar,
                            setup=setup,
                            resolved_at=bar.closed_at,
                            breakeven_armed_at=None,
                            exit_price=setup.invalidation_price,
                            outcome="stop",
                            r_multiple=Decimal("-1"),
                        ),
                        exit_index,
                        "filled",
                    )
                continue
            # Source replay containment: initial stop wins any unresolved same-bar race.
            if _touches(bar, setup.invalidation_price):
                return (
                    _trade(
                        signal=signal,
                        fill_bar=fill_bar,
                        setup=setup,
                        resolved_at=bar.closed_at,
                        breakeven_armed_at=None,
                        exit_price=setup.invalidation_price,
                        outcome="stop",
                        r_multiple=Decimal("-1"),
                    ),
                    exit_index,
                    "filled",
                )
            if _touches(bar, setup.take_profit_price):
                return (
                    _trade(
                        signal=signal,
                        fill_bar=fill_bar,
                        setup=setup,
                        resolved_at=bar.closed_at,
                        breakeven_armed_at=None,
                        exit_price=setup.take_profit_price,
                        outcome="target",
                        r_multiple=_r_multiple(setup),
                    ),
                    exit_index,
                    "filled",
                )
            if _touches(bar, setup.three_r_price):
                # The stop transition becomes actionable only after this bar closes.
                breakeven_armed_at = bar.closed_at
            continue

        # Once 3R has been observed on a prior closed bar, BE is the effective stop.
        if _touches(bar, setup.entry_price):
            return (
                _trade(
                    signal=signal,
                    fill_bar=fill_bar,
                    setup=setup,
                    resolved_at=bar.closed_at,
                    breakeven_armed_at=breakeven_armed_at,
                    exit_price=setup.entry_price,
                    outcome="breakeven",
                    r_multiple=Decimal(0),
                ),
                exit_index,
                "filled",
            )
        if _touches(bar, setup.take_profit_price):
            return (
                _trade(
                    signal=signal,
                    fill_bar=fill_bar,
                    setup=setup,
                    resolved_at=bar.closed_at,
                    breakeven_armed_at=breakeven_armed_at,
                    exit_price=setup.take_profit_price,
                    outcome="target",
                    r_multiple=_r_multiple(setup),
                ),
                exit_index,
                "filled",
            )

    return (
        _trade(
            signal=signal,
            fill_bar=fill_bar,
            setup=setup,
            resolved_at=None,
            breakeven_armed_at=breakeven_armed_at,
            exit_price=None,
            outcome="data_end_censored",
            r_multiple=None,
        ),
        len(series) - 1,
        "filled",
    )


def _max_drawdown_r(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > maximum:
            maximum = drawdown
    return maximum


def _streaks(trades: tuple[Vt31SilverBulletV2Trade, ...]) -> tuple[int, int]:
    losing = 0
    winning = 0
    current_losing = 0
    current_winning = 0
    for trade in trades:
        if trade.outcome == "target":
            current_winning += 1
            current_losing = 0
        elif trade.outcome == "stop":
            current_losing += 1
            current_winning = 0
        else:
            current_losing = 0
            current_winning = 0
        losing = max(losing, current_losing)
        winning = max(winning, current_winning)
    return losing, winning


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def run_vt31_silver_bullet_v2_backtest(path: Path) -> Vt31SilverBulletV2BacktestReport:
    """Run one source-bound, no-lookahead NAS100 VT-31 V2 research pass."""

    series, account_fingerprint, evidence_fingerprint, checked_at, software_sha = _load(path)
    index_by_open = {item.opened_at: index for index, item in enumerate(series)}
    day_groups: dict[date, list[OhlcSnapshot]] = {}
    for bar in series:
        day_groups.setdefault(_ny_date(bar.opened_at), []).append(bar)

    trades: list[Vt31SilverBulletV2Trade] = []
    setup_count = 0
    unfilled = 0
    pending_gap = 0
    decision_days = 0
    abstain_evaluations: dict[str, int] = {}
    session_abstains: dict[str, int] = {}
    for local_day in sorted(day_groups):
        bars = tuple(day_groups[local_day])
        reference = tuple(
            item
            for item in bars
            if (9, 0, 0) <= _ny_wall(item.opened_at) < (10, 0, 0)
        )
        session = tuple(
            item
            for item in bars
            if (10, 0, 0) <= _ny_wall(item.opened_at) < (11, 0, 0)
        )
        if len(reference) != 60 or not _contiguous(reference) or not session:
            _increment(session_abstains, "reference-or-session-data-incomplete")
            continue
        if _ny_wall(session[0].opened_at) != (10, 0, 0):
            _increment(session_abstains, "session-does-not-start-at-10-new-york")
            continue
        decision_days += 1
        selected_setup: tuple[int, Vt31SilverBulletV2Setup] | None = None
        prefix: list[OhlcSnapshot] = list(reference)
        previous_session_bar: OhlcSnapshot | None = None
        last_reason = "no-evaluation"
        for bar in session:
            if previous_session_bar is not None and not _expected_next(
                previous_session_bar, bar
            ):
                last_reason = "session-data-gap"
                break
            prefix.append(bar)
            evaluated = evaluate_vt31_silver_bullet_v2(
                Vt31SilverBulletV2Input(
                    instrument=Instrument(_SYMBOL),
                    as_of=bar.closed_at,
                    m1_candles=tuple(prefix),
                )
            )
            if evaluated.decision is DemoTradingDecision.SETUP and evaluated.setup is not None:
                selected_setup = (index_by_open[bar.opened_at], evaluated.setup)
                break
            last_reason = evaluated.reason_code
            _increment(abstain_evaluations, evaluated.reason_code)
            previous_session_bar = bar
        if selected_setup is None:
            _increment(session_abstains, last_reason)
            continue
        setup_count += 1
        signal_index, setup = selected_setup
        trade, _consumed, status = _model_trade(
            series,
            signal_index=signal_index,
            setup=setup,
        )
        if status == "unfilled":
            unfilled += 1
        elif status == "pending_gap":
            pending_gap += 1
        elif trade is not None:
            trades.append(trade)

    return Vt31SilverBulletV2BacktestReport(
        software_sha=software_sha,
        account_fingerprint=account_fingerprint,
        evidence_fingerprint=evidence_fingerprint,
        checked_at=checked_at,
        decision_days=decision_days,
        setup_count=setup_count,
        unfilled_setup_count=unfilled,
        pending_gap_count=pending_gap,
        abstain_evaluation_counts=tuple(sorted(abstain_evaluations.items())),
        session_abstain_counts=tuple(sorted(session_abstains.items())),
        trades=tuple(trades),
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print(
            "usage: python -m qore.infrastructure.trader_lab."
            "vt31_silver_bullet_v2_backtest PATH"
        )
        return 2
    try:
        report = run_vt31_silver_bullet_v2_backtest(Path(arguments[0]))
    except Vt31SilverBulletV2BacktestError as error:
        print(f"VT-31 V2 backtest failed: {error}", file=sys.stderr)
        return 1
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
