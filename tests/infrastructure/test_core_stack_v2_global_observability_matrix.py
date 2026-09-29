from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.global_observability_matrix import (
    AvailabilityState,
    CalendarMappingState,
    GlobalSensorTemporalMetadata,
    TemporalReadinessStage,
    build_global_market_observability_matrix,
)
from qore.infrastructure.core_stack_v2.global_sensor_registry import (
    GlobalPerceptionSensorRegistry,
    GlobalSensorDisposition,
    GlobalSensorGovernanceStage,
    GlobalSensorRecord,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
CATALOG_SHA = "a" * 64


def _sensor(
    key: str,
    *,
    disposition: GlobalSensorDisposition = GlobalSensorDisposition.DISCOVERED,
) -> GlobalSensorRecord:
    stages = (
        (GlobalSensorGovernanceStage.DISCOVER_PROVIDER_SYMBOL,)
        if disposition is not GlobalSensorDisposition.ADMITTED
        else tuple(GlobalSensorGovernanceStage)
    )
    return GlobalSensorRecord(
        instrument_key=key,
        provider="PROVIDER",
        provider_symbol=key.split(":")[1],
        provider_symbol_id=int(key.split(":")[2]),
        family=None,
        observed_at=NOW,
        evidence_cutoff_at=NOW,
        completed_stages=stages,
        disposition=disposition,
        uncertainty_bps=10000 if disposition is not GlobalSensorDisposition.ADMITTED else 1000,
        provenance_refs=(f"sensor:{key}",),
        reason_codes=("TEST",),
    )


def _registry(*sensors: GlobalSensorRecord) -> GlobalPerceptionSensorRegistry:
    return GlobalPerceptionSensorRegistry(
        as_of=NOW,
        provider_catalog_sha256=CATALOG_SHA,
        sensors=tuple(sorted(sensors, key=lambda item: item.instrument_key)),
    )


def _metadata(
    key: str,
    **overrides: object,
) -> GlobalSensorTemporalMetadata:
    values: dict[str, object] = {
        "instrument_key": key,
        "canonical_instrument_id": "canonical:" + key,
        "family": "indices-benchmarks",
        "calendar_mapping": CalendarMappingState.MAPPED,
        "calendar_id": "calendar:1",
        "calendar_version": "v1",
        "iana_timezone": "America/New_York",
        "provider_schedule_available": True,
        "provider_schedule_timezone": "UTC",
        "historical_availability": AvailabilityState.FULL,
        "realtime_availability": AvailabilityState.FULL,
        "expected_cadence_capability": True,
        "liquidity_observability": True,
        "comparability_ready": True,
        "provenance_refs": ("metadata:1",),
    }
    values.update(overrides)
    return GlobalSensorTemporalMetadata(**values)  # type: ignore[arg-type]


def test_missing_temporal_metadata_remains_discovered_and_unmapped() -> None:
    registry = _registry(_sensor("PROVIDER:AAA:1"))

    matrix = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=(),
        as_of=NOW,
    )

    row = matrix.rows[0]
    assert row.readiness is TemporalReadinessStage.DISCOVERED
    assert row.calendar_mapping is CalendarMappingState.UNMAPPED
    assert row.scientific_disposition is GlobalSensorDisposition.DISCOVERED


def test_identity_verified_without_calendar_does_not_become_temporally_ready() -> None:
    registry = _registry(_sensor("PROVIDER:AAA:1"))
    metadata = _metadata(
        "PROVIDER:AAA:1",
        calendar_mapping=CalendarMappingState.UNMAPPED,
        calendar_id=None,
        calendar_version=None,
        iana_timezone=None,
    )

    matrix = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=(metadata,),
        as_of=NOW,
    )

    assert matrix.rows[0].readiness is TemporalReadinessStage.IDENTITY_VERIFIED


def test_calendar_mapping_without_cadence_stops_at_calendar_mapped() -> None:
    registry = _registry(_sensor("PROVIDER:AAA:1"))
    metadata = _metadata(
        "PROVIDER:AAA:1",
        expected_cadence_capability=False,
    )

    matrix = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=(metadata,),
        as_of=NOW,
    )

    assert matrix.rows[0].readiness is TemporalReadinessStage.CALENDAR_MAPPED


def test_temporal_observability_and_relational_readiness_are_distinct() -> None:
    registry = _registry(
        _sensor("PROVIDER:AAA:1"),
        _sensor("PROVIDER:BBB:2"),
    )
    metadata = (
        _metadata(
            "PROVIDER:AAA:1",
            comparability_ready=False,
            provenance_refs=("metadata:a",),
        ),
        _metadata(
            "PROVIDER:BBB:2",
            comparability_ready=True,
            provenance_refs=("metadata:b",),
        ),
    )

    matrix = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=metadata,
        as_of=NOW,
    )

    assert matrix.rows[0].readiness is TemporalReadinessStage.TEMPORALLY_OBSERVABLE
    assert matrix.rows[1].readiness is TemporalReadinessStage.RELATIONALLY_COMPARABLE


def test_scientific_admission_remains_separate_from_relational_readiness() -> None:
    registry = _registry(
        _sensor(
            "PROVIDER:AAA:1",
            disposition=GlobalSensorDisposition.ADMITTED,
        )
    )

    matrix = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=(_metadata("PROVIDER:AAA:1"),),
        as_of=NOW,
    )

    assert matrix.rows[0].readiness is TemporalReadinessStage.SCIENTIFICALLY_ADMITTED


def test_matrix_is_deterministic_under_metadata_permutation() -> None:
    registry = _registry(
        _sensor("PROVIDER:AAA:1"),
        _sensor("PROVIDER:BBB:2"),
    )
    first = _metadata(
        "PROVIDER:AAA:1",
        provenance_refs=("metadata:a",),
    )
    second = _metadata(
        "PROVIDER:BBB:2",
        provenance_refs=("metadata:b",),
    )

    left = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=(second, first),
        as_of=NOW,
    )
    right = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=registry.fingerprint(),
        metadata=(first, second),
        as_of=NOW,
    )

    assert left.rows == right.rows
    assert left.fingerprint() == right.fingerprint()
