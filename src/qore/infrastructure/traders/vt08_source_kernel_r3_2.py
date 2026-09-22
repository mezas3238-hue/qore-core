"""VT-08 Revision 3.2 shared primary-audio source model.

This module contains only methodology semantics shared by the rebuilt Forex and
Futures Traders. Market allowlists, market-family timing authority, daily setup
selection, order state, and economic execution stay outside the source kernel.

DeepSeek Revision 3.2 is retained as frozen independent witness evidence. The
primary TTrades video/audio remains authoritative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.kernel.errors import InfrastructureError

PRIMARY_SOURCE = "youtube:FAKWJ-1NlLE"
PRIMARY_SOURCE_SHA256 = (
    "bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271"
)
INDEPENDENT_WITNESS = "deepseek-r3.2-frozen"
METHODOLOGY_VERSION = "r3.2-primary-audio-v1"
OPERATING_TIMEZONE = "America/New_York"
_NY = ZoneInfo(OPERATING_TIMEZONE)

SOURCE_FOREX_ANCHORS = (1, 5, 9, 13)
SOURCE_FUTURES_ANCHORS = (2, 6, 10, 14)
OWNER_FOREX_ANCHORS = (1, 5, 9)
OWNER_FUTURES_ANCHORS = (2, 6, 10)


class VT08SourceKernelValidationError(InfrastructureError):
    """Violation of a Revision 3.2 source-model invariant."""

    __slots__ = ()


class VT08MarketFamily(StrEnum):
    FOREX = "forex"
    FUTURES = "futures"


class VT08TimingProfile(StrEnum):
    SOURCE_COMPLETE = "source-complete"
    OWNER_OPERATIONAL = "owner-operational-subset"


class VT08LtfProfile(StrEnum):
    M15 = "m15-standard"
    M5_FRACTAL = "m5-fractal"
    M3_FRACTAL = "m3-fractal"


class VT08DeliverySequence(StrEnum):
    BULL_OLHC = "open-low-high-close"
    BEAR_OHLC = "open-high-low-close"


class VT08Scenario(StrEnum):
    C2 = "c2-reversal-expansion"
    C3 = "c3-continuation-expansion"


class VT08WickEvidence(StrEnum):
    """Qualitative evidence only; no source-authorized numerical threshold exists."""

    SHALLOW_EARLY_RANGE_AVAILABLE = "shallow-early-range-available"
    LARGE_OPPOSING_MOVE = "large-opposing-move"
    RANGE_CONSUMED = "range-materially-consumed"
    UNRESOLVED = "unresolved"


class VT08EntryFamily(StrEnum):
    REVERSAL_ENTRY = "reversal-entry"
    CONTINUATION_ENTRY = "continuation-entry"
    CONFIDENT_ENTRY = "confident-entry"
    POSITIONAL_ENTRY = "positional-entry"
    OPEN_ENTRY = "open-entry"
    POI_CONTINUATION_ENTRY = "poi-continuation-entry"


class VT08StopFamily(StrEnum):
    PS_STOP = "protected-swing-stop"
    CISD_EQ_50_STOP = "50pct-cisd-eq-stop"
    OPPOSING_CANDLE_STOP = "opposing-candle-stop"
    FVG_STOP = "fvg-stop"
    BODY_LOW_STOP = "body-low-stop"


class VT08TargetFamily(StrEnum):
    TWO_R_PLUS = "2r-plus"
    EXTERNAL_LIQUIDITY = "external-liquidity"
    NEGATIVE_ONE_SD = "negative-one-standard-deviation"
    DAILY_OPEN = "daily-open"
    SESSION_EXTREME = "session-extreme"


class VT08ProvenanceClass(StrEnum):
    SOURCE_EXPLICIT = "source-explicit"
    SOURCE_REPEATED = "source-repeated"
    SOURCE_FORMALIZATION = "source-formalization"
    POST_SOURCE_AUTHOR_CLARIFICATION = "post-source-author-clarification"
    OWNER_EXECUTION_POLICY = "owner-execution-policy"
    OPERATIONAL_CONTAINMENT = "operational-containment"
    STILL_AMBIGUOUS = "still-ambiguous"


def _require_aware(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise VT08SourceKernelValidationError(f"{field_name} must be timezone-aware")


def _require_price(value: Decimal, *, field_name: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise VT08SourceKernelValidationError(
            f"{field_name} must be a positive finite Decimal"
        )


def _require_non_empty(value: str, *, field_name: str) -> None:
    if type(value) is not str or not value.strip():
        raise VT08SourceKernelValidationError(f"{field_name} must be non-empty")


def anchor_hours(
    family: VT08MarketFamily,
    profile: VT08TimingProfile,
) -> tuple[int, ...]:
    """Return source-complete or Owner-subset anchors without conflating them."""

    if type(family) is not VT08MarketFamily:
        raise VT08SourceKernelValidationError("family must be exact VT08MarketFamily")
    if type(profile) is not VT08TimingProfile:
        raise VT08SourceKernelValidationError("profile must be exact VT08TimingProfile")
    if family is VT08MarketFamily.FOREX:
        if profile is VT08TimingProfile.SOURCE_COMPLETE:
            return SOURCE_FOREX_ANCHORS
        return OWNER_FOREX_ANCHORS
    if profile is VT08TimingProfile.SOURCE_COMPLETE:
        return SOURCE_FUTURES_ANCHORS
    return OWNER_FUTURES_ANCHORS


def is_authorized_anchor(
    *,
    family: VT08MarketFamily,
    profile: VT08TimingProfile,
    opened_at: datetime,
) -> bool:
    """Check one DST-aware H4 opening anchor in America/New_York."""

    _require_aware(opened_at, field_name="opened_at")
    local = opened_at.astimezone(_NY)
    exact_hour = local.minute == 0 and local.second == 0 and local.microsecond == 0
    return exact_hour and local.hour in anchor_hours(family, profile)


def ltf_minutes(profile: VT08LtfProfile) -> int:
    """Return the independent observation granularity for one frozen LTF profile."""

    if type(profile) is not VT08LtfProfile:
        raise VT08SourceKernelValidationError("profile must be exact VT08LtfProfile")
    if profile is VT08LtfProfile.M15:
        return 15
    if profile is VT08LtfProfile.M5_FRACTAL:
        return 5
    return 3


def delivery_sequence(side: DemoTradingSetupSide) -> VT08DeliverySequence:
    """Map an already-known directional hypothesis to the source delivery sequence.

    This does not infer direction from the completed candle or from a future outcome.
    """

    if type(side) is not DemoTradingSetupSide:
        raise VT08SourceKernelValidationError("side must be exact DemoTradingSetupSide")
    if side is DemoTradingSetupSide.LONG:
        return VT08DeliverySequence.BULL_OLHC
    return VT08DeliverySequence.BEAR_OHLC


def scenario_for_wick(wick: VT08WickEvidence) -> VT08Scenario | None:
    """Resolve only the qualitative C2/C3 distinction supplied by Revision 3.2."""

    if type(wick) is not VT08WickEvidence:
        raise VT08SourceKernelValidationError("wick must be exact VT08WickEvidence")
    if wick is VT08WickEvidence.SHALLOW_EARLY_RANGE_AVAILABLE:
        return VT08Scenario.C2
    if wick in (VT08WickEvidence.LARGE_OPPOSING_MOVE, VT08WickEvidence.RANGE_CONSUMED):
        return VT08Scenario.C3
    return None


@dataclass(frozen=True, slots=True)
class VT08SourceProvenance:
    classification: VT08ProvenanceClass
    source_refs: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        if type(self.classification) is not VT08ProvenanceClass:
            raise VT08SourceKernelValidationError("classification must be exact provenance")
        if type(self.source_refs) is not tuple or not self.source_refs:
            raise VT08SourceKernelValidationError("source_refs must be a non-empty tuple")
        if any(type(item) is not str or not item.strip() for item in self.source_refs):
            raise VT08SourceKernelValidationError("source_refs must contain non-empty strings")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise VT08SourceKernelValidationError("source_refs must be unique")
        _require_non_empty(self.note, field_name="note")


@dataclass(frozen=True, slots=True)
class VT08EquilibriumReference:
    """Causal 50% equilibrium of an explicitly identified source range."""

    range_source: str
    range_high: Decimal
    range_low: Decimal
    formed_at: datetime
    known_at: datetime
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        _require_non_empty(self.range_source, field_name="range_source")
        _require_price(self.range_high, field_name="range_high")
        _require_price(self.range_low, field_name="range_low")
        _require_aware(self.formed_at, field_name="formed_at")
        _require_aware(self.known_at, field_name="known_at")
        if self.range_low >= self.range_high:
            raise VT08SourceKernelValidationError("EQ range_low must be below range_high")
        if self.known_at < self.formed_at:
            raise VT08SourceKernelValidationError("EQ cannot be known before it forms")
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("EQ provenance must be exact")

    @property
    def eq_price(self) -> Decimal:
        return (self.range_high + self.range_low) / Decimal(2)


@dataclass(frozen=True, slots=True)
class VT08CisdEvidence:
    """Causal close through the opposing delivery series after important-level reach."""

    side: DemoTradingSetupSide
    important_level_ref: str
    opposing_series_open: Decimal
    opposing_series_extreme: Decimal
    confirmed_close: Decimal
    formed_at: datetime
    confirmed_at: datetime
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        if type(self.side) is not DemoTradingSetupSide:
            raise VT08SourceKernelValidationError("CISD side must be exact")
        _require_non_empty(self.important_level_ref, field_name="important_level_ref")
        for field_name, value in (
            ("opposing_series_open", self.opposing_series_open),
            ("opposing_series_extreme", self.opposing_series_extreme),
            ("confirmed_close", self.confirmed_close),
        ):
            _require_price(value, field_name=field_name)
        _require_aware(self.formed_at, field_name="formed_at")
        _require_aware(self.confirmed_at, field_name="confirmed_at")
        if self.confirmed_at < self.formed_at:
            raise VT08SourceKernelValidationError("CISD cannot confirm before formation")
        crossed = (
            self.confirmed_close > self.opposing_series_open
            if self.side is DemoTradingSetupSide.LONG
            else self.confirmed_close < self.opposing_series_open
        )
        if not crossed:
            raise VT08SourceKernelValidationError(
                "CISD confirmation must close through the opposing delivery series"
            )
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("CISD provenance must be exact")


@dataclass(frozen=True, slots=True)
class VT08ProtectedSwing:
    side: DemoTradingSetupSide
    price: Decimal
    established_at: datetime
    cisd: VT08CisdEvidence
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        if type(self.side) is not DemoTradingSetupSide:
            raise VT08SourceKernelValidationError("protected-swing side must be exact")
        _require_price(self.price, field_name="protected_swing_price")
        _require_aware(self.established_at, field_name="established_at")
        if type(self.cisd) is not VT08CisdEvidence or self.cisd.side is not self.side:
            raise VT08SourceKernelValidationError("protected swing requires same-side CISD")
        if self.established_at < self.cisd.confirmed_at:
            raise VT08SourceKernelValidationError("protected swing cannot predate CISD")
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("protected-swing provenance must be exact")


@dataclass(frozen=True, slots=True)
class VT08HtfLifecycle:
    """One current H4 authority interval; a trade may not survive its close."""

    opened_at: datetime
    closes_at: datetime
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        _require_aware(self.opened_at, field_name="opened_at")
        _require_aware(self.closes_at, field_name="closes_at")
        elapsed = self.closes_at.astimezone(UTC) - self.opened_at.astimezone(UTC)
        if elapsed != timedelta(hours=4):
            raise VT08SourceKernelValidationError(
                "HTF lifecycle must be exactly four elapsed hours"
            )
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("lifecycle provenance must be exact")

    def require_decision_inside(self, decision_at: datetime) -> None:
        _require_aware(decision_at, field_name="decision_at")
        if not self.opened_at <= decision_at < self.closes_at:
            raise VT08SourceKernelValidationError("decision is outside the current H4")

    @property
    def trade_valid_until(self) -> datetime:
        return self.closes_at


@dataclass(frozen=True, slots=True)
class VT08EntryCandidate:
    """One source-supported entry-family candidate; not daily selection authority."""

    candidate_id: str
    family: VT08EntryFamily
    side: DemoTradingSetupSide
    ltf_profile: VT08LtfProfile
    formed_at: datetime
    confirmed_at: datetime
    decision_at: datetime
    zone_low: Decimal
    zone_high: Decimal
    executable_price: Decimal | None
    compatible_stop_families: tuple[VT08StopFamily, ...]
    compatible_target_families: tuple[VT08TargetFamily, ...]
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        _require_non_empty(self.candidate_id, field_name="candidate_id")
        if type(self.family) is not VT08EntryFamily:
            raise VT08SourceKernelValidationError("entry family must be exact")
        if type(self.side) is not DemoTradingSetupSide:
            raise VT08SourceKernelValidationError("entry side must be exact")
        if type(self.ltf_profile) is not VT08LtfProfile:
            raise VT08SourceKernelValidationError("entry LTF profile must be exact")
        for field_name, value in (
            ("formed_at", self.formed_at),
            ("confirmed_at", self.confirmed_at),
            ("decision_at", self.decision_at),
        ):
            _require_aware(value, field_name=field_name)
        if not self.formed_at <= self.confirmed_at <= self.decision_at:
            raise VT08SourceKernelValidationError("entry evidence must be causal")
        _require_price(self.zone_low, field_name="zone_low")
        _require_price(self.zone_high, field_name="zone_high")
        if self.zone_low > self.zone_high:
            raise VT08SourceKernelValidationError("entry zone is inverted")
        if self.executable_price is not None:
            _require_price(self.executable_price, field_name="executable_price")
            if not self.zone_low <= self.executable_price <= self.zone_high:
                raise VT08SourceKernelValidationError(
                    "executable price must remain inside its source-resolved zone"
                )
        if not self.compatible_stop_families or not self.compatible_target_families:
            raise VT08SourceKernelValidationError(
                "entry candidate requires source-compatible stop and target families"
            )
        if len(set(self.compatible_stop_families)) != len(self.compatible_stop_families):
            raise VT08SourceKernelValidationError("compatible stop families must be unique")
        if len(set(self.compatible_target_families)) != len(
            self.compatible_target_families
        ):
            raise VT08SourceKernelValidationError("compatible target families must be unique")
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("entry provenance must be exact")


@dataclass(frozen=True, slots=True)
class VT08StopCandidate:
    family: VT08StopFamily
    price: Decimal
    known_at: datetime
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        if type(self.family) is not VT08StopFamily:
            raise VT08SourceKernelValidationError("stop family must be exact")
        _require_price(self.price, field_name="stop_price")
        _require_aware(self.known_at, field_name="stop_known_at")
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("stop provenance must be exact")


@dataclass(frozen=True, slots=True)
class VT08TargetCandidate:
    family: VT08TargetFamily
    price: Decimal
    known_at: datetime
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        if type(self.family) is not VT08TargetFamily:
            raise VT08SourceKernelValidationError("target family must be exact")
        _require_price(self.price, field_name="target_price")
        _require_aware(self.known_at, field_name="target_known_at")
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("target provenance must be exact")


@dataclass(frozen=True, slots=True)
class VT08SourceBundle:
    """One coherent source-supported entry/stop/target relationship."""

    bundle_id: str
    entry_family: VT08EntryFamily
    stop_family: VT08StopFamily
    target_family: VT08TargetFamily
    provenance: VT08SourceProvenance

    def __post_init__(self) -> None:
        _require_non_empty(self.bundle_id, field_name="bundle_id")
        if type(self.entry_family) is not VT08EntryFamily:
            raise VT08SourceKernelValidationError("bundle entry family must be exact")
        if type(self.stop_family) is not VT08StopFamily:
            raise VT08SourceKernelValidationError("bundle stop family must be exact")
        if type(self.target_family) is not VT08TargetFamily:
            raise VT08SourceKernelValidationError("bundle target family must be exact")
        if type(self.provenance) is not VT08SourceProvenance:
            raise VT08SourceKernelValidationError("bundle provenance must be exact")


def validate_source_bundle(
    *,
    entry: VT08EntryCandidate,
    stop: VT08StopCandidate,
    target: VT08TargetCandidate,
    bundle: VT08SourceBundle,
    lifecycle: VT08HtfLifecycle,
) -> None:
    """Reject unsupported Cartesian combinations and all future evidence."""

    if (entry.family, stop.family, target.family) != (
        bundle.entry_family,
        bundle.stop_family,
        bundle.target_family,
    ):
        raise VT08SourceKernelValidationError(
            "blind entry/stop/target Cartesian products are prohibited"
        )
    if stop.family not in entry.compatible_stop_families:
        raise VT08SourceKernelValidationError("stop family is incompatible with entry")
    if target.family not in entry.compatible_target_families:
        raise VT08SourceKernelValidationError("target family is incompatible with entry")
    lifecycle.require_decision_inside(entry.decision_at)
    if stop.known_at > entry.decision_at or target.known_at > entry.decision_at:
        raise VT08SourceKernelValidationError("future stop/target evidence is prohibited")


def methodology_fingerprint() -> str:
    """Fingerprint source semantics without asserting unresolved selection priority."""

    material = {
        "primary_source": PRIMARY_SOURCE,
        "primary_source_sha256": PRIMARY_SOURCE_SHA256,
        "independent_witness": INDEPENDENT_WITNESS,
        "methodology_version": METHODOLOGY_VERSION,
        "source_forex_anchors": SOURCE_FOREX_ANCHORS,
        "source_futures_anchors": SOURCE_FUTURES_ANCHORS,
        "owner_forex_anchors": OWNER_FOREX_ANCHORS,
        "owner_futures_anchors": OWNER_FUTURES_ANCHORS,
        "ltf_profiles": [item.value for item in VT08LtfProfile],
        "entry_families": [item.value for item in VT08EntryFamily],
        "stop_families": [item.value for item in VT08StopFamily],
        "target_families": [item.value for item in VT08TargetFamily],
        "trade_valid_until": "current-h4-close",
        "daily_fill_cap": 1,
        "daily_selection": "unresolved-owner-policy-required",
        "numeric_shallow_large_threshold": None,
    }
    encoded = json.dumps(
        material,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
