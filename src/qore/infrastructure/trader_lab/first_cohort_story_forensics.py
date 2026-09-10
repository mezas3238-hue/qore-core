"""Deterministic visual-story forensics for the first Trader Lab cohort.

This module consumes exact retained QORE market, backtest, and characterization
artifacts and emits a renderer-neutral story pack.  The pack is designed for a
TradingView Lightweight Charts surface, but visualization never becomes an
evidence source or authority boundary.

All sequence claims are closed-bar claims.  Intrabar ordering is never inferred.
Decision-time context is kept separate from post-outcome/oracle observations.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import cast

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    FirstCohortBacktestError,
    _load,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_SCHEMA = "qore.trader_lab.first_cohort_story_forensics.v1"
_BACKTEST_SCHEMA = "qore.trader_lab.first_cohort_backtest.v1"
_CHARACTERIZATION_SCHEMA = "qore.trader_lab.first_cohort_characterization.v1"
_SELECTION_POLICY = "representative-extreme-recent-context-anomaly-v1"
_RENDERER_ID = "tradingview-lightweight-charts"
_RENDERER_VERSION = "5.2.1"
_CONTEXT_BARS = 60
_POST_EXIT_BARS = 20
_REQUIRED_STORY_COUNT = 5
_DIRECT_STOP_MAX_MFE_R = Decimal("0.25")
_SIGNIFICANT_GIVEBACK_MIN_MFE_R = Decimal("0.50")
_ONE_R = Decimal("1")
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")


class FirstCohortStoryForensicsError(FirstCohortBacktestError):
    """Raised when story evidence is inconsistent, ambiguous, or incomplete."""

    __slots__ = ()


class StoryOutcome(StrEnum):
    """Closed set of realized outcome signs used for streak construction."""

    WIN = "win"
    LOSS = "loss"


class StoryClassification(StrEnum):
    """Versioned provisional research classification for one exact episode."""

    LOSS_DIRECT_NO_EDGE = "LOSS_DIRECT_NO_EDGE"
    LOSS_AFTER_SMALL_MFE = "LOSS_AFTER_SMALL_MFE"
    LOSS_AFTER_SIGNIFICANT_MFE = "LOSS_AFTER_SIGNIFICANT_MFE"
    LOSS_AFTER_1R_OR_MORE = "LOSS_AFTER_1R_OR_MORE"
    LOSS_NORMAL_ACCEPTABLE = "LOSS_NORMAL_ACCEPTABLE"
    WIN_CANONICAL = "WIN_CANONICAL"
    WIN_OTHER = "WIN_OTHER"


@dataclass(frozen=True, slots=True)
class _TradeRecord:
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


@dataclass(frozen=True, slots=True)
class _SetupContext:
    setup_reason: str
    session: str
    trend_regime: str
    volatility_regime: str
    timeframe: str

    @property
    def signature(self) -> str:
        return "|".join(
            (
                self.session,
                self.trend_regime,
                self.volatility_regime,
                self.timeframe,
            )
        )


@dataclass(frozen=True, slots=True)
class _TrajectoryPoint:
    at: datetime
    close: Decimal
    return_fraction: Decimal
    r_multiple: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "at": self.at.isoformat(),
            "time_unix": int(self.at.timestamp()),
            "close": format(self.close, "f"),
            "return_fraction": format(self.return_fraction, "f"),
            "r_multiple": format(self.r_multiple, "f"),
        }


@dataclass(frozen=True, slots=True)
class _Episode:
    episode_id: str
    trader_code: str
    symbol: str
    execution_period: str
    trade: _TradeRecord
    context: _SetupContext
    bars: tuple[OhlcSnapshot, ...]
    trajectory: tuple[_TrajectoryPoint, ...]
    mfe_fraction: Decimal
    mfe_r: Decimal
    mfe_at: datetime
    mae_fraction: Decimal
    mae_r: Decimal
    mae_at: datetime
    classification: StoryClassification

    @property
    def outcome(self) -> StoryOutcome:
        return StoryOutcome.WIN if self.trade.return_rate > 0 else StoryOutcome.LOSS

    def payload(self) -> dict[str, object]:
        decision_narrative = (
            f"{self.trader_code.upper()} observed a {self.trade.side.value} setup at "
            f"{self.trade.signal_at.isoformat()} in session={self.context.session}, "
            f"trend_regime={self.context.trend_regime}, "
            f"volatility_regime={self.context.volatility_regime}. "
            f"The frozen setup reason was {self.context.setup_reason}."
        )
        outcome_narrative = _outcome_narrative(self)
        return {
            "episode_id": self.episode_id,
            "trader_code": self.trader_code,
            "symbol": self.symbol,
            "execution_period": self.execution_period,
            "classification": self.classification.value,
            "outcome": self.outcome.value,
            "decision_time": {
                "signal_at": self.trade.signal_at.isoformat(),
                "side": self.trade.side.value,
                "entry_price": format(self.trade.entry_price, "f"),
                "stop_loss": format(self.trade.stop_loss, "f"),
                "take_profit": format(self.trade.take_profit, "f"),
                "setup_reason": self.context.setup_reason,
                "session": self.context.session,
                "trend_regime": self.context.trend_regime,
                "volatility_regime": self.context.volatility_regime,
                "timeframe": self.context.timeframe,
                "narrative": decision_narrative,
            },
            "post_outcome": {
                "filled_at": self.trade.filled_at.isoformat(),
                "exited_at": self.trade.exited_at.isoformat(),
                "exit_reason": self.trade.exit_reason,
                "exit_price": format(self.trade.exit_price, "f"),
                "return_rate": format(self.trade.return_rate, "f"),
                "close_path_mfe_fraction": format(self.mfe_fraction, "f"),
                "close_path_mfe_r": format(self.mfe_r, "f"),
                "close_path_mfe_at": self.mfe_at.isoformat(),
                "close_path_mae_fraction": format(self.mae_fraction, "f"),
                "close_path_mae_r": format(self.mae_r, "f"),
                "close_path_mae_at": self.mae_at.isoformat(),
                "measurement": "closed-bar-path; no intrabar ordering inferred",
                "narrative": outcome_narrative,
            },
            "chart": {
                "renderer": _RENDERER_ID,
                "renderer_version": _RENDERER_VERSION,
                "source_of_truth": "qore-retained-evidence",
                "bars": [_bar_payload(bar) for bar in self.bars],
                "price_lines": [
                    {
                        "kind": "entry",
                        "price": format(self.trade.entry_price, "f"),
                    },
                    {
                        "kind": "stop_loss",
                        "price": format(self.trade.stop_loss, "f"),
                    },
                    {
                        "kind": "take_profit",
                        "price": format(self.trade.take_profit, "f"),
                    },
                ],
                "markers": [
                    _marker("signal", self.trade.signal_at, "SIG"),
                    _marker("entry", self.trade.filled_at, "ENTRY"),
                    _marker("mfe", self.mfe_at, f"MFE {format(self.mfe_r, 'f')}R"),
                    _marker("mae", self.mae_at, f"MAE {format(self.mae_r, 'f')}R"),
                    _marker("exit", self.trade.exited_at, self.trade.exit_reason.upper()),
                ],
                "frame_sequence": _frame_sequence(self),
                "screenshot_capable": True,
            },
            "trajectory": [point.payload() for point in self.trajectory],
        }


@dataclass(frozen=True, slots=True)
class _Streak:
    outcome: StoryOutcome
    episodes: tuple[_Episode, ...]

    @property
    def start_at(self) -> datetime:
        return self.episodes[0].trade.filled_at

    @property
    def end_at(self) -> datetime:
        return self.episodes[-1].trade.exited_at

    @property
    def compounded_return(self) -> Decimal:
        equity = Decimal(1)
        for episode in self.episodes:
            equity *= Decimal(1) + episode.trade.return_rate
        return equity - Decimal(1)

    @property
    def context_signature(self) -> str:
        signatures = Counter(episode.context.signature for episode in self.episodes)
        return sorted(signatures.items(), key=lambda item: (-item[1], item[0]))[0][0]

    @property
    def streak_id(self) -> str:
        material = "|".join(episode.episode_id for episode in self.episodes)
        return f"streak-{sha256(material.encode('utf-8')).hexdigest()[:20]}"

    def payload(self) -> dict[str, object]:
        return {
            "streak_id": self.streak_id,
            "outcome": self.outcome.value,
            "length": len(self.episodes),
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "compounded_return": format(self.compounded_return, "f"),
            "dominant_context_signature": self.context_signature,
            "episode_ids": [episode.episode_id for episode in self.episodes],
        }


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortStoryForensicsError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortStoryForensicsError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortStoryForensicsError(f"{field_name} must be a non-empty string")
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortStoryForensicsError(f"{field_name} must be bool")
    return value


def _timestamp(value: object, *, field_name: str) -> datetime:
    raw = _text(value, field_name=field_name)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise FirstCohortStoryForensicsError(f"{field_name} must be RFC3339") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FirstCohortStoryForensicsError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _decimal(value: object, *, field_name: str, positive: bool = False) -> Decimal:
    raw = _text(value, field_name=field_name)
    try:
        parsed = Decimal(raw)
    except InvalidOperation as error:
        raise FirstCohortStoryForensicsError(f"{field_name} must be decimal") from error
    if not parsed.is_finite() or (positive and parsed <= 0):
        requirement = "positive finite" if positive else "finite"
        raise FirstCohortStoryForensicsError(f"{field_name} must be {requirement} decimal")
    return parsed


def _read_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortStoryForensicsError(f"cannot read {field_name}") from error
    return _object(decoded, field_name=field_name)


def _side(value: object, *, field_name: str) -> DemoTradingSetupSide:
    raw = _text(value, field_name=field_name)
    try:
        return DemoTradingSetupSide(raw)
    except ValueError as error:
        raise FirstCohortStoryForensicsError(f"{field_name} must be canonical") from error


def _trade(item: object) -> _TradeRecord:
    row = _object(item, field_name="backtest trade")
    exit_reason = _text(row.get("exit_reason"), field_name="trade exit_reason")
    if exit_reason not in {"stop", "target", "time_exit", "gap_exit"}:
        raise FirstCohortStoryForensicsError("unsupported trade exit reason")
    trade = _TradeRecord(
        signal_at=_timestamp(row.get("signal_at"), field_name="trade signal_at"),
        filled_at=_timestamp(row.get("filled_at"), field_name="trade filled_at"),
        exited_at=_timestamp(row.get("exited_at"), field_name="trade exited_at"),
        side=_side(row.get("side"), field_name="trade side"),
        entry_price=_decimal(row.get("entry_price"), field_name="trade entry_price", positive=True),
        stop_loss=_decimal(row.get("stop_loss"), field_name="trade stop_loss", positive=True),
        take_profit=_decimal(
            row.get("take_profit"), field_name="trade take_profit", positive=True
        ),
        exit_price=_decimal(row.get("exit_price"), field_name="trade exit_price", positive=True),
        return_rate=_decimal(row.get("return_rate"), field_name="trade return_rate"),
        exit_reason=exit_reason,
    )
    if not trade.signal_at <= trade.filled_at <= trade.exited_at:
        raise FirstCohortStoryForensicsError("trade timestamps must be monotonic")
    return trade


def _load_backtest(
    path: Path,
    *,
    account_fingerprint: str,
    symbol: str,
    software_sha: str,
    trader_code: str,
) -> tuple[str, tuple[_TradeRecord, ...]]:
    payload = _read_json(path, field_name="backtest evidence")
    if _text(payload.get("schema"), field_name="backtest schema") != _BACKTEST_SCHEMA:
        raise FirstCohortStoryForensicsError("story forensics requires first-cohort backtest v1")
    if _text(payload.get("environment"), field_name="backtest environment") != "demo":
        raise FirstCohortStoryForensicsError("backtest evidence must be DEMO")
    if not _strict_bool(payload.get("read_only"), field_name="backtest read_only"):
        raise FirstCohortStoryForensicsError("backtest evidence must be read-only")
    if _text(payload.get("symbol"), field_name="backtest symbol") != symbol:
        raise FirstCohortStoryForensicsError("market/backtest symbol mismatch")
    if (
        _text(payload.get("account_fingerprint"), field_name="backtest account")
        != account_fingerprint
    ):
        raise FirstCohortStoryForensicsError("market/backtest account mismatch")
    if _text(payload.get("software_sha"), field_name="backtest software_sha") != software_sha:
        raise FirstCohortStoryForensicsError("market/backtest software SHA mismatch")
    matches: list[dict[str, object]] = []
    for item in _array(payload.get("results"), field_name="backtest results"):
        row = _object(item, field_name="backtest result")
        if _text(row.get("trader_code"), field_name="backtest trader_code") == trader_code:
            matches.append(row)
    if len(matches) != 1:
        raise FirstCohortStoryForensicsError("backtest must contain exactly one requested Trader")
    result = matches[0]
    execution_period = _text(result.get("execution_period"), field_name="execution_period")
    trades = tuple(_trade(item) for item in _array(result.get("trades"), field_name="trades"))
    if tuple(sorted(trades, key=lambda trade: trade.signal_at)) != trades:
        raise FirstCohortStoryForensicsError("backtest trades must be chronological")
    return execution_period, trades


def _setup_context(item: object) -> tuple[datetime, DemoTradingSetupSide, Decimal, _SetupContext]:
    row = _object(item, field_name="characterization setup")
    if not _strict_bool(row.get("filled"), field_name="setup filled"):
        raise FirstCohortStoryForensicsError("requested setup context must be filled")
    return (
        _timestamp(row.get("signal_at"), field_name="setup signal_at"),
        _side(row.get("side"), field_name="setup side"),
        _decimal(row.get("entry_price"), field_name="setup entry_price", positive=True),
        _SetupContext(
            setup_reason=_text(row.get("setup_reason"), field_name="setup reason"),
            session=_text(row.get("session"), field_name="setup session"),
            trend_regime=_text(row.get("trend_regime"), field_name="trend regime"),
            volatility_regime=_text(
                row.get("volatility_regime"), field_name="volatility regime"
            ),
            timeframe=_text(row.get("timeframe"), field_name="setup timeframe"),
        ),
    )


def _load_characterization(
    path: Path,
    *,
    account_fingerprint: str,
    symbol: str,
    software_sha: str,
    trader_code: str,
) -> tuple[str, str, dict[tuple[datetime, DemoTradingSetupSide, Decimal], _SetupContext]]:
    payload = _read_json(path, field_name="characterization evidence")
    if (
        _text(payload.get("schema"), field_name="characterization schema")
        != _CHARACTERIZATION_SCHEMA
    ):
        raise FirstCohortStoryForensicsError("story forensics requires characterization v1")
    if _text(payload.get("environment"), field_name="characterization environment") != "demo":
        raise FirstCohortStoryForensicsError("characterization evidence must be DEMO")
    if not _strict_bool(payload.get("read_only"), field_name="characterization read_only"):
        raise FirstCohortStoryForensicsError("characterization must be read-only")
    if _text(payload.get("symbol"), field_name="characterization symbol") != symbol:
        raise FirstCohortStoryForensicsError("market/characterization symbol mismatch")
    if (
        _text(payload.get("account_fingerprint"), field_name="characterization account")
        != account_fingerprint
    ):
        raise FirstCohortStoryForensicsError("market/characterization account mismatch")
    if (
        _text(payload.get("software_sha"), field_name="characterization software_sha")
        != software_sha
    ):
        raise FirstCohortStoryForensicsError("market/characterization software SHA mismatch")
    holdout = _object(payload.get("holdout_governance"), field_name="holdout governance")
    if _text(holdout.get("state"), field_name="holdout state") != "consumed_for_research":
        raise FirstCohortStoryForensicsError("story forensics requires research-consumed evidence")
    trader_matches: list[dict[str, object]] = []
    for item in _array(payload.get("results"), field_name="characterization results"):
        row = _object(item, field_name="characterization result")
        if _text(row.get("trader_code"), field_name="characterization trader_code") == trader_code:
            trader_matches.append(row)
    if len(trader_matches) != 1:
        raise FirstCohortStoryForensicsError(
            "characterization must contain exactly one requested Trader"
        )
    profiles = _array(trader_matches[0].get("profiles"), field_name="profiles")
    defaults = [
        _object(item, field_name="profile")
        for item in profiles
        if _text(
            _object(item, field_name="profile").get("profile"), field_name="profile label"
        )
        == "production-default"
    ]
    if len(defaults) != 1:
        raise FirstCohortStoryForensicsError("exactly one production-default profile is required")
    profile = defaults[0]
    config_fingerprint = _text(
        profile.get("config_fingerprint"), field_name="config fingerprint"
    )
    methodology = _object(profile.get("methodology_identity"), field_name="methodology identity")
    methodology_fingerprint = _text(
        methodology.get("methodology_fingerprint"), field_name="methodology fingerprint"
    )
    contexts: dict[tuple[datetime, DemoTradingSetupSide, Decimal], _SetupContext] = {}
    for item in _array(profile.get("setups"), field_name="profile setups"):
        row = _object(item, field_name="characterization setup")
        if not _strict_bool(row.get("filled"), field_name="setup filled"):
            continue
        signal_at, side, entry_price, context = _setup_context(row)
        key = (signal_at, side, entry_price)
        if key in contexts:
            raise FirstCohortStoryForensicsError("duplicate filled characterization setup")
        contexts[key] = context
    return config_fingerprint, methodology_fingerprint, contexts


def _bar_payload(bar: OhlcSnapshot) -> dict[str, object]:
    return {
        "time": int(bar.closed_at.timestamp()),
        "opened_at": bar.opened_at.astimezone(UTC).isoformat(),
        "closed_at": bar.closed_at.astimezone(UTC).isoformat(),
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
    }


def _marker(kind: str, at: datetime, label: str) -> dict[str, object]:
    return {
        "kind": kind,
        "time": int(at.timestamp()),
        "at": at.isoformat(),
        "label": label,
    }


def _return_fraction(
    *, side: DemoTradingSetupSide, entry: Decimal, close: Decimal
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return (close - entry) / entry
    return (entry - close) / entry


def _trajectory(
    trade: _TradeRecord,
    execution: tuple[OhlcSnapshot, ...],
    closed_index: dict[datetime, int],
) -> tuple[_TrajectoryPoint, ...]:
    fill_index = closed_index.get(trade.filled_at)
    exit_index = closed_index.get(trade.exited_at)
    if fill_index is None or exit_index is None or exit_index < fill_index:
        raise FirstCohortStoryForensicsError("trade path cannot be bound to execution bars")
    risk_fraction = abs(trade.entry_price - trade.stop_loss) / trade.entry_price
    if risk_fraction <= 0:
        raise FirstCohortStoryForensicsError("trade risk fraction must be positive")
    points: list[_TrajectoryPoint] = []
    for bar in execution[fill_index : exit_index + 1]:
        close = Decimal(str(bar.close))
        return_fraction = _return_fraction(
            side=trade.side,
            entry=trade.entry_price,
            close=close,
        )
        points.append(
            _TrajectoryPoint(
                at=bar.closed_at,
                close=close,
                return_fraction=return_fraction,
                r_multiple=return_fraction / risk_fraction,
            )
        )
    if not points:
        raise FirstCohortStoryForensicsError("trade trajectory cannot be empty")
    return tuple(points)


def _excursions(
    points: tuple[_TrajectoryPoint, ...],
) -> tuple[Decimal, Decimal, datetime, Decimal, Decimal, datetime]:
    max_point = max(points, key=lambda point: (point.r_multiple, -point.at.timestamp()))
    min_point = min(points, key=lambda point: (point.r_multiple, point.at.timestamp()))
    mfe_r = max(max_point.r_multiple, Decimal(0))
    mae_r = max(-min_point.r_multiple, Decimal(0))
    mfe_fraction = max(max_point.return_fraction, Decimal(0))
    mae_fraction = max(-min_point.return_fraction, Decimal(0))
    return (
        mfe_fraction,
        mfe_r,
        max_point.at,
        mae_fraction,
        mae_r,
        min_point.at,
    )


def _classification(
    trade: _TradeRecord,
    *,
    mfe_r: Decimal,
) -> StoryClassification:
    if trade.return_rate > 0:
        if trade.exit_reason == "target":
            return StoryClassification.WIN_CANONICAL
        return StoryClassification.WIN_OTHER
    if trade.exit_reason != "stop":
        return StoryClassification.LOSS_NORMAL_ACCEPTABLE
    if mfe_r <= _DIRECT_STOP_MAX_MFE_R:
        return StoryClassification.LOSS_DIRECT_NO_EDGE
    if mfe_r >= _ONE_R:
        return StoryClassification.LOSS_AFTER_1R_OR_MORE
    if mfe_r >= _SIGNIFICANT_GIVEBACK_MIN_MFE_R:
        return StoryClassification.LOSS_AFTER_SIGNIFICANT_MFE
    return StoryClassification.LOSS_AFTER_SMALL_MFE


def _episode_id(
    *,
    trader_code: str,
    symbol: str,
    execution_period: str,
    trade: _TradeRecord,
) -> str:
    material = "|".join(
        (
            trader_code,
            symbol,
            execution_period,
            trade.signal_at.isoformat(),
            trade.filled_at.isoformat(),
            trade.exited_at.isoformat(),
            trade.side.value,
            format(trade.entry_price, "f"),
            format(trade.stop_loss, "f"),
            format(trade.take_profit, "f"),
        )
    )
    return f"episode-{sha256(material.encode('utf-8')).hexdigest()[:20]}"


def _episode(
    *,
    trader_code: str,
    symbol: str,
    execution_period: str,
    trade: _TradeRecord,
    context: _SetupContext,
    execution: tuple[OhlcSnapshot, ...],
    closed_index: dict[datetime, int],
) -> _Episode:
    signal_index = closed_index.get(trade.signal_at)
    exit_index = closed_index.get(trade.exited_at)
    if signal_index is None or exit_index is None:
        raise FirstCohortStoryForensicsError("trade boundaries are absent from execution evidence")
    start = max(0, signal_index - _CONTEXT_BARS)
    end = min(len(execution) - 1, exit_index + _POST_EXIT_BARS)
    bars = execution[start : end + 1]
    points = _trajectory(trade, execution, closed_index)
    mfe_fraction, mfe_r, mfe_at, mae_fraction, mae_r, mae_at = _excursions(points)
    return _Episode(
        episode_id=_episode_id(
            trader_code=trader_code,
            symbol=symbol,
            execution_period=execution_period,
            trade=trade,
        ),
        trader_code=trader_code,
        symbol=symbol,
        execution_period=execution_period,
        trade=trade,
        context=context,
        bars=bars,
        trajectory=points,
        mfe_fraction=mfe_fraction,
        mfe_r=mfe_r,
        mfe_at=mfe_at,
        mae_fraction=mae_fraction,
        mae_r=mae_r,
        mae_at=mae_at,
        classification=_classification(trade, mfe_r=mfe_r),
    )


def _frame_sequence(episode: _Episode) -> list[dict[str, object]]:
    ordered = [
        ("context", episode.bars[0].closed_at),
        ("signal", episode.trade.signal_at),
        ("entry", episode.trade.filled_at),
        ("mfe", episode.mfe_at),
        ("mae", episode.mae_at),
        ("exit", episode.trade.exited_at),
        ("post_exit", episode.bars[-1].closed_at),
    ]
    frames: list[dict[str, object]] = []
    seen: set[tuple[str, datetime]] = set()
    for stage, at in ordered:
        key = (stage, at)
        if key in seen:
            continue
        seen.add(key)
        frames.append(
            {
                "stage": stage,
                "visible_through": at.isoformat(),
                "visible_through_unix": int(at.timestamp()),
            }
        )
    return frames


def _outcome_narrative(episode: _Episode) -> str:
    trade = episode.trade
    if episode.classification is StoryClassification.LOSS_DIRECT_NO_EDGE:
        return (
            f"The position exited by stop with only {format(episode.mfe_r, 'f')}R of "
            "closed-bar favorable excursion before the loss. This is a provisional "
            "direct-stop/no-material-edge episode, not proof that the setup rule is defective."
        )
    if episode.classification in {
        StoryClassification.LOSS_AFTER_SIGNIFICANT_MFE,
        StoryClassification.LOSS_AFTER_1R_OR_MORE,
    }:
        return (
            f"The position later exited by stop after first reaching "
            f"{format(episode.mfe_r, 'f')}R of closed-bar favorable excursion. "
            "This is a provisional giveback/lifecycle candidate; it does not authorize a "
            "trailing-stop or exit-rule change."
        )
    if episode.outcome is StoryOutcome.WIN:
        return (
            f"The position exited by {trade.exit_reason} with realized return "
            f"{format(trade.return_rate, 'f')} and closed-bar MFE "
            f"{format(episode.mfe_r, 'f')}R. The winning path is descriptive research evidence."
        )
    return (
        f"The position exited by {trade.exit_reason} with realized return "
        f"{format(trade.return_rate, 'f')}. The loss is retained as a valid observed outcome "
        "until a broader causal family is established."
    )


def _streaks(episodes: tuple[_Episode, ...]) -> tuple[_Streak, ...]:
    if not episodes:
        return ()
    rows: list[_Streak] = []
    current_outcome = episodes[0].outcome
    current: list[_Episode] = []
    for episode in episodes:
        if episode.outcome is not current_outcome:
            rows.append(_Streak(outcome=current_outcome, episodes=tuple(current)))
            current_outcome = episode.outcome
            current = []
        current.append(episode)
    if current:
        rows.append(_Streak(outcome=current_outcome, episodes=tuple(current)))
    return tuple(rows)


def _pick_distinct_streaks(
    candidates: tuple[_Streak, ...],
    *,
    count: int = _REQUIRED_STORY_COUNT,
) -> tuple[tuple[_Streak, str], ...]:
    if not candidates:
        return ()
    selected: list[tuple[_Streak, str]] = []
    used: set[str] = set()

    def add(streak: _Streak, reason: str) -> None:
        if streak.streak_id not in used and len(selected) < count:
            used.add(streak.streak_id)
            selected.append((streak, reason))

    longest = min(candidates, key=lambda item: (-len(item.episodes), item.start_at))
    add(longest, "longest")
    lengths = [len(item.episodes) for item in candidates]
    median_length = Decimal(str(median(lengths)))
    typical = min(
        candidates,
        key=lambda item: (
            abs(Decimal(len(item.episodes)) - median_length),
            item.start_at,
        ),
    )
    add(typical, "typical-length")
    recent = max(candidates, key=lambda item: (item.start_at, item.streak_id))
    add(recent, "most-recent")
    signatures = Counter(item.context_signature for item in candidates)
    dominant_signature = sorted(signatures.items(), key=lambda item: (-item[1], item[0]))[0][0]
    dominant = min(
        (item for item in candidates if item.context_signature == dominant_signature),
        key=lambda item: (-len(item.episodes), item.start_at),
    )
    add(dominant, "dominant-context")
    returns = [item.compounded_return for item in candidates]
    median_return = Decimal(str(median(returns)))
    anomalous = max(
        candidates,
        key=lambda item: (
            abs(item.compounded_return - median_return),
            len(item.episodes),
            item.start_at,
        ),
    )
    add(anomalous, "return-anomaly")
    for item in sorted(
        candidates,
        key=lambda streak: (-len(streak.episodes), streak.start_at, streak.streak_id),
    ):
        add(item, "deterministic-fill")
    return tuple(selected)


def _pick_distinct_episodes(
    candidates: tuple[_Episode, ...],
    *,
    metric: str,
    count: int = _REQUIRED_STORY_COUNT,
) -> tuple[tuple[_Episode, str], ...]:
    if not candidates:
        return ()
    selected: list[tuple[_Episode, str]] = []
    used: set[str] = set()

    def value(episode: _Episode) -> Decimal:
        if metric == "mfe_r":
            return episode.mfe_r
        if metric == "return_rate":
            return episode.trade.return_rate
        raise FirstCohortStoryForensicsError("unsupported episode selection metric")

    def add(episode: _Episode, reason: str) -> None:
        if episode.episode_id not in used and len(selected) < count:
            used.add(episode.episode_id)
            selected.append((episode, reason))

    ordered = sorted(candidates, key=lambda item: (value(item), item.trade.filled_at))
    add(ordered[0], "metric-low-extreme")
    values = [value(item) for item in candidates]
    median_value = Decimal(str(median(values)))
    typical = min(
        candidates,
        key=lambda item: (abs(value(item) - median_value), item.trade.filled_at),
    )
    add(typical, "metric-typical")
    recent = max(candidates, key=lambda item: (item.trade.filled_at, item.episode_id))
    add(recent, "most-recent")
    signatures = Counter(item.context.signature for item in candidates)
    dominant_signature = sorted(signatures.items(), key=lambda item: (-item[1], item[0]))[0][0]
    dominant = min(
        (item for item in candidates if item.context.signature == dominant_signature),
        key=lambda item: (item.trade.filled_at, item.episode_id),
    )
    add(dominant, "dominant-context")
    anomalous = max(
        candidates,
        key=lambda item: (
            abs(value(item) - median_value),
            item.trade.filled_at,
            item.episode_id,
        ),
    )
    add(anomalous, "metric-anomaly")
    for item in ordered:
        add(item, "deterministic-fill")
    return tuple(selected)


def _selected_streak_payload(
    rows: tuple[tuple[_Streak, str], ...],
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for streak, reason in rows:
        payload = streak.payload()
        payload["selection_reason"] = reason
        payloads.append(payload)
    return payloads


def _selected_episode_payload(
    rows: tuple[tuple[_Episode, str], ...],
) -> list[dict[str, object]]:
    return [
        {
            "episode_id": episode.episode_id,
            "selection_reason": reason,
            "classification": episode.classification.value,
        }
        for episode, reason in rows
    ]


def _family_status(actual: int) -> dict[str, object]:
    return {
        "required": _REQUIRED_STORY_COUNT,
        "selected": actual,
        "status": "READY" if actual >= _REQUIRED_STORY_COUNT else "INSUFFICIENT_EVIDENCE",
    }


def run_story_forensics(
    market_path: Path,
    backtest_path: Path,
    characterization_path: Path,
    trader_code: str,
) -> dict[str, object]:
    """Build one deterministic visual-story pack for one Trader and one market."""
    if trader_code not in _CODES:
        raise FirstCohortStoryForensicsError("unknown first-cohort Trader code")
    series, account_fingerprint, symbol, checked_at, software_sha = _load(market_path)
    execution_period, trades = _load_backtest(
        backtest_path,
        account_fingerprint=account_fingerprint,
        symbol=symbol,
        software_sha=software_sha,
        trader_code=trader_code,
    )
    config_fingerprint, methodology_fingerprint, contexts = _load_characterization(
        characterization_path,
        account_fingerprint=account_fingerprint,
        symbol=symbol,
        software_sha=software_sha,
        trader_code=trader_code,
    )
    execution = series.get(execution_period)
    if execution is None or not execution:
        raise FirstCohortStoryForensicsError("execution period missing from market evidence")
    closed_index = {bar.closed_at: index for index, bar in enumerate(execution)}
    episodes: list[_Episode] = []
    for trade in trades:
        key = (trade.signal_at, trade.side, trade.entry_price)
        context = contexts.get(key)
        if context is None:
            raise FirstCohortStoryForensicsError(
                "backtest trade has no exact production-default characterization setup"
            )
        episodes.append(
            _episode(
                trader_code=trader_code,
                symbol=symbol,
                execution_period=execution_period,
                trade=trade,
                context=context,
                execution=execution,
                closed_index=closed_index,
            )
        )
    retained = tuple(episodes)
    streaks = _streaks(retained)
    winning_streaks = tuple(item for item in streaks if item.outcome is StoryOutcome.WIN)
    losing_streaks = tuple(item for item in streaks if item.outcome is StoryOutcome.LOSS)
    selected_winning_streaks = _pick_distinct_streaks(winning_streaks)
    selected_losing_streaks = _pick_distinct_streaks(losing_streaks)
    direct_stops = tuple(
        episode
        for episode in retained
        if episode.classification is StoryClassification.LOSS_DIRECT_NO_EDGE
    )
    givebacks = tuple(
        episode
        for episode in retained
        if episode.classification
        in {
            StoryClassification.LOSS_AFTER_SIGNIFICANT_MFE,
            StoryClassification.LOSS_AFTER_1R_OR_MORE,
        }
    )
    canonical_winners = tuple(
        episode
        for episode in retained
        if episode.classification is StoryClassification.WIN_CANONICAL
    )
    selected_direct = _pick_distinct_episodes(direct_stops, metric="mfe_r")
    selected_givebacks = _pick_distinct_episodes(givebacks, metric="mfe_r")
    selected_winners = _pick_distinct_episodes(canonical_winners, metric="return_rate")
    episode_payloads = [episode.payload() for episode in retained]
    source_binding = {
        "symbol": symbol,
        "account_fingerprint": account_fingerprint,
        "checked_at": checked_at.isoformat(),
        "software_sha": software_sha,
        "trader_code": trader_code,
        "config_fingerprint": config_fingerprint,
        "methodology_fingerprint": methodology_fingerprint,
        "execution_period": execution_period,
    }
    fingerprint_material = json.dumps(
        {
            "schema": _SCHEMA,
            "source_binding": source_binding,
            "selection_policy": _SELECTION_POLICY,
            "episode_ids": [episode.episode_id for episode in retained],
            "winning_streak_ids": [row[0].streak_id for row in selected_winning_streaks],
            "losing_streak_ids": [row[0].streak_id for row in selected_losing_streaks],
            "direct_stop_ids": [row[0].episode_id for row in selected_direct],
            "giveback_ids": [row[0].episode_id for row in selected_givebacks],
            "canonical_winner_ids": [row[0].episode_id for row in selected_winners],
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "source_binding": source_binding,
        "selection_policy": {
            "policy_id": _SELECTION_POLICY,
            "required_per_family": _REQUIRED_STORY_COUNT,
            "manual_cherry_pick_allowed": False,
            "direct_stop_max_closed_bar_mfe_r": format(_DIRECT_STOP_MAX_MFE_R, "f"),
            "giveback_min_closed_bar_mfe_r": format(
                _SIGNIFICANT_GIVEBACK_MIN_MFE_R, "f"
            ),
            "one_r_giveback_threshold": format(_ONE_R, "f"),
        },
        "epistemic_contract": {
            "decision_time_and_post_outcome_separated": True,
            "intrabar_ordering_inferred": False,
            "post_outcome_may_not_justify_entry": True,
            "visual_pattern_is_not_certification": True,
        },
        "renderer_contract": {
            "default_renderer": _RENDERER_ID,
            "renderer_version": _RENDERER_VERSION,
            "license_family": "Apache-2.0",
            "market_data_source": "qore-retained-evidence",
            "tradingview_is_evidence_source": False,
            "tradingview_has_execution_authority": False,
            "supports_candles": True,
            "supports_markers": True,
            "supports_price_lines": True,
            "supports_frame_sequence": True,
            "supports_client_screenshot": True,
        },
        "family_status": {
            "winning_streaks": _family_status(len(selected_winning_streaks)),
            "losing_streaks": _family_status(len(selected_losing_streaks)),
            "direct_stop_episodes": _family_status(len(selected_direct)),
            "giveback_episodes": _family_status(len(selected_givebacks)),
            "canonical_winners": _family_status(len(selected_winners)),
        },
        "story_families": {
            "winning_streaks": _selected_streak_payload(selected_winning_streaks),
            "losing_streaks": _selected_streak_payload(selected_losing_streaks),
            "direct_stop_episodes": _selected_episode_payload(selected_direct),
            "giveback_episodes": _selected_episode_payload(selected_givebacks),
            "canonical_winners": _selected_episode_payload(selected_winners),
        },
        "episode_count": len(retained),
        "episodes": episode_payloads,
        "forensics_fingerprint": sha256(fingerprint_material.encode("utf-8")).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 4:
        print(
            "usage: python -m qore.infrastructure.trader_lab.first_cohort_story_forensics "
            "MARKET_EVIDENCE BACKTEST CHARACTERIZATION TRADER_CODE",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_story_forensics(
            Path(arguments[0]),
            Path(arguments[1]),
            Path(arguments[2]),
            arguments[3],
        )
    except FirstCohortBacktestError as error:
        print(f"first-cohort story forensics failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
