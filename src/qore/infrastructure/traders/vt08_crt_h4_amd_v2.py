"""VT-08 V2 — source-faithful TTrades 4H Power-of-Three research contract.

Primary source
--------------
Human Owner-provided TTrades video ``youtube:FAKWJ-1NlLE``
(``1000854868.mp4``, SHA-256
``bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271``).

This module intentionally encodes only rules demonstrated or stated by that
lesson and its explicitly required TTrades Candle-2/Candle-3/CISD prerequisites.
It does *not* turn qualitative teaching into invented numerical thresholds.

Source-faithful boundaries
--------------------------
* H4 PO3 is accumulation -> manipulation -> distribution/expansion.
* Candle 2 can reverse-to-expansion when its opposing wick/run is *shallow*.
* A large/deep Candle-2 opposing run means wait for Candle 3 continuation.
* M15 is the demonstrated lower-timeframe confirmation for the H4 model.
* CISD confirms the protected swing after the opposing run; entry is after the
  wick has formed, not while trying to catch the wick.
* The protected-swing extreme is the source-grounded invalidation reference.
* The lesson uses a directional bias/context, but does not specify one universal
  machine formula for deriving it from OHLC. Bias therefore enters as explicit
  source/context evidence instead of a fabricated D1 rule.
* ``shallow`` versus ``large/deep`` is qualitative in the source. It therefore
  enters as explicit source judgment; no 50%, ATR, body/wick, or other threshold
  is invented here.
* The lesson's targets are contextual examples. This contract does not invent a
  universal take-profit or fixed-R target.

Outputs are research evidence only. They grant no Risk, broker, DEMO, LIVE,
Production, or real-capital authority.
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
METHODOLOGY_VERSION = "v2.2-source-faithful"
PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
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
FUTURES_MARKETS = frozenset({"NAS100", "SP500", "US30"})
FX_MARKETS = frozenset(
    {"AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD", "USDJPY"}
)
SOURCE_TIMING_AMBIGUOUS_MARKETS = frozenset({"XAUUSD"})
RULESET = (
    "primary-video-only-plus-explicit-prerequisites;h4-po3-amd;"
    "candle2-shallow-wick-reversal-to-expansion;"
    "candle2-large-opposing-run-wait-candle3-continuation;"
    "m15-lower-timeframe-confirmation;cisd-protected-swing;"
    "let-wick-form-trade-body;bias-is-explicit-source-context;"
    "wick-size-is-explicit-qualitative-source-judgment;"
    "no-invented-wick-threshold;no-mandatory-d1-formula;"
    "no-universal-take-profit;research-only"
)


class Vt08CrtH4AmdV2Error(InfrastructureError):
    __slots__ = ()


class Vt08CrtH4AmdV2ValidationError(Vt08CrtH4AmdV2Error):
    __slots__ = ()


class Vt08CrtH4AmdV2Scenario(StrEnum):
    REVERSAL_EXPANSION_C2 = "reversal-expansion-candle2"
    CONTINUATION_EXPANSION_C3 = "continuation-expansion-candle3"


class Vt08CrtH4AmdV2WickProfile(StrEnum):
    """Qualitative source language; deliberately not derived from a ratio."""

    SHALLOW = "shallow"
    LARGE = "large-deep-opposing-run"
    UNRESOLVED = "unresolved"


class Vt08CrtH4AmdV2TimingFamily(StrEnum):
    FUTURES = "futures-02-06-10-new-york"
    FOREX = "forex-01-05-09-new-york"
    SOURCE_UNRESOLVED = "source-unresolved"


class Vt08CrtH4AmdV2AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    BIAS_CONTEXT_REQUIRED = "bias-context-required-by-source"
    WICK_CLASSIFICATION_REQUIRED = "qualitative-wick-classification-required"
    WAIT_FOR_CANDLE3 = "large-candle2-run-wait-for-candle3"
    CANDLE2_LARGE_RUN_REQUIRED = "candle3-requires-large-candle2-opposing-run"
    CANDLE2_REVERSAL_REQUIRED = "candle3-requires-candle2-reversal"
    REFERENCE_BOUNDARY_NOT_RUN = "reference-boundary-not-run"
    NO_CISD_PROTECTED_SWING = "no-cisd-protected-swing"
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
        for field_name, timestamp_value in (
            ("opened_at", self.opened_at),
            ("closed_at", self.closed_at),
        ):
            if timestamp_value.tzinfo is None or timestamp_value.utcoffset() is None:
                raise Vt08CrtH4AmdV2ValidationError(
                    f"{field_name} must be timezone-aware"
                )
        if self.closed_at <= self.opened_at:
            raise Vt08CrtH4AmdV2ValidationError("candle close must follow open")
        for field_name, price_value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if not price_value.is_finite() or price_value <= 0:
                raise Vt08CrtH4AmdV2ValidationError(
                    f"{field_name} must be positive finite Decimal"
                )
        if self.low > self.high:
            raise Vt08CrtH4AmdV2ValidationError("low must not exceed high")
        if self.low > min(self.open, self.close) or self.high < max(
            self.open, self.close
        ):
            raise Vt08CrtH4AmdV2ValidationError("OHLC body must lie inside high/low")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2SourceContext:
    """Source-required discretionary evidence that the video does not quantify.

    ``bias_side`` and ``wick_profile`` must come from an upstream source-faithful
    context/annotation authority. This class exists specifically to prevent the
    evaluator from fabricating those judgments from arbitrary numeric thresholds.
    """

    bias_side: DemoTradingSetupSide | None
    wick_profile: Vt08CrtH4AmdV2WickProfile
    provenance: str

    def __post_init__(self) -> None:
        if self.bias_side is not None and type(self.bias_side) is not DemoTradingSetupSide:
            raise Vt08CrtH4AmdV2ValidationError("bias_side must be canonical or None")
        if type(self.wick_profile) is not Vt08CrtH4AmdV2WickProfile:
            raise Vt08CrtH4AmdV2ValidationError("wick_profile must be exact source enum")
        if type(self.provenance) is not str or not self.provenance.strip():
            raise Vt08CrtH4AmdV2ValidationError("source context provenance is required")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Setup:
    side: DemoTradingSetupSide
    scenario: Vt08CrtH4AmdV2Scenario
    entry_price: Decimal
    stop_loss: Decimal
    signal_at: datetime
    expires_at: datetime
    cisd_level: Decimal
    protected_swing_extreme: Decimal
    wick_profile: Vt08CrtH4AmdV2WickProfile
    take_profit: None = None

    def __post_init__(self) -> None:
        if self.side is DemoTradingSetupSide.LONG:
            valid = self.stop_loss < self.entry_price
        else:
            valid = self.entry_price < self.stop_loss
        if not valid:
            raise Vt08CrtH4AmdV2ValidationError(
                "protected-swing stop must be strictly directional"
            )
        if self.signal_at.tzinfo is None or self.signal_at.utcoffset() is None:
            raise Vt08CrtH4AmdV2ValidationError("signal_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise Vt08CrtH4AmdV2ValidationError("expires_at must be timezone-aware")
        if self.signal_at >= self.expires_at:
            raise Vt08CrtH4AmdV2ValidationError("signal must precede H4 close")
        if self.take_profit is not None:
            raise Vt08CrtH4AmdV2ValidationError(
                "VT-08 V2 source does not define one universal take-profit"
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
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "ruleset": RULESET,
        "supported_markets": SUPPORTED_MARKETS,
    }
    return sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def timing_family_for_market(symbol: str) -> Vt08CrtH4AmdV2TimingFamily | None:
    """Map only source-explicit asset families; do not guess XAUUSD's family."""

    if symbol not in SUPPORTED_MARKETS:
        return None
    if symbol in FUTURES_MARKETS:
        return Vt08CrtH4AmdV2TimingFamily.FUTURES
    if symbol in FX_MARKETS:
        return Vt08CrtH4AmdV2TimingFamily.FOREX
    return Vt08CrtH4AmdV2TimingFamily.SOURCE_UNRESOLVED


