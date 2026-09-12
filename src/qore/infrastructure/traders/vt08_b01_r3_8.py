"""VT-08 R3.8 B01 source-faithful historical replay subset.

This module implements only the narrow author-clarified B01 subset frozen after
the R3.8 source adjudication. It deliberately does not replace the historical
VT-08 V2 evaluator or grant DEMO/LIVE execution authority.

The executable research contract is restricted to Forex and to the Human Owner
01:00/05:00/09:00 America/New_York entry anchors. Source H4 and source-day bars
are reconstructed only from complete contiguous M15 evidence, avoiding the
unresolved Futures 14:00/session-break construction.

Four historical-replay containments are explicit and fingerprinted:
- fill exactly at the new H4 open (broker order type remains unresolved);
- use the protected-swing structural level with no execution offset;
- use a conservative initial 2R replay target;
- close any still-open modeled trade at the next H4 boundary.

Those containments are QORE research policies, not universal TTrades source claims.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import (
    DemoTradingError,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
)
from qore.kernel.errors import InfrastructureError

TRADER_CODE = "vt-08"
TRADER_VERSION = "r3.8-b01-author-clarified-v1"
METHODOLOGY_ID = "ttrades-h4-po3-b01"
METHODOLOGY_VERSION = "r3.8-author-clarified-b01-v1"
OPERATING_TIMEZONE = "America/New_York"
_NY = ZoneInfo(OPERATING_TIMEZONE)

PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
OWNER_FOREX_ENTRY_ANCHORS = (1, 5, 9)
SOURCE_FOREX_H4_ANCHORS = (1, 5, 9, 13, 17, 21)
AUTHORIZED_FOREX_MARKETS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
)

OPERATIONAL_CONTAINMENTS = (
    "historical-fill-at-new-h4-open-broker-order-type-unspecified",
    "protected-swing-structural-level-no-stop-offset",
    "conservative-initial-2r-replay-target",
    "close-modeled-position-at-next-h4-boundary",
)
TARGET_POLICY = "conservative-initial-2r"
DAILY_SELECTION_POLICY = "exactly-one-b01-candidate-per-market-ny-date-else-abstain"


class Vt08B01R38Error(InfrastructureError):
    __slots__ = ()


class Vt08B01R38ValidationError(Vt08B01R38Error):
    __slots__ = ()


class Vt08B01AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    OUTSIDE_OWNER_ANCHOR = "outside-owner-anchor"
    INCOMPLETE_SOURCE_H4 = "incomplete-source-h4"
    INCOMPLETE_SOURCE_DAY = "incomplete-source-day"
    BIAS_UNRESOLVED = "bias-unresolved"
    C2_REVERSAL_MISMATCH = "c2-reversal-mismatch"
    NO_PROTECTED_SWING = "no-protected-swing"
    MULTIPLE_PROTECTED_SWINGS = "multiple-protected-swings"
    INVALID_RISK_GEOMETRY = "invalid-risk-geometry"


@dataclass(frozen=True, slots=True)
class Vt08B01Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        for name, value in (("opened_at", self.opened_at), ("closed_at", self.closed_at)):
            if (
                type(value) is not datetime
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise Vt08B01R38ValidationError(f"{name} must be timezone-aware")
        if self.closed_at <= self.opened_at:
            raise Vt08B01R38ValidationError("bar close must follow open")
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                raise Vt08B01R38ValidationError(f"{name} must be positive finite Decimal")
        if self.low > self.high:
            raise Vt08B01R38ValidationError("bar low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise Vt08B01R38ValidationError("bar open must lie inside low/high")
        if not self.low <= self.close <= self.high:
            raise Vt08B01R38ValidationError("bar close must lie inside low/high")


@dataclass(frozen=True, slots=True)
class Vt08B01ProtectedSwing:
    side: DemoTradingSetupSide
    price: Decimal
    cisd_level: Decimal
    confirmed_at: datetime
    opposing_series_opened_at: datetime

    def __post_init__(self) -> None:
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt08B01R38ValidationError("protected swing side must be canonical")
        for name, value in (("price", self.price), ("cisd_level", self.cisd_level)):
            if type(value) is not Decimal or not value.is_finite() or value <= 0:
                raise Vt08B01R38ValidationError(f"{name} must be positive Decimal")
        for name, value in (
            ("confirmed_at", self.confirmed_at),
            ("opposing_series_opened_at", self.opposing_series_opened_at),
        ):
            if (
                type(value) is not datetime
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise Vt08B01R38ValidationError(f"{name} must be timezone-aware")
        if self.confirmed_at <= self.opposing_series_opened_at:
            raise Vt08B01R38ValidationError(
                "CISD must confirm after the opposing series begins"
            )


@dataclass(frozen=True, slots=True)
class Vt08B01Candidate:
    symbol: str
    side: DemoTradingSetupSide
    decision_at: datetime
    entry_anchor_hour: int
    reference_h4: Vt08B01Bar
    candle2: Vt08B01Bar
    protected_swing: Vt08B01ProtectedSwing
    setup: DemoTradingSetupSpec
    methodology_fingerprint: str
    operational_containments: tuple[str, ...] = OPERATIONAL_CONTAINMENTS

    def __post_init__(self) -> None:
        if self.symbol not in AUTHORIZED_FOREX_MARKETS:
            raise Vt08B01R38ValidationError(
                "candidate market is outside R3.8 Forex subset"
            )
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt08B01R38ValidationError("candidate side must be canonical")
        if type(self.decision_at) is not datetime or self.decision_at.tzinfo is None:
            raise Vt08B01R38ValidationError("decision_at must be timezone-aware")
        if self.entry_anchor_hour not in OWNER_FOREX_ENTRY_ANCHORS:
            raise Vt08B01R38ValidationError(
                "candidate anchor is outside Owner subset"
            )
        if self.protected_swing.side is not self.side or self.setup.side is not self.side:
            raise Vt08B01R38ValidationError("candidate side evidence must agree")
        if self.candle2.closed_at.astimezone(UTC) != self.decision_at.astimezone(UTC):
            raise Vt08B01R38ValidationError(
                "decision must occur at Candle-2 close/new H4 open"
            )
        if (
            type(self.methodology_fingerprint) is not str
            or len(self.methodology_fingerprint) != 64
        ):
            raise Vt08B01R38ValidationError(
                "methodology fingerprint must be SHA-256"
            )


@dataclass(frozen=True, slots=True)
class Vt08B01Evaluation:
    candidate: Vt08B01Candidate | None
    abstain_reason: Vt08B01AbstainReason | None

    def __post_init__(self) -> None:
        if (self.candidate is None) == (self.abstain_reason is None):
            raise Vt08B01R38ValidationError(
                "evaluation must contain exactly one of candidate or abstain reason"
            )

    @property
    def is_setup(self) -> bool:
        return self.candidate is not None


def methodology_fingerprint() -> str:
    material = {
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "primary_source": PRIMARY_SOURCE,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "profile": "author-clarified",
        "authorized_forex_markets": AUTHORIZED_FOREX_MARKETS,
        "owner_forex_entry_anchors": OWNER_FOREX_ENTRY_ANCHORS,
        "source_forex_h4_anchors": SOURCE_FOREX_H4_ANCHORS,
        "bias": (
            "close>pdh-long;close<pdl-short;sweep-pdl-close-back-long;"
            "sweep-pdh-close-back-short;conflict-or-other-abstain"
        ),
        "scenario": "completed-candle2-reversal-relative-to-prior-h4",
        "cisd": "m15-close-through-first-opposing-series-open-after-reference-sweep",
        "ps_selection": "exactly-one-valid-protected-swing-else-abstain",
        "entry": "new-h4-open",
        "target": TARGET_POLICY,
        "daily_selection": DAILY_SELECTION_POLICY,
        "operational_containments": OPERATIONAL_CONTAINMENTS,
        "futures_14": "excluded-fundamentally-unresolved",
    }
    return sha256(
        json.dumps(
            material,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise Vt08B01R38ValidationError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _aggregate_window(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    opened_at_local: datetime,
    closed_at_local: datetime,
) -> Vt08B01Bar | None:
    if opened_at_local.tzinfo is None or closed_at_local.tzinfo is None:
        raise Vt08B01R38ValidationError("source windows must be timezone-aware")
    opened_at = opened_at_local.astimezone(UTC)
    closed_at = closed_at_local.astimezone(UTC)
    if closed_at <= opened_at:
        return None
    expected: list[Vt08B01Bar] = []
    cursor = opened_at
    while cursor < closed_at:
        bar = bars_by_open.get(cursor)
        if (
            bar is None
            or bar.closed_at.astimezone(UTC) != cursor + timedelta(minutes=15)
        ):
            return None
        expected.append(bar)
        cursor += timedelta(minutes=15)
    if cursor != closed_at or not expected:
        return None
    return Vt08B01Bar(
        opened_at=opened_at,
        closed_at=closed_at,
        open=expected[0].open,
        high=max(item.high for item in expected),
        low=min(item.low for item in expected),
        close=expected[-1].close,
    )


def source_h4_from_m15(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    opened_at_local: datetime,
) -> Vt08B01Bar | None:
    local = opened_at_local.astimezone(_NY)
    if local.minute != 0 or local.second != 0 or local.microsecond != 0:
        return None
    if local.hour not in SOURCE_FOREX_H4_ANCHORS:
        return None
    closed_local = local + timedelta(hours=4)
    if (
        closed_local.astimezone(UTC) - local.astimezone(UTC)
        != timedelta(hours=4)
    ):
        # DST-transition H4 construction is not silently invented.
        return None
    return _aggregate_window(
        bars_by_open,
        opened_at_local=local,
        closed_at_local=closed_local,
    )


def source_day_from_m15(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    end_date: date,
) -> Vt08B01Bar | None:
    end_local = datetime.combine(end_date, time(hour=17), tzinfo=_NY)
    start_local = datetime.combine(
        end_date - timedelta(days=1),
        time(hour=17),
        tzinfo=_NY,
    )
    return _aggregate_window(
        bars_by_open,
        opened_at_local=start_local,
        closed_at_local=end_local,
    )


def _latest_complete_source_days(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    before_local: datetime,
    count: int = 2,
) -> tuple[Vt08B01Bar, ...]:
    if count < 1:
        raise Vt08B01R38ValidationError("source-day count must be positive")
    if before_local.tzinfo is None or before_local.utcoffset() is None:
        raise Vt08B01R38ValidationError("before_local must be timezone-aware")
    end_date = before_local.astimezone(_NY).date() - timedelta(days=1)
    retained: list[Vt08B01Bar] = []
    for offset in range(10):
        candidate = source_day_from_m15(
            bars_by_open,
            end_date=end_date - timedelta(days=offset),
        )
        if candidate is not None:
            retained.append(candidate)
            if len(retained) == count:
                break
    return tuple(retained)


def resolve_bias(
    *,
    previous_day: Vt08B01Bar,
    current_day: Vt08B01Bar,
) -> DemoTradingSetupSide | None:
    if current_day.close > previous_day.high:
        return DemoTradingSetupSide.LONG
    if current_day.close < previous_day.low:
        return DemoTradingSetupSide.SHORT

    bullish_reversal = (
        current_day.low < previous_day.low
        and previous_day.low < current_day.close
    )
    bearish_reversal = (
        current_day.high > previous_day.high
        and current_day.close < previous_day.high
    )
    if bullish_reversal == bearish_reversal:
        return None
    return DemoTradingSetupSide.LONG if bullish_reversal else DemoTradingSetupSide.SHORT


def _candle2_reversal_side(
    reference: Vt08B01Bar,
    candle2: Vt08B01Bar,
) -> DemoTradingSetupSide | None:
    swept_high = candle2.high > reference.high
    swept_low = candle2.low < reference.low
    if swept_high == swept_low:
        return None
    if not reference.low < candle2.close < reference.high:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def protected_swings_in_candle2(
    bars: tuple[Vt08B01Bar, ...],
    *,
    side: DemoTradingSetupSide,
    important_level: Decimal,
) -> tuple[Vt08B01ProtectedSwing, ...]:
    if type(side) is not DemoTradingSetupSide:
        raise Vt08B01R38ValidationError("side must be canonical")
    if type(important_level) is not Decimal or not important_level.is_finite():
        raise Vt08B01R38ValidationError("important level must be finite Decimal")

    candidates: list[Vt08B01ProtectedSwing] = []
    series_open: Decimal | None = None
    series_opened_at: datetime | None = None
    series_extreme: Decimal | None = None

    def _opposing(bar: Vt08B01Bar) -> bool:
        if side is DemoTradingSetupSide.LONG:
            return bar.close < bar.open
        return bar.close > bar.open

    for bar in bars:
        if _opposing(bar):
            if series_open is None:
                series_open = bar.open
                series_opened_at = bar.opened_at
                series_extreme = (
                    bar.low if side is DemoTradingSetupSide.LONG else bar.high
                )
            else:
                assert series_extreme is not None
                series_extreme = (
                    min(series_extreme, bar.low)
                    if side is DemoTradingSetupSide.LONG
                    else max(series_extreme, bar.high)
                )
            continue

        if (
            series_open is not None
            and series_opened_at is not None
            and series_extreme is not None
        ):
            swept = (
                series_extreme < important_level
                if side is DemoTradingSetupSide.LONG
                else series_extreme > important_level
            )
            confirmed = (
                bar.close > series_open
                if side is DemoTradingSetupSide.LONG
                else bar.close < series_open
            )
            if swept and confirmed:
                candidates.append(
                    Vt08B01ProtectedSwing(
                        side=side,
                        price=series_extreme,
                        cisd_level=series_open,
                        confirmed_at=bar.closed_at,
                        opposing_series_opened_at=series_opened_at,
                    )
                )
        series_open = None
        series_opened_at = None
        series_extreme = None

    return tuple(candidates)


def _window_bars(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[Vt08B01Bar, ...] | None:
    start = _utc(opened_at)
    end = _utc(closed_at)
    retained: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=15)
    return tuple(retained) if cursor == end else None


def evaluate_b01_at_entry_indexed(
    *,
    symbol: str,
    bars_by_open: dict[datetime, Vt08B01Bar],
    decision_at: datetime,
) -> Vt08B01Evaluation:
    if symbol not in AUTHORIZED_FOREX_MARKETS:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.UNSUPPORTED_MARKET)

    decision_utc = _utc(decision_at)
    decision_local = decision_utc.astimezone(_NY)
    if (
        decision_local.minute != 0
        or decision_local.second != 0
        or decision_local.microsecond != 0
        or decision_local.hour not in OWNER_FOREX_ENTRY_ANCHORS
    ):
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.OUTSIDE_OWNER_ANCHOR)

    reference_local = decision_local - timedelta(hours=8)
    candle2_local = decision_local - timedelta(hours=4)
    reference = source_h4_from_m15(bars_by_open, opened_at_local=reference_local)
    candle2 = source_h4_from_m15(bars_by_open, opened_at_local=candle2_local)
    if reference is None or candle2 is None or candle2.closed_at != decision_utc:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.INCOMPLETE_SOURCE_H4)

    source_days = _latest_complete_source_days(
        bars_by_open,
        before_local=decision_local,
        count=2,
    )
    if len(source_days) != 2:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.INCOMPLETE_SOURCE_DAY)
    current_day, previous_day = source_days

    side = resolve_bias(previous_day=previous_day, current_day=current_day)
    if side is None:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.BIAS_UNRESOLVED)
    if _candle2_reversal_side(reference, candle2) is not side:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.C2_REVERSAL_MISMATCH)

    candle2_m15 = _window_bars(
        bars_by_open,
        opened_at=candle2.opened_at,
        closed_at=candle2.closed_at,
    )
    if candle2_m15 is None:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.INCOMPLETE_SOURCE_H4)

    important_level = (
        reference.low if side is DemoTradingSetupSide.LONG else reference.high
    )
    swings = protected_swings_in_candle2(
        candle2_m15,
        side=side,
        important_level=important_level,
    )
    if not swings:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.NO_PROTECTED_SWING)
    if len(swings) != 1:
        return Vt08B01Evaluation(
            None,
            Vt08B01AbstainReason.MULTIPLE_PROTECTED_SWINGS,
        )
    protected = swings[0]

    entry_bar = bars_by_open.get(decision_utc)
    if entry_bar is None:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.INCOMPLETE_SOURCE_H4)
    entry = entry_bar.open
    stop = protected.price
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.INVALID_RISK_GEOMETRY)
    target = (
        entry + Decimal(2) * risk
        if side is DemoTradingSetupSide.LONG
        else entry - Decimal(2) * risk
    )
    if target <= 0:
        return Vt08B01Evaluation(None, Vt08B01AbstainReason.INVALID_RISK_GEOMETRY)

    try:
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=entry,
            invalidation_price=stop,
            take_profit_price=target,
            entry_reason=(
                "vt08-r3.8-b01-positional-new-h4-open;"
                "exactly-one-protected-swing;"
                "operational-containment-stop-no-offset;"
                "operational-containment-conservative-initial-2r;"
                "operational-containment-h4-close-all"
            ),
        )
    except DemoTradingError as error:
        raise Vt08B01R38ValidationError("B01 setup geometry is invalid") from error

    return Vt08B01Evaluation(
        candidate=Vt08B01Candidate(
            symbol=symbol,
            side=side,
            decision_at=decision_utc,
            entry_anchor_hour=decision_local.hour,
            reference_h4=reference,
            candle2=candle2,
            protected_swing=protected,
            setup=setup,
            methodology_fingerprint=methodology_fingerprint(),
        ),
        abstain_reason=None,
    )


def evaluate_b01_at_entry(
    *,
    symbol: str,
    m15_bars: tuple[Vt08B01Bar, ...],
    decision_at: datetime,
) -> Vt08B01Evaluation:
    bars_by_open = {item.opened_at.astimezone(UTC): item for item in m15_bars}
    if len(bars_by_open) != len(m15_bars):
        raise Vt08B01R38ValidationError(
            "M15 evidence contains duplicate open timestamps"
        )
    return evaluate_b01_at_entry_indexed(
        symbol=symbol,
        bars_by_open=bars_by_open,
        decision_at=decision_at,
    )
