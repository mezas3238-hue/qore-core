"""Source-bound VT-08 CRT / 4H Power-of-Three research candidate.

This module is additive.  It does not replace ``Vt08Crt4hAmd`` V1.

Primary methodology source:
- TTrades, ``Trading The 4 Hour Power Of Three - OHLC / OLHC``
  (youtube:FAKWJ-1NlLE, 2025-09-20).
- The contemporaneous TTrades article/PDF describing 4H PO3 as AMD,
  ``let the wick form, trade the body``, with M15 lower-timeframe confirmation.

Secondary TTrades material is used only to make CISD mechanical: bullish CISD
requires a close through the opening price of the down-close delivery sequence
that formed the low; bearish CISD is the mirror.  No FVG requirement from V1 is
silently carried into V2 because the source lesson does not require one.

Authority boundary:
``SOURCE-ALIGNED H4 + M15 EVIDENCE -> VT-08 V2 SETUP/ABSTAIN``.
The output is research evidence only and creates no quantity, account, Risk,
broker, DEMO, LIVE, Production, or real-capital authority.
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

_TRADER_CODE = "vt-08"
_TRADER_VERSION = "v2"
_METHODOLOGY_ID = "crt-h4-po3-amd-source"
_METHODOLOGY_VERSION = "v2"
_PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
_PRIMARY_SOURCE_ARTICLE = (
    "https://ttrades.com/trading-the-4-hour-power-of-3-open-high-low-close-strategy/"
)
_CISD_SOURCE = "https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/"
_SUPPORTED_MARKETS = frozenset(
    {
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "XAUUSD",
        "NAS100",
        "SP500",
        "GBPJPY",
        "AUDJPY",
        "US30",
    }
)

_RULESET = (
    "source-video:FAKWJ-1NlLE;h4-power-of-three-amd;higher-timeframe-closure-first;"
    "new-york-local-source-h4-windows;lower-timeframe-m15;let-wick-form-trade-body;"
    "wick-opposes-h4-bias;cisd-closes-through-opposing-delivery-sequence-open;"
    "entry-at-first-confirming-m15-close;stop-at-wick-extreme;terminal-at-source-h4-close;"
    "no-v1-fvg-requirement;continuation-and-reversal-profiled-separately;research-only"
)


class Vt08CrtH4AmdV2Error(InfrastructureError):
    """Base error for the source-bound VT-08 V2 research candidate."""

    __slots__ = ()


class Vt08CrtH4AmdV2ValidationError(Vt08CrtH4AmdV2Error):
    """Fail-closed validation error for VT-08 V2."""

    __slots__ = ()


class Vt08CrtH4AmdV2Profile(StrEnum):
    """Source-demonstrated 4H expansion families."""

    CONTINUATION = "continuation-expansion"
    REVERSAL = "reversal-expansion"


class Vt08CrtH4AmdV2Closure(StrEnum):
    """Mechanical higher-timeframe closure used to determine directional bias."""

    RANGE_EXPANSION = "range-expansion-closure"
    CANDLE2_REVERSAL = "candle2-reversal-closure"


class Vt08CrtH4AmdV2AbstainReason(StrEnum):
    """Explicit reasons the source contract refuses to manufacture a setup."""

    UNSUPPORTED_MARKET = "unsupported-market"
    INSUFFICIENT_HTF_CONTEXT = "insufficient-htf-context"
    NO_VALID_HTF_CLOSURE = "no-valid-htf-closure"
    CURRENT_H4_WINDOW_EMPTY = "current-h4-window-empty"
    NO_OPPOSING_WICK = "no-opposing-wick"
    NO_CISD = "no-cisd"
    INVALID_GEOMETRY = "invalid-geometry"


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Bar:
    """One exact closed M15 observation used by the source-bound evaluator."""

    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        _aware(self.opened_at, field_name="opened_at")
        _aware(self.closed_at, field_name="closed_at")
        if self.closed_at <= self.opened_at:
            raise Vt08CrtH4AmdV2ValidationError("bar close must follow bar open")
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            _positive_decimal(value, field_name=name)
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise Vt08CrtH4AmdV2ValidationError("OHLC body must lie inside high/low")
        if self.low > self.high:
            raise Vt08CrtH4AmdV2ValidationError("bar low must not exceed high")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2H4Candle:
    """One complete source-aligned four-hour candle derived from M15 evidence."""

    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        _aware(self.opened_at, field_name="h4 opened_at")
        _aware(self.closed_at, field_name="h4 closed_at")
        if self.closed_at <= self.opened_at:
            raise Vt08CrtH4AmdV2ValidationError("H4 close must follow H4 open")
        for name, value in (
            ("h4 open", self.open),
            ("h4 high", self.high),
            ("h4 low", self.low),
            ("h4 close", self.close),
        ):
            _positive_decimal(value, field_name=name)
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise Vt08CrtH4AmdV2ValidationError("H4 body must lie inside high/low")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Config:
    """Frozen source configuration; there is no optimization parameter in V2."""

    lower_timeframe: str = "M15"
    exit_model: str = "source-h4-close"

    def __post_init__(self) -> None:
        if self.lower_timeframe != "M15":
            raise Vt08CrtH4AmdV2ValidationError("VT-08 V2 source contract requires M15")
        if self.exit_model != "source-h4-close":
            raise Vt08CrtH4AmdV2ValidationError(
                "VT-08 V2 may not invent a non-source exit model"
            )

    def fingerprint(self) -> str:
        return _digest(
            {
                "schema": "qore.trader.vt08.crt-h4-amd-v2.config.v1",
                "lower_timeframe": self.lower_timeframe,
                "exit_model": self.exit_model,
            }
        )


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Input:
    """Decision-time evidence for one in-progress source-aligned H4 candle."""

    symbol: str
    as_of: datetime
    previous_h4: tuple[Vt08CrtH4AmdV2H4Candle, ...]
    current_h4_opened_at: datetime
    current_h4_closes_at: datetime
    current_m15: tuple[Vt08CrtH4AmdV2Bar, ...]

    def __post_init__(self) -> None:
        if type(self.symbol) is not str or not self.symbol:
            raise Vt08CrtH4AmdV2ValidationError("symbol must be non-empty str")
        _aware(self.as_of, field_name="as_of")
        _aware(self.current_h4_opened_at, field_name="current_h4_opened_at")
        _aware(self.current_h4_closes_at, field_name="current_h4_closes_at")
        if self.current_h4_closes_at <= self.current_h4_opened_at:
            raise Vt08CrtH4AmdV2ValidationError("current H4 window must be positive")
        if type(self.previous_h4) is not tuple or any(
            type(item) is not Vt08CrtH4AmdV2H4Candle for item in self.previous_h4
        ):
            raise Vt08CrtH4AmdV2ValidationError("previous_h4 must be immutable exact candles")
        if type(self.current_m15) is not tuple or any(
            type(item) is not Vt08CrtH4AmdV2Bar for item in self.current_m15
        ):
            raise Vt08CrtH4AmdV2ValidationError("current_m15 must be immutable exact bars")
        previous: Vt08CrtH4AmdV2Bar | None = None
        for item in self.current_m15:
            item.__post_init__()
            if item.opened_at < self.current_h4_opened_at:
                raise Vt08CrtH4AmdV2ValidationError("M15 bar predates current H4 window")
            if item.closed_at > min(self.as_of, self.current_h4_closes_at):
                raise Vt08CrtH4AmdV2ValidationError("future M15 evidence is prohibited")
            if previous is not None and item.opened_at < previous.opened_at:
                raise Vt08CrtH4AmdV2ValidationError("M15 evidence must be chronological")
            previous = item


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Setup:
    """Research setup at confirmed M15 CISD; not an executable order."""

    side: DemoTradingSetupSide
    profile: Vt08CrtH4AmdV2Profile
    htf_closure: Vt08CrtH4AmdV2Closure
    entry_price: Decimal
    invalidation_price: Decimal
    cisd_level: Decimal
    manipulation_extreme: Decimal
    h4_open_price: Decimal
    signal_at: datetime
    terminal_at: datetime

    def __post_init__(self) -> None:
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt08CrtH4AmdV2ValidationError("setup side must be canonical")
        if type(self.profile) is not Vt08CrtH4AmdV2Profile:
            raise Vt08CrtH4AmdV2ValidationError("setup profile must be exact")
        if type(self.htf_closure) is not Vt08CrtH4AmdV2Closure:
            raise Vt08CrtH4AmdV2ValidationError("HTF closure must be exact")
        for name, value in (
            ("entry_price", self.entry_price),
            ("invalidation_price", self.invalidation_price),
            ("cisd_level", self.cisd_level),
            ("manipulation_extreme", self.manipulation_extreme),
            ("h4_open_price", self.h4_open_price),
        ):
            _positive_decimal(value, field_name=name)
        _aware(self.signal_at, field_name="signal_at")
        _aware(self.terminal_at, field_name="terminal_at")
        if self.signal_at >= self.terminal_at:
            raise Vt08CrtH4AmdV2ValidationError("setup must precede source H4 close")
        if self.side is DemoTradingSetupSide.LONG:
            if not self.invalidation_price < self.entry_price:
                raise Vt08CrtH4AmdV2ValidationError("LONG stop must be below entry")
        elif not self.entry_price < self.invalidation_price:
            raise Vt08CrtH4AmdV2ValidationError("SHORT stop must be above entry")


@dataclass(frozen=True, slots=True)
class Vt08CrtH4AmdV2Evaluation:
    """Deterministic source-bound research decision."""

    decision: DemoTradingDecision
    symbol: str
    evaluated_at: datetime
    config_fingerprint: str
    methodology_fingerprint: str
    setup: Vt08CrtH4AmdV2Setup | None
    abstain_reason: Vt08CrtH4AmdV2AbstainReason | None


def _aware(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise Vt08CrtH4AmdV2ValidationError(f"{field_name} must be timezone-aware")


def _positive_decimal(value: Decimal, *, field_name: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise Vt08CrtH4AmdV2ValidationError(
            f"{field_name} must be positive finite Decimal"
        )


def _digest(payload: object) -> str:
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def methodology_fingerprint(config: Vt08CrtH4AmdV2Config) -> str:
    """Return immutable identity of this exact source reconstruction."""

    return _digest(
        {
            "schema": "qore.trader.vt08.crt-h4-amd-v2.methodology.v1",
            "trader_code": _TRADER_CODE,
            "trader_version": _TRADER_VERSION,
            "methodology_id": _METHODOLOGY_ID,
            "methodology_version": _METHODOLOGY_VERSION,
            "primary_source": _PRIMARY_SOURCE,
            "primary_source_article": _PRIMARY_SOURCE_ARTICLE,
            "cisd_source": _CISD_SOURCE,
            "ruleset": _RULESET,
            "supported_markets": sorted(_SUPPORTED_MARKETS),
            "config_fingerprint": config.fingerprint(),
        }
    )


def _htf_bias(
    previous: tuple[Vt08CrtH4AmdV2H4Candle, ...],
) -> tuple[DemoTradingSetupSide, Vt08CrtH4AmdV2Profile, Vt08CrtH4AmdV2Closure] | None:
    """Use only fully closed source-H4 candles to determine the next-candle bias.

    A sweep-and-close-back-inside is the source-family reversal closure.  A
    decisive close outside the prior candle range is the continuation/expansion
    closure.  Two-sided sweeps are intentionally ambiguous and rejected.
    """

    if len(previous) < 2:
        return None
    base, signal = previous[-2], previous[-1]
    swept_high = signal.high > base.high
    swept_low = signal.low < base.low
    if swept_high and swept_low:
        return None
    if swept_low and base.low < signal.close < base.high:
        return (
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2Profile.REVERSAL,
            Vt08CrtH4AmdV2Closure.CANDLE2_REVERSAL,
        )
    if swept_high and base.low < signal.close < base.high:
        return (
            DemoTradingSetupSide.SHORT,
            Vt08CrtH4AmdV2Profile.REVERSAL,
            Vt08CrtH4AmdV2Closure.CANDLE2_REVERSAL,
        )
    if signal.close > base.high:
        return (
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2Profile.CONTINUATION,
            Vt08CrtH4AmdV2Closure.RANGE_EXPANSION,
        )
    if signal.close < base.low:
        return (
            DemoTradingSetupSide.SHORT,
            Vt08CrtH4AmdV2Profile.CONTINUATION,
            Vt08CrtH4AmdV2Closure.RANGE_EXPANSION,
        )
    return None


def _cisd_setup(
    bars: tuple[Vt08CrtH4AmdV2Bar, ...],
    *,
    side: DemoTradingSetupSide,
    profile: Vt08CrtH4AmdV2Profile,
    closure: Vt08CrtH4AmdV2Closure,
    h4_close: datetime,
) -> Vt08CrtH4AmdV2Setup | None:
    if not bars:
        return None
    h4_open = bars[0].open
    sequence_open: Decimal | None = None
    extreme: Decimal | None = None
    extreme_index: int | None = None
    previous_opposing = False

    for index, bar in enumerate(bars):
        opposing = (
            bar.close < bar.open
            if side is DemoTradingSetupSide.LONG
            else bar.close > bar.open
        )
        if opposing:
            if not previous_opposing:
                sequence_open = bar.open
            candidate_extreme = (
                bar.low if side is DemoTradingSetupSide.LONG else bar.high
            )
            wick_formed = (
                candidate_extreme < h4_open
                if side is DemoTradingSetupSide.LONG
                else candidate_extreme > h4_open
            )
            if wick_formed and (
                extreme is None
                or (
                    candidate_extreme < extreme
                    if side is DemoTradingSetupSide.LONG
                    else candidate_extreme > extreme
                )
            ):
                extreme = candidate_extreme
                extreme_index = index
            previous_opposing = True
            continue

        if extreme is not None:
            extreme = (
                min(extreme, bar.low)
                if side is DemoTradingSetupSide.LONG
                else max(extreme, bar.high)
            )
        if (
            sequence_open is not None
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
                try:
                    return Vt08CrtH4AmdV2Setup(
                        side=side,
                        profile=profile,
                        htf_closure=closure,
                        entry_price=bar.close,
                        invalidation_price=extreme,
                        cisd_level=sequence_open,
                        manipulation_extreme=extreme,
                        h4_open_price=h4_open,
                        signal_at=bar.closed_at.astimezone(UTC),
                        terminal_at=h4_close.astimezone(UTC),
                    )
                except Vt08CrtH4AmdV2ValidationError:
                    return None
        previous_opposing = False
    return None


def _abstain(
    inputs: Vt08CrtH4AmdV2Input,
    config: Vt08CrtH4AmdV2Config,
    reason: Vt08CrtH4AmdV2AbstainReason,
) -> Vt08CrtH4AmdV2Evaluation:
    return Vt08CrtH4AmdV2Evaluation(
        decision=DemoTradingDecision.ABSTAIN,
        symbol=inputs.symbol,
        evaluated_at=inputs.as_of.astimezone(UTC),
        config_fingerprint=config.fingerprint(),
        methodology_fingerprint=methodology_fingerprint(config),
        setup=None,
        abstain_reason=reason,
    )


def evaluate_vt08_crt_h4_amd_v2(
    inputs: Vt08CrtH4AmdV2Input,
    config: Vt08CrtH4AmdV2Config | None = None,
) -> Vt08CrtH4AmdV2Evaluation:
    """Evaluate the frozen source reconstruction without hidden optimization."""

    if type(inputs) is not Vt08CrtH4AmdV2Input:
        raise Vt08CrtH4AmdV2ValidationError("VT-08 V2 requires exact input")
    inputs.__post_init__()
    selected = Vt08CrtH4AmdV2Config() if config is None else config
    if type(selected) is not Vt08CrtH4AmdV2Config:
        raise Vt08CrtH4AmdV2ValidationError("VT-08 V2 requires exact config")
    selected.__post_init__()

    if inputs.symbol not in _SUPPORTED_MARKETS:
        return _abstain(inputs, selected, Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET)
    if len(inputs.previous_h4) < 2:
        return _abstain(
            inputs,
            selected,
            Vt08CrtH4AmdV2AbstainReason.INSUFFICIENT_HTF_CONTEXT,
        )
    directional = _htf_bias(inputs.previous_h4)
    if directional is None:
        return _abstain(
            inputs,
            selected,
            Vt08CrtH4AmdV2AbstainReason.NO_VALID_HTF_CLOSURE,
        )
    if not inputs.current_m15:
        return _abstain(
            inputs,
            selected,
            Vt08CrtH4AmdV2AbstainReason.CURRENT_H4_WINDOW_EMPTY,
        )
    side, profile, closure = directional
    h4_open = inputs.current_m15[0].open
    wick_exists = (
        min(item.low for item in inputs.current_m15) < h4_open
        if side is DemoTradingSetupSide.LONG
        else max(item.high for item in inputs.current_m15) > h4_open
    )
    if not wick_exists:
        return _abstain(inputs, selected, Vt08CrtH4AmdV2AbstainReason.NO_OPPOSING_WICK)
    setup = _cisd_setup(
        inputs.current_m15,
        side=side,
        profile=profile,
        closure=closure,
        h4_close=inputs.current_h4_closes_at,
    )
    if setup is None:
        return _abstain(inputs, selected, Vt08CrtH4AmdV2AbstainReason.NO_CISD)
    return Vt08CrtH4AmdV2Evaluation(
        decision=DemoTradingDecision.SETUP,
        symbol=inputs.symbol,
        evaluated_at=inputs.as_of.astimezone(UTC),
        config_fingerprint=selected.fingerprint(),
        methodology_fingerprint=methodology_fingerprint(selected),
        setup=setup,
        abstain_reason=None,
    )


SUPPORTED_VT08_V2_MARKETS = tuple(sorted(_SUPPORTED_MARKETS))
PRIMARY_VT08_V2_SOURCE = _PRIMARY_SOURCE
VT08_V2_RULESET = _RULESET
