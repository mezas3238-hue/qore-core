"""VT-08 V2 — source-bound TTrades 4H Power-of-Three reconstruction.

This module replaces the falsified first V2 interpretation while preserving the
Trader identity ``vt-08`` / ``v2``.  The old 13k-trade campaign remains historical
failure evidence only.

Primary source:
- TTrades, "Trading The 4 Hour Power Of Three - OHLC / OLHC"
  (youtube:FAKWJ-1NlLE, Human Owner-provided copy).

Corroborating TTrades material is used only where the primary lesson explicitly
points to prerequisite concepts: Candle 2/3 closures, CISD, protected swings and
daily-bias alignment.

Frozen source interpretation:
- one institutional H4 1-5-9 sequence per New-York day for FX/spot markets;
- one institutional H4 2-6-10 sequence per New-York day for futures-style markets;
- Candle 1 is accumulation/reference;
- Candle 2 must manipulate one edge of Candle 1 and agree with a one-sided daily bias;
- a protected swing is confirmed by lower-timeframe M15 CISD;
- if Candle 2 confirms while the opposing run remains in the shallow half of the
  Candle-1 range, the body of Candle 2 may be traded;
- otherwise a completed large-wick Candle 2 reversal is followed by Candle 3,
  where a new shallow opposing wick + CISD is required before entry;
- stop is the protected-swing manipulation extreme;
- the primary objective is the prior completed daily candle's directional extreme;
- unresolved trades at the source H4 close are censored, never relabelled as wins.

The 50% split is the source's equilibrium concept.  It is not an optimized
parameter.  No output grants DEMO/LIVE/Risk/execution authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.kernel.errors import InfrastructureError

TRADER_CODE = "vt-08"
TRADER_VERSION = "v2"
METHODOLOGY_ID = "ttrades-h4-po3-source"
METHODOLOGY_VERSION = "v2.1-reconstructed"
PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
SUPPORTED_MARKETS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "SP500",
    "US30",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
)
FUTURES_STYLE_MARKETS = frozenset({"NAS100", "SP500", "US30", "XAUUSD"})
RULESET = (
    "human-owner-primary-source;daily-bias-required;one-source-sequence-per-ny-day;"
    "fx-h4-01-05-09;futures-style-h4-02-06-10;candle1-accumulation;"
    "candle2-manipulation;protected-swing-via-m15-cisd;equilibrium-50pct-source-filter;"
    "shallow-c2-same-candle-expansion;large-c2-reversal-then-c3-continuation;"
    "entry-at-confirming-m15-close;stop-protected-swing-extreme;"
    "target-prior-daily-directional-extreme;h4-close-unresolved-censor;research-only"
)


class Vt08CrtH4AmdV2Error(InfrastructureError):
    __slots__ = ()


class Vt08CrtH4AmdV2ValidationError(Vt08CrtH4AmdV2Error):
    __slots__ = ()


class Vt08CrtH4AmdV2Scenario(StrEnum):
    CANDLE2_EXPANSION = "candle2-expansion"
    CANDLE3_CONTINUATION = "candle3-continuation"


class Vt08CrtH4AmdV2DailyMode(StrEnum):
    CONTINUATION = "continuation"
    REVERSAL = "reversal"


class Vt08CrtH4AmdV2AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    DAILY_BIAS_MISSING = "daily-bias-missing"
    CANDLE2_NOT_ALIGNED = "candle2-not-aligned"
    CANDLE2_NOT_REVERSAL = "candle2-not-reversal"
    NO_PROTECTED_SWING = "no-protected-swing"
    MANIPULATION_TOO_DEEP_FOR_C2 = "manipulation-too-deep-for-candle2"
    MANIPULATION_TOO_DEEP_FOR_C3 = "manipulation-too-deep-for-candle3"
    INVALID_TARGET = "invalid-source-target"
    INVALID_GEOMETRY = "invalid-geometry"


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Candle:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        for name, instant in (
            ("opened_at", self.opened_at),
            ("closed_at", self.closed_at),
        ):
            if (
                type(instant) is not datetime
                or instant.tzinfo is None
                or instant.utcoffset() is None
            ):
                raise Vt08CrtH4AmdV2ValidationError(f"{name} must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise Vt08CrtH4AmdV2ValidationError("candle close must follow open")
        for name, price in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if type(price) is not Decimal or not price.is_finite() or price <= 0:
                raise Vt08CrtH4AmdV2ValidationError(
                    f"{name} must be positive finite Decimal"
                )
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise Vt08CrtH4AmdV2ValidationError("OHLC body must lie inside high/low")
        if self.low > self.high:
            raise Vt08CrtH4AmdV2ValidationError("low must not exceed high")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Bias:
    side: DemoTradingSetupSide
    mode: Vt08CrtH4AmdV2DailyMode
    target: Decimal


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Setup:
    side: DemoTradingSetupSide
    scenario: Vt08CrtH4AmdV2Scenario
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    signal_at: datetime
    expires_at: datetime
    cisd_level: Decimal
    manipulation_extreme: Decimal
    manipulation_fraction_of_reference: Decimal

    def __post_init__(self) -> None:
        if self.side is DemoTradingSetupSide.LONG:
            valid = self.stop_loss < self.entry_price < self.take_profit
        else:
            valid = self.take_profit < self.entry_price < self.stop_loss
        if not valid:
            raise Vt08CrtH4AmdV2ValidationError(
                "setup geometry must be strictly directional"
            )
        if not Decimal(0) <= self.manipulation_fraction_of_reference:
            raise Vt08CrtH4AmdV2ValidationError(
                "manipulation fraction must be non-negative"
            )


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Evaluation:
    decision: DemoTradingDecision
    setup: Vt08CrtH4AmdV2Setup | None
    abstain_reason: Vt08CrtH4AmdV2AbstainReason | None
    methodology_fingerprint: str


def methodology_fingerprint() -> str:
    material = {
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "primary_source": PRIMARY_SOURCE,
        "ruleset": RULESET,
        "supported_markets": SUPPORTED_MARKETS,
    }
    return sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def daily_bias(
    reference: Vt08CrtH4AmdV2Candle,
    signal: Vt08CrtH4AmdV2Candle,
) -> Vt08CrtH4AmdV2Bias | None:
    """Mechanical one-sided bias from TTrades candle-closure logic."""

    swept_high = signal.high > reference.high
    swept_low = signal.low < reference.low
    if swept_high and swept_low:
        return None
    if signal.close > reference.high:
        return Vt08CrtH4AmdV2Bias(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2DailyMode.CONTINUATION,
            signal.high,
        )
    if signal.close < reference.low:
        return Vt08CrtH4AmdV2Bias(
            DemoTradingSetupSide.SHORT,
            Vt08CrtH4AmdV2DailyMode.CONTINUATION,
            signal.low,
        )
    if swept_low and reference.low < signal.close < reference.high:
        return Vt08CrtH4AmdV2Bias(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2DailyMode.REVERSAL,
            signal.high,
        )
    if swept_high and reference.low < signal.close < reference.high:
        return Vt08CrtH4AmdV2Bias(
            DemoTradingSetupSide.SHORT,
            Vt08CrtH4AmdV2DailyMode.REVERSAL,
            signal.low,
        )
    return None


def h4_reversal_direction(
    reference: Vt08CrtH4AmdV2Candle,
    manipulation: Vt08CrtH4AmdV2Candle,
) -> DemoTradingSetupSide | None:
    swept_high = manipulation.high > reference.high
    swept_low = manipulation.low < reference.low
    closes_inside = reference.low < manipulation.close < reference.high
    if not closes_inside or swept_high == swept_low:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def _manipulation_fraction(
    reference: Vt08CrtH4AmdV2Candle,
    *,
    candidate_open: Decimal,
    extreme: Decimal,
    side: DemoTradingSetupSide,
) -> Decimal:
    width = reference.high - reference.low
    if width <= 0:
        raise Vt08CrtH4AmdV2ValidationError("reference range must be positive")
    leg = (
        candidate_open - extreme
        if side is DemoTradingSetupSide.LONG
        else extreme - candidate_open
    )
    return max(Decimal(0), leg) / width


def _protected_swing(
    bars: tuple[Vt08CrtH4AmdV2Candle, ...],
    *,
    side: DemoTradingSetupSide,
    required_sweep_level: Decimal | None,
) -> tuple[Vt08CrtH4AmdV2Candle, Decimal, Decimal] | None:
    """Return first causal CISD confirmation after the required manipulation.

    Bullish CISD: first down-close delivery sequence that makes the protected low,
    followed by a close above the first down-close open.  Bearish is mirrored.
    """

    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    extreme_index: int | None = None
    sweep_observed = required_sweep_level is None
    in_opposing_sequence = False

    for index, bar in enumerate(bars):
        if required_sweep_level is not None:
            if side is DemoTradingSetupSide.LONG and bar.low < required_sweep_level:
                sweep_observed = True
            if side is DemoTradingSetupSide.SHORT and bar.high > required_sweep_level:
                sweep_observed = True
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not in_opposing_sequence:
                sequence_open = bar.open
            candidate = bar.low if side is DemoTradingSetupSide.LONG else bar.high
            if extreme is None or (
                candidate < extreme
                if side is DemoTradingSetupSide.LONG
                else candidate > extreme
            ):
                extreme = candidate
                extreme_index = index
            in_opposing_sequence = True
            continue
        if (
            sweep_observed
            and sequence_open is not None
            and extreme is not None
            and extreme_index is not None
            and index > extreme_index
        ):
            confirmed = (
                bar.close > sequence_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < sequence_open
            )
            if confirmed:
                return bar, sequence_open, extreme
        in_opposing_sequence = False
    return None


def _abstain(reason: Vt08CrtH4AmdV2AbstainReason) -> Vt08CrtH4AmdV2Evaluation:
    return Vt08CrtH4AmdV2Evaluation(
        decision=DemoTradingDecision.ABSTAIN,
        setup=None,
        abstain_reason=reason,
        methodology_fingerprint=methodology_fingerprint(),
    )


def evaluate_candle2_expansion(
    *,
    symbol: str,
    daily_reference: Vt08CrtH4AmdV2Candle,
    daily_signal: Vt08CrtH4AmdV2Candle,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2_open: Decimal,
    h4_candle2_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
) -> Vt08CrtH4AmdV2Evaluation:
    """Causally evaluate the source's shallow-wick Candle-2 expansion case."""

    if symbol not in SUPPORTED_MARKETS:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET)
    bias = daily_bias(daily_reference, daily_signal)
    if bias is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.DAILY_BIAS_MISSING)
    required = (
        h4_reference.low
        if bias.side is DemoTradingSetupSide.LONG
        else h4_reference.high
    )
    protected = _protected_swing(
        observed_m15,
        side=bias.side,
        required_sweep_level=required,
    )
    if protected is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.NO_PROTECTED_SWING)
    confirmation, cisd_level, extreme = protected
    fraction = _manipulation_fraction(
        h4_reference,
        candidate_open=h4_candle2_open,
        extreme=extreme,
        side=bias.side,
    )
    if fraction > Decimal("0.5"):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.MANIPULATION_TOO_DEEP_FOR_C2)
    entry = confirmation.close
    target = bias.target
    if (
        bias.side is DemoTradingSetupSide.LONG and target <= entry
    ) or (
        bias.side is DemoTradingSetupSide.SHORT and target >= entry
    ):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_TARGET)
    try:
        setup = Vt08CrtH4AmdV2Setup(
            side=bias.side,
            scenario=Vt08CrtH4AmdV2Scenario.CANDLE2_EXPANSION,
            entry_price=entry,
            stop_loss=extreme,
            take_profit=target,
            signal_at=confirmation.closed_at.astimezone(UTC),
            expires_at=h4_candle2_closes_at.astimezone(UTC),
            cisd_level=cisd_level,
            manipulation_extreme=extreme,
            manipulation_fraction_of_reference=fraction,
        )
    except Vt08CrtH4AmdV2ValidationError:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    return Vt08CrtH4AmdV2Evaluation(
        DemoTradingDecision.SETUP,
        setup,
        None,
        methodology_fingerprint(),
    )


