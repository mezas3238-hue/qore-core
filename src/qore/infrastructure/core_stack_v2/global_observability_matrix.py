"""Deterministic GEN-2 global market observability/comparability matrix."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from qore.infrastructure.core_stack_v2.global_sensor_registry import (
    GlobalPerceptionSensorRegistry,
    GlobalSensorDisposition,
)


class CalendarMappingState(StrEnum):
    MAPPED = "MAPPED"
    UNMAPPED = "UNMAPPED"
    AMBIGUOUS = "AMBIGUOUS"


class AvailabilityState(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class TemporalReadinessStage(StrEnum):
    DISCOVERED = "DISCOVERED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    CALENDAR_MAPPED = "CALENDAR_MAPPED"
    TEMPORALLY_OBSERVABLE = "TEMPORALLY_OBSERVABLE"
    RELATIONALLY_COMPARABLE = "RELATIONALLY_COMPARABLE"
    SCIENTIFICALLY_ADMITTED = "SCIENTIFICALLY_ADMITTED"


READINESS_ORDER: Final = tuple(TemporalReadinessStage)


@dataclass(frozen=True, slots=True)
class GlobalSensorTemporalMetadata:
    instrument_key: str
    canonical_instrument_id: str | None
    family: str | None
    calendar_mapping: CalendarMappingState
    calendar_id: str | None
    calendar_version: str | None
    iana_timezone: str | None
    provider_schedule_available: bool
    provider_schedule_timezone: str | None
    historical_availability: AvailabilityState
    realtime_availability: AvailabilityState
    expected_cadence_capability: bool
    liquidity_observability: bool
    comparability_ready: bool
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.instrument_key.strip():
            raise ValueError("temporal metadata instrument_key must be non-empty")
        if (
            self.calendar_mapping is CalendarMappingState.MAPPED
            and (
                not self.calendar_id
                or not self.calendar_version
                or not self.iana_timezone
            )
        ):
            raise ValueError(
                "mapped calendar requires id/version/IANA timezone"
            )
        if self.provenance_refs != tuple(sorted(set(self.provenance_refs))):
            raise ValueError(
                "temporal metadata provenance must be canonical"
            )


@dataclass(frozen=True, slots=True)
class GlobalMarketObservabilityRow:
    instrument_key: str
    provider: str
    provider_symbol: str
    provider_symbol_id: int
    family: str | None
    canonical_instrument_id: str | None
    calendar_mapping: CalendarMappingState
    calendar_id: str | None
    calendar_version: str | None
    iana_timezone: str | None
    provider_schedule_available: bool
    provider_schedule_timezone: str | None
    historical_availability: AvailabilityState
    realtime_availability: AvailabilityState
    expected_cadence_capability: bool
    liquidity_observability: bool
    readiness: TemporalReadinessStage
    scientific_disposition: GlobalSensorDisposition
    provenance_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GlobalMarketObservabilityMatrix:
    as_of: datetime
    sensor_registry_fingerprint: str
    rows: tuple[GlobalMarketObservabilityRow, ...]
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("observability matrix as_of must be aware")
        if len(self.sensor_registry_fingerprint) != 64:
            raise ValueError("sensor registry fingerprint must be sha256")
        keys = tuple(item.instrument_key for item in self.rows)
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError(
                "observability matrix rows must be unique and canonical"
            )
        if self.execution_authority or self.risk_authority or self.sizing_authority:
            raise ValueError("observability matrix is cognition-only")

    def fingerprint(self) -> str:
        payload = {
            "as_of": self.as_of.astimezone(UTC).isoformat(),
            "sensor_registry_fingerprint": self.sensor_registry_fingerprint,
            "rows": [
                {
                    "instrument_key": row.instrument_key,
                    "provider": row.provider,
                    "provider_symbol": row.provider_symbol,
                    "provider_symbol_id": row.provider_symbol_id,
                    "family": row.family,
                    "canonical_instrument_id": row.canonical_instrument_id,
                    "calendar_mapping": row.calendar_mapping.value,
                    "calendar_id": row.calendar_id,
                    "calendar_version": row.calendar_version,
                    "iana_timezone": row.iana_timezone,
                    "provider_schedule_available": (
                        row.provider_schedule_available
                    ),
                    "provider_schedule_timezone": (
                        row.provider_schedule_timezone
                    ),
                    "historical_availability": (
                        row.historical_availability.value
                    ),
                    "realtime_availability": (
                        row.realtime_availability.value
                    ),
                    "expected_cadence_capability": (
                        row.expected_cadence_capability
                    ),
                    "liquidity_observability": row.liquidity_observability,
                    "readiness": row.readiness.value,
                    "scientific_disposition": (
                        row.scientific_disposition.value
                    ),
                    "provenance_refs": row.provenance_refs,
                }
                for row in self.rows
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _readiness(
    *,
    metadata: GlobalSensorTemporalMetadata,
    disposition: GlobalSensorDisposition,
) -> TemporalReadinessStage:
    if metadata.canonical_instrument_id is None:
        return TemporalReadinessStage.DISCOVERED
    if metadata.calendar_mapping is not CalendarMappingState.MAPPED:
        return TemporalReadinessStage.IDENTITY_VERIFIED
    if not (
        metadata.provider_schedule_available
        and metadata.expected_cadence_capability
        and metadata.liquidity_observability
    ):
        return TemporalReadinessStage.CALENDAR_MAPPED
    if metadata.realtime_availability in {
        AvailabilityState.NONE,
        AvailabilityState.UNKNOWN,
    }:
        return TemporalReadinessStage.CALENDAR_MAPPED
    if not metadata.comparability_ready:
        return TemporalReadinessStage.TEMPORALLY_OBSERVABLE
    if disposition is GlobalSensorDisposition.ADMITTED:
        return TemporalReadinessStage.SCIENTIFICALLY_ADMITTED
    return TemporalReadinessStage.RELATIONALLY_COMPARABLE


def build_global_market_observability_matrix(
    *,
    registry: GlobalPerceptionSensorRegistry,
    sensor_registry_fingerprint: str,
    metadata: tuple[GlobalSensorTemporalMetadata, ...],
    as_of: datetime,
) -> GlobalMarketObservabilityMatrix:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("matrix as_of must be timezone-aware")
    by_key = {item.instrument_key: item for item in metadata}
    if len(by_key) != len(metadata):
        raise ValueError("duplicate temporal metadata instrument key")

    rows: list[GlobalMarketObservabilityRow] = []
    for sensor in registry.sensors:
        item = by_key.get(sensor.instrument_key)
        if item is None:
            item = GlobalSensorTemporalMetadata(
                instrument_key=sensor.instrument_key,
                canonical_instrument_id=None,
                family=sensor.family,
                calendar_mapping=CalendarMappingState.UNMAPPED,
                calendar_id=None,
                calendar_version=None,
                iana_timezone=None,
                provider_schedule_available=False,
                provider_schedule_timezone=None,
                historical_availability=AvailabilityState.UNKNOWN,
                realtime_availability=AvailabilityState.UNKNOWN,
                expected_cadence_capability=False,
                liquidity_observability=False,
                comparability_ready=False,
                provenance_refs=sensor.provenance_refs,
            )
        if item.instrument_key != sensor.instrument_key:
            raise ValueError("matrix metadata identity drift")
        rows.append(
            GlobalMarketObservabilityRow(
                instrument_key=sensor.instrument_key,
                provider=sensor.provider,
                provider_symbol=sensor.provider_symbol,
                provider_symbol_id=sensor.provider_symbol_id,
                family=item.family,
                canonical_instrument_id=item.canonical_instrument_id,
                calendar_mapping=item.calendar_mapping,
                calendar_id=item.calendar_id,
                calendar_version=item.calendar_version,
                iana_timezone=item.iana_timezone,
                provider_schedule_available=(
                    item.provider_schedule_available
                ),
                provider_schedule_timezone=item.provider_schedule_timezone,
                historical_availability=item.historical_availability,
                realtime_availability=item.realtime_availability,
                expected_cadence_capability=(
                    item.expected_cadence_capability
                ),
                liquidity_observability=item.liquidity_observability,
                readiness=_readiness(
                    metadata=item,
                    disposition=sensor.disposition,
                ),
                scientific_disposition=sensor.disposition,
                provenance_refs=tuple(
                    sorted(
                        set(sensor.provenance_refs + item.provenance_refs)
                    )
                ),
            )
        )

    return GlobalMarketObservabilityMatrix(
        as_of=as_of.astimezone(UTC),
        sensor_registry_fingerprint=sensor_registry_fingerprint,
        rows=tuple(sorted(rows, key=lambda item: item.instrument_key)),
    )
