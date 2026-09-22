"""VT-08 Futures/index C2 positional-entry R1 research candidate.

The methodology was frozen before economic replay in
VT08-INDEX-C2-POSITIONAL-R1-FREEZE.md.  This module intentionally implements
only the completed-C2, M15-CISD, exactly-one-Protected-Swing subset.  It is
research-only and grants no DEMO/LIVE/production authority.
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
TRADER_VERSION = "index-c2-positional-r1"
METHODOLOGY_ID = "ttrades-h4-po3-index-c2-positional"
METHODOLOGY_VERSION = "r1-source-adjudicated-2026-09-13"
PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
OPERATING_TIMEZONE = "America/New_York"
_NY = ZoneInfo(OPERATING_TIMEZONE)

AUTHORIZED_MARKETS = ("NAS100", "SP500", "US30")
OWNER_ENTRY_ANCHORS_NY = (2, 6, 10)
SOURCE_FUTURES_H4_OPENS_NY = (2, 6, 10, 14)
SOURCE_DAILY_OPEN_HOUR_NY = 18
RECONSTRUCTION_ONLY_H4_HOUR_NY = 22
LTF_PROFILE = "M15"
SCENARIO_SCOPE = "completed-c2-only"
POI_FAMILY = "previous-h4-extreme"
TARGET_POLICY = "fixed-initial-2r-post-source-formalization"
DAILY_SELECTION_POLICY = "exactly-one-r1-candidate-per-market-ny-date-else-abstain"

OPERATIONAL_CONTAINMENTS = (
    "cfds-are-research-proxies-for-futures-structure",
    "18ny-source-day-reconstructed-as-92-available-m15-bars",
    "22ny-is-reconstruction-only-not-operational-entry-anchor",
    "c3-excluded-from-r1",
    "exactly-one-valid-protected-swing-else-abstain",
    "historical-fill-at-new-h4-open-broker-order-type-unspecified",
    "protected-swing-structural-level-no-stop-offset",
    "fixed-initial-2r-replay-target",
    "same-m15-bar-stop-first",
    "close-modeled-position-at-next-h4-boundary",
    "exactly-one-r1-candidate-per-market-ny-date-else-abstain",
)

SOURCE_REFS = (
    "ttrades:trading-the-4-hour-power-of-3:2025-09-20",
    "ttrades:important-time-levels:2025-07-19",
    "ttrades:understanding-cisd:2025-06-29",
    "ttrades:protected-swings:2025-08-06",
    "ttrades:cisd-confirms-swing-points:2026-01-10",
    "ttrades:positional-entries:2026-08-08",
    "ttrades:only-trading-strategy-2026:2026-01-03",
)


class Vt08IndexC2R1Error(InfrastructureError):
    __slots__ = ()


class Vt08IndexC2R1AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    OUTSIDE_OWNER_ANCHOR = "outside-owner-anchor"
    INCOMPLETE_SOURCE_DAYS = "incomplete-source-days"
    BIAS_UNRESOLVED = "bias-unresolved"
    INCOMPLETE_H4 = "incomplete-h4"
    C2_REVERSAL_MISMATCH = "c2-reversal-mismatch"
    NO_PROTECTED_SWING = "no-protected-swing"
    MULTIPLE_PROTECTED_SWINGS = "multiple-protected-swings"
    MISSING_ENTRY_OPEN = "missing-entry-open"
    INVALID_RISK_GEOMETRY = "invalid-risk-geometry"


@dataclass(frozen=True, slots=True)
class Vt08IndexC2R1Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        _require_aware(self.opened_at, name="opened_at")
        _require_aware(self.closed_at, name="closed_at")
        if self.closed_at <= self.opened_at:
            raise Vt08IndexC2R1Error("bar close must follow open")
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            _require_price(value, name=name)
        if self.low > self.high:
            raise Vt08IndexC2R1Error("bar low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise Vt08IndexC2R1Error("bar open must lie inside low/high")
        if not self.low <= self.close <= self.high:
            raise Vt08IndexC2R1Error("bar close must lie inside low/high")


@dataclass(frozen=True, slots=True)
class Vt08IndexC2R1ProtectedSwing:
    side: DemoTradingSetupSide
    price: Decimal
    cisd_level: Decimal
    confirmed_at: datetime
    opposing_series_opened_at: datetime

    def __post_init__(self) -> None:
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt08IndexC2R1Error("protected-swing side must be canonical")
        _require_price(self.price, name="protected_swing_price")
        _require_price(self.cisd_level, name="cisd_level")
        _require_aware(self.confirmed_at, name="confirmed_at")
        _require_aware(
            self.opposing_series_opened_at,
            name="opposing_series_opened_at",
        )
        if self.confirmed_at <= self.opposing_series_opened_at:
            raise Vt08IndexC2R1Error("protected swing must follow opposing series")


@dataclass(frozen=True, slots=True)
class Vt08IndexC2R1Candidate:
    symbol: str
    side: DemoTradingSetupSide
    decision_at: datetime
    entry_anchor_hour: int
    reference_h4: Vt08IndexC2R1Bar
    candle2: Vt08IndexC2R1Bar
    protected_swing: Vt08IndexC2R1ProtectedSwing
    setup: DemoTradingSetupSpec
    methodology_fingerprint: str

    def __post_init__(self) -> None:
        if self.symbol not in AUTHORIZED_MARKETS:
            raise Vt08IndexC2R1Error("candidate market is outside R1 scope")
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt08IndexC2R1Error("candidate side must be canonical")
        _require_aware(self.decision_at, name="decision_at")
        if self.entry_anchor_hour not in OWNER_ENTRY_ANCHORS_NY:
            raise Vt08IndexC2R1Error("candidate anchor is outside Owner subset")
        if self.protected_swing.side is not self.side:
            raise Vt08IndexC2R1Error("protected swing side drifted")
        if self.setup.side is not self.side:
            raise Vt08IndexC2R1Error("setup side drifted")
        if self.candle2.closed_at.astimezone(UTC) != self.decision_at.astimezone(UTC):
            raise Vt08IndexC2R1Error("decision must equal completed Candle-2 close")
        if len(self.methodology_fingerprint) != 64:
            raise Vt08IndexC2R1Error("methodology fingerprint must be SHA-256")


@dataclass(frozen=True, slots=True)
class Vt08IndexC2R1Evaluation:
    candidate: Vt08IndexC2R1Candidate | None
    abstain_reason: Vt08IndexC2R1AbstainReason | None

    def __post_init__(self) -> None:
        if (self.candidate is None) == (self.abstain_reason is None):
            raise Vt08IndexC2R1Error(
                "evaluation must contain exactly one candidate or abstain reason"
            )

    @property
    def is_setup(self) -> bool:
        return self.candidate is not None


def _require_aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise Vt08IndexC2R1Error(f"{name} must be timezone-aware")


def _require_price(value: Decimal, *, name: str) -> None:
    if not value.is_finite() or value <= 0:
        raise Vt08IndexC2R1Error(f"{name} must be a positive finite Decimal")


def _utc(value: datetime) -> datetime:
    _require_aware(value, name="timestamp")
    return value.astimezone(UTC)


def methodology_fingerprint() -> str:
    material = {
        "trader_code": TRADER_CODE,
        "trader_version": TRADER_VERSION,
        "methodology_id": METHODOLOGY_ID,
        "methodology_version": METHODOLOGY_VERSION,
        "primary_source": PRIMARY_SOURCE,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "operating_timezone": OPERATING_TIMEZONE,
        "authorized_markets": AUTHORIZED_MARKETS,
        "owner_entry_anchors_ny": OWNER_ENTRY_ANCHORS_NY,
        "source_futures_h4_opens_ny": SOURCE_FUTURES_H4_OPENS_NY,
        "source_daily_open_hour_ny": SOURCE_DAILY_OPEN_HOUR_NY,
        "reconstruction_only_h4_hour_ny": RECONSTRUCTION_ONLY_H4_HOUR_NY,
        "ltf_profile": LTF_PROFILE,
        "scenario_scope": SCENARIO_SCOPE,
        "poi_family": POI_FAMILY,
        "target_policy": TARGET_POLICY,
        "daily_selection_policy": DAILY_SELECTION_POLICY,
        "operational_containments": OPERATIONAL_CONTAINMENTS,
        "source_refs": SOURCE_REFS,
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


def _aggregate_contiguous_m15(
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    *,
    opened_at_local: datetime,
    count: int,
) -> Vt08IndexC2R1Bar | None:
    _require_aware(opened_at_local, name="opened_at_local")
    if count < 1:
        raise Vt08IndexC2R1Error("aggregate count must be positive")
    start = opened_at_local.astimezone(UTC)
    rows: list[Vt08IndexC2R1Bar] = []
    cursor = start
    for _ in range(count):
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at.astimezone(UTC) != cursor + timedelta(minutes=15):
            return None
        rows.append(bar)
        cursor += timedelta(minutes=15)
    return Vt08IndexC2R1Bar(
        opened_at=rows[0].opened_at,
        closed_at=rows[-1].closed_at,
        open=rows[0].open,
        high=max(item.high for item in rows),
        low=min(item.low for item in rows),
        close=rows[-1].close,
    )


def _source_day(
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    *,
    end_date: date,
) -> Vt08IndexC2R1Bar | None:
    start_local = datetime.combine(
        end_date - timedelta(days=1),
        time(hour=SOURCE_DAILY_OPEN_HOUR_NY),
        tzinfo=_NY,
    )
    day = _aggregate_contiguous_m15(
        bars_by_open,
        opened_at_local=start_local,
        count=92,
    )
    if day is None:
        return None
    expected_close_local = datetime.combine(
        end_date,
        time(hour=17),
        tzinfo=_NY,
    )
    if day.closed_at.astimezone(UTC) != expected_close_local.astimezone(UTC):
        return None
    return day


def _latest_complete_source_days(
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    *,
    before_local: datetime,
) -> tuple[Vt08IndexC2R1Bar, Vt08IndexC2R1Bar] | None:
    _require_aware(before_local, name="before_local")
    end_date = before_local.astimezone(_NY).date() - timedelta(days=1)
    retained: list[Vt08IndexC2R1Bar] = []
    for offset in range(14):
        candidate = _source_day(bars_by_open, end_date=end_date - timedelta(days=offset))
        if candidate is not None:
            retained.append(candidate)
            if len(retained) == 2:
                current_day, previous_day = retained
                return previous_day, current_day
    return None


def resolve_daily_bias(
    *,
    previous_day: Vt08IndexC2R1Bar,
    current_day: Vt08IndexC2R1Bar,
) -> DemoTradingSetupSide | None:
    if current_day.close > previous_day.high:
        return DemoTradingSetupSide.LONG
    if current_day.close < previous_day.low:
        return DemoTradingSetupSide.SHORT

    bullish_reversal = (
        current_day.low < previous_day.low and current_day.close > previous_day.low
    )
    bearish_reversal = (
        current_day.high > previous_day.high and current_day.close < previous_day.high
    )
    if bullish_reversal == bearish_reversal:
        return None
    return DemoTradingSetupSide.LONG if bullish_reversal else DemoTradingSetupSide.SHORT


def _c2_reversal_side(
    reference: Vt08IndexC2R1Bar,
    candle2: Vt08IndexC2R1Bar,
) -> DemoTradingSetupSide | None:
    swept_high = candle2.high > reference.high
    swept_low = candle2.low < reference.low
    if swept_high == swept_low:
        return None
    if not reference.low < candle2.close < reference.high:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def _window_bars(
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    *,
    opened_at: datetime,
    count: int,
) -> tuple[Vt08IndexC2R1Bar, ...] | None:
    start = _utc(opened_at)
    rows: list[Vt08IndexC2R1Bar] = []
    cursor = start
    for _ in range(count):
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at.astimezone(UTC) != cursor + timedelta(minutes=15):
            return None
        rows.append(bar)
        cursor += timedelta(minutes=15)
    return tuple(rows)


def protected_swings_in_candle2(
    bars: tuple[Vt08IndexC2R1Bar, ...],
    *,
    side: DemoTradingSetupSide,
    important_level: Decimal,
) -> tuple[Vt08IndexC2R1ProtectedSwing, ...]:
    _require_price(important_level, name="important_level")
    candidates: list[Vt08IndexC2R1ProtectedSwing] = []
    series_open: Decimal | None = None
    series_opened_at: datetime | None = None
    series_extreme: Decimal | None = None

    def opposing(bar: Vt08IndexC2R1Bar) -> bool:
        if side is DemoTradingSetupSide.LONG:
            return bar.close < bar.open
        return bar.close > bar.open

    for bar in bars:
        if opposing(bar):
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
                    Vt08IndexC2R1ProtectedSwing(
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


def evaluate_at_entry_indexed(
    *,
    symbol: str,
    bars_by_open: dict[datetime, Vt08IndexC2R1Bar],
    decision_at: datetime,
) -> Vt08IndexC2R1Evaluation:
    if symbol not in AUTHORIZED_MARKETS:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.UNSUPPORTED_MARKET,
        )

    decision_utc = _utc(decision_at)
    decision_local = decision_utc.astimezone(_NY)
    if (
        decision_local.minute != 0
        or decision_local.second != 0
        or decision_local.microsecond != 0
        or decision_local.hour not in OWNER_ENTRY_ANCHORS_NY
    ):
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.OUTSIDE_OWNER_ANCHOR,
        )

    source_days = _latest_complete_source_days(
        bars_by_open,
        before_local=decision_local,
    )
    if source_days is None:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.INCOMPLETE_SOURCE_DAYS,
        )
    previous_day, current_day = source_days
    side = resolve_daily_bias(previous_day=previous_day, current_day=current_day)
    if side is None:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.BIAS_UNRESOLVED,
        )

    reference_local = decision_local - timedelta(hours=8)
    candle2_local = decision_local - timedelta(hours=4)
    reference = _aggregate_contiguous_m15(
        bars_by_open,
        opened_at_local=reference_local,
        count=16,
    )
    candle2 = _aggregate_contiguous_m15(
        bars_by_open,
        opened_at_local=candle2_local,
        count=16,
    )
    if reference is None or candle2 is None:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.INCOMPLETE_H4,
        )
    if candle2.closed_at.astimezone(UTC) != decision_utc:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.INCOMPLETE_H4,
        )
    if _c2_reversal_side(reference, candle2) is not side:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.C2_REVERSAL_MISMATCH,
        )

    candle2_m15 = _window_bars(
        bars_by_open,
        opened_at=candle2.opened_at,
        count=16,
    )
    if candle2_m15 is None:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.INCOMPLETE_H4,
        )
    important_level = (
        reference.low if side is DemoTradingSetupSide.LONG else reference.high
    )
    swings = protected_swings_in_candle2(
        candle2_m15,
        side=side,
        important_level=important_level,
    )
    if not swings:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.NO_PROTECTED_SWING,
        )
    if len(swings) != 1:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.MULTIPLE_PROTECTED_SWINGS,
        )
    protected = swings[0]

    entry_bar = bars_by_open.get(decision_utc)
    if entry_bar is None:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.MISSING_ENTRY_OPEN,
        )
    entry = entry_bar.open
    stop = protected.price
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.INVALID_RISK_GEOMETRY,
        )
    target = (
        entry + Decimal(2) * risk
        if side is DemoTradingSetupSide.LONG
        else entry - Decimal(2) * risk
    )
    if target <= 0:
        return Vt08IndexC2R1Evaluation(
            None,
            Vt08IndexC2R1AbstainReason.INVALID_RISK_GEOMETRY,
        )

    try:
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=entry,
            invalidation_price=stop,
            take_profit_price=target,
            entry_reason=(
                "vt08-index-c2-positional-r1;completed-c2;daily-bias;"
                "m15-cisd;exactly-one-protected-swing;new-h4-open;"
                "zero-stop-offset-containment;fixed-2r-replay-containment"
            ),
        )
    except DemoTradingError as error:
        raise Vt08IndexC2R1Error("R1 setup geometry is invalid") from error

    return Vt08IndexC2R1Evaluation(
        candidate=Vt08IndexC2R1Candidate(
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


def evaluate_at_entry(
    *,
    symbol: str,
    m15_bars: tuple[Vt08IndexC2R1Bar, ...],
    decision_at: datetime,
) -> Vt08IndexC2R1Evaluation:
    bars_by_open = {item.opened_at.astimezone(UTC): item for item in m15_bars}
    if len(bars_by_open) != len(m15_bars):
        raise Vt08IndexC2R1Error("M15 evidence contains duplicate open timestamps")
    return evaluate_at_entry_indexed(
        symbol=symbol,
        bars_by_open=bars_by_open,
        decision_at=decision_at,
    )