def evaluate_candle3_continuation(
    *,
    symbol: str,
    daily_reference: Vt08CrtH4AmdV2Candle,
    daily_signal: Vt08CrtH4AmdV2Candle,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2: Vt08CrtH4AmdV2Candle,
    h4_candle3_open: Decimal,
    h4_candle3_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
) -> Vt08CrtH4AmdV2Evaluation:
    """Evaluate Candle 3 only after a completed large-wick Candle 2 reversal."""

    if symbol not in SUPPORTED_MARKETS:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET)
    bias = daily_bias(daily_reference, daily_signal)
    if bias is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.DAILY_BIAS_MISSING)
    c2_side = h4_reversal_direction(h4_reference, h4_candle2)
    if c2_side is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_NOT_REVERSAL)
    if c2_side is not bias.side:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_NOT_ALIGNED)
    c2_extreme = (
        h4_candle2.low
        if bias.side is DemoTradingSetupSide.LONG
        else h4_candle2.high
    )
    c2_fraction = _manipulation_fraction(
        h4_reference,
        candidate_open=h4_candle2.open,
        extreme=c2_extreme,
        side=bias.side,
    )
    if c2_fraction <= Decimal("0.5"):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_NOT_REVERSAL)
    protected = _protected_swing(
        observed_m15,
        side=bias.side,
        required_sweep_level=None,
    )
    if protected is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.NO_PROTECTED_SWING)
    confirmation, cisd_level, extreme = protected
    c3_fraction = _manipulation_fraction(
        h4_candle2,
        candidate_open=h4_candle3_open,
        extreme=extreme,
        side=bias.side,
    )
    if c3_fraction > Decimal("0.5"):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.MANIPULATION_TOO_DEEP_FOR_C3)
    entry = confirmation.close
    target = bias.target
    if (
        bias.side is DemoTradingSetupSide.LONG and target <= entry
    ) or (
        bias.side is DemoTradingSetupSide.SHORT and target >= entry
    ):
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_TARGET)
    try:
        setup = Vt08CrtH4AmdV2Setup(
            side=bias.side,
            scenario=Vt08CrtH4AmdV2Scenario.CANDLE3_CONTINUATION,
            entry_price=entry,
            stop_loss=extreme,
            take_profit=target,
            signal_at=confirmation.closed_at.astimezone(UTC),
            expires_at=h4_candle3_closes_at.astimezone(UTC),
            cisd_level=cisd_level,
            manipulation_extreme=extreme,
            manipulation_fraction_of_reference=c3_fraction,
        )
    except Vt08CrtH4AmdV2ValidationError:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    return Vt08CrtH4AmdV2Evaluation(
        DemoTradingDecision.SETUP,
        setup,
        None,
        methodology_fingerprint(),
    )
