"""VT-08 V3 — source-bound nested CRT 1-5-9 research candidate.

V3 is additive and does not modify VT-08 V1 or V2.

Primary evidence is the Human Owner-provided three-video CRT package frozen by
SHA-256, not a later optimization result:
- 9968f10cee6b5c94d7406c3cdc31bef2623221a5a6e6529f7b4293c1bbe97664
- fceacd2b59039bc94aea3b7390804c1c68f1ac10b1e7bc3e318a7645d867a5ee
- 57206b5c3e48a2281b4648da7c69b1c20c39ea5c1edd34c689a1a9080341c225

Observed source hierarchy:
1. a higher-timeframe CRT range supplies directional context;
2. H4 candles labelled 1, 5 and 9 form the 1-5-9 CRT sequence;
3. the H4 distribution is refined with a subordinate H1 CRT;
4. entry is refined again on M15; M5/M3 is shown as optional sniper refinement.

Deterministic V3 freeze:
- D1 uses two fully closed provider daily candles: reference then manipulation;
- H4 reference is 01:00-05:00 New York and manipulation is 05:00-09:00;
- the 09:00-13:00 H4 candle is the distribution window;
- H1 09:00-10:00 is reference and 10:00-11:00 is manipulation;
- M15 11:00-11:15 is reference and 11:15-11:30 is manipulation;
- if D1/H4/H1/M15 all imply the same CRT direction, entry is the 11:30 M15 open;
- stop is the M15 manipulation extreme;
- target is the opposite edge of the H4 01:00 reference candle;
- unresolved cases at 13:00 New York are censored, never fabricated as exits.

The source teaches CRT fractality and the 1-5-9 nesting, but does not prove that
every discretionary human selection maps uniquely to one algorithmic rule. The
specific deterministic choices above are versioned, falsifiable
operationalization choices. This module grants no DEMO/LIVE/Risk authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingSetupSide,
)
from qore.kernel.errors import InfrastructureError

TRADER_CODE = "vt-08"
TRADER_VERSION = "v3"
METHODOLOGY_ID = "crt-159-fractal-nested"
METHODOLOGY_VERSION = "v3"
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
PRIMARY_SOURCE_SHA256 = (
    "9968f10cee6b5c94d7406c3cdc31bef2623221a5a6e6529f7b4293c1bbe97664",
    "fceacd2b59039bc94aea3b7390804c1c68f1ac10b1e7bc3e318a7645d867a5ee",
    "57206b5c3e48a2281b4648da7c69b1c20c39ea5c1edd34c689a1a9080341c225",
)
RULESET = (
    "human-owner-three-video-source-freeze;crt-fractal-hierarchy;"
    "d1-reference-manipulation-context;new-york-h4-01-05-09;"
    "h4-01-reference;h4-05-manipulation;h4-09-distribution;"
    "h1-09-reference;h1-10-manipulation;m15-11:00-reference;"
    "m15-11:15-manipulation;entry-next-m15-open-11:30;"
    "all-level-directions-must-agree;stop-m15-manipulation-extreme;"
    "target-opposite-h4-01-range-edge;13:00-unresolved-censor;research-only"
)


class Vt08Crt159V3Error(InfrastructureError):
    __slots__ = ()


class Vt08Crt159V3ValidationError(Vt08Crt159V3Error):
    __slots__ = ()


class Vt08Crt159V3AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    DAILY_CONTEXT_MISSING = "daily-context-missing"
    DAILY_CRT_INVALID = "daily-crt-invalid"
    H4_CRT_INVALID = "h4-crt-invalid"
    H1_CRT_INVALID = "h1-crt-invalid"
    M15_CRT_INVALID = "m15-crt-invalid"
    DIRECTION_DISAGREEMENT = "direction-disagreement"
    INVALID_ENTRY_GEOMETRY = "invalid-entry-geometry"


@dataclass(frozen=True, slots=True)
class Vt08Crt159V3Candle:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        for name, value in (
            ("opened_at", self.opened_at),
            ("closed_at", self.closed_at),
        ):
            if (
                type(value) is not datetime
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise Vt08Crt159V3ValidationError(
                    f"{name} must be timezone-aware"
                )
        if self.closed_at <= self.opened_at:
            raise Vt08Crt159V3ValidationError("candle close must follow open")
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                raise Vt08Crt159V3ValidationError(
                    f"{name} must be positive Decimal"
                )
        if (
            self.low > min(self.open, self.close)
            or self.high < max(self.open, self.close)
        ):
            raise Vt08Crt159V3ValidationError(
                "OHLC body must lie inside high/low"
            )
        if self.low > self.high:
            raise Vt08Crt159V3ValidationError("low must not exceed high")


@dataclass(frozen=True, slots=True)
class Vt08Crt159V3Input:
    symbol: str
    as_of: datetime
    daily_reference: Vt08Crt159V3Candle | None
    daily_manipulation: Vt08Crt159V3Candle | None
    h4_reference_01: Vt08Crt159V3Candle
    h4_manipulation_05: Vt08Crt159V3Candle
    h1_reference_09: Vt08Crt159V3Candle
    h1_manipulation_10: Vt08Crt159V3Candle
    m15_reference_1100: Vt08Crt159V3Candle
    m15_manipulation_1115: Vt08Crt159V3Candle
    entry_bar_1130: Vt08Crt159V3Candle
    h4_distribution_closes_at: datetime

    def __post_init__(self) -> None:
        if type(self.symbol) is not str or not self.symbol:
            raise Vt08Crt159V3ValidationError("symbol must be non-empty str")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise Vt08Crt159V3ValidationError("as_of must be timezone-aware")
        if (
            self.h4_distribution_closes_at.tzinfo is None
            or self.h4_distribution_closes_at.utcoffset() is None
        ):
            raise Vt08Crt159V3ValidationError(
                "h4_distribution_closes_at must be timezone-aware"
            )
        if self.entry_bar_1130.opened_at > self.as_of:
            raise Vt08Crt159V3ValidationError(
                "future entry-bar evidence is prohibited"
            )
        if self.entry_bar_1130.opened_at >= self.h4_distribution_closes_at:
            raise Vt08Crt159V3ValidationError(
                "entry must precede H4 distribution close"
            )


@dataclass(frozen=True, slots=True)
class Vt08Crt159V3Setup:
    side: DemoTradingSetupSide
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    daily_target: Decimal
    m15_sweep_extreme: Decimal
    signal_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.side is DemoTradingSetupSide.LONG:
            valid = self.stop_loss < self.entry_price < self.take_profit
        else:
            valid = self.take_profit < self.entry_price < self.stop_loss
        if not valid:
            raise Vt08Crt159V3ValidationError(
                "setup geometry must be strictly directional"
            )


@dataclass(frozen=True, slots=True)
class Vt08Crt159V3Evaluation:
    decision: DemoTradingDecision
    setup: Vt08Crt159V3Setup | None
    abstain_reason: Vt08Crt159V3AbstainReason | None
    methodology_fingerprint: str


def _fingerprint() -> str:
    material = {
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "ruleset": RULESET,
        "supported_markets": SUPPORTED_MARKETS,
    }
    return sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def crt_direction(
    reference: Vt08Crt159V3Candle,
    manipulation: Vt08Crt159V3Candle,
) -> DemoTradingSetupSide | None:
    """Classic CRT: exactly one range edge swept, close returns inside range."""

    swept_high = manipulation.high > reference.high
    swept_low = manipulation.low < reference.low
    closes_inside = reference.low < manipulation.close < reference.high
    if not closes_inside or swept_high == swept_low:
        return None
    return (
        DemoTradingSetupSide.SHORT
        if swept_high
        else DemoTradingSetupSide.LONG
    )


def _abstain(
    reason: Vt08Crt159V3AbstainReason,
) -> Vt08Crt159V3Evaluation:
    return Vt08Crt159V3Evaluation(
        decision=DemoTradingDecision.ABSTAIN,
        setup=None,
        abstain_reason=reason,
        methodology_fingerprint=_fingerprint(),
    )


def evaluate_vt08_crt_159_v3(
    inputs: Vt08Crt159V3Input,
) -> Vt08Crt159V3Evaluation:
    """Evaluate one fully observable nested 1-5-9 decision without lookahead."""

    if type(inputs) is not Vt08Crt159V3Input:
        raise Vt08Crt159V3ValidationError("VT-08 V3 requires exact input")
    inputs.__post_init__()
    if inputs.symbol not in SUPPORTED_MARKETS:
        return _abstain(Vt08Crt159V3AbstainReason.UNSUPPORTED_MARKET)
    if inputs.daily_reference is None or inputs.daily_manipulation is None:
        return _abstain(Vt08Crt159V3AbstainReason.DAILY_CONTEXT_MISSING)

    daily_side = crt_direction(
        inputs.daily_reference,
        inputs.daily_manipulation,
    )
    if daily_side is None:
        return _abstain(Vt08Crt159V3AbstainReason.DAILY_CRT_INVALID)
    h4_side = crt_direction(
        inputs.h4_reference_01,
        inputs.h4_manipulation_05,
    )
    if h4_side is None:
        return _abstain(Vt08Crt159V3AbstainReason.H4_CRT_INVALID)
    h1_side = crt_direction(
        inputs.h1_reference_09,
        inputs.h1_manipulation_10,
    )
    if h1_side is None:
        return _abstain(Vt08Crt159V3AbstainReason.H1_CRT_INVALID)
    m15_side = crt_direction(
        inputs.m15_reference_1100,
        inputs.m15_manipulation_1115,
    )
    if m15_side is None:
        return _abstain(Vt08Crt159V3AbstainReason.M15_CRT_INVALID)
    if len({daily_side, h4_side, h1_side, m15_side}) != 1:
        return _abstain(Vt08Crt159V3AbstainReason.DIRECTION_DISAGREEMENT)

    side = daily_side
    entry = inputs.entry_bar_1130.open
    if side is DemoTradingSetupSide.LONG:
        stop = inputs.m15_manipulation_1115.low
        target = inputs.h4_reference_01.high
        daily_target = inputs.daily_reference.high
    else:
        stop = inputs.m15_manipulation_1115.high
        target = inputs.h4_reference_01.low
        daily_target = inputs.daily_reference.low
    try:
        setup = Vt08Crt159V3Setup(
            side=side,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            daily_target=daily_target,
            m15_sweep_extreme=stop,
            signal_at=inputs.entry_bar_1130.opened_at,
            expires_at=inputs.h4_distribution_closes_at,
        )
    except Vt08Crt159V3ValidationError:
        return _abstain(Vt08Crt159V3AbstainReason.INVALID_ENTRY_GEOMETRY)
    return Vt08Crt159V3Evaluation(
        decision=DemoTradingDecision.SETUP,
        setup=setup,
        abstain_reason=None,
        methodology_fingerprint=_fingerprint(),
    )