def _protected_swing(
    bars: tuple[Vt08CrtH4AmdV2Candle, ...],
    *,
    side: DemoTradingSetupSide,
    required_run_level: Decimal | None,
) -> tuple[Vt08CrtH4AmdV2Candle, Decimal, Decimal] | None:
    """Return first causal CISD confirmation after the opposing run.

    The primary video explicitly depends on TTrades' Candle-2/Candle-3 material.
    CISD is therefore operationalized using TTrades' definition: for bullish
    delivery, the first down-close sequence that makes the low is protected once
    price closes above the opening price of that sequence; bearish is mirrored.
    """

    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    extreme_index: int | None = None
    run_observed = required_run_level is None
    in_opposing_sequence = False

    for index, bar in enumerate(bars):
        if required_run_level is not None:
            if side is DemoTradingSetupSide.LONG and bar.low < required_run_level:
                run_observed = True
            elif side is DemoTradingSetupSide.SHORT and bar.high > required_run_level:
                run_observed = True

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
            run_observed
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


def _validate_common(
    *,
    symbol: str,
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation | None:
    if symbol not in SUPPORTED_MARKETS:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET)
    if context.bias_side is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.BIAS_CONTEXT_REQUIRED)
    if context.wick_profile is Vt08CrtH4AmdV2WickProfile.UNRESOLVED:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.WICK_CLASSIFICATION_REQUIRED)
    return None


