"""Global market time integrity and relational comparability for Shared GEN-2.

This module is cognition-only. It deliberately separates canonical market
session state, provider observability, causal event alignment, liquidity
observability and relational comparability.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from qore.infrastructure.market_clock_schedule import (
    WallClockBoundary,
    resolve_wall_clock_boundary_utc,
)


class TemporalComparabilityError(ValueError):
    """GEN-2 time-integrity or comparability invariant failed closed."""


def _require_aware(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TemporalComparabilityError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TemporalComparabilityError(
            f"{field_name} must be timezone-aware"
        )


def _millis(delta: timedelta) -> int:
    return delta // timedelta(milliseconds=1)


def _sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MarketSessionState(StrEnum):
    OPEN_ACTIVE = "OPEN_ACTIVE"
    OPEN_LOW_LIQUIDITY = "OPEN_LOW_LIQUIDITY"
    PRE_SESSION = "PRE_SESSION"
    POST_SESSION = "POST_SESSION"
    SESSION_BREAK = "SESSION_BREAK"
    CLOSED = "CLOSED"
    HOLIDAY = "HOLIDAY"
    PARTIAL_SESSION = "PARTIAL_SESSION"
    HALTED = "HALTED"
    UNKNOWN = "UNKNOWN"


class ProviderOperationalSignal(StrEnum):
    HEALTHY = "HEALTHY"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ProviderObservabilityState(StrEnum):
    HEALTHY = "HEALTHY"
    DELAYED = "DELAYED"
    STALE = "STALE"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class LiquidityState(StrEnum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    ILLIQUID = "ILLIQUID"
    UNKNOWN = "UNKNOWN"


class RelationalComparabilityState(StrEnum):
    COMPARABLE = "COMPARABLE"
    PARTIALLY_COMPARABLE = "PARTIALLY_COMPARABLE"
    STALE_PEER = "STALE_PEER"
    ASYNC_MARKET = "ASYNC_MARKET"
    ILLIQUID_PEER = "ILLIQUID_PEER"
    CLOSED_PEER = "CLOSED_PEER"
    PARTIAL_SESSION = "PARTIAL_SESSION"
    HOLIDAY_SESSION = "HOLIDAY_SESSION"
    TRADING_HALT = "TRADING_HALT"
    PROVIDER_DELAYED = "PROVIDER_DELAYED"
    PROVIDER_DEGRADED = "PROVIDER_DEGRADED"
    TIMESTAMP_INCONSISTENT = "TIMESTAMP_INCONSISTENT"
    INSUFFICIENT = "INSUFFICIENT"


class ComparabilityConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class ComparabilityUncertainty(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    MAXIMUM = "MAXIMUM"


@dataclass(frozen=True, slots=True, order=True)
class WeeklySessionRule:
    """One canonical local session interval anchored to a weekday."""

    weekday: int
    opens_at: WallClockBoundary
    closes_at: WallClockBoundary
    state: MarketSessionState = MarketSessionState.OPEN_ACTIVE

    def __post_init__(self) -> None:
        if type(self.weekday) is not int or not 0 <= self.weekday <= 6:
            raise TemporalComparabilityError("weekday must be int 0..6")
        if self.state not in {
            MarketSessionState.OPEN_ACTIVE,
            MarketSessionState.OPEN_LOW_LIQUIDITY,
        }:
            raise TemporalComparabilityError(
                "weekly session state must be an open state"
            )


@dataclass(frozen=True, slots=True, order=True)
class DateSessionInterval:
    opens_at: WallClockBoundary
    closes_at: WallClockBoundary
    state: MarketSessionState = MarketSessionState.OPEN_ACTIVE

    def __post_init__(self) -> None:
        if self.state not in {
            MarketSessionState.OPEN_ACTIVE,
            MarketSessionState.OPEN_LOW_LIQUIDITY,
        }:
            raise TemporalComparabilityError(
                "date interval state must be an open state"
            )


@dataclass(frozen=True, slots=True)
class CalendarDateOverride:
    local_date: date
    state: MarketSessionState
    intervals: tuple[DateSessionInterval, ...] = ()

    def __post_init__(self) -> None:
        if type(self.local_date) is not date:
            raise TemporalComparabilityError(
                "calendar override local_date must be exact date"
            )
        if self.state is MarketSessionState.HOLIDAY:
            if self.intervals:
                raise TemporalComparabilityError(
                    "holiday override cannot contain open intervals"
                )
        elif self.state is MarketSessionState.PARTIAL_SESSION:
            if not self.intervals:
                raise TemporalComparabilityError(
                    "partial session requires explicit intervals"
                )
        else:
            raise TemporalComparabilityError(
                "calendar override must be HOLIDAY or PARTIAL_SESSION"
            )
        if self.intervals != tuple(sorted(set(self.intervals))):
            raise TemporalComparabilityError(
                "calendar override intervals must be canonical"
            )


class CanonicalMarketStructure(StrEnum):
    """Canonical market organization without inventing a single venue."""

    CENTRALIZED_VENUE = "CENTRALIZED_VENUE"
    DISTRIBUTED_OTC = "DISTRIBUTED_OTC"
    MULTI_VENUE_COMPOSITE = "MULTI_VENUE_COMPOSITE"
    CONTINUOUS_NETWORK = "CONTINUOUS_NETWORK"


@dataclass(frozen=True, slots=True)
class GlobalMarketCalendar:
    calendar_id: str
    version: str
    venue: str | None
    iana_timezone: str
    weekly_sessions: tuple[WeeklySessionRule, ...]
    date_overrides: tuple[CalendarDateOverride, ...]
    provenance_refs: tuple[str, ...]
    market_structure: CanonicalMarketStructure = (
        CanonicalMarketStructure.CENTRALIZED_VENUE
    )

    def __post_init__(self) -> None:
        for name in ("calendar_id", "version", "iana_timezone"):
            if not str(getattr(self, name)).strip():
                raise TemporalComparabilityError(f"{name} must be non-empty")
        if self.venue is not None and not self.venue.strip():
            raise TemporalComparabilityError(
                "calendar venue must be non-empty or None"
            )
        if self.market_structure is CanonicalMarketStructure.CENTRALIZED_VENUE:
            if self.venue is None:
                raise TemporalComparabilityError(
                    "centralized market calendar requires venue"
                )
        elif self.venue is not None:
            raise TemporalComparabilityError(
                "non-centralized market calendar cannot claim single venue"
            )
        try:
            ZoneInfo(self.iana_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise TemporalComparabilityError(
                "calendar iana_timezone is invalid"
            ) from exc
        if self.weekly_sessions != tuple(sorted(set(self.weekly_sessions))):
            raise TemporalComparabilityError(
                "weekly sessions must be unique and canonical"
            )
        override_dates = tuple(item.local_date for item in self.date_overrides)
        if override_dates != tuple(sorted(override_dates)):
            raise TemporalComparabilityError(
                "calendar overrides must use chronological order"
            )
        if len(override_dates) != len(set(override_dates)):
            raise TemporalComparabilityError(
                "calendar override dates must be unique"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "calendar provenance must be unique and canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "calendar_id": self.calendar_id,
                "version": self.version,
                "venue": self.venue,
                "market_structure": self.market_structure.value,
                "iana_timezone": self.iana_timezone,
                "weekly_sessions": [
                    {
                        "weekday": item.weekday,
                        "opens_at": item.opens_at.logical_values(),
                        "closes_at": item.closes_at.logical_values(),
                        "state": item.state.value,
                    }
                    for item in self.weekly_sessions
                ],
                "date_overrides": [
                    {
                        "local_date": item.local_date.isoformat(),
                        "state": item.state.value,
                        "intervals": [
                            {
                                "opens_at": interval.opens_at.logical_values(),
                                "closes_at": interval.closes_at.logical_values(),
                                "state": interval.state.value,
                            }
                            for interval in item.intervals
                        ],
                    }
                    for item in self.date_overrides
                ],
                "provenance_refs": self.provenance_refs,
            }
        )


@dataclass(frozen=True, slots=True, order=True)
class MarketCalendarBinding:
    instrument_key: str
    canonical_instrument_id: str
    calendar_id: str
    provider_schedule_timezone: str | None
    timezone_mapping_version: str
    provenance_refs: tuple[str, ...]
    market_structure: CanonicalMarketStructure = (
        CanonicalMarketStructure.CENTRALIZED_VENUE
    )

    def __post_init__(self) -> None:
        for name in (
            "instrument_key",
            "canonical_instrument_id",
            "calendar_id",
            "timezone_mapping_version",
        ):
            if not str(getattr(self, name)).strip():
                raise TemporalComparabilityError(f"{name} must be non-empty")
        if (
            self.provider_schedule_timezone is not None
            and not self.provider_schedule_timezone.strip()
        ):
            raise TemporalComparabilityError(
                "provider_schedule_timezone must be non-empty or None"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "binding provenance must be unique and canonical"
            )


class CanonicalCalendarMappingStatus(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class CanonicalCalendarMappingRecord:
    """Governed provider instrument -> canonical venue/calendar evidence."""

    instrument_key: str
    provider: str
    provider_symbol: str
    provider_symbol_id: int
    status: CanonicalCalendarMappingStatus
    canonical_instrument_id: str | None
    venue: str | None
    calendar_id: str | None
    calendar_version: str | None
    iana_timezone: str | None
    provider_schedule_timezone: str | None
    timezone_mapping_version: str | None
    identity_evidence_refs: tuple[str, ...]
    venue_evidence_refs: tuple[str, ...]
    calendar_evidence_refs: tuple[str, ...]
    provider_schedule_evidence_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    market_structure: CanonicalMarketStructure | None = None
    market_structure_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.instrument_key.strip()
            or not self.provider.strip()
            or not self.provider_symbol.strip()
        ):
            raise TemporalComparabilityError(
                "canonical mapping provider identity must be explicit"
            )
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise TemporalComparabilityError(
                "canonical mapping provider_symbol_id must be positive int"
            )
        for name in (
            "identity_evidence_refs",
            "venue_evidence_refs",
            "calendar_evidence_refs",
            "provider_schedule_evidence_refs",
            "reason_codes",
            "market_structure_evidence_refs",
        ):
            values = getattr(self, name)
            if values != tuple(sorted(set(values))):
                raise TemporalComparabilityError(
                    f"{name} must be unique and canonical"
                )
        if (
            self.provider_schedule_timezone is not None
            and not self.provider_schedule_timezone.strip()
        ):
            raise TemporalComparabilityError(
                "provider schedule timezone must be non-empty or None"
            )
        if self.status is CanonicalCalendarMappingStatus.VERIFIED:
            required = (
                self.canonical_instrument_id,
                self.calendar_id,
                self.calendar_version,
                self.iana_timezone,
                self.timezone_mapping_version,
            )
            if any(value is None or not value.strip() for value in required):
                raise TemporalComparabilityError(
                    "verified canonical mapping requires complete canonical identity"
                )
            if self.market_structure is None:
                raise TemporalComparabilityError(
                    "verified canonical mapping requires market structure"
                )
            if not self.identity_evidence_refs:
                raise TemporalComparabilityError(
                    "verified canonical mapping requires identity evidence"
                )
            if not self.market_structure_evidence_refs:
                raise TemporalComparabilityError(
                    "verified canonical mapping requires market structure evidence"
                )
            if (
                self.market_structure
                is CanonicalMarketStructure.CENTRALIZED_VENUE
            ):
                if self.venue is None or not self.venue.strip():
                    raise TemporalComparabilityError(
                        "centralized verified mapping requires venue"
                    )
                if not self.venue_evidence_refs:
                    raise TemporalComparabilityError(
                        "verified canonical mapping requires venue evidence"
                    )
            else:
                if self.venue is not None:
                    raise TemporalComparabilityError(
                        "non-centralized verified mapping cannot claim single venue"
                    )
                if self.venue_evidence_refs:
                    raise TemporalComparabilityError(
                        "non-centralized verified mapping cannot carry venue evidence"
                    )
            if not self.calendar_evidence_refs:
                raise TemporalComparabilityError(
                    "verified canonical mapping requires calendar evidence"
                )
            canonical_refs = (
                self.identity_evidence_refs
                + self.market_structure_evidence_refs
                + self.venue_evidence_refs
                + self.calendar_evidence_refs
            )
            if any(
                item.startswith("provider-schedule:")
                for item in canonical_refs
            ):
                raise TemporalComparabilityError(
                    "provider schedule evidence cannot satisfy canonical evidence"
                )
            if set(canonical_refs) & set(self.provider_schedule_evidence_refs):
                raise TemporalComparabilityError(
                    "provider schedule evidence cannot satisfy canonical evidence"
                )
            try:
                ZoneInfo(self.iana_timezone or "")
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise TemporalComparabilityError(
                    "verified canonical mapping IANA timezone is invalid"
                ) from exc

    def fingerprint(self) -> str:
        return _sha256(
            {
                "instrument_key": self.instrument_key,
                "provider": self.provider,
                "provider_symbol": self.provider_symbol,
                "provider_symbol_id": self.provider_symbol_id,
                "status": self.status.value,
                "canonical_instrument_id": self.canonical_instrument_id,
                "venue": self.venue,
                "market_structure": (
                    None
                    if self.market_structure is None
                    else self.market_structure.value
                ),
                "calendar_id": self.calendar_id,
                "calendar_version": self.calendar_version,
                "iana_timezone": self.iana_timezone,
                "provider_schedule_timezone": self.provider_schedule_timezone,
                "timezone_mapping_version": self.timezone_mapping_version,
                "identity_evidence_refs": self.identity_evidence_refs,
                "venue_evidence_refs": self.venue_evidence_refs,
                "calendar_evidence_refs": self.calendar_evidence_refs,
                "provider_schedule_evidence_refs": (
                    self.provider_schedule_evidence_refs
                ),
                "market_structure_evidence_refs": (
                    self.market_structure_evidence_refs
                ),
                "reason_codes": self.reason_codes,
            }
        )

    def to_binding(self) -> MarketCalendarBinding:
        if self.status is not CanonicalCalendarMappingStatus.VERIFIED:
            raise TemporalComparabilityError(
                "only VERIFIED canonical mapping may create calendar binding"
            )
        assert self.canonical_instrument_id is not None
        assert self.calendar_id is not None
        assert self.timezone_mapping_version is not None
        assert self.market_structure is not None
        provenance = tuple(
            sorted(
                set(
                    self.identity_evidence_refs
                    + self.market_structure_evidence_refs
                    + self.venue_evidence_refs
                    + self.calendar_evidence_refs
                    + self.provider_schedule_evidence_refs
                )
            )
        )
        return MarketCalendarBinding(
            instrument_key=self.instrument_key,
            canonical_instrument_id=self.canonical_instrument_id,
            calendar_id=self.calendar_id,
            provider_schedule_timezone=self.provider_schedule_timezone,
            timezone_mapping_version=self.timezone_mapping_version,
            provenance_refs=provenance,
            market_structure=self.market_structure,
        )


@dataclass(frozen=True, slots=True)
class CanonicalCalendarMappingRegistry:
    """Deterministic mapping evidence registry; no heuristic auto-promotion."""

    version: str
    records: tuple[CanonicalCalendarMappingRecord, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "canonical mapping registry version must be non-empty"
            )
        keys = tuple(item.instrument_key for item in self.records)
        if keys != tuple(sorted(keys)):
            raise TemporalComparabilityError(
                "canonical mapping records must use canonical instrument order"
            )
        if len(keys) != len(set(keys)):
            raise TemporalComparabilityError(
                "canonical mapping instrument keys must be unique"
            )
        provider_ids = tuple(
            (item.provider, item.provider_symbol_id)
            for item in self.records
        )
        if len(provider_ids) != len(set(provider_ids)):
            raise TemporalComparabilityError(
                "canonical mapping provider identities must be unique"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "canonical mapping registry provenance must be canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "records": [
                    {
                        "instrument_key": item.instrument_key,
                        "mapping_fingerprint": item.fingerprint(),
                    }
                    for item in self.records
                ],
                "provenance_refs": self.provenance_refs,
            }
        )

    def record_for(
        self,
        instrument_key: str,
    ) -> CanonicalCalendarMappingRecord | None:
        if not instrument_key.strip():
            raise TemporalComparabilityError(
                "canonical mapping lookup instrument_key must be non-empty"
            )
        return next(
            (
                item
                for item in self.records
                if item.instrument_key == instrument_key
            ),
            None,
        )

    def verified_bindings(self) -> tuple[MarketCalendarBinding, ...]:
        return tuple(
            item.to_binding()
            for item in self.records
            if item.status is CanonicalCalendarMappingStatus.VERIFIED
        )


@dataclass(frozen=True, slots=True)
class GlobalMarketCalendarRegistry:
    version: str
    calendars: tuple[GlobalMarketCalendar, ...]
    bindings: tuple[MarketCalendarBinding, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "calendar registry version must be non-empty"
            )
        calendar_ids = tuple(item.calendar_id for item in self.calendars)
        if calendar_ids != tuple(sorted(calendar_ids)):
            raise TemporalComparabilityError(
                "calendar registry calendars must be canonical"
            )
        if len(calendar_ids) != len(set(calendar_ids)):
            raise TemporalComparabilityError(
                "calendar registry calendar ids must be unique"
            )
        binding_keys = tuple(item.instrument_key for item in self.bindings)
        if binding_keys != tuple(sorted(binding_keys)):
            raise TemporalComparabilityError(
                "calendar bindings must be canonical"
            )
        if len(binding_keys) != len(set(binding_keys)):
            raise TemporalComparabilityError(
                "calendar binding instrument keys must be unique"
            )
        known = set(calendar_ids)
        if any(item.calendar_id not in known for item in self.bindings):
            raise TemporalComparabilityError(
                "calendar binding references unknown calendar"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "registry provenance must be unique and canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "calendars": [
                    {
                        "calendar_id": item.calendar_id,
                        "fingerprint": item.fingerprint(),
                    }
                    for item in self.calendars
                ],
                "bindings": [
                    {
                        "instrument_key": item.instrument_key,
                        "canonical_instrument_id": item.canonical_instrument_id,
                        "calendar_id": item.calendar_id,
                        "market_structure": item.market_structure.value,
                        "provider_schedule_timezone": (
                            item.provider_schedule_timezone
                        ),
                        "timezone_mapping_version": (
                            item.timezone_mapping_version
                        ),
                        "provenance_refs": item.provenance_refs,
                    }
                    for item in self.bindings
                ],
                "provenance_refs": self.provenance_refs,
            }
        )

    def binding_for(self, instrument_key: str) -> MarketCalendarBinding | None:
        return next(
            (
                item
                for item in self.bindings
                if item.instrument_key == instrument_key
            ),
            None,
        )

    def calendar_for(
        self,
        instrument_key: str,
    ) -> GlobalMarketCalendar | None:
        binding = self.binding_for(instrument_key)
        if binding is None:
            return None
        return next(
            (
                item
                for item in self.calendars
                if item.calendar_id == binding.calendar_id
            ),
            None,
        )


def build_governed_global_market_calendar_registry(
    *,
    version: str,
    mapping_registry: CanonicalCalendarMappingRegistry,
    calendars: tuple[GlobalMarketCalendar, ...],
    provenance_refs: tuple[str, ...],
) -> GlobalMarketCalendarRegistry:
    """Bind only independently verified mappings to exact canonical calendars."""

    if not version.strip():
        raise TemporalComparabilityError(
            "governed calendar registry version must be non-empty"
        )
    if provenance_refs != tuple(sorted(set(provenance_refs))):
        raise TemporalComparabilityError(
            "governed calendar registry provenance must be canonical"
        )
    calendar_by_id = {item.calendar_id: item for item in calendars}
    if len(calendar_by_id) != len(calendars):
        raise TemporalComparabilityError(
            "governed calendar registry calendars must be unique"
        )

    bindings: list[MarketCalendarBinding] = []
    for record in mapping_registry.records:
        if record.status is not CanonicalCalendarMappingStatus.VERIFIED:
            continue
        assert record.calendar_id is not None
        assert record.calendar_version is not None
        assert record.venue is not None
        assert record.iana_timezone is not None
        calendar = calendar_by_id.get(record.calendar_id)
        if calendar is None:
            raise TemporalComparabilityError(
                "verified mapping references missing canonical calendar"
            )
        if calendar.version != record.calendar_version:
            raise TemporalComparabilityError(
                "verified mapping calendar version drift"
            )
        if calendar.market_structure is not record.market_structure:
            raise TemporalComparabilityError(
                "verified mapping market structure drift"
            )
        if calendar.venue != record.venue:
            raise TemporalComparabilityError(
                "verified mapping calendar venue drift"
            )
        if calendar.iana_timezone != record.iana_timezone:
            raise TemporalComparabilityError(
                "verified mapping calendar timezone drift"
            )
        bindings.append(record.to_binding())

    registry_provenance = tuple(
        sorted(
            set(
                provenance_refs
                + (
                    "canonical-mapping-registry:"
                    + mapping_registry.fingerprint(),
                )
                + tuple(
                    "canonical-calendar:"
                    + item.calendar_id
                    + ":"
                    + item.fingerprint()
                    for item in calendars
                )
            )
        )
    )
    return GlobalMarketCalendarRegistry(
        version=version,
        calendars=calendars,
        bindings=tuple(sorted(bindings, key=lambda item: item.instrument_key)),
        provenance_refs=registry_provenance,
    )


@dataclass(frozen=True, slots=True)
class MarketSessionSnapshot:
    instrument_key: str
    evaluation_at: datetime
    state: MarketSessionState
    is_economically_active: bool
    calendar_id: str | None
    calendar_version: str | None
    iana_timezone: str | None
    local_date: date | None
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_aware(self.evaluation_at, field_name="session evaluation_at")
        if not self.instrument_key.strip():
            raise TemporalComparabilityError(
                "session instrument_key must be non-empty"
            )
        if type(self.is_economically_active) is not bool:
            raise TemporalComparabilityError(
                "is_economically_active must be bool"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "session provenance must be unique and canonical"
            )


def _boundary_key(boundary: WallClockBoundary) -> tuple[int, int, int]:
    return boundary.logical_values()


def _window(
    *,
    local_date: date,
    opens_at: WallClockBoundary,
    closes_at: WallClockBoundary,
    timezone_name: str,
) -> tuple[datetime, datetime] | None:
    close_date = local_date
    if _boundary_key(closes_at) <= _boundary_key(opens_at):
        close_date += timedelta(days=1)
    opened = resolve_wall_clock_boundary_utc(
        local_date=local_date,
        boundary=opens_at,
        timezone_name=timezone_name,
    )
    closed = resolve_wall_clock_boundary_utc(
        local_date=close_date,
        boundary=closes_at,
        timezone_name=timezone_name,
    )
    if opened is None or closed is None:
        return None
    if closed <= opened:
        raise TemporalComparabilityError(
            "calendar interval must close after it opens"
        )
    return (opened, closed)


def evaluate_market_session(
    *,
    registry: GlobalMarketCalendarRegistry,
    instrument_key: str,
    evaluation_at: datetime,
    halted: bool = False,
) -> MarketSessionSnapshot:
    """Evaluate canonical market session state at an exact causal instant."""

    _require_aware(evaluation_at, field_name="market evaluation_at")
    evaluation = evaluation_at.astimezone(UTC)
    binding = registry.binding_for(instrument_key)
    calendar = registry.calendar_for(instrument_key)
    if binding is None or calendar is None:
        return MarketSessionSnapshot(
            instrument_key=instrument_key,
            evaluation_at=evaluation,
            state=MarketSessionState.UNKNOWN,
            is_economically_active=False,
            calendar_id=None,
            calendar_version=None,
            iana_timezone=None,
            local_date=None,
            provenance_refs=(
                f"calendar-registry:{registry.fingerprint()}",
            ),
        )

    zone = ZoneInfo(calendar.iana_timezone)
    local_date = evaluation.astimezone(zone).date()
    provenance = tuple(
        sorted(
            set(
                registry.provenance_refs
                + calendar.provenance_refs
                + binding.provenance_refs
            )
        )
    )
    if halted:
        return MarketSessionSnapshot(
            instrument_key=instrument_key,
            evaluation_at=evaluation,
            state=MarketSessionState.HALTED,
            is_economically_active=False,
            calendar_id=calendar.calendar_id,
            calendar_version=calendar.version,
            iana_timezone=calendar.iana_timezone,
            local_date=local_date,
            provenance_refs=provenance,
        )

    override = next(
        (
            item
            for item in calendar.date_overrides
            if item.local_date == local_date
        ),
        None,
    )
    if override is not None:
        if override.state is MarketSessionState.HOLIDAY:
            return MarketSessionSnapshot(
                instrument_key=instrument_key,
                evaluation_at=evaluation,
                state=MarketSessionState.HOLIDAY,
                is_economically_active=False,
                calendar_id=calendar.calendar_id,
                calendar_version=calendar.version,
                iana_timezone=calendar.iana_timezone,
                local_date=local_date,
                provenance_refs=provenance,
            )
        for interval in override.intervals:
            bounds = _window(
                local_date=local_date,
                opens_at=interval.opens_at,
                closes_at=interval.closes_at,
                timezone_name=calendar.iana_timezone,
            )
            if bounds is None:
                return MarketSessionSnapshot(
                    instrument_key=instrument_key,
                    evaluation_at=evaluation,
                    state=MarketSessionState.UNKNOWN,
                    is_economically_active=False,
                    calendar_id=calendar.calendar_id,
                    calendar_version=calendar.version,
                    iana_timezone=calendar.iana_timezone,
                    local_date=local_date,
                    provenance_refs=provenance,
                )
            if bounds[0] <= evaluation < bounds[1]:
                return MarketSessionSnapshot(
                    instrument_key=instrument_key,
                    evaluation_at=evaluation,
                    state=MarketSessionState.PARTIAL_SESSION,
                    is_economically_active=True,
                    calendar_id=calendar.calendar_id,
                    calendar_version=calendar.version,
                    iana_timezone=calendar.iana_timezone,
                    local_date=local_date,
                    provenance_refs=provenance,
                )
        return MarketSessionSnapshot(
            instrument_key=instrument_key,
            evaluation_at=evaluation,
            state=MarketSessionState.PARTIAL_SESSION,
            is_economically_active=False,
            calendar_id=calendar.calendar_id,
            calendar_version=calendar.version,
            iana_timezone=calendar.iana_timezone,
            local_date=local_date,
            provenance_refs=provenance,
        )

    active_state: MarketSessionState | None = None
    current_day_windows: list[tuple[datetime, datetime]] = []
    previous_day_windows: list[tuple[datetime, datetime]] = []
    previous_anchor = local_date - timedelta(days=1)
    for anchor_date in (previous_anchor, local_date):
        for rule in calendar.weekly_sessions:
            if rule.weekday != anchor_date.weekday():
                continue
            bounds = _window(
                local_date=anchor_date,
                opens_at=rule.opens_at,
                closes_at=rule.closes_at,
                timezone_name=calendar.iana_timezone,
            )
            if bounds is None:
                return MarketSessionSnapshot(
                    instrument_key=instrument_key,
                    evaluation_at=evaluation,
                    state=MarketSessionState.UNKNOWN,
                    is_economically_active=False,
                    calendar_id=calendar.calendar_id,
                    calendar_version=calendar.version,
                    iana_timezone=calendar.iana_timezone,
                    local_date=local_date,
                    provenance_refs=provenance,
                )
            if anchor_date == local_date:
                current_day_windows.append(bounds)
            elif anchor_date == previous_anchor:
                previous_day_windows.append(bounds)
            if bounds[0] <= evaluation < bounds[1]:
                active_state = rule.state

    if active_state is not None:
        return MarketSessionSnapshot(
            instrument_key=instrument_key,
            evaluation_at=evaluation,
            state=active_state,
            is_economically_active=True,
            calendar_id=calendar.calendar_id,
            calendar_version=calendar.version,
            iana_timezone=calendar.iana_timezone,
            local_date=local_date,
            provenance_refs=provenance,
        )

    if not current_day_windows:
        inactive_state = MarketSessionState.CLOSED
    else:
        first_open = min(item[0] for item in current_day_windows)
        last_close = max(item[1] for item in current_day_windows)
        previous_closes_today = tuple(
            closed
            for _, closed in previous_day_windows
            if closed.astimezone(zone).date() == local_date
        )
        if evaluation < first_open:
            if (
                previous_closes_today
                and evaluation >= max(previous_closes_today)
            ):
                inactive_state = MarketSessionState.SESSION_BREAK
            else:
                inactive_state = MarketSessionState.PRE_SESSION
        elif evaluation >= last_close:
            inactive_state = MarketSessionState.POST_SESSION
        else:
            inactive_state = MarketSessionState.SESSION_BREAK

    return MarketSessionSnapshot(
        instrument_key=instrument_key,
        evaluation_at=evaluation,
        state=inactive_state,
        is_economically_active=False,
        calendar_id=calendar.calendar_id,
        calendar_version=calendar.version,
        iana_timezone=calendar.iana_timezone,
        local_date=local_date,
        provenance_refs=provenance,
    )


@dataclass(frozen=True, slots=True)
class ProviderInstrumentIdentity:
    instrument_key: str
    provider: str
    provider_symbol_id: int

    def __post_init__(self) -> None:
        if not self.instrument_key.strip() or not self.provider.strip():
            raise TemporalComparabilityError(
                "provider identity must be explicit"
            )
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise TemporalComparabilityError(
                "provider_symbol_id must be positive int"
            )


@dataclass(frozen=True, slots=True)
class TemporalMarketObservation:
    identity: ProviderInstrumentIdentity
    canonical_instrument_id: str
    market_time_at: datetime | None
    venue_time_at: datetime | None
    provider_event_time_at: datetime
    receipt_time_at: datetime
    observation_time_at: datetime
    processing_time_at: datetime
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.canonical_instrument_id.strip():
            raise TemporalComparabilityError(
                "canonical_instrument_id must be non-empty"
            )
        if not self.evidence_ref.strip():
            raise TemporalComparabilityError(
                "observation evidence_ref must be non-empty"
            )
        for name in (
            "provider_event_time_at",
            "receipt_time_at",
            "observation_time_at",
            "processing_time_at",
        ):
            _require_aware(getattr(self, name), field_name=name)
        for name in ("market_time_at", "venue_time_at"):
            value = getattr(self, name)
            if value is not None:
                _require_aware(value, field_name=name)
                if value > self.provider_event_time_at:
                    raise TemporalComparabilityError(
                        f"{name} cannot be after provider event time"
                    )
        if not (
            self.provider_event_time_at
            <= self.receipt_time_at
            <= self.observation_time_at
            <= self.processing_time_at
        ):
            raise TemporalComparabilityError(
                "provider_event <= receipt <= observation <= processing required"
            )


@dataclass(frozen=True, slots=True)
class AlignedTemporalPair:
    evaluation_at: datetime
    source_identity: ProviderInstrumentIdentity
    target_identity: ProviderInstrumentIdentity
    source: TemporalMarketObservation | None
    target: TemporalMarketObservation | None
    source_age_ms: int | None
    target_age_ms: int | None
    temporal_skew_ms: int | None

    def __post_init__(self) -> None:
        _require_aware(self.evaluation_at, field_name="pair evaluation_at")


class GlobalTemporalAlignmentEngine:
    """Select latest legally observable states without future pairing."""

    @staticmethod
    def latest_at(
        observations: Sequence[TemporalMarketObservation],
        *,
        evaluation_at: datetime,
        expected_identity: ProviderInstrumentIdentity,
    ) -> TemporalMarketObservation | None:
        _require_aware(evaluation_at, field_name="alignment evaluation_at")
        evaluation = evaluation_at.astimezone(UTC)
        rows = tuple(observations)
        for item in rows:
            if item.identity != expected_identity:
                raise TemporalComparabilityError(
                    "provider identity drift in temporal alignment"
                )
            if (
                item.provider_event_time_at > evaluation
                or item.receipt_time_at > evaluation
                or item.observation_time_at > evaluation
                or item.processing_time_at > evaluation
            ):
                raise TemporalComparabilityError(
                    "future observation supplied to historical alignment"
                )
        if not rows:
            return None
        return max(
            rows,
            key=lambda item: (
                item.provider_event_time_at,
                item.receipt_time_at,
                item.processing_time_at,
                item.evidence_ref,
            ),
        )

    @classmethod
    def align_pair(
        cls,
        *,
        source_observations: Sequence[TemporalMarketObservation],
        target_observations: Sequence[TemporalMarketObservation],
        evaluation_at: datetime,
        source_identity: ProviderInstrumentIdentity,
        target_identity: ProviderInstrumentIdentity,
    ) -> AlignedTemporalPair:
        _require_aware(evaluation_at, field_name="pair evaluation_at")
        evaluation = evaluation_at.astimezone(UTC)
        source = cls.latest_at(
            source_observations,
            evaluation_at=evaluation,
            expected_identity=source_identity,
        )
        target = cls.latest_at(
            target_observations,
            evaluation_at=evaluation,
            expected_identity=target_identity,
        )
        source_age = (
            None
            if source is None
            else _millis(evaluation - source.provider_event_time_at)
        )
        target_age = (
            None
            if target is None
            else _millis(evaluation - target.provider_event_time_at)
        )
        skew = (
            None
            if source is None or target is None
            else abs(
                _millis(
                    source.provider_event_time_at
                    - target.provider_event_time_at
                )
            )
        )
        return AlignedTemporalPair(
            evaluation_at=evaluation,
            source_identity=source_identity,
            target_identity=target_identity,
            source=source,
            target=target,
            source_age_ms=source_age,
            target_age_ms=target_age,
            temporal_skew_ms=skew,
        )


@dataclass(frozen=True, slots=True)
class ExpectedUpdateCadencePolicy:
    version: str
    instrument_key: str
    provider: str
    session_state: MarketSessionState
    expected_interval_ms: int
    delayed_after_ms: int
    stale_after_ms: int
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "cadence policy version must be non-empty"
            )
        if not self.instrument_key.strip() or not self.provider.strip():
            raise TemporalComparabilityError(
                "cadence policy identity must be explicit"
            )
        for name in (
            "expected_interval_ms",
            "delayed_after_ms",
            "stale_after_ms",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise TemporalComparabilityError(
                    f"{name} must be positive int"
                )
        if not (
            self.expected_interval_ms
            <= self.delayed_after_ms
            <= self.stale_after_ms
        ):
            raise TemporalComparabilityError(
                "cadence thresholds must be monotonic"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "cadence provenance must be unique and canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "instrument_key": self.instrument_key,
                "provider": self.provider,
                "session_state": self.session_state.value,
                "expected_interval_ms": self.expected_interval_ms,
                "delayed_after_ms": self.delayed_after_ms,
                "stale_after_ms": self.stale_after_ms,
                "provenance_refs": self.provenance_refs,
            }
        )


@dataclass(frozen=True, slots=True)
class ExpectedUpdateCadencePolicyRegistry:
    """Exact instrument/provider/session cadence policies; no global stale fallback."""

    version: str
    policies: tuple[ExpectedUpdateCadencePolicy, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "cadence registry version must be non-empty"
            )
        keys = tuple(
            (
                item.instrument_key,
                item.provider,
                item.session_state.value,
            )
            for item in self.policies
        )
        if keys != tuple(sorted(keys)):
            raise TemporalComparabilityError(
                "cadence policies must use canonical key order"
            )
        if len(keys) != len(set(keys)):
            raise TemporalComparabilityError(
                "cadence policy keys must be unique"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "cadence registry provenance must be canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "policies": [
                    {
                        "instrument_key": item.instrument_key,
                        "provider": item.provider,
                        "session_state": item.session_state.value,
                        "policy_fingerprint": item.fingerprint(),
                    }
                    for item in self.policies
                ],
                "provenance_refs": self.provenance_refs,
            }
        )

    def policy_for(
        self,
        *,
        instrument_key: str,
        provider: str,
        session_state: MarketSessionState,
    ) -> ExpectedUpdateCadencePolicy | None:
        if not instrument_key.strip() or not provider.strip():
            raise TemporalComparabilityError(
                "cadence lookup identity must be explicit"
            )
        return next(
            (
                item
                for item in self.policies
                if item.instrument_key == instrument_key
                and item.provider == provider
                and item.session_state is session_state
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class ProviderObservabilitySnapshot:
    identity: ProviderInstrumentIdentity
    evaluation_at: datetime
    state: ProviderObservabilityState
    update_age_ms: int | None
    transport_delay_ms: int | None
    cadence_policy_version: str
    cadence_policy_fingerprint: str
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_aware(
            self.evaluation_at,
            field_name="provider evaluation_at",
        )
        if self.update_age_ms is not None and self.update_age_ms < 0:
            raise TemporalComparabilityError(
                "provider update_age_ms cannot be negative"
            )
        if (
            self.transport_delay_ms is not None
            and self.transport_delay_ms < 0
        ):
            raise TemporalComparabilityError(
                "provider transport_delay_ms cannot be negative"
            )


def assess_provider_observability(
    *,
    identity: ProviderInstrumentIdentity,
    observation: TemporalMarketObservation | None,
    evaluation_at: datetime,
    cadence: ExpectedUpdateCadencePolicy,
    operational_signal: ProviderOperationalSignal,
    provenance_refs: tuple[str, ...],
) -> ProviderObservabilitySnapshot:
    """Separate provider health from market behavior and quote freshness."""

    _require_aware(evaluation_at, field_name="provider evaluation_at")
    evaluation = evaluation_at.astimezone(UTC)
    if cadence.instrument_key != identity.instrument_key:
        raise TemporalComparabilityError(
            "cadence instrument identity mismatch"
        )
    if cadence.provider != identity.provider:
        raise TemporalComparabilityError("cadence provider identity mismatch")
    if provenance_refs != tuple(sorted(set(provenance_refs))):
        raise TemporalComparabilityError(
            "provider provenance must be unique and canonical"
        )
    if observation is not None and observation.identity != identity:
        raise TemporalComparabilityError(
            "provider observation identity drift"
        )
    if observation is not None and observation.processing_time_at > evaluation:
        raise TemporalComparabilityError(
            "future provider observation is forbidden"
        )

    update_age_ms: int | None = None
    transport_delay_ms: int | None = None
    if observation is not None:
        update_age_ms = _millis(
            evaluation - observation.provider_event_time_at
        )
        transport_delay_ms = _millis(
            observation.receipt_time_at
            - observation.provider_event_time_at
        )

    if operational_signal is ProviderOperationalSignal.UNAVAILABLE:
        state = ProviderObservabilityState.UNAVAILABLE
    elif operational_signal is ProviderOperationalSignal.DEGRADED:
        state = ProviderObservabilityState.DEGRADED
    elif operational_signal is ProviderOperationalSignal.PARTIAL:
        state = ProviderObservabilityState.PARTIAL
    elif operational_signal is ProviderOperationalSignal.UNKNOWN:
        state = ProviderObservabilityState.UNKNOWN
    elif observation is None or update_age_ms is None:
        state = ProviderObservabilityState.UNKNOWN
    elif update_age_ms > cadence.stale_after_ms:
        state = ProviderObservabilityState.STALE
    elif (
        transport_delay_ms is not None
        and transport_delay_ms > cadence.delayed_after_ms
    ):
        state = ProviderObservabilityState.DELAYED
    else:
        state = ProviderObservabilityState.HEALTHY

    return ProviderObservabilitySnapshot(
        identity=identity,
        evaluation_at=evaluation,
        state=state,
        update_age_ms=update_age_ms,
        transport_delay_ms=transport_delay_ms,
        cadence_policy_version=cadence.version,
        cadence_policy_fingerprint=cadence.fingerprint(),
        provenance_refs=provenance_refs,
    )


@dataclass(frozen=True, slots=True)
class LiquidityObservation:
    instrument_key: str
    evaluation_at: datetime
    state: LiquidityState
    activity_ratio_bps: int
    spread_quality_bps: int
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_aware(
            self.evaluation_at,
            field_name="liquidity evaluation_at",
        )
        if not self.instrument_key.strip():
            raise TemporalComparabilityError(
                "liquidity instrument_key must be non-empty"
            )
        for name in ("activity_ratio_bps", "spread_quality_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise TemporalComparabilityError(
                    f"{name} must be int within 0..10000"
                )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "liquidity provenance must be unique and canonical"
            )


@dataclass(frozen=True, slots=True)
class LiquidityObservabilityPolicy:
    """Policy for interpreting measured activity without hiding provider health."""

    version: str
    instrument_key: str
    provider: str
    session_state: MarketSessionState
    normal_activity_ratio_bps: int
    illiquid_below_activity_ratio_bps: int
    minimum_spread_quality_bps: int
    max_provider_update_age_ms: int
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "liquidity policy version must be non-empty"
            )
        if not self.instrument_key.strip() or not self.provider.strip():
            raise TemporalComparabilityError(
                "liquidity policy identity must be explicit"
            )
        for name in (
            "normal_activity_ratio_bps",
            "illiquid_below_activity_ratio_bps",
            "minimum_spread_quality_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise TemporalComparabilityError(
                    f"{name} must be int within 0..10000"
                )
        if (
            self.illiquid_below_activity_ratio_bps
            > self.normal_activity_ratio_bps
        ):
            raise TemporalComparabilityError(
                "illiquid activity threshold cannot exceed normal threshold"
            )
        if (
            type(self.max_provider_update_age_ms) is not int
            or self.max_provider_update_age_ms <= 0
        ):
            raise TemporalComparabilityError(
                "max_provider_update_age_ms must be positive int"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "liquidity policy provenance must be canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "instrument_key": self.instrument_key,
                "provider": self.provider,
                "session_state": self.session_state.value,
                "normal_activity_ratio_bps": self.normal_activity_ratio_bps,
                "illiquid_below_activity_ratio_bps": (
                    self.illiquid_below_activity_ratio_bps
                ),
                "minimum_spread_quality_bps": (
                    self.minimum_spread_quality_bps
                ),
                "max_provider_update_age_ms": (
                    self.max_provider_update_age_ms
                ),
                "provenance_refs": self.provenance_refs,
            }
        )


def assess_liquidity_observability(
    *,
    identity: ProviderInstrumentIdentity,
    evaluation_at: datetime,
    provider_snapshot: ProviderObservabilitySnapshot,
    session_state: MarketSessionState,
    activity_ratio_bps: int,
    spread_quality_bps: int,
    policy: LiquidityObservabilityPolicy,
    provenance_refs: tuple[str, ...],
) -> LiquidityObservation:
    """Interpret measured liquidity while failing closed on provider uncertainty."""

    _require_aware(evaluation_at, field_name="liquidity evaluation_at")
    evaluation = evaluation_at.astimezone(UTC)
    if provider_snapshot.identity != identity:
        raise TemporalComparabilityError(
            "liquidity provider identity drift"
        )
    if provider_snapshot.evaluation_at.astimezone(UTC) != evaluation:
        raise TemporalComparabilityError(
            "liquidity provider evaluation time drift"
        )
    if policy.instrument_key != identity.instrument_key:
        raise TemporalComparabilityError(
            "liquidity policy instrument identity mismatch"
        )
    if policy.provider != identity.provider:
        raise TemporalComparabilityError(
            "liquidity policy provider identity mismatch"
        )
    if policy.session_state is not session_state:
        raise TemporalComparabilityError(
            "liquidity policy session state mismatch"
        )
    for name, value in (
        ("activity_ratio_bps", activity_ratio_bps),
        ("spread_quality_bps", spread_quality_bps),
    ):
        if type(value) is not int or not 0 <= value <= 10_000:
            raise TemporalComparabilityError(
                f"{name} must be int within 0..10000"
            )
    if provenance_refs != tuple(sorted(set(provenance_refs))):
        raise TemporalComparabilityError(
            "liquidity provenance must be unique and canonical"
        )

    provider_unreliable = provider_snapshot.state in {
        ProviderObservabilityState.PARTIAL,
        ProviderObservabilityState.DEGRADED,
        ProviderObservabilityState.UNAVAILABLE,
        ProviderObservabilityState.UNKNOWN,
        ProviderObservabilityState.STALE,
    }
    if (
        provider_unreliable
        or provider_snapshot.update_age_ms is None
        or provider_snapshot.update_age_ms > policy.max_provider_update_age_ms
    ):
        state = LiquidityState.UNKNOWN
    elif activity_ratio_bps < policy.illiquid_below_activity_ratio_bps:
        state = LiquidityState.ILLIQUID
    elif (
        activity_ratio_bps < policy.normal_activity_ratio_bps
        or spread_quality_bps < policy.minimum_spread_quality_bps
    ):
        state = LiquidityState.LOW
    else:
        state = LiquidityState.NORMAL

    return LiquidityObservation(
        instrument_key=identity.instrument_key,
        evaluation_at=evaluation,
        state=state,
        activity_ratio_bps=activity_ratio_bps,
        spread_quality_bps=spread_quality_bps,
        provenance_refs=provenance_refs,
    )


@dataclass(frozen=True, slots=True)
class TemporalSkewPolicy:
    """Scope-specific cross-market skew budget with no universal fallback."""

    version: str
    relation_kind: str
    source_family: str
    target_family: str
    horizon: str
    session_scope: str
    liquidity_scope: str
    max_temporal_skew_ms: int
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "version",
            "relation_kind",
            "source_family",
            "target_family",
            "horizon",
            "session_scope",
            "liquidity_scope",
        ):
            if not str(getattr(self, name)).strip():
                raise TemporalComparabilityError(
                    f"temporal skew {name} must be non-empty"
                )
        if (
            type(self.max_temporal_skew_ms) is not int
            or self.max_temporal_skew_ms < 0
        ):
            raise TemporalComparabilityError(
                "max_temporal_skew_ms must be non-negative int"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "temporal skew provenance must be canonical"
            )

    def scope_key(self) -> tuple[str, ...]:
        return (
            self.relation_kind,
            self.source_family,
            self.target_family,
            self.horizon,
            self.session_scope,
            self.liquidity_scope,
        )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "scope_key": self.scope_key(),
                "max_temporal_skew_ms": self.max_temporal_skew_ms,
                "provenance_refs": self.provenance_refs,
            }
        )


@dataclass(frozen=True, slots=True)
class TemporalSkewPolicyRegistry:
    version: str
    policies: tuple[TemporalSkewPolicy, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "temporal skew registry version must be non-empty"
            )
        keys = tuple(item.scope_key() for item in self.policies)
        if keys != tuple(sorted(keys)):
            raise TemporalComparabilityError(
                "temporal skew policies must use canonical scope order"
            )
        if len(keys) != len(set(keys)):
            raise TemporalComparabilityError(
                "temporal skew policy scopes must be unique"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "temporal skew registry provenance must be canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "policies": [
                    {
                        "scope_key": item.scope_key(),
                        "policy_fingerprint": item.fingerprint(),
                    }
                    for item in self.policies
                ],
                "provenance_refs": self.provenance_refs,
            }
        )

    def policy_for(
        self,
        *,
        relation_kind: str,
        source_family: str,
        target_family: str,
        horizon: str,
        session_scope: str,
        liquidity_scope: str,
    ) -> TemporalSkewPolicy | None:
        key = (
            relation_kind,
            source_family,
            target_family,
            horizon,
            session_scope,
            liquidity_scope,
        )
        if any(not item.strip() for item in key):
            raise TemporalComparabilityError(
                "temporal skew lookup scope must be explicit"
            )
        return next(
            (item for item in self.policies if item.scope_key() == key),
            None,
        )


@dataclass(frozen=True, slots=True)
class RelationalComparabilityPolicy:
    version: str
    relation_scope: str
    source_max_age_ms: int
    target_max_age_ms: int
    max_temporal_skew_ms: int
    minimum_activity_ratio_bps: int
    allow_open_low_liquidity: bool
    allow_partial_session: bool
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip() or not self.relation_scope.strip():
            raise TemporalComparabilityError(
                "comparability policy identity must be explicit"
            )
        for name in (
            "source_max_age_ms",
            "target_max_age_ms",
            "max_temporal_skew_ms",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise TemporalComparabilityError(
                    f"{name} must be non-negative int"
                )
        if (
            type(self.minimum_activity_ratio_bps) is not int
            or not 0 <= self.minimum_activity_ratio_bps <= 10_000
        ):
            raise TemporalComparabilityError(
                "minimum_activity_ratio_bps must be 0..10000"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "policy provenance must be unique and canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "relation_scope": self.relation_scope,
                "source_max_age_ms": self.source_max_age_ms,
                "target_max_age_ms": self.target_max_age_ms,
                "max_temporal_skew_ms": self.max_temporal_skew_ms,
                "minimum_activity_ratio_bps": (
                    self.minimum_activity_ratio_bps
                ),
                "allow_open_low_liquidity": (
                    self.allow_open_low_liquidity
                ),
                "allow_partial_session": self.allow_partial_session,
                "provenance_refs": self.provenance_refs,
            }
        )


@dataclass(frozen=True, slots=True)
class RelationalComparabilityPolicyRegistry:
    """Versioned exact-match policy registry with no implicit fallback."""

    version: str
    policies: tuple[RelationalComparabilityPolicy, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise TemporalComparabilityError(
                "comparability policy registry version must be non-empty"
            )
        scopes = tuple(item.relation_scope for item in self.policies)
        if scopes != tuple(sorted(scopes)):
            raise TemporalComparabilityError(
                "comparability policies must use canonical scope order"
            )
        if len(scopes) != len(set(scopes)):
            raise TemporalComparabilityError(
                "comparability policy scopes must be unique"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "comparability registry provenance must be unique and canonical"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "version": self.version,
                "policies": [
                    {
                        "relation_scope": item.relation_scope,
                        "policy_version": item.version,
                        "policy_fingerprint": item.fingerprint(),
                    }
                    for item in self.policies
                ],
                "provenance_refs": self.provenance_refs,
            }
        )

    def policy_for(
        self,
        relation_scope: str,
    ) -> RelationalComparabilityPolicy | None:
        """Return only an exact governed policy; unknown scope remains unresolved."""

        if not relation_scope.strip():
            raise TemporalComparabilityError(
                "relation_scope lookup must be non-empty"
            )
        return next(
            (
                item
                for item in self.policies
                if item.relation_scope == relation_scope
            ),
            None,
        )


class TemporalGovernanceClosureStatus(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True, slots=True)
class TemporalGovernanceClosureAssessment:
    """Machine-readable GEN-2 closure gate; never grants relational authority."""

    status: TemporalGovernanceClosureStatus
    sensor_count: int
    canonical_mapping_verified_count: int
    calendar_count: int
    binding_count: int
    cadence_policy_registry_frozen: bool
    liquidity_policy_registry_frozen: bool
    temporal_skew_policy_registry_frozen: bool
    comparability_policy_registry_frozen: bool
    anti_leakage_pass: bool
    deterministic_validation_pass: bool
    blockers: tuple[str, ...]
    relational_claims_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "sensor_count",
            "canonical_mapping_verified_count",
            "calendar_count",
            "binding_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise TemporalComparabilityError(
                    f"{name} must be non-negative int"
                )
        for name in (
            "cadence_policy_registry_frozen",
            "liquidity_policy_registry_frozen",
            "temporal_skew_policy_registry_frozen",
            "comparability_policy_registry_frozen",
            "anti_leakage_pass",
            "deterministic_validation_pass",
            "relational_claims_authorized",
        ):
            if type(getattr(self, name)) is not bool:
                raise TemporalComparabilityError(
                    f"{name} must be strict bool"
                )
        if self.blockers != tuple(sorted(set(self.blockers))):
            raise TemporalComparabilityError(
                "temporal governance blockers must be canonical"
            )
        expected = (
            TemporalGovernanceClosureStatus.READY
            if not self.blockers
            else TemporalGovernanceClosureStatus.NOT_READY
        )
        if self.status is not expected:
            raise TemporalComparabilityError(
                "temporal governance status/blocker mismatch"
            )
        if self.relational_claims_authorized:
            raise TemporalComparabilityError(
                "GEN-2 closure cannot authorize relational claims"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "status": self.status.value,
                "sensor_count": self.sensor_count,
                "canonical_mapping_verified_count": (
                    self.canonical_mapping_verified_count
                ),
                "calendar_count": self.calendar_count,
                "binding_count": self.binding_count,
                "cadence_policy_registry_frozen": (
                    self.cadence_policy_registry_frozen
                ),
                "liquidity_policy_registry_frozen": (
                    self.liquidity_policy_registry_frozen
                ),
                "temporal_skew_policy_registry_frozen": (
                    self.temporal_skew_policy_registry_frozen
                ),
                "comparability_policy_registry_frozen": (
                    self.comparability_policy_registry_frozen
                ),
                "anti_leakage_pass": self.anti_leakage_pass,
                "deterministic_validation_pass": (
                    self.deterministic_validation_pass
                ),
                "blockers": self.blockers,
                "relational_claims_authorized": False,
            }
        )


def assess_temporal_governance_closure(
    *,
    sensor_count: int,
    canonical_mapping_verified_count: int,
    calendar_count: int,
    binding_count: int,
    cadence_policy_registry_frozen: bool,
    liquidity_policy_registry_frozen: bool,
    temporal_skew_policy_registry_frozen: bool,
    comparability_policy_registry_frozen: bool,
    anti_leakage_pass: bool,
    deterministic_validation_pass: bool,
) -> TemporalGovernanceClosureAssessment:
    """Evaluate GEN-2 closure independently from later relation science."""

    blockers: list[str] = []
    if sensor_count <= 0:
        blockers.append("SENSOR_UNIVERSE_EMPTY")
    if canonical_mapping_verified_count != sensor_count:
        blockers.append("CANONICAL_MAPPING_INCOMPLETE")
    if calendar_count <= 0:
        blockers.append("CANONICAL_CALENDAR_REGISTRY_EMPTY")
    if binding_count != sensor_count:
        blockers.append("CALENDAR_BINDING_INCOMPLETE")
    if not cadence_policy_registry_frozen:
        blockers.append("CADENCE_POLICY_REGISTRY_NOT_FROZEN")
    if not liquidity_policy_registry_frozen:
        blockers.append("LIQUIDITY_POLICY_REGISTRY_NOT_FROZEN")
    if not temporal_skew_policy_registry_frozen:
        blockers.append("TEMPORAL_SKEW_POLICY_REGISTRY_NOT_FROZEN")
    if not comparability_policy_registry_frozen:
        blockers.append("COMPARABILITY_POLICY_REGISTRY_NOT_FROZEN")
    if not anti_leakage_pass:
        blockers.append("ANTI_LEAKAGE_NOT_PASS")
    if not deterministic_validation_pass:
        blockers.append("DETERMINISTIC_VALIDATION_NOT_PASS")

    canonical_blockers = tuple(sorted(set(blockers)))
    status = (
        TemporalGovernanceClosureStatus.READY
        if not canonical_blockers
        else TemporalGovernanceClosureStatus.NOT_READY
    )
    return TemporalGovernanceClosureAssessment(
        status=status,
        sensor_count=sensor_count,
        canonical_mapping_verified_count=canonical_mapping_verified_count,
        calendar_count=calendar_count,
        binding_count=binding_count,
        cadence_policy_registry_frozen=cadence_policy_registry_frozen,
        liquidity_policy_registry_frozen=liquidity_policy_registry_frozen,
        temporal_skew_policy_registry_frozen=temporal_skew_policy_registry_frozen,
        comparability_policy_registry_frozen=comparability_policy_registry_frozen,
        anti_leakage_pass=anti_leakage_pass,
        deterministic_validation_pass=deterministic_validation_pass,
        blockers=canonical_blockers,
    )


@dataclass(frozen=True, slots=True)
class RelationalObservation:
    source_identity: ProviderInstrumentIdentity
    target_identity: ProviderInstrumentIdentity
    evaluation_at: datetime
    source_event_at: datetime | None
    target_event_at: datetime | None
    source_age_ms: int | None
    target_age_ms: int | None
    source_session_state: MarketSessionState
    target_session_state: MarketSessionState
    source_liquidity_state: LiquidityState
    target_liquidity_state: LiquidityState
    source_provider_state: ProviderObservabilityState
    target_provider_state: ProviderObservabilityState
    temporal_skew_ms: int | None
    comparability_state: RelationalComparabilityState
    confidence: ComparabilityConfidence
    uncertainty: ComparabilityUncertainty
    calendar_registry_fingerprint: str
    comparability_policy_version: str
    comparability_policy_fingerprint: str
    provenance_refs: tuple[str, ...]
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _require_aware(
            self.evaluation_at,
            field_name="relational evaluation_at",
        )
        for value in (self.source_event_at, self.target_event_at):
            if value is not None:
                _require_aware(value, field_name="relational event time")
                if value > self.evaluation_at:
                    raise TemporalComparabilityError(
                        "future relational event is forbidden"
                    )
        for name in (
            "calendar_registry_fingerprint",
            "comparability_policy_fingerprint",
        ):
            value = getattr(self, name)
            if len(value) != 64:
                raise TemporalComparabilityError(
                    f"{name} must be sha256 hex"
                )
            try:
                int(value, 16)
            except ValueError as exc:
                raise TemporalComparabilityError(
                    f"{name} must be sha256 hex"
                ) from exc
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise TemporalComparabilityError(
                "relational provenance must be unique and canonical"
            )
        if (
            self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise TemporalComparabilityError(
                "relational observation cannot carry sovereign authority"
            )

    def fingerprint(self) -> str:
        return _sha256(
            {
                "source_identity": (
                    self.source_identity.instrument_key,
                    self.source_identity.provider,
                    self.source_identity.provider_symbol_id,
                ),
                "target_identity": (
                    self.target_identity.instrument_key,
                    self.target_identity.provider,
                    self.target_identity.provider_symbol_id,
                ),
                "evaluation_at": self.evaluation_at.astimezone(UTC).isoformat(),
                "source_event_at": (
                    None
                    if self.source_event_at is None
                    else self.source_event_at.astimezone(UTC).isoformat()
                ),
                "target_event_at": (
                    None
                    if self.target_event_at is None
                    else self.target_event_at.astimezone(UTC).isoformat()
                ),
                "source_age_ms": self.source_age_ms,
                "target_age_ms": self.target_age_ms,
                "source_session_state": self.source_session_state.value,
                "target_session_state": self.target_session_state.value,
                "source_liquidity_state": self.source_liquidity_state.value,
                "target_liquidity_state": self.target_liquidity_state.value,
                "source_provider_state": self.source_provider_state.value,
                "target_provider_state": self.target_provider_state.value,
                "temporal_skew_ms": self.temporal_skew_ms,
                "comparability_state": self.comparability_state.value,
                "confidence": self.confidence.value,
                "uncertainty": self.uncertainty.value,
                "calendar_registry_fingerprint": (
                    self.calendar_registry_fingerprint
                ),
                "comparability_policy_version": (
                    self.comparability_policy_version
                ),
                "comparability_policy_fingerprint": (
                    self.comparability_policy_fingerprint
                ),
                "provenance_refs": self.provenance_refs,
            }
        )


def _confidence(
    state: RelationalComparabilityState,
) -> tuple[ComparabilityConfidence, ComparabilityUncertainty]:
    if state is RelationalComparabilityState.COMPARABLE:
        return (
            ComparabilityConfidence.HIGH,
            ComparabilityUncertainty.LOW,
        )
    if state is RelationalComparabilityState.PARTIALLY_COMPARABLE:
        return (
            ComparabilityConfidence.MEDIUM,
            ComparabilityUncertainty.MEDIUM,
        )
    if state is RelationalComparabilityState.INSUFFICIENT:
        return (
            ComparabilityConfidence.UNKNOWN,
            ComparabilityUncertainty.MAXIMUM,
        )
    return (
        ComparabilityConfidence.LOW,
        ComparabilityUncertainty.HIGH,
    )


def assess_relational_comparability(
    *,
    pair: AlignedTemporalPair,
    source_session: MarketSessionSnapshot,
    target_session: MarketSessionSnapshot,
    source_provider: ProviderObservabilitySnapshot,
    target_provider: ProviderObservabilitySnapshot,
    source_liquidity: LiquidityObservation,
    target_liquidity: LiquidityObservation,
    policy: RelationalComparabilityPolicy,
    calendar_registry_fingerprint: str,
    provenance_refs: tuple[str, ...],
) -> RelationalObservation:
    """Fail closed before any future relational claim is allowed."""

    evaluation = pair.evaluation_at.astimezone(UTC)
    for session_snapshot in (source_session, target_session):
        if session_snapshot.evaluation_at.astimezone(UTC) != evaluation:
            raise TemporalComparabilityError(
                "session snapshot evaluation time drift"
            )
    for provider_snapshot in (source_provider, target_provider):
        if provider_snapshot.evaluation_at.astimezone(UTC) != evaluation:
            raise TemporalComparabilityError(
                "provider snapshot evaluation time drift"
            )
    for liquidity_snapshot in (source_liquidity, target_liquidity):
        if liquidity_snapshot.evaluation_at.astimezone(UTC) != evaluation:
            raise TemporalComparabilityError(
                "liquidity snapshot evaluation time drift"
            )
    if source_provider.identity != pair.source_identity:
        raise TemporalComparabilityError(
            "source provider identity drift"
        )
    if target_provider.identity != pair.target_identity:
        raise TemporalComparabilityError(
            "target provider identity drift"
        )
    if source_session.instrument_key != pair.source_identity.instrument_key:
        raise TemporalComparabilityError(
            "source session identity drift"
        )
    if target_session.instrument_key != pair.target_identity.instrument_key:
        raise TemporalComparabilityError(
            "target session identity drift"
        )
    if source_liquidity.instrument_key != pair.source_identity.instrument_key:
        raise TemporalComparabilityError(
            "source liquidity identity drift"
        )
    if target_liquidity.instrument_key != pair.target_identity.instrument_key:
        raise TemporalComparabilityError(
            "target liquidity identity drift"
        )
    if provenance_refs != tuple(sorted(set(provenance_refs))):
        raise TemporalComparabilityError(
            "relational provenance must be unique and canonical"
        )

    sessions = {source_session.state, target_session.state}
    provider_states = {source_provider.state, target_provider.state}
    liquidity_states = {source_liquidity.state, target_liquidity.state}

    if pair.source is None or pair.target is None:
        state = RelationalComparabilityState.INSUFFICIENT
    elif MarketSessionState.UNKNOWN in sessions:
        state = RelationalComparabilityState.INSUFFICIENT
    elif MarketSessionState.HALTED in sessions:
        state = RelationalComparabilityState.TRADING_HALT
    elif MarketSessionState.HOLIDAY in sessions:
        state = RelationalComparabilityState.HOLIDAY_SESSION
    elif MarketSessionState.PARTIAL_SESSION in sessions:
        state = RelationalComparabilityState.PARTIAL_SESSION
    elif sessions & {
        MarketSessionState.CLOSED,
        MarketSessionState.PRE_SESSION,
        MarketSessionState.POST_SESSION,
        MarketSessionState.SESSION_BREAK,
    }:
        state = RelationalComparabilityState.CLOSED_PEER
    elif provider_states & {
        ProviderObservabilityState.UNAVAILABLE,
        ProviderObservabilityState.DEGRADED,
        ProviderObservabilityState.PARTIAL,
        ProviderObservabilityState.UNKNOWN,
    }:
        state = RelationalComparabilityState.PROVIDER_DEGRADED
    elif ProviderObservabilityState.DELAYED in provider_states:
        state = RelationalComparabilityState.PROVIDER_DELAYED
    elif ProviderObservabilityState.STALE in provider_states:
        state = RelationalComparabilityState.STALE_PEER
    elif LiquidityState.UNKNOWN in liquidity_states:
        state = RelationalComparabilityState.INSUFFICIENT
    elif LiquidityState.ILLIQUID in liquidity_states:
        state = RelationalComparabilityState.ILLIQUID_PEER
    elif (
        pair.source_age_ms is None
        or pair.target_age_ms is None
        or pair.temporal_skew_ms is None
    ):
        state = RelationalComparabilityState.INSUFFICIENT
    elif (
        pair.source_age_ms > policy.source_max_age_ms
        or pair.target_age_ms > policy.target_max_age_ms
    ):
        state = RelationalComparabilityState.STALE_PEER
    elif pair.temporal_skew_ms > policy.max_temporal_skew_ms:
        state = RelationalComparabilityState.ASYNC_MARKET
    elif (
        source_liquidity.activity_ratio_bps
        < policy.minimum_activity_ratio_bps
        or target_liquidity.activity_ratio_bps
        < policy.minimum_activity_ratio_bps
    ):
        state = RelationalComparabilityState.ILLIQUID_PEER
    elif (
        MarketSessionState.OPEN_LOW_LIQUIDITY in sessions
        or LiquidityState.LOW in liquidity_states
    ):
        state = (
            RelationalComparabilityState.PARTIALLY_COMPARABLE
            if policy.allow_open_low_liquidity
            else RelationalComparabilityState.ILLIQUID_PEER
        )
    else:
        state = RelationalComparabilityState.COMPARABLE

    if (
        state is RelationalComparabilityState.PARTIAL_SESSION
        and policy.allow_partial_session
        and source_session.is_economically_active
        and target_session.is_economically_active
    ):
        state = RelationalComparabilityState.PARTIALLY_COMPARABLE

    confidence, uncertainty = _confidence(state)
    source_event = (
        None
        if pair.source is None
        else pair.source.provider_event_time_at
    )
    target_event = (
        None
        if pair.target is None
        else pair.target.provider_event_time_at
    )
    return RelationalObservation(
        source_identity=pair.source_identity,
        target_identity=pair.target_identity,
        evaluation_at=evaluation,
        source_event_at=source_event,
        target_event_at=target_event,
        source_age_ms=pair.source_age_ms,
        target_age_ms=pair.target_age_ms,
        source_session_state=source_session.state,
        target_session_state=target_session.state,
        source_liquidity_state=source_liquidity.state,
        target_liquidity_state=target_liquidity.state,
        source_provider_state=source_provider.state,
        target_provider_state=target_provider.state,
        temporal_skew_ms=pair.temporal_skew_ms,
        comparability_state=state,
        confidence=confidence,
        uncertainty=uncertainty,
        calendar_registry_fingerprint=calendar_registry_fingerprint,
        comparability_policy_version=policy.version,
        comparability_policy_fingerprint=policy.fingerprint(),
        provenance_refs=provenance_refs,
    )
