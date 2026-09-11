"""Source-bound VT-31 AM Silver Bullet research candidate.

The source authority is the Human Owner-provided TTrades video. VT-31 V1 is
preserved as historical evidence; this module is V2 and grants no Risk, broker,
DEMO, LIVE, or real-capital authority.
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
_SOURCE_FILE_NAME = "1000856441.mp4"
_SOURCE_FILE_SHA256 = "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
_TRADER_CODE = "vt-31"
_TRADER_VERSION = "v2"
_METHODOLOGY_ID = "silver-bullet-am-nq"
_METHODOLOGY_VERSION = "v2.1-source-complete"
_SUPPORTED_SYMBOLS = frozenset({"NAS100"})

_RULESET = (
    "source-video:o0v4KQxZbpU;source-file-sha256:bd729056fadc30d20045e4677240b3a6"
    "cbb65123ced317e7413b6ffe81936ddf;nas100-only;no-daily-bias;"
    "new-york-10:00-11:00-entry-window;frozen-09:00-10:00-hour-range;"
    "strict-range-side-raid;m1-post-raid-structural-close;"
    "breaker-block-order-block-fair-value-gap-entry-family;"
    "no-hidden-entry-model-priority;limit-entry;stop-at-methodological-swing-extreme;"
    "target-opposite-09:00-hour-range;unfilled-entry-expires-11:00;"
    "position-may-survive-11:00;research-lifecycle-3r-to-breakeven"
)


class Vt31SilverBulletV2Error(InfrastructureError):
    """Base error for VT-31 V2 source-bound research evaluation."""

    __slots__ = ()


class Vt31SilverBulletV2ValidationError(Vt31SilverBulletV2Error):
    """Input or invariant violation for VT-31 V2."""

    __slots__ = ()


class Vt31SilverBulletV2EntryModel(StrEnum):
    """Entry families repeatedly demonstrated in the source video."""

    BREAKER_BLOCK = "breaker-block"
    ORDER_BLOCK = "order-block"
    FAIR_VALUE_GAP = "fair-value-gap"
    # Compatibility alias for the earlier incomplete V2 research adapter.
    FVG_CONSEQUENT_ENCROACHMENT = "fair-value-gap"


class Vt31SilverBulletV2ConfluencePolicy(StrEnum):
    """Versioned containment for source-ambiguous simultaneous entry families."""

    FAIL_CLOSED_NON_EQUIVALENT = "fail-closed-non-equivalent-v1"


class Vt31SilverBulletV2AbstainReason(StrEnum):
    """Stable fail-closed reasons for source-bound VT-31 V2 research."""

    UNSUPPORTED_METHOD_MARKET = "unsupported-method-market"
    WINDOW_CLOSED = "window-closed"
    REFERENCE_RANGE_MISSING = "reference-range-missing"
    NO_RAID = "no-raid"
    AMBIGUOUS_RAID = "ambiguous-raid"
    NO_POST_RAID_STRUCTURE_SHIFT = "no-post-raid-structure-shift"
    NO_VALID_ENTRY_MODEL = "no-valid-entry-model"
    AMBIGUOUS_ENTRY_MODEL_CONFLUENCE = "ambiguous-entry-model-confluence"
    INVALID_GEOMETRY = "invalid-geometry"


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Config:
    """Research configuration with no hidden model priority or bias input."""

    preferred_entry_model: Vt31SilverBulletV2EntryModel | None = None
    confluence_policy: Vt31SilverBulletV2ConfluencePolicy = (
        Vt31SilverBulletV2ConfluencePolicy.FAIL_CLOSED_NON_EQUIVALENT
    )

    def __post_init__(self) -> None:
        if self.preferred_entry_model is not None and type(self.preferred_entry_model) is not (
            Vt31SilverBulletV2EntryModel
        ):
            raise Vt31SilverBulletV2ValidationError(
                "preferred_entry_model must be exact Vt31SilverBulletV2EntryModel or None"
            )
        if type(self.confluence_policy) is not Vt31SilverBulletV2ConfluencePolicy:
            raise Vt31SilverBulletV2ValidationError(
                "confluence_policy must be exact Vt31SilverBulletV2ConfluencePolicy"
            )

    def fingerprint(self) -> str:
        payload = {
            "schema": "qore.trader.vt31.silver-bullet-v2.config.v2",
            "preferred_entry_model": (
                self.preferred_entry_model.value
                if self.preferred_entry_model is not None
                else None
            ),
            "confluence_policy": self.confluence_policy.value,
            "structural_confirmation_formalization": "structural-close-v1",
            "block_entry_price_formalization": "body-midpoint-v1",
            "fvg_entry_price_formalization": "consequent-encroachment-v1",
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
    """One source-bound research setup, never a broker order or Risk authorization."""

    side: DemoTradingSetupSide
    entry_price: Decimal
    methodological_stop_extreme: Decimal
    technical_stop_buffer: Decimal
    invalidation_price: Decimal
    take_profit_price: Decimal
    reference_range: Vt31SilverBulletV2ReferenceRange
    raid_at: datetime
    confirmation_at: datetime
    decision_at: datetime
    entry_model: Vt31SilverBulletV2EntryModel
    entry_models: tuple[Vt31SilverBulletV2EntryModel, ...]
    entry_zone_lower: Decimal
    entry_zone_upper: Decimal
    entry_price_formalization: str
    expires_at: datetime
    source_video: str
    source_timestamps: tuple[str, ...]

    def __post_init__(self) -> None:
        for price_field_name, price_value in (
            ("entry_price", self.entry_price),
            ("methodological_stop_extreme", self.methodological_stop_extreme),
            ("invalidation_price", self.invalidation_price),
            ("take_profit_price", self.take_profit_price),
            ("entry_zone_lower", self.entry_zone_lower),
            ("entry_zone_upper", self.entry_zone_upper),
        ):
            if (
                type(price_value) is not Decimal
                or not price_value.is_finite()
                or price_value <= 0
            ):
                raise Vt31SilverBulletV2ValidationError(
                    f"{price_field_name} must be positive finite Decimal"
                )
        if (
            type(self.technical_stop_buffer) is not Decimal
            or not self.technical_stop_buffer.is_finite()
            or self.technical_stop_buffer < 0
        ):
            raise Vt31SilverBulletV2ValidationError(
                "technical_stop_buffer must be non-negative finite Decimal"
            )
        if self.technical_stop_buffer != 0:
            raise Vt31SilverBulletV2ValidationError(
                "source-bound Trader may not invent a non-zero broker stop buffer"
            )
        if self.invalidation_price != self.methodological_stop_extreme:
            raise Vt31SilverBulletV2ValidationError(
                "source-bound stop must equal methodological swing extreme "
                "before broker normalization"
            )
        if type(self.side) is not DemoTradingSetupSide:
            raise Vt31SilverBulletV2ValidationError("setup side must be canonical")
        if type(self.reference_range) is not Vt31SilverBulletV2ReferenceRange:
            raise Vt31SilverBulletV2ValidationError("reference_range must be exact")
        if type(self.entry_model) is not Vt31SilverBulletV2EntryModel:
            raise Vt31SilverBulletV2ValidationError("entry_model must be exact")
        if (
            type(self.entry_models) is not tuple
            or not self.entry_models
            or any(type(item) is not Vt31SilverBulletV2EntryModel for item in self.entry_models)
            or len(set(self.entry_models)) != len(self.entry_models)
            or self.entry_model not in self.entry_models
        ):
            raise Vt31SilverBulletV2ValidationError(
                "entry_models must be unique exact models containing entry_model"
            )
        if self.entry_zone_lower > self.entry_zone_upper:
            raise Vt31SilverBulletV2ValidationError("entry zone must be ordered")
        if not self.entry_zone_lower <= self.entry_price <= self.entry_zone_upper:
            raise Vt31SilverBulletV2ValidationError("entry price must lie inside entry zone")
        if type(self.entry_price_formalization) is not str or not self.entry_price_formalization:
            raise Vt31SilverBulletV2ValidationError(
                "entry_price_formalization must be non-empty"
            )
        for timestamp_field_name, timestamp_value in (
            ("raid_at", self.raid_at),
            ("confirmation_at", self.confirmation_at),
            ("decision_at", self.decision_at),
            ("expires_at", self.expires_at),
        ):
            _require_aware(timestamp_value, field_name=timestamp_field_name)
        if not self.raid_at <= self.confirmation_at <= self.decision_at:
            raise Vt31SilverBulletV2ValidationError(
                "raid, confirmation and decision timestamps must be causal"
            )
        if self.decision_at >= self.expires_at:
            raise Vt31SilverBulletV2ValidationError("decision must precede 11:00 expiry")
        if type(self.source_video) is not str or self.source_video != _SOURCE_VIDEO_ID:
            raise Vt31SilverBulletV2ValidationError("setup must bind exact source video")
        if (
            type(self.source_timestamps) is not tuple
            or not self.source_timestamps
            or any(type(item) is not str or not item for item in self.source_timestamps)
        ):
            raise Vt31SilverBulletV2ValidationError(
                "setup must retain source timestamp provenance"
            )
        if self.side is DemoTradingSetupSide.SHORT:
            valid = self.take_profit_price < self.entry_price < self.invalidation_price
        else:
            valid = self.invalidation_price < self.entry_price < self.take_profit_price
        if not valid:
            raise Vt31SilverBulletV2ValidationError(
                "setup geometry must point from entry toward opposite range boundary"
            )

    @property
    def initial_risk(self) -> Decimal:
        return abs(self.entry_price - self.invalidation_price)

    @property
    def expected_r_multiple(self) -> Decimal:
        return abs(self.take_profit_price - self.entry_price) / self.initial_risk

    @property
    def three_r_price(self) -> Decimal:
        distance = self.initial_risk * Decimal(3)
        if self.side is DemoTradingSetupSide.SHORT:
            return self.entry_price - distance
        return self.entry_price + distance


@dataclass(frozen=True, slots=True)
class Vt31SilverBulletV2Evaluation:
    """Deterministic VT-31 V2 decision with exact methodology and evidence identity."""

    decision: DemoTradingDecision
    instrument: Instrument
    evaluated_at: datetime
    config_fingerprint: str
    methodology_fingerprint: str
    evidence_fingerprint: str
    setup: Vt31SilverBulletV2Setup | None
    abstain_reason: Vt31SilverBulletV2AbstainReason | None
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.decision) is not DemoTradingDecision:
            raise Vt31SilverBulletV2ValidationError("decision must be canonical")
        if type(self.instrument) is not Instrument:
            raise Vt31SilverBulletV2ValidationError("instrument must be exact Instrument")
        _require_aware(self.evaluated_at, field_name="evaluated_at")
        for field_name, value in (
            ("config_fingerprint", self.config_fingerprint),
            ("methodology_fingerprint", self.methodology_fingerprint),
            ("evidence_fingerprint", self.evidence_fingerprint),
        ):
            if type(value) is not str or len(value) != 64 or any(
                character not in "0123456789abcdef" for character in value
            ):
                raise Vt31SilverBulletV2ValidationError(
                    f"{field_name} must be lowercase SHA-256"
                )
        if type(self.reason_code) is not str or not self.reason_code:
            raise Vt31SilverBulletV2ValidationError("reason_code must be non-empty")
        if self.decision is DemoTradingDecision.SETUP:
            if self.setup is None or self.abstain_reason is not None or self.reason_code != "setup":
                raise Vt31SilverBulletV2ValidationError(
                    "SETUP requires setup, setup reason code and no abstain_reason"
                )
        elif (
            self.setup is not None
            or self.abstain_reason is None
            or self.reason_code != self.abstain_reason.value
        ):
            raise Vt31SilverBulletV2ValidationError(
                "ABSTAIN requires exact stable abstain reason code and no setup"
            )


@dataclass(frozen=True, slots=True)
class _StructureConfirmation:
    confirmation_index: int
    extreme_index: int
    extreme: Decimal
    anchor: Decimal


@dataclass(frozen=True, slots=True)
class _EntryCandidate:
    model: Vt31SilverBulletV2EntryModel
    entry_price: Decimal
    zone_lower: Decimal
    zone_upper: Decimal
    formed_at: datetime
    source_timestamps: tuple[str, ...]
    price_formalization: str


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
            "schema": "qore.trader.vt31.silver-bullet-v2.methodology.v2",
            "trader_code": _TRADER_CODE,
            "trader_version": _TRADER_VERSION,
            "methodology_id": _METHODOLOGY_ID,
            "methodology_version": _METHODOLOGY_VERSION,
            "source_video": _SOURCE_VIDEO_ID,
            "source_file": _SOURCE_FILE_NAME,
            "source_file_sha256": _SOURCE_FILE_SHA256,
            "ruleset": _RULESET,
            "daily_bias_required": False,
            "risk_quantity_authority": False,
            "preferred_entry_model": (
                config.preferred_entry_model.value
                if config.preferred_entry_model is not None
                else None
            ),
            "confluence_policy": config.confluence_policy.value,
        }
    )


def _evidence_fingerprint(inputs: Vt31SilverBulletV2Input) -> str:
    return _digest(
        {
            "schema": "qore.trader.vt31.silver-bullet-v2.evidence.v1",
            "instrument": inputs.instrument.symbol,
            "as_of": inputs.as_of.astimezone(UTC).isoformat(timespec="microseconds"),
            "bars": [
                {
                    "opened_at": item.opened_at.astimezone(UTC).isoformat(
                        timespec="microseconds"
                    ),
                    "closed_at": item.closed_at.astimezone(UTC).isoformat(
                        timespec="microseconds"
                    ),
                    "open": str(item.open),
                    "high": str(item.high),
                    "low": str(item.low),
                    "close": str(item.close),
                }
                for item in inputs.m1_candles
            ],
        }
    )


def _require_aware(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise Vt31SilverBulletV2ValidationError(f"{field_name} must be timezone-aware")


def _price(value: float) -> Decimal:
    return Decimal(str(value))


def _body_zone(bar: OhlcSnapshot) -> tuple[Decimal, Decimal]:
    opened = _price(bar.open)
    closed = _price(bar.close)
    return min(opened, closed), max(opened, closed)


def _midpoint(lower: Decimal, upper: Decimal) -> Decimal:
    return (lower + upper) / Decimal(2)


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


def _reference_range(
    inputs: Vt31SilverBulletV2Input,
) -> Vt31SilverBulletV2ReferenceRange | None:
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
    reference: Vt31SilverBulletV2ReferenceRange,
) -> _StructureConfirmation | None:
    """Formalize repeated source language without an invented aggression threshold."""

    extreme_index = raid_index
    extreme_bar = bars[raid_index]
    if side is DemoTradingSetupSide.SHORT:
        extreme = _price(extreme_bar.high)
        anchor = _price(extreme_bar.low)
        for index in range(raid_index + 1, len(bars)):
            bar = bars[index]
            if _price(bar.high) > extreme:
                extreme = _price(bar.high)
                extreme_index = index
                anchor = _price(bar.low)
                continue
            close = _price(bar.close)
            if close < anchor and close < reference.high:
                return _StructureConfirmation(index, extreme_index, extreme, anchor)
        return None

    extreme = _price(extreme_bar.low)
    anchor = _price(extreme_bar.high)
    for index in range(raid_index + 1, len(bars)):
        bar = bars[index]
        if _price(bar.low) < extreme:
            extreme = _price(bar.low)
            extreme_index = index
            anchor = _price(bar.high)
            continue
        close = _price(bar.close)
        if close > anchor and close > reference.low:
            return _StructureConfirmation(index, extreme_index, extreme, anchor)
    return None


def _breaker_candidate(
    bars: tuple[OhlcSnapshot, ...],
    *,
    side: DemoTradingSetupSide,
    structure: _StructureConfirmation,
) -> _EntryCandidate | None:
    source_bar = bars[structure.extreme_index]
    opened = _price(source_bar.open)
    closed = _price(source_bar.close)
    required_opposite_close = (
        closed > opened
        if side is DemoTradingSetupSide.SHORT
        else closed < opened
    )
    if not required_opposite_close:
        return None
    lower, upper = _body_zone(source_bar)
    return _EntryCandidate(
        model=Vt31SilverBulletV2EntryModel.BREAKER_BLOCK,
        entry_price=_midpoint(lower, upper),
        zone_lower=lower,
        zone_upper=upper,
        formed_at=bars[structure.confirmation_index].closed_at.astimezone(UTC),
        source_timestamps=("05:31-05:52", "07:12-07:43", "20:01-20:25"),
        price_formalization="entry-zone-body-midpoint-v1",
    )


def _order_block_candidate(
    bars: tuple[OhlcSnapshot, ...],
    *,
    raid_index: int,
    side: DemoTradingSetupSide,
    structure: _StructureConfirmation,
) -> _EntryCandidate | None:
    candidates: list[OhlcSnapshot] = []
    for bar in bars[raid_index : structure.confirmation_index + 1]:
        opened = _price(bar.open)
        closed = _price(bar.close)
        opposite = (
            closed > opened
            if side is DemoTradingSetupSide.SHORT
            else closed < opened
        )
        if opposite:
            candidates.append(bar)
    if not candidates:
        return None
    source_bar = candidates[-1]
    lower, upper = _body_zone(source_bar)
    return _EntryCandidate(
        model=Vt31SilverBulletV2EntryModel.ORDER_BLOCK,
        entry_price=_midpoint(lower, upper),
        zone_lower=lower,
        zone_upper=upper,
        formed_at=bars[structure.confirmation_index].closed_at.astimezone(UTC),
        source_timestamps=("10:22-10:52", "17:42-18:12"),
        price_formalization="entry-zone-body-midpoint-v1",
    )


def _fvg_candidate(
    bars: tuple[OhlcSnapshot, ...],
    *,
    side: DemoTradingSetupSide,
    confirmation_index: int,
) -> _EntryCandidate | None:
    start = max(2, confirmation_index)
    for third_index in range(start, len(bars)):
        first = bars[third_index - 2]
        third = bars[third_index]
        if side is DemoTradingSetupSide.SHORT and _price(third.high) < _price(first.low):
            lower = _price(third.high)
            upper = _price(first.low)
            return _EntryCandidate(
                model=Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP,
                entry_price=_midpoint(lower, upper),
                zone_lower=lower,
                zone_upper=upper,
                formed_at=third.closed_at.astimezone(UTC),
                source_timestamps=("11:34-12:24", "22:08-22:44"),
                price_formalization="fvg-consequent-encroachment-v1",
            )
        if side is DemoTradingSetupSide.LONG and _price(third.low) > _price(first.high):
            lower = _price(first.high)
            upper = _price(third.low)
            return _EntryCandidate(
                model=Vt31SilverBulletV2EntryModel.FAIR_VALUE_GAP,
                entry_price=_midpoint(lower, upper),
                zone_lower=lower,
                zone_upper=upper,
                formed_at=third.closed_at.astimezone(UTC),
                source_timestamps=("12:55-13:16", "13:30-14:17"),
                price_formalization="fvg-consequent-encroachment-v1",
            )
    return None


def _entry_candidates(
    bars: tuple[OhlcSnapshot, ...],
    *,
    raid_index: int,
    side: DemoTradingSetupSide,
    structure: _StructureConfirmation,
) -> tuple[_EntryCandidate, ...]:
    candidates = tuple(
        item
        for item in (
            _breaker_candidate(bars, side=side, structure=structure),
            _order_block_candidate(
                bars,
                raid_index=raid_index,
                side=side,
                structure=structure,
            ),
            _fvg_candidate(
                bars,
                side=side,
                confirmation_index=structure.confirmation_index,
            ),
        )
        if item is not None
    )
    return tuple(sorted(candidates, key=lambda item: (item.formed_at, item.model.value)))


def _select_candidate(
    candidates: tuple[_EntryCandidate, ...],
    config: Vt31SilverBulletV2Config,
) -> tuple[_EntryCandidate | None, tuple[Vt31SilverBulletV2EntryModel, ...], bool]:
    if not candidates:
        return None, (), False
    earliest = candidates[0].formed_at
    contemporaneous = tuple(item for item in candidates if item.formed_at == earliest)
    models = tuple(item.model for item in contemporaneous)
    preferred = config.preferred_entry_model
    if preferred is not None:
        selected = next((item for item in contemporaneous if item.model is preferred), None)
        if selected is not None:
            return selected, models, False
    prices = {item.entry_price for item in contemporaneous}
    if len(prices) == 1:
        return contemporaneous[0], models, False
    if len(contemporaneous) == 1:
        return contemporaneous[0], models, False
    return None, models, True


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
        evidence_fingerprint=_evidence_fingerprint(inputs),
        setup=None,
        abstain_reason=reason,
        reason_code=reason.value,
    )


def evaluate_vt31_silver_bullet_v2(
    inputs: Vt31SilverBulletV2Input,
    config: Vt31SilverBulletV2Config | None = None,
) -> Vt31SilverBulletV2Evaluation:
    """Evaluate VT-31 V2 using source-bound, causal, fail-closed semantics."""

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

    structure = _structure_shift(
        bars,
        raid_index=raid_index,
        side=side,
        reference=reference,
    )
    if structure is None:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.NO_POST_RAID_STRUCTURE_SHIFT,
        )

    candidates = _entry_candidates(
        bars,
        raid_index=raid_index,
        side=side,
        structure=structure,
    )
    candidate, confluence_models, ambiguous = _select_candidate(candidates, selected)
    if ambiguous:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.AMBIGUOUS_ENTRY_MODEL_CONFLUENCE,
        )
    if candidate is None:
        return _abstain(
            inputs,
            selected,
            Vt31SilverBulletV2AbstainReason.NO_VALID_ENTRY_MODEL,
        )

    target = reference.low if side is DemoTradingSetupSide.SHORT else reference.high
    try:
        setup = Vt31SilverBulletV2Setup(
            side=side,
            entry_price=candidate.entry_price,
            methodological_stop_extreme=structure.extreme,
            technical_stop_buffer=Decimal(0),
            invalidation_price=structure.extreme,
            take_profit_price=target,
            reference_range=reference,
            raid_at=bars[raid_index].closed_at.astimezone(UTC),
            confirmation_at=bars[structure.confirmation_index].closed_at.astimezone(UTC),
            decision_at=candidate.formed_at,
            entry_model=candidate.model,
            entry_models=confluence_models or (candidate.model,),
            entry_zone_lower=candidate.zone_lower,
            entry_zone_upper=candidate.zone_upper,
            entry_price_formalization=candidate.price_formalization,
            expires_at=_window_close(inputs.as_of),
            source_video=_SOURCE_VIDEO_ID,
            source_timestamps=candidate.source_timestamps,
        )
    except Vt31SilverBulletV2ValidationError:
        return _abstain(inputs, selected, Vt31SilverBulletV2AbstainReason.INVALID_GEOMETRY)

    return Vt31SilverBulletV2Evaluation(
        decision=DemoTradingDecision.SETUP,
        instrument=inputs.instrument,
        evaluated_at=inputs.as_of.astimezone(UTC),
        config_fingerprint=selected.fingerprint(),
        methodology_fingerprint=_methodology_fingerprint(selected),
        evidence_fingerprint=_evidence_fingerprint(inputs),
        setup=setup,
        abstain_reason=None,
        reason_code="setup",
    )
