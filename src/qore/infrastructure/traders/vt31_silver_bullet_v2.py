"""Source-bound VT-31 Silver Bullet AM research candidate.

This module intentionally does not replace :class:`Vt31SilverBullet` V1.  It
implements the source-confirmed AM framework reconstructed from the Human
Owner-provided TTrades video ``youtube:o0v4KQxZbpU`` and keeps discretionary
entry choices explicit and versioned.

Authority boundary:

``CANONICAL M1 EVIDENCE -> VT-31 V2 RESEARCH EVALUATION -> SETUP/ABSTAIN``

The evaluator creates no quantity, account, Risk, broker, DEMO, LIVE or
real-capital authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.kernel.errors import InfrastructureError

_NY = ZoneInfo("America/New_York")
_M1_SECONDS = 60
_SOURCE_VIDEO_ID = "youtube:o0v4KQxZbpU"
_TRADER_CODE = "vt-31"
_TRADER_VERSION = "v2"
_METHODOLOGY_ID = "silver-bullet-am-nq"
_METHODOLOGY_VERSION = "v2"
_SUPPORTED_SYMBOLS = frozenset({"NAS100"})

_RULESET = (
    "source-video:o0v4KQxZbpU;nas100-only;new-york-10:00-11:00-entry-window;"
    "frozen-09:00-10:00-m1-derived-hour-range;strict-range-side-raid;"
    "m1-post-raid-structure-shift;post-confirmation-fvg;fvg-consequent-encroachment-entry;"
    "stop-at-raid-extreme;target-opposite-09:00-hour-range;unfilled-entry-expires-11:00"
)


class Vt31SilverBulletV2Error(InfrastructureError):
    """Base error for VT-31 V2 source-bound research evaluation."""

    __slots__ = ()


class Vt31SilverBulletV2ValidationError(Vt31SilverBulletV2Error):
    """Input or invariant violation for VT-31 V2."""

    __slots__ = ()


class Vt31SilverBulletV2EntryModel(StrEnum):
    """Source-demonstrated entry model made explicit as configuration."""

    FVG_CONSEQUENT_ENCROACHMENT = "fvg-consequent-encroachment"


class Vt31SilverBulletV2AbstainReason(StrEnum):
    """Explicit fail-closed reasons for source-bound VT-31 V2 research."""

    UNSUPPORTED_METHOD_MARKET = "unsupported-method-market"
    WINDOW_CLOSED = "window-closed"
    REFERENCE_RANGE_MISSING = "reference-range-missing"
    NO_RAID = "no-raid"
    AMBIGUOUS_RAID = "ambiguous-raid"
    NO_POST_RAID_STRUCTURE_SHIFT = "no-post-raid-structure-shift"
    NO_POST_CONFIRMATION_FVG = "no-post-confirmation-fvg"
    INVALID_GEOMETRY = "invalid-geometry"


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Config:
    """Exact research configuration; no hidden discretionary entry selection."""

    entry_model: Vt31SilverBulletV2EntryModel = (
        Vt31SilverBulletV2EntryModel.FVG_CONSEQUENT_ENCROACHMENT
    )

    def __post_init__(self) -> None:
        if type(self.entry_model) is not Vt31SilverBulletV2EntryModel:
            raise Vt31SilverBulletV2ValidationError(
                "entry_model must be exact Vt31SilverBulletV2EntryModel"
            )

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.trader.vt31.silver-bullet-v2.config.v1",
            "entry_model": self.entry_model.value,
        }
        return _digest(payload)


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Input:
    """Canonical M1 evidence visible at one explicit evaluation instant."""

    instrument: Instrument
    as_of: datetime
    m1_candles: tuple[OhlcSnapshot, ...]

    def __post_init__(self) -> None:
        if type(self.instrument) is not Instrument:
            raise Vt31SilverBulletV2ValidationError("instrument must be exact Instrument")
        self.instrument.__post_init__()
        _require_aware(self.as_of, field_name="as_of")
        if type(self.m1_candles) is not tuple or any(
            type(item) is not OhlcSnapshot for item in self.m1_candles
        ):
            raise Vt31SilverBulletV2ValidationError(
                "m1_candles must be an immutable OhlcSnapshot tuple"
            )
        previous: OhlcSnapshot | None = None
        identities: set[tuple[datetime, datetime]] = set()
        for candle in self.m1_candles:
            candle.__post_init__()
            if candle.instrument != self.instrument:
                raise Vt31SilverBulletV2ValidationError(
                    "all VT-31 V2 evidence must bind the exact input instrument"
                )
            if candle.timeframe.seconds != _M1_SECONDS:
                raise Vt31SilverBulletV2ValidationError("VT-31 V2 requires exact M1 evidence")
            if candle.closed_at > self.as_of:
                raise Vt31SilverBulletV2ValidationError(
                    "future or still-open M1 candle is not admissible"
                )
            identity = (candle.opened_at.astimezone(UTC), candle.closed_at.astimezone(UTC))
            if identity in identities:
                raise Vt31SilverBulletV2ValidationError("duplicate M1 candle is not admissible")
            identities.add(identity)
            if previous is not None and candle.opened_at < previous.opened_at:
                raise Vt31SilverBulletV2ValidationError(
                    "VT-31 V2 M1 evidence must be chronological"
                )
            previous = candle


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2ReferenceRange:
    """Frozen 09:00-10:00 New York range derived from exactly sixty M1 bars."""

    high: Decimal
    low: Decimal
    opened_at: datetime
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Setup:
    """One source-bound research setup, not an order or Risk authorization."""

    side: DemoTradingSetupSide
    entry_price: Decimal
    invalidation_price: Decimal
    take_profit_price: Decimal
    reference_range: Vt31SilverBulletV2ReferenceRange
    raid_at: datetime
    confirmation_at: datetime
    entry_model: Vt31SilverBulletV2EntryModel
    expires_at: datetime

    def __post_init__(self) -> None:
        for price_field_name, price_value in (
            ("entry_price", self.entry_price),
            ("invalidation_price", self.invalidation_price),
            ("take_profit_price", self.take_profit_price),
        ):
            if (
                type(price_value) is not Decimal
                or not price_value.is_finite()
                or price_value <= 0
            ):
                raise Vt31SilverBulletV2ValidationError(
                    f"{price_field_name} must be positive finite Decimal"
                )
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt31SilverBulletV2ValidationError("setup side must be canonical")
        if type(self.reference_range) is not Vt31SilverBulletV2ReferenceRange:
            raise Vt31SilverBulletV2ValidationError("reference_range must be exact")
        if type(self.entry_model) is not Vt31SilverBulletV2EntryModel:
            raise Vt31SilverBulletV2ValidationError("entry_model must be exact")
        for timestamp_field_name, timestamp_value in (
            ("raid_at", self.raid_at),
            ("confirmation_at", self.confirmation_at),
            ("expires_at", self.expires_at),
        ):
            _require_aware(timestamp_value, field_name=timestamp_field_name)
        if self.confirmation_at < self.raid_at:
            raise Vt31SilverBulletV2ValidationError(
                "confirmation must not precede the range raid"
            )
        if self.side is DemoTradingSetupSide.SHORT:
            valid = self.take_profit_price < self.entry_price < self.invalidation_price
        else:
            valid = self.invalidation_price < self.entry_price < self.take_profit_price
        if not valid:
            raise Vt31SilverBulletV2ValidationError(
                "setup geometry must point from entry toward opposite range boundary"
            )


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Evaluation:
    """Deterministic VT-31 V2 research decision with frozen provenance identity."""

    decision: DemoTradingDecision
    instrument: Instrument
    evaluated_at: datetime
    config_fingerprint: str
    methodology_fingerprint: str
    setup: Vt31SilverBulletV2Setup | None
    abstain_reason: Vt31SilverBulletV2AbstainReason | None

    def __post_init__(self) -> None:
        if type(self.decision) is not DemoTradingDecision:
            raise Vt31SilverBulletV2ValidationError("decision must be canonical")
        if type(self.instrument) is not Instrument:
            raise Vt31SilverBulletV2ValidationError("instrument must be exact Instrument")
        _require_aware(self.evaluated_at, field_name="evaluated_at")
        for field_name, value in (
            ("config_fingerprint", self.config_fingerprint),
            ("methodology_fingerprint", self.methodology_fingerprint),
        ):
            if type(value) is not str or len(value) != 64 or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise Vt31SilverBulletV2ValidationError(
                    f"{field_name} must be lowercase SHA-256"
                )
        if self.decision is DemoTradingDecision.SETUP:
            if self.setup is None or self.abstain_reason is not None:
                raise Vt31SilverBulletV2ValidationError(
                    "SETUP requires setup and prohibits abstain_reason"
                )
        elif self.setup is not None or self.abstain_reason is None:
            raise Vt31SilverBulletV2ValidationError(
                "ABSTAIN requires reason and prohibits setup"
            )


@dataclass(frozen=True, slots=True)
class _Fvg:
    lower: Decimal
    upper: Decimal
    formed_at: datetime


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _methodology_fingerprint(config: Vt31SilverBulletV2Config) -> str:
    return _digest(
        {
            "schema": "qore.trader.vt31.silver-bullet-v2.methodology.v1",
            "trader_code": _TRADER_CODE,
            "trader_version": _TRADER_VERSION,
            "methodology_id": _METHODOLOGY_ID,
            "methodology_version": _METHODOLOGY_VERSION,
            "source_video": _SOURCE_VIDEO_ID,
            "ruleset": _RULESET,
            "entry_model": config.entry_model.value,
        }
    )


def _require_aware(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise Vt31SilverBulletV2ValidationError(f"{field_name} must be timezone-aware")


def _price(value: float) -> Decimal:
    return Decimal(str(value))


def _ny_wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _inside_am_window(value: datetime) -> bool:
    wall = _ny_wall(value)
    return (10, 0, 0) <= wall < (11, 0, 0)


def _window_close(as_of: datetime) -> datetime:
    local = as_of.astimezone(_NY)
    close = datetime.combine(local.date(), time(11, 0), tzinfo=_NY)
    return close.astimezone(UTC)


def _same_ny_date(value: datetime, as_of: datetime) -> bool:
    return value.astimezone(_NY).date() == as_of.astimezone(_NY).date()


def _reference_range(inputs: Vt31SilverBulletV2Input) -> Vt31SilverBulletV2ReferenceRange | None:
    bars = tuple(
        item
        for item in inputs.m1_candles
        if _same_ny_date(item.opened_at, inputs.as_of)
        and (9, 0, 0) <= _ny_wall(item.opened_at) < (10, 0, 0)
    )
    if len(bars) != 60:
        return None
    for previous, current in zip(bars, bars[1:], strict=False):
        if current.opened_at.astimezone(UTC) != previous.closed_at.astimezone(UTC):
            return None
    if _ny_wall(bars[0].opened_at) != (9, 0, 0):
        return None
    if _ny_wall(bars[-1].closed_at) != (10, 0, 0):
        return None
    return Vt31SilverBulletV2ReferenceRange(
        high=max((_price(item.high) for item in bars), key=lambda value: value),
        low=min((_price(item.low) for item in bars), key=lambda value: value),
        opened_at=bars[0].opened_at.astimezone(UTC),
        closed_at=bars[-1].closed_at.astimezone(UTC),
    )


def _am_bars(inputs: Vt31SilverBulletV2Input) -> tuple[OhlcSnapshot, ...]:
    return tuple(
        item
        for item in inputs.m1_candles
        if _same_ny_date(item.opened_at, inputs.as_of)
        and _inside_am_window(item.opened_at)
        and item.closed_at <= inputs.as_of
    )


def _raid(
    bars: tuple[OhlcSnapshot, ...],
    reference: Vt31SilverBulletV2ReferenceRange,
) -> tuple[int, DemoTradingSetupSide, Decimal] | None:
    for index, bar in enumerate(bars):
        high_raid = _price(bar.high) > reference.high
        low_raid = _price(bar.low) < reference.low
        if high_raid and low_raid:
            return index, DemoTradingSetupSide.SHORT, Decimal("NaN")
        if high_raid:
            return index, DemoTradingSetupSide.SHORT, _price(bar.high)
        if low_raid:
            return index, DemoTradingSetupSide.LONG, _price(bar.low)
    return None


def _structure_shift(
    bars: tuple[OhlcSnapshot, ...],
    *,
    raid_index: int,
    side: DemoTradingSetupSide,
) -> tuple[int, Decimal] | None:
    """Operationalize the video's 'low/high that made the new extreme' close rule.

    For a short, every post-raid new high updates the structural anchor to that
    candle's low. A later close below that low confirms the shift. Long is the
    exact mirror. This preserves chronological, post-raid causality and does not
    reuse a pre-raid structure signal.
    """

    extreme_bar = bars[raid_index]
    if side is DemoTradingSetupSide.SHORT:
        extreme = _price(extreme_bar.high)
        anchor = _price(extreme_bar.low)
        for index in range(raid_index + 1, len(bars)):
            bar = bars[index]
            if _price(bar.high) > extreme:
                extreme = _price(bar.high)
                anchor = _price(bar.low)
                continue
            if _price(bar.close) < anchor:
                return index, extreme
        return None

    extreme = _price(extreme_bar.low)
    anchor = _price(extreme_bar.high)
    for index in range(raid_index + 1, len(bars)):
        bar = bars[index]
        if _price(bar.low) < extreme:
            extreme = _price(bar.low)
            anchor = _price(bar.high)
            continue
        if _price(bar.close) > anchor:
            return index, extreme
    return None


def _post_confirmation_fvg(
    bars: tuple[OhlcSnapshot, ...],
    *,
    side: DemoTradingSetupSide,
    confirmation_index: int,
) -> _Fvg | None:
    start = max(2, confirmation_index)
    for third_index in range(start, len(bars)):
        first = bars[third_index - 2]
        third = bars[third_index]
        if side is DemoTradingSetupSide.SHORT and _price(third.high) < _price(first.low):
            return _Fvg(
                lower=_price(third.high),
                upper=_price(first.low),
                formed_at=third.closed_at.astimezone(UTC),
            )
        if side is DemoTradingSetupSide.LONG and _price(third.low) > _price(first.high):
            return _Fvg(
                lower=_price(first.high),
                upper=_price(third.low),
                formed_at=third.closed_at.astimezone(UTC),
            )
    return None


def _abstain(
    inputs: Vt31SilverBulletV2Input,
    config: Vt31SilverBulletV2Config,
    reason: Vt31SilverBulletV2AbstainReason,
) -> Vt31SilverBulletV2Evaluation:
    return Vt31SilverBulletV2Evaluation(
        decision=DemoTradingDecision.ABSTAIN,
        instrument=inputs.instrument,
        evaluated_at=inputs.as_of.astimezone(UTC),
        config_fingerprint=config.fingerprint(),
        methodology_fingerprint=_methodology_fingerprint(config),
        setup=None,
        abstain_reason=reason,
    )


def evaluate_vt31_silver_bullet_v2(
    inputs: Vt31SilverBulletV2Input,
    config: Vt31SilverBulletV2Config | None = None,
) -> Vt31SilverBulletV2Evaluation:
    """Evaluate the source-bound AM Silver Bullet V2 candidate fail-closed."""

    if type(inputs) is not Vt31SilverBulletV2Input:
        raise Vt31SilverBulletV2ValidationError(
            "VT-31 V2 requires exact Vt31SilverBulletV2Input"
        )
    inputs.__post_init__()
    selected = Vt31SilverBulletV2Config() if config is None else config
    if type(selected) is not Vt31SilverBulletV2Config:
        raise Vt31SilverBulletV2ValidationError(
            "VT-31 V2 config must be exact Vt31SilverBulletV2Config"
        )
    selected.__post_init__()

    if inputs.instrument.symbol not in _SUPPORTED_SYMBOLS:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.UNSUPPORTED_METHOD_MARKET,
        )
    if not _inside_am_window(inputs.as_of):
        return _abstain(inputs, selected, Vt31SilverBulletV2AbstainReason.WINDOW_CLOSED)

    reference = _reference_range(inputs)
    if reference is None:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.REFERENCE_RANGE_MISSING,
        )
    bars = _am_bars(inputs)
    raid = _raid(bars, reference)
    if raid is None:
        return _abstain(inputs, selected, Vt31SilverBulletV2AbstainReason.NO_RAID)
    raid_index, side, initial_extreme = raid
    if not initial_extreme.is_finite():
        return _abstain(inputs, selected, Vt31SilverBulletV2AbstainReason.AMBIGUOUS_RAID)

    shifted = _structure_shift(bars, raid_index=raid_index, side=side)
    if shifted is None:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.NO_POST_RAID_STRUCTURE_SHIFT,
        )
    confirmation_index, raid_extreme = shifted
    fvg = _post_confirmation_fvg(
        bars,
        side=side,
        confirmation_index=confirmation_index,
    )
    if fvg is None:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.NO_POST_CONFIRMATION_FVG,
        )

    entry = (fvg.lower + fvg.upper) / Decimal(2)
    target = reference.low if side is DemoTradingSetupSide.SHORT else reference.high
    try:
        setup = Vt31SilverBulletV2Setup(
            side=side,
            entry_price=entry,
            invalidation_price=raid_extreme,
            take_profit_price=target,
            reference_range=reference,
            raid_at=bars[raid_index].closed_at.astimezone(UTC),
            confirmation_at=bars[confirmation_index].closed_at.astimezone(UTC),
            entry_model=selected.entry_model,
            expires_at=_window_close(inputs.as_of),
        )
    except Vt31SilverBulletV2ValidationError:
        return _abstain(inputs, selected, Vt31SilverBulletV2AbstainReason.INVALID_GEOMETRY)

    return Vt31SilverBulletV2Evaluation(
        decision=DemoTradingDecision.SETUP,
        instrument=inputs.instrument,
        evaluated_at=inputs.as_of.astimezone(UTC),
        config_fingerprint=selected.fingerprint(),
        methodology_fingerprint=_methodology_fingerprint(selected),
        setup=setup,
        abstain_reason=None,
    )