def evaluate_reversal_expansion_candle2(
    *,
    symbol: str,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation:
    """Evaluate the source's shallow-wick Candle-2 reversal-to-expansion case."""

    blocked = _validate_common(symbol=symbol, context=context)
    if blocked is not None:
        return blocked
    if context.wick_profile is Vt08CrtH4AmdV2WickProfile.LARGE:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.WAIT_FOR_CANDLE3)
    side = context.bias_side
    assert side is not None
    required_run_level = (
        h4_reference.low if side is DemoTradingSetupSide.LONG else h4_reference.high
    )
    protected = _protected_swing(
        observed_m15,
        side=side,
        required_run_level=required_run_level,
    )
    if protected is None:
        touched = any(
            bar.low < required_run_level
            if side is DemoTradingSetupSide.LONG
            else bar.high > required_run_level
            for bar in observed_m15
        )
        return _abstain(
            Vt08CrtH4AmdV2AbstainReason.NO_CISD_PROTECTED_SWING
            if touched
            else Vt08CrtH4AmdV2AbstainReason.REFERENCE_BOUNDARY_NOT_RUN
        )
    confirmation, cisd_level, extreme = protected
    try:
        setup = Vt08CrtH4AmdV2Setup(
            side=side,
            scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
            entry_price=confirmation.close,
            stop_loss=extreme,
            signal_at=confirmation.closed_at.astimezone(UTC),
            expires_at=h4_candle2_closes_at.astimezone(UTC),
            cisd_level=cisd_level,
            protected_swing_extreme=extreme,
            wick_profile=context.wick_profile,
        )
    except Vt08CrtH4AmdV2ValidationError:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    return Vt08CrtH4AmdV2Evaluation(
        DemoTradingDecision.SETUP,
        setup,
        None,
        methodology_fingerprint(),
    )


def _candle2_reversal_side(
    reference: Vt08CrtH4AmdV2Candle,
    candle2: Vt08CrtH4AmdV2Candle,
) -> DemoTradingSetupSide | None:
    swept_high = candle2.high > reference.high
    swept_low = candle2.low < reference.low
    if swept_high == swept_low:
        return None
    closes_back_inside = reference.low < candle2.close < reference.high
    if not closes_back_inside:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def evaluate_continuation_expansion_candle3(
    *,
    symbol: str,
    h4_reference: Vt08CrtH4AmdV2Candle,
    h4_candle2: Vt08CrtH4AmdV2Candle,
    h4_candle3_closes_at: datetime,
    observed_m15: tuple[Vt08CrtH4AmdV2Candle, ...],
    candle2_wick_profile: Vt08CrtH4AmdV2WickProfile,
    context: Vt08CrtH4AmdV2SourceContext,
) -> Vt08CrtH4AmdV2Evaluation:
    """Evaluate Candle 3 only after a source-classified large Candle-2 reversal."""

    blocked = _validate_common(symbol=symbol, context=context)
    if blocked is not None:
        return blocked
    if candle2_wick_profile is not Vt08CrtH4AmdV2WickProfile.LARGE:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_LARGE_RUN_REQUIRED)
    if context.wick_profile is not Vt08CrtH4AmdV2WickProfile.SHALLOW:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.WICK_CLASSIFICATION_REQUIRED)
    side = context.bias_side
    assert side is not None
    reversal_side = _candle2_reversal_side(h4_reference, h4_candle2)
    if reversal_side is not side:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.CANDLE2_REVERSAL_REQUIRED)
    protected = _protected_swing(
        observed_m15,
        side=side,
        required_run_level=None,
    )
    if protected is None:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.NO_CISD_PROTECTED_SWING)
    confirmation, cisd_level, extreme = protected
    try:
        setup = Vt08CrtH4AmdV2Setup(
            side=side,
            scenario=Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3,
            entry_price=confirmation.close,
            stop_loss=extreme,
            signal_at=confirmation.closed_at.astimezone(UTC),
            expires_at=h4_candle3_closes_at.astimezone(UTC),
            cisd_level=cisd_level,
            protected_swing_extreme=extreme,
            wick_profile=context.wick_profile,
        )
    except Vt08CrtH4AmdV2ValidationError:
        return _abstain(Vt08CrtH4AmdV2AbstainReason.INVALID_GEOMETRY)
    return Vt08CrtH4AmdV2Evaluation(
        DemoTradingDecision.SETUP,
        setup,
        None,
        methodology_fingerprint(),
    )
