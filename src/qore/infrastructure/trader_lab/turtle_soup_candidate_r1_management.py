"""Predeclared QORE experimental management for Turtle Soup candidate R1.

These policies are deliberately NOT canonical Connors/Raschke Turtle Soup rules.
They operationalize the mechanically unresolved exit-management space declared in
``TURTLE-SOUP-CANDIDATE-R1-EXPERIMENTAL-MANAGEMENT-GRID.md`` for development
characterization only.
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
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1 import (
    RESEARCH_IDENTITY,
    TurtleSoupR1Setup,
    TurtleSoupR1ValidationError,
    TurtleSoupR1Variant,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r1.experimental_management.v1"
_ONE = Decimal("1")
_HALF = Decimal("0.50")


class TurtleSoupR1ExperimentalPolicyId(StrEnum):
    C_TRAIL1_H3 = "C_TRAIL1_H3"
    C_TRAIL2_H3 = "C_TRAIL2_H3"
    C_TRAIL1_H6 = "C_TRAIL1_H6"
    C_TRAIL2_H6 = "C_TRAIL2_H6"
    P_B2_F50_TRAIL1_H10 = "P_B2_F50_TRAIL1_H10"
    P_B2_F50_TRAIL2_H10 = "P_B2_F50_TRAIL2_H10"
    P_B4_F50_TRAIL1_H10 = "P_B4_F50_TRAIL1_H10"
    P_B4_F50_TRAIL2_H10 = "P_B4_F50_TRAIL2_H10"
    P_B6_F50_TRAIL1_H10 = "P_B6_F50_TRAIL1_H10"
    P_B6_F50_TRAIL2_H10 = "P_B6_F50_TRAIL2_H10"


class TurtleSoupR1ManagementDecision(StrEnum):
    CLOSED = "closed"
    CENSORED = "censored"


class TurtleSoupR1ManagementExitReason(StrEnum):
    STOP = "stop"
    TIME_EXIT = "time-exit"
    INSUFFICIENT_DATA = "insufficient-data"


@dataclass(frozen=True, slots=True)
class TurtleSoupR1ExperimentalPolicy:
    policy_id: TurtleSoupR1ExperimentalPolicyId
    variant: TurtleSoupR1Variant
    trail_lookback_bars: int
    hard_exit_bar: int
    partial_bar: int | None = None
    partial_fraction: Decimal | None = None

    def __post_init__(self) -> None:
        expected = _POLICY_DEFINITIONS.get(self.policy_id)
        actual = (
            self.variant,
            self.trail_lookback_bars,
            self.hard_exit_bar,
            self.partial_bar,
            self.partial_fraction,
        )
        if expected is None or expected != actual:
            raise TurtleSoupR1ValidationError(
                "experimental policy must match the frozen predeclared grid"
            )

    def fingerprint(self) -> str:
        payload = {
            "schema": _SCHEMA,
            "research_identity": RESEARCH_IDENTITY,
            "provenance": "QORE_EXPERIMENTAL_MANAGEMENT",
            "policy_id": self.policy_id.value,
            "variant": self.variant.value,
            "trail_lookback_bars": self.trail_lookback_bars,
            "hard_exit_bar": self.hard_exit_bar,
            "partial_bar": self.partial_bar,
            "partial_fraction": (
                None
                if self.partial_fraction is None
                else format(self.partial_fraction.normalize(), "f")
            ),
            "exit_precedence": [
                "active-stop",
                "bar-close",
                "scheduled-partial",
                "trail-update-for-next-bar",
                "hard-time-exit",
            ],
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()


_POLICY_DEFINITIONS: dict[
    TurtleSoupR1ExperimentalPolicyId,
    tuple[TurtleSoupR1Variant, int, int, int | None, Decimal | None],
] = {
    TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3: (
        TurtleSoupR1Variant.CLASSIC,
        1,
        3,
        None,
        None,
    ),
    TurtleSoupR1ExperimentalPolicyId.C_TRAIL2_H3: (
        TurtleSoupR1Variant.CLASSIC,
        2,
        3,
        None,
        None,
    ),
    TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H6: (
        TurtleSoupR1Variant.CLASSIC,
        1,
        6,
        None,
        None,
    ),
    TurtleSoupR1ExperimentalPolicyId.C_TRAIL2_H6: (
        TurtleSoupR1Variant.CLASSIC,
        2,
        6,
        None,
        None,
    ),
    TurtleSoupR1ExperimentalPolicyId.P_B2_F50_TRAIL1_H10: (
        TurtleSoupR1Variant.PLUS_ONE,
        1,
        10,
        2,
        _HALF,
    ),
    TurtleSoupR1ExperimentalPolicyId.P_B2_F50_TRAIL2_H10: (
        TurtleSoupR1Variant.PLUS_ONE,
        2,
        10,
        2,
        _HALF,
    ),
    TurtleSoupR1ExperimentalPolicyId.P_B4_F50_TRAIL1_H10: (
        TurtleSoupR1Variant.PLUS_ONE,
        1,
        10,
        4,
        _HALF,
    ),
    TurtleSoupR1ExperimentalPolicyId.P_B4_F50_TRAIL2_H10: (
        TurtleSoupR1Variant.PLUS_ONE,
        2,
        10,
        4,
        _HALF,
    ),
    TurtleSoupR1ExperimentalPolicyId.P_B6_F50_TRAIL1_H10: (
        TurtleSoupR1Variant.PLUS_ONE,
        1,
        10,
        6,
        _HALF,
    ),
    TurtleSoupR1ExperimentalPolicyId.P_B6_F50_TRAIL2_H10: (
        TurtleSoupR1Variant.PLUS_ONE,
        2,
        10,
        6,
        _HALF,
    ),
}


@dataclass(frozen=True, slots=True)
class TurtleSoupR1ManagementResult:
    policy_id: TurtleSoupR1ExperimentalPolicyId
    policy_fingerprint: str
    decision: TurtleSoupR1ManagementDecision
    exit_reason: TurtleSoupR1ManagementExitReason
    gross_r: Decimal | None
    bars_observed: int
    partial_executed: bool
    partial_exit_price: Decimal | None
    final_exit_price: Decimal | None
    final_stop_price: Decimal

    def __post_init__(self) -> None:
        if len(self.policy_fingerprint) != 64:
            raise TurtleSoupR1ValidationError("policy_fingerprint must be SHA-256")
        if type(self.bars_observed) is not int or self.bars_observed < 0:
            raise TurtleSoupR1ValidationError("bars_observed must be a non-negative int")
        if self.decision is TurtleSoupR1ManagementDecision.CLOSED:
            if self.gross_r is None or self.final_exit_price is None:
                raise TurtleSoupR1ValidationError(
                    "closed management result requires gross_r and final exit"
                )
        elif self.gross_r is not None or self.final_exit_price is not None:
            raise TurtleSoupR1ValidationError(
                "censored management result cannot claim realized gross_r/final exit"
            )
        if self.partial_executed != (self.partial_exit_price is not None):
            raise TurtleSoupR1ValidationError(
                "partial execution flag and partial price must agree"
            )


def policy_for(
    policy_id: TurtleSoupR1ExperimentalPolicyId,
) -> TurtleSoupR1ExperimentalPolicy:
    if type(policy_id) is not TurtleSoupR1ExperimentalPolicyId:
        raise TurtleSoupR1ValidationError("policy_id must be frozen policy enum")
    definition = _POLICY_DEFINITIONS[policy_id]
    return TurtleSoupR1ExperimentalPolicy(policy_id, *definition)


def frozen_policy_ids() -> tuple[TurtleSoupR1ExperimentalPolicyId, ...]:
    return tuple(TurtleSoupR1ExperimentalPolicyId)


def _decimal(field: MarketOhlcField, *, name: str) -> Decimal:
    if (
        type(field) is not MarketOhlcField
        or field.validity is not MarketOhlcFieldValidity.VALID
        or field.price is None
    ):
        raise TurtleSoupR1ValidationError(f"management {name} must be valid price evidence")
    value = field.price.value
    if not value.is_finite() or value <= 0:
        raise TurtleSoupR1ValidationError(
            f"management {name} must be a positive finite price"
        )
    return value


def _ohlc(
    bar: QualifiedOhlcBarObservation,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if type(bar) is not QualifiedOhlcBarObservation:
        raise TurtleSoupR1ValidationError(
            "management evidence must be QualifiedOhlcBarObservation"
        )
    return (
        _decimal(bar.open, name="open"),
        _decimal(bar.high, name="high"),
        _decimal(bar.low, name="low"),
        _decimal(bar.close, name="close"),
    )


def _validate_bars(
    setup: TurtleSoupR1Setup,
    bars: tuple[QualifiedOhlcBarObservation, ...],
) -> None:
    if type(bars) is not tuple:
        raise TurtleSoupR1ValidationError("management bars must be a tuple")
    previous: QualifiedOhlcBarObservation | None = None
    for bar in bars:
        _ohlc(bar)
        if bar.opened_at < setup.fill_at:
            raise TurtleSoupR1ValidationError("management bar begins before setup fill")
        if previous is not None:
            if bar.opened_at < previous.closed_at:
                raise TurtleSoupR1ValidationError(
                    "management bars must be chronological and non-overlapping"
                )
            if (
                bar.instrument != previous.instrument
                or bar.source != previous.source
                or bar.price_side is not previous.price_side
                or bar.timeframe != previous.timeframe
            ):
                raise TurtleSoupR1ValidationError(
                    "management bars must be one homogeneous evidence stream"
                )
        previous = bar


def _directional_delta(
    *, side: DemoTradingSetupSide, entry: Decimal, exit_price: Decimal
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return exit_price - entry
    if side is DemoTradingSetupSide.SHORT:
        return entry - exit_price
    raise TurtleSoupR1ValidationError("unsupported management side")


def _stop_fill(
    *,
    side: DemoTradingSetupSide,
    active_stop: Decimal,
    open_price: Decimal,
    high: Decimal,
    low: Decimal,
) -> Decimal | None:
    if side is DemoTradingSetupSide.LONG:
        if open_price <= active_stop:
            return open_price
        if low <= active_stop:
            return active_stop
        return None
    if side is DemoTradingSetupSide.SHORT:
        if open_price >= active_stop:
            return open_price
        if high >= active_stop:
            return active_stop
        return None
    raise TurtleSoupR1ValidationError("unsupported management side")


def _trail_candidate(
    *,
    side: DemoTradingSetupSide,
    recent_bars: tuple[QualifiedOhlcBarObservation, ...],
) -> Decimal:
    lows = tuple(_ohlc(bar)[2] for bar in recent_bars)
    highs = tuple(_ohlc(bar)[1] for bar in recent_bars)
    if side is DemoTradingSetupSide.LONG:
        return min(lows)
    if side is DemoTradingSetupSide.SHORT:
        return max(highs)
    raise TurtleSoupR1ValidationError("unsupported management side")


def _ratchet_stop(
    *, side: DemoTradingSetupSide, current_stop: Decimal, candidate: Decimal
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return max(current_stop, candidate)
    if side is DemoTradingSetupSide.SHORT:
        return min(current_stop, candidate)
    raise TurtleSoupR1ValidationError("unsupported management side")


def replay_experimental_management(
    *,
    setup: TurtleSoupR1Setup,
    management_bars: tuple[QualifiedOhlcBarObservation, ...],
    policy: TurtleSoupR1ExperimentalPolicy,
) -> TurtleSoupR1ManagementResult:
    """Replay one frozen experimental policy causally after a source-faithful fill."""

    if type(setup) is not TurtleSoupR1Setup:
        raise TurtleSoupR1ValidationError("setup must be TurtleSoupR1Setup")
    if type(policy) is not TurtleSoupR1ExperimentalPolicy:
        raise TurtleSoupR1ValidationError("policy must be frozen experimental policy")
    if setup.variant is not policy.variant:
        raise TurtleSoupR1ValidationError("management policy variant does not match setup")
    _validate_bars(setup, management_bars)

    entry = setup.executable_entry_price
    initial_stop = setup.initial_stop_price
    initial_risk = abs(entry - initial_stop)
    if initial_risk <= 0:
        raise TurtleSoupR1ValidationError("initial risk must be positive")

    active_stop = initial_stop
    remaining = _ONE
    realized_price_delta = Decimal("0")
    partial_executed = False
    partial_exit_price: Decimal | None = None
    observed: list[QualifiedOhlcBarObservation] = []

    for bar_index, bar in enumerate(management_bars, start=1):
        open_price, high, low, close = _ohlc(bar)
        stop_fill = _stop_fill(
            side=setup.side,
            active_stop=active_stop,
            open_price=open_price,
            high=high,
            low=low,
        )
        if stop_fill is not None:
            realized_price_delta += remaining * _directional_delta(
                side=setup.side,
                entry=entry,
                exit_price=stop_fill,
            )
            return TurtleSoupR1ManagementResult(
                policy.policy_id,
                policy.fingerprint(),
                TurtleSoupR1ManagementDecision.CLOSED,
                TurtleSoupR1ManagementExitReason.STOP,
                realized_price_delta / initial_risk,
                bar_index,
                partial_executed,
                partial_exit_price,
                stop_fill,
                active_stop,
            )

        observed.append(bar)

        if (
            policy.partial_bar == bar_index
            and policy.partial_fraction is not None
            and remaining == _ONE
        ):
            favorable = _directional_delta(
                side=setup.side,
                entry=entry,
                exit_price=close,
            ) > 0
            if favorable:
                realized_price_delta += policy.partial_fraction * _directional_delta(
                    side=setup.side,
                    entry=entry,
                    exit_price=close,
                )
                remaining -= policy.partial_fraction
                partial_executed = True
                partial_exit_price = close

        trail_is_active = (
            policy.partial_bar is None or bar_index >= policy.partial_bar
        )
        if trail_is_active and len(observed) >= policy.trail_lookback_bars:
            recent = tuple(observed[-policy.trail_lookback_bars :])
            candidate = _trail_candidate(side=setup.side, recent_bars=recent)
            active_stop = _ratchet_stop(
                side=setup.side,
                current_stop=active_stop,
                candidate=candidate,
            )

        if bar_index == policy.hard_exit_bar:
            realized_price_delta += remaining * _directional_delta(
                side=setup.side,
                entry=entry,
                exit_price=close,
            )
            return TurtleSoupR1ManagementResult(
                policy.policy_id,
                policy.fingerprint(),
                TurtleSoupR1ManagementDecision.CLOSED,
                TurtleSoupR1ManagementExitReason.TIME_EXIT,
                realized_price_delta / initial_risk,
                bar_index,
                partial_executed,
                partial_exit_price,
                close,
                active_stop,
            )

    return TurtleSoupR1ManagementResult(
        policy.policy_id,
        policy.fingerprint(),
        TurtleSoupR1ManagementDecision.CENSORED,
        TurtleSoupR1ManagementExitReason.INSUFFICIENT_DATA,
        None,
        len(management_bars),
        partial_executed,
        partial_exit_price,
        None,
        active_stop,
    )
