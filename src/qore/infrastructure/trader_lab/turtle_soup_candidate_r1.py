"""Source-faithful research contracts for the new Turtle Soup candidate.

This module deliberately lives in Trader Lab rather than the canonical Trader
catalog.  ``VT-09`` is obsolete and grants no identity or methodology authority
to this research candidate.

The executable source contracts implemented here are the adjudicated rules from
Connors/Raschke ``Street Smarts``:

* Classic Turtle Soup: 20-bar reference, previous extreme at least four bars /
  sessions earlier, same-session reversal stop entry after a strict breakout,
  one-tick protective stop beyond the observed session extreme, and source-
  authorized trailing-stop management whose exact algorithm remains unresolved.
* Turtle Soup Plus One: 20-bar reference, previous extreme at least three bars /
  sessions earlier, breakout bar closes at/beyond the reference, next-bar stop
  entry at the earlier reference, cancellation after that next bar, and a
  one-tick stop beyond the observed two-bar extreme.  Partial-profit/trailing
  details remain source-discretionary and are not fabricated here.

The detector is causal.  When lower-timeframe OHLC cannot establish the order of
breakout and recovery inside one path bar, it returns ``AMBIGUOUS`` rather than
inventing an intrabar path.  No profit target is fabricated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.market_observation import (
    MarketOhlcField,
    MarketOhlcFieldValidity,
    QualifiedOhlcBarObservation,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.kernel.errors import InfrastructureError

SOURCE_TITLE = "Street Smarts: High Probability Short-Term Trading Strategies"
SOURCE_AUTHORS = "Laurence A. Connors / Linda Bradford Raschke"
RESEARCH_IDENTITY = "turtle-soup-candidate-r1"
CANONICAL_TRADER_CODE = "CODE_UNASSIGNED"


class TurtleSoupR1Error(InfrastructureError):
    """Base error for Turtle Soup candidate R1 research."""

    __slots__ = ()


class TurtleSoupR1ValidationError(TurtleSoupR1Error):
    """Violation of source-faithful research invariants."""

    __slots__ = ()


class TurtleSoupR1Variant(StrEnum):
    CLASSIC = "classic"
    PLUS_ONE = "plus-one"


class TurtleSoupR1Decision(StrEnum):
    SETUP = "setup"
    ABSTAIN = "abstain"
    AMBIGUOUS = "ambiguous"


class TurtleSoupR1Reason(StrEnum):
    INSUFFICIENT_HISTORY = "insufficient-history"
    INVALID_EVIDENCE = "invalid-evidence"
    REFERENCE_TIE = "reference-tie"
    REFERENCE_TOO_RECENT = "reference-too-recent"
    NO_BREAKOUT = "no-breakout"
    NO_CLOSE_CONFIRMATION = "no-close-confirmation"
    NO_ENTRY = "no-entry"
    INTRABAR_PATH_AMBIGUOUS = "intrabar-path-ambiguous"


class TurtleSoupR1ManagementFamily(StrEnum):
    CLASSIC_TRAILING_STOP_UNRESOLVED = "classic-trailing-stop-unresolved"
    PLUS_ONE_PARTIAL_2_TO_6_BARS_PLUS_TRAIL_UNRESOLVED = (
        "plus-one-partial-2-to-6-bars-plus-trail-unresolved"
    )


@dataclass(frozen=True, slots=True)
class TurtleSoupR1Config:
    """Frozen source axes plus the explicit unresolved Classic tick choice.

    ``classic_entry_offset_ticks`` is intentionally explicit because the source
    allows a 5--10 tick band for the Classic entry.  It is not silently optimized
    or attributed to a single canonical number.
    """

    tick_size: Decimal
    classic_entry_offset_ticks: int = 5
    lookback: int = 20
    classic_min_reference_age: int = 4
    plus_one_min_reference_age: int = 3

    def __post_init__(self) -> None:
        if type(self.tick_size) is not Decimal or not self.tick_size.is_finite():
            raise TurtleSoupR1ValidationError("tick_size must be a finite Decimal")
        if self.tick_size <= 0:
            raise TurtleSoupR1ValidationError("tick_size must be positive")
        if type(self.classic_entry_offset_ticks) is not int or not (
            5 <= self.classic_entry_offset_ticks <= 10
        ):
            raise TurtleSoupR1ValidationError(
                "classic_entry_offset_ticks must preserve the source 5..10 tick band"
            )
        if self.lookback != 20:
            raise TurtleSoupR1ValidationError("source-faithful lookback must equal 20")
        if self.classic_min_reference_age != 4:
            raise TurtleSoupR1ValidationError(
                "source-faithful Classic reference age must equal 4"
            )
        if self.plus_one_min_reference_age != 3:
            raise TurtleSoupR1ValidationError(
                "source-faithful Plus One reference age must equal 3"
            )

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.trader_lab.turtle_soup_candidate_r1.config.v1",
            "research_identity": RESEARCH_IDENTITY,
            "source": SOURCE_TITLE,
            "authors": SOURCE_AUTHORS,
            "tick_size": format(self.tick_size.normalize(), "f"),
            "classic_entry_offset_ticks": self.classic_entry_offset_ticks,
            "lookback": self.lookback,
            "classic_min_reference_age": self.classic_min_reference_age,
            "plus_one_min_reference_age": self.plus_one_min_reference_age,
            "classic_management": (
                TurtleSoupR1ManagementFamily.CLASSIC_TRAILING_STOP_UNRESOLVED.value
            ),
            "plus_one_management": (
                TurtleSoupR1ManagementFamily.
                PLUS_ONE_PARTIAL_2_TO_6_BARS_PLUS_TRAIL_UNRESOLVED.value
            ),
        }
        return sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class TurtleSoupR1Setup:
    variant: TurtleSoupR1Variant
    side: DemoTradingSetupSide
    reference_price: Decimal
    reference_age: int
    entry_trigger_price: Decimal
    executable_entry_price: Decimal
    initial_stop_price: Decimal
    signal_opened_at: object
    fill_at: object
    management_family: TurtleSoupR1ManagementFamily
    config_fingerprint: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("reference_price", self.reference_price),
            ("entry_trigger_price", self.entry_trigger_price),
            ("executable_entry_price", self.executable_entry_price),
            ("initial_stop_price", self.initial_stop_price),
        ):
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                raise TurtleSoupR1ValidationError(
                    f"{field_name} must be a positive finite Decimal"
                )
        if self.reference_age < 1:
            raise TurtleSoupR1ValidationError("reference_age must be positive")
        if self.side is DemoTradingSetupSide.LONG:
            if not self.initial_stop_price < self.executable_entry_price:
                raise TurtleSoupR1ValidationError("LONG stop must be below entry")
        else:
            if not self.initial_stop_price > self.executable_entry_price:
                raise TurtleSoupR1ValidationError("SHORT stop must be above entry")


@dataclass(frozen=True, slots=True)
class TurtleSoupR1Evaluation:
    decision: TurtleSoupR1Decision
    reason: TurtleSoupR1Reason | None
    setup: TurtleSoupR1Setup | None

    def __post_init__(self) -> None:
        if self.decision is TurtleSoupR1Decision.SETUP:
            if self.reason is not None or self.setup is None:
                raise TurtleSoupR1ValidationError(
                    "SETUP evaluation requires setup and no reason"
                )
        elif self.reason is None or self.setup is not None:
            raise TurtleSoupR1ValidationError(
                "non-SETUP evaluation requires reason and no setup"
            )


def _decimal(field: MarketOhlcField, *, field_name: str) -> Decimal:
    if (
        type(field) is not MarketOhlcField
        or field.validity is not MarketOhlcFieldValidity.VALID
        or field.price is None
    ):
        raise TurtleSoupR1ValidationError(f"{field_name} must be valid price evidence")
    return field.price.value


def _ohlc(bar: QualifiedOhlcBarObservation) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if type(bar) is not QualifiedOhlcBarObservation:
        raise TurtleSoupR1ValidationError(
            "bar evidence must be QualifiedOhlcBarObservation"
        )
    return (
        _decimal(bar.open, field_name="open"),
        _decimal(bar.high, field_name="high"),
        _decimal(bar.low, field_name="low"),
        _decimal(bar.close, field_name="close"),
    )


def _same_stream(
    left: QualifiedOhlcBarObservation,
    right: QualifiedOhlcBarObservation,
) -> bool:
    return (
        left.instrument == right.instrument
        and left.source == right.source
        and left.price_side is right.price_side
    )


def _validate_history(
    history: tuple[QualifiedOhlcBarObservation, ...], *, lookback: int
) -> None:
    if type(history) is not tuple or len(history) < lookback:
        raise TurtleSoupR1ValidationError("history must contain at least 20 bars")
    first = history[0]
    if type(first) is not QualifiedOhlcBarObservation:
        raise TurtleSoupR1ValidationError("history contains invalid bar evidence")
    previous: QualifiedOhlcBarObservation | None = None
    for bar in history:
        _ohlc(bar)
        if not _same_stream(first, bar) or bar.timeframe != first.timeframe:
            raise TurtleSoupR1ValidationError(
                "history must share instrument/source/side/timeframe"
            )
        if previous is not None and bar.opened_at < previous.closed_at:
            raise TurtleSoupR1ValidationError("history must be chronological and non-overlapping")
        previous = bar


def _validate_path(
    history: tuple[QualifiedOhlcBarObservation, ...],
    path: tuple[QualifiedOhlcBarObservation, ...],
) -> None:
    if type(path) is not tuple or not path:
        raise TurtleSoupR1ValidationError("execution path must be a non-empty tuple")
    anchor = history[-1]
    first = path[0]
    if not _same_stream(anchor, first):
        raise TurtleSoupR1ValidationError(
            "execution path must share history instrument/source/price side"
        )
    path_seconds = first.timeframe.fixed_seconds
    history_seconds = anchor.timeframe.fixed_seconds
    if path_seconds is None:
        raise TurtleSoupR1ValidationError("execution path must use a fixed timeframe")
    if history_seconds is not None and path_seconds >= history_seconds:
        raise TurtleSoupR1ValidationError(
            "execution path timeframe must be lower than history timeframe"
        )
    previous: QualifiedOhlcBarObservation | None = None
    for bar in path:
        _ohlc(bar)
        if not _same_stream(first, bar) or bar.timeframe != first.timeframe:
            raise TurtleSoupR1ValidationError(
                "execution path must be one homogeneous evidence stream"
            )
        if previous is not None and bar.opened_at != previous.closed_at:
            raise TurtleSoupR1ValidationError(
                "execution path must be contiguous with no gaps or overlaps"
            )
        previous = bar


def _reference(
    history: tuple[QualifiedOhlcBarObservation, ...],
    *,
    side: DemoTradingSetupSide,
    lookback: int,
) -> tuple[Decimal, int] | None:
    window = history[-lookback:]
    prices = tuple(
        _ohlc(bar)[2] if side is DemoTradingSetupSide.LONG else _ohlc(bar)[1]
        for bar in window
    )
    reference = min(prices) if side is DemoTradingSetupSide.LONG else max(prices)
    matches = tuple(index for index, price in enumerate(prices) if price == reference)
    if len(matches) != 1:
        return None
    window_index = matches[0]
    absolute_index = len(history) - lookback + window_index
    age = len(history) - absolute_index
    return reference, age


def _abstain(reason: TurtleSoupR1Reason) -> TurtleSoupR1Evaluation:
    return TurtleSoupR1Evaluation(TurtleSoupR1Decision.ABSTAIN, reason, None)


def _ambiguous(reason: TurtleSoupR1Reason) -> TurtleSoupR1Evaluation:
    return TurtleSoupR1Evaluation(TurtleSoupR1Decision.AMBIGUOUS, reason, None)


def evaluate_classic(
    *,
    history: tuple[QualifiedOhlcBarObservation, ...],
    current_session_path: tuple[QualifiedOhlcBarObservation, ...],
    side: DemoTradingSetupSide,
    config: TurtleSoupR1Config,
) -> TurtleSoupR1Evaluation:
    """Evaluate one source-faithful Classic Turtle Soup session causally."""

    if type(side) is not DemoTradingSetupSide or type(config) is not TurtleSoupR1Config:
        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
    try:
        _validate_history(history, lookback=config.lookback)
        _validate_path(history, current_session_path)
    except TurtleSoupR1ValidationError:
        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
    reference = _reference(history, side=side, lookback=config.lookback)
    if reference is None:
        return _ambiguous(TurtleSoupR1Reason.REFERENCE_TIE)
    reference_price, reference_age = reference
    if reference_age < config.classic_min_reference_age:
        return _abstain(TurtleSoupR1Reason.REFERENCE_TOO_RECENT)

    offset = config.tick_size * config.classic_entry_offset_ticks
    entry_trigger = (
        reference_price + offset
        if side is DemoTradingSetupSide.LONG
        else reference_price - offset
    )
    if entry_trigger <= 0:
        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)

    swept = False
    running_extreme: Decimal | None = None
    for bar in current_session_path:
        open_price, high, low, _ = _ohlc(bar)
        if side is DemoTradingSetupSide.LONG:
            is_sweep = low < reference_price
            same_bar_recovery = is_sweep and high >= entry_trigger
            if not swept and same_bar_recovery:
                return _ambiguous(TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS)
            if not swept and is_sweep:
                swept = True
                running_extreme = low
                continue
            if swept:
                if running_extreme is None:
                    raise TurtleSoupR1ValidationError("lost LONG running extreme")
                if high >= entry_trigger:
                    executable_entry = max(open_price, entry_trigger)
                    stop = running_extreme - config.tick_size
                    if stop <= 0 or stop >= executable_entry:
                        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
                    return TurtleSoupR1Evaluation(
                        TurtleSoupR1Decision.SETUP,
                        None,
                        TurtleSoupR1Setup(
                            variant=TurtleSoupR1Variant.CLASSIC,
                            side=side,
                            reference_price=reference_price,
                            reference_age=reference_age,
                            entry_trigger_price=entry_trigger,
                            executable_entry_price=executable_entry,
                            initial_stop_price=stop,
                            signal_opened_at=current_session_path[0].opened_at,
                            fill_at=bar.opened_at,
                            management_family=(
                                TurtleSoupR1ManagementFamily.
                                CLASSIC_TRAILING_STOP_UNRESOLVED
                            ),
                            config_fingerprint=config.fingerprint(),
                        ),
                    )
                running_extreme = min(running_extreme, low)
        else:
            is_sweep = high > reference_price
            same_bar_recovery = is_sweep and low <= entry_trigger
            if not swept and same_bar_recovery:
                return _ambiguous(TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS)
            if not swept and is_sweep:
                swept = True
                running_extreme = high
                continue
            if swept:
                if running_extreme is None:
                    raise TurtleSoupR1ValidationError("lost SHORT running extreme")
                if low <= entry_trigger:
                    executable_entry = min(open_price, entry_trigger)
                    stop = running_extreme + config.tick_size
                    if stop <= executable_entry:
                        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
                    return TurtleSoupR1Evaluation(
                        TurtleSoupR1Decision.SETUP,
                        None,
                        TurtleSoupR1Setup(
                            variant=TurtleSoupR1Variant.CLASSIC,
                            side=side,
                            reference_price=reference_price,
                            reference_age=reference_age,
                            entry_trigger_price=entry_trigger,
                            executable_entry_price=executable_entry,
                            initial_stop_price=stop,
                            signal_opened_at=current_session_path[0].opened_at,
                            fill_at=bar.opened_at,
                            management_family=(
                                TurtleSoupR1ManagementFamily.
                                CLASSIC_TRAILING_STOP_UNRESOLVED
                            ),
                            config_fingerprint=config.fingerprint(),
                        ),
                    )
                running_extreme = max(running_extreme, high)
    return _abstain(
        TurtleSoupR1Reason.NO_ENTRY if swept else TurtleSoupR1Reason.NO_BREAKOUT
    )


def evaluate_plus_one(
    *,
    history: tuple[QualifiedOhlcBarObservation, ...],
    breakout_bar: QualifiedOhlcBarObservation,
    next_bar_path: tuple[QualifiedOhlcBarObservation, ...],
    side: DemoTradingSetupSide,
    config: TurtleSoupR1Config,
) -> TurtleSoupR1Evaluation:
    """Evaluate source-faithful Turtle Soup Plus One without future-bar leakage."""

    if type(side) is not DemoTradingSetupSide or type(config) is not TurtleSoupR1Config:
        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
    try:
        _validate_history(history, lookback=config.lookback)
        _ohlc(breakout_bar)
        if (
            not _same_stream(history[-1], breakout_bar)
            or breakout_bar.timeframe != history[-1].timeframe
            or breakout_bar.opened_at < history[-1].closed_at
        ):
            raise TurtleSoupR1ValidationError("breakout bar is not the next source bar")
        _validate_path((*history, breakout_bar), next_bar_path)
        if next_bar_path[0].opened_at < breakout_bar.closed_at:
            raise TurtleSoupR1ValidationError("Plus One path must begin after breakout bar")
    except TurtleSoupR1ValidationError:
        return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)

    reference = _reference(history, side=side, lookback=config.lookback)
    if reference is None:
        return _ambiguous(TurtleSoupR1Reason.REFERENCE_TIE)
    reference_price, reference_age = reference
    if reference_age < config.plus_one_min_reference_age:
        return _abstain(TurtleSoupR1Reason.REFERENCE_TOO_RECENT)

    _, breakout_high, breakout_low, breakout_close = _ohlc(breakout_bar)
    if side is DemoTradingSetupSide.LONG:
        if breakout_low >= reference_price:
            return _abstain(TurtleSoupR1Reason.NO_BREAKOUT)
        if breakout_close > reference_price:
            return _abstain(TurtleSoupR1Reason.NO_CLOSE_CONFIRMATION)
        running_extreme = breakout_low
        for bar in next_bar_path:
            open_price, high, low, _ = _ohlc(bar)
            if high >= reference_price:
                if low < running_extreme:
                    return _ambiguous(TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS)
                executable_entry = max(open_price, reference_price)
                stop = running_extreme - config.tick_size
                if stop <= 0 or stop >= executable_entry:
                    return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
                return TurtleSoupR1Evaluation(
                    TurtleSoupR1Decision.SETUP,
                    None,
                    TurtleSoupR1Setup(
                        variant=TurtleSoupR1Variant.PLUS_ONE,
                        side=side,
                        reference_price=reference_price,
                        reference_age=reference_age,
                        entry_trigger_price=reference_price,
                        executable_entry_price=executable_entry,
                        initial_stop_price=stop,
                        signal_opened_at=breakout_bar.opened_at,
                        fill_at=bar.opened_at,
                        management_family=(
                            TurtleSoupR1ManagementFamily.
                            PLUS_ONE_PARTIAL_2_TO_6_BARS_PLUS_TRAIL_UNRESOLVED
                        ),
                        config_fingerprint=config.fingerprint(),
                    ),
                )
            running_extreme = min(running_extreme, low)
    else:
        if breakout_high <= reference_price:
            return _abstain(TurtleSoupR1Reason.NO_BREAKOUT)
        if breakout_close < reference_price:
            return _abstain(TurtleSoupR1Reason.NO_CLOSE_CONFIRMATION)
        running_extreme = breakout_high
        for bar in next_bar_path:
            open_price, high, low, _ = _ohlc(bar)
            if low <= reference_price:
                if high > running_extreme:
                    return _ambiguous(TurtleSoupR1Reason.INTRABAR_PATH_AMBIGUOUS)
                executable_entry = min(open_price, reference_price)
                stop = running_extreme + config.tick_size
                if stop <= executable_entry:
                    return _abstain(TurtleSoupR1Reason.INVALID_EVIDENCE)
                return TurtleSoupR1Evaluation(
                    TurtleSoupR1Decision.SETUP,
                    None,
                    TurtleSoupR1Setup(
                        variant=TurtleSoupR1Variant.PLUS_ONE,
                        side=side,
                        reference_price=reference_price,
                        reference_age=reference_age,
                        entry_trigger_price=reference_price,
                        executable_entry_price=executable_entry,
                        initial_stop_price=stop,
                        signal_opened_at=breakout_bar.opened_at,
                        fill_at=bar.opened_at,
                        management_family=(
                            TurtleSoupR1ManagementFamily.
                            PLUS_ONE_PARTIAL_2_TO_6_BARS_PLUS_TRAIL_UNRESOLVED
                        ),
                        config_fingerprint=config.fingerprint(),
                    ),
                )
            running_extreme = max(running_extreme, high)
    return _abstain(TurtleSoupR1Reason.NO_ENTRY)
