from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId, DomainMetadataValue
from qore.infrastructure.adapter_observability import (
    AdapterLatencyMeasurement,
    AdapterMetric,
    AdapterMetricName,
    AdapterObservabilityBoundary,
    AdapterObservabilityError,
    AdapterObservabilitySnapshot,
    AdapterObservabilityValidationError,
    AdapterObservedError,
    AdapterObservedErrorSeverity,
    AdapterReadiness,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.kernel.result import Success

_RAW_SECRET = "super-secret-value-123"
_OBSERVED_AT = datetime(2026, 8, 7, 21, 37, tzinfo=UTC)
_PROVIDER = ProviderDescriptor(
    provider_id=ProviderId(UUID("f6000000-0000-0000-0000-000000000001")),
    provider_name=ProviderName("reference-provider"),
    enablement=ProviderEnablement.READ_ONLY,
    capabilities=ProviderCapabilitySet(
        (
            ProviderCapability.HEALTH,
            ProviderCapability.MARKET_DATA_READ,
        )
    ),
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f6000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("f6000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.reference"),
)


class _Observer:
    def __init__(self, snapshot: AdapterObservabilitySnapshot) -> None:
        self._snapshot = snapshot

    def observe(
        self,
        *,
        observed_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Success[AdapterObservabilitySnapshot]:
        assert observed_at == self._snapshot.observed_at
        assert isinstance(metadata, ExternalRequestMetadata)
        return Success(self._snapshot)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(UUID("f6000000-0000-0000-0000-000000000010"))
    )


def _ready_health() -> ExternalHealth:
    return ExternalHealth(
        descriptor=_SOURCE,
        availability=PortAvailability.AVAILABLE,
        checked_at=_OBSERVED_AT,
    )


def _degraded_health() -> ExternalHealth:
    return ExternalHealth(
        descriptor=_SOURCE,
        availability=PortAvailability.DEGRADED,
        checked_at=_OBSERVED_AT,
        message="latency above readiness threshold",
    )


def _ready_snapshot() -> AdapterObservabilitySnapshot:
    return AdapterObservabilitySnapshot(
        provider=_PROVIDER,
        source=_SOURCE,
        readiness=AdapterReadiness.READY,
        observed_at=_OBSERVED_AT,
        latency=AdapterLatencyMeasurement(12),
        health=_ready_health(),
        metrics=(
            AdapterMetric(AdapterMetricName("requests.total"), 10, "count"),
            AdapterMetric(AdapterMetricName("latency.p50"), 12, "ms"),
        ),
        metadata={"region": "ny", "window": "startup"},
    )


def test_observability_snapshot_is_canonical_and_deterministic() -> None:
    snapshot = _ready_snapshot()

    assert snapshot.readiness is AdapterReadiness.READY
    assert snapshot.latency == AdapterLatencyMeasurement(12)
    assert snapshot.logical_values() == _ready_snapshot().logical_values()
    assert snapshot.logical_values()[2] == "ready"
    assert snapshot.logical_values()[3] == "2026-08-07T21:37:00+00:00"
    assert snapshot.logical_values()[4] == (12,)
    assert snapshot.logical_values()[6] == (
        ("latency.p50", 12, "ms"),
        ("requests.total", 10, "count"),
    )
    assert tuple(snapshot.metadata.items()) == (
        ("region", "ny"),
        ("window", "startup"),
    )
    for surface in (repr(snapshot), repr(snapshot.logical_values())):
        assert _RAW_SECRET not in surface


def test_degraded_snapshot_carries_sanitized_observed_errors() -> None:
    observed_error = AdapterObservedError(
        error_type="timeout",
        message="provider response exceeded injected timeout",
        severity=AdapterObservedErrorSeverity.ERROR,
        observed_at=_OBSERVED_AT,
        metadata={"attempt": 1},
    )
    snapshot = AdapterObservabilitySnapshot(
        provider=_PROVIDER,
        source=_SOURCE,
        readiness=AdapterReadiness.DEGRADED,
        observed_at=_OBSERVED_AT,
        latency=AdapterLatencyMeasurement(250),
        health=_degraded_health(),
        last_errors=(observed_error,),
        message="adapter degraded by provider timeout",
    )

    assert snapshot.logical_values()[2] == "degraded"
    assert snapshot.logical_values()[7] == (
        (
            "timeout",
            "provider response exceeded injected timeout",
            "error",
            "2026-08-07T21:37:00+00:00",
            (("attempt", 1),),
        ),
    )
    assert _RAW_SECRET not in repr(snapshot.logical_values())


def test_observable_text_and_metadata_reject_sensitive_payloads() -> None:
    with pytest.raises(AdapterObservabilityValidationError, match="sensitive"):
        AdapterObservedError(
            error_type="timeout",
            message="provider returned token=super-secret-value-123",
            severity=AdapterObservedErrorSeverity.ERROR,
            observed_at=_OBSERVED_AT,
        )
    with pytest.raises(AdapterObservabilityValidationError, match="secret-like"):
        AdapterMetricName("api_key.failure")
    with pytest.raises(AdapterObservabilityValidationError, match="secret-like"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            metadata={"api_key": "inline"},
        )
    with pytest.raises(AdapterObservabilityValidationError, match="reserved"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            metadata={"value": "inline"},
        )
    with pytest.raises(AdapterObservabilityValidationError, match="immutable"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            metadata={"payload": cast(DomainMetadataValue, object())},
        )


def test_latency_metrics_and_errors_validate_runtime_bypasses() -> None:
    with pytest.raises(AdapterObservabilityValidationError, match="integer"):
        AdapterLatencyMeasurement(cast(int, True))
    with pytest.raises(AdapterObservabilityValidationError, match="non-negative"):
        AdapterLatencyMeasurement(-1)
    with pytest.raises(AdapterObservabilityValidationError, match="finite"):
        AdapterMetric(AdapterMetricName("latency.p99"), float("nan"), "ms")
    with pytest.raises(AdapterObservabilityValidationError, match="finite number"):
        AdapterMetric(AdapterMetricName("latency.p99"), cast(int | float, True), "ms")
    with pytest.raises(AdapterObservabilityValidationError, match="timezone-aware"):
        AdapterObservedError(
            error_type="timeout",
            message="provider response exceeded injected timeout",
            severity=AdapterObservedErrorSeverity.ERROR,
            observed_at=datetime(2026, 8, 7, 21, 37),
        )
    with pytest.raises(AdapterObservabilityValidationError, match="severity"):
        AdapterObservedError(
            error_type="timeout",
            message="provider response exceeded injected timeout",
            severity=cast(AdapterObservedErrorSeverity, "error"),
            observed_at=_OBSERVED_AT,
        )


def test_snapshot_rejects_inconsistent_or_mutable_runtime_values() -> None:
    metric = AdapterMetric(AdapterMetricName("requests.total"), 1, "count")
    with pytest.raises(AdapterObservabilityValidationError, match="ProviderDescriptor"):
        AdapterObservabilitySnapshot(
            provider=cast(ProviderDescriptor, object()),
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
        )
    with pytest.raises(AdapterObservabilityValidationError, match="metrics must be a tuple"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            metrics=cast(tuple[AdapterMetric, ...], [metric]),
        )
    with pytest.raises(AdapterObservabilityValidationError, match="duplicates"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            metrics=(metric, metric),
        )
    with pytest.raises(AdapterObservabilityValidationError, match="last errors"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            last_errors=(
                AdapterObservedError(
                    error_type="timeout",
                    message="provider response exceeded injected timeout",
                    severity=AdapterObservedErrorSeverity.WARNING,
                    observed_at=_OBSERVED_AT,
                ),
            ),
        )
    with pytest.raises(AdapterObservabilityValidationError, match="need a message"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.DEGRADED,
            observed_at=_OBSERVED_AT,
        )


def test_snapshot_validates_health_descriptor_and_availability() -> None:
    other_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f6000000-0000-0000-0000-000000000004")),
        source_id=SourceId(UUID("f6000000-0000-0000-0000-000000000005")),
        port_name=PortName("market-data.other"),
    )
    mismatched_health = ExternalHealth(
        descriptor=other_source,
        availability=PortAvailability.AVAILABLE,
        checked_at=_OBSERVED_AT,
    )

    with pytest.raises(AdapterObservabilityValidationError, match="descriptor"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            health=mismatched_health,
        )
    with pytest.raises(AdapterObservabilityValidationError, match="availability"):
        AdapterObservabilitySnapshot(
            provider=_PROVIDER,
            source=_SOURCE,
            readiness=AdapterReadiness.READY,
            observed_at=_OBSERVED_AT,
            health=_degraded_health(),
        )


def test_observability_boundary_is_structural() -> None:
    snapshot = _ready_snapshot()
    observer: AdapterObservabilityBoundary = _Observer(snapshot)

    result = observer.observe(observed_at=_OBSERVED_AT, metadata=_metadata())

    assert isinstance(result, Success)
    assert result.value is snapshot
    assert _RAW_SECRET not in repr(result.value.logical_values())


def test_public_exports_include_adapter_observability_contracts() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.AdapterLatencyMeasurement is AdapterLatencyMeasurement
    assert infrastructure.AdapterMetric is AdapterMetric
    assert infrastructure.AdapterMetricName is AdapterMetricName
    assert infrastructure.AdapterObservabilityBoundary is AdapterObservabilityBoundary
    assert infrastructure.AdapterObservabilityError is AdapterObservabilityError
    assert issubclass(AdapterObservabilityError, ExternalPortError)
    assert infrastructure.AdapterObservabilitySnapshot is AdapterObservabilitySnapshot
    assert (
        infrastructure.AdapterObservabilityValidationError
        is AdapterObservabilityValidationError
    )
    assert infrastructure.AdapterObservedError is AdapterObservedError
    assert infrastructure.AdapterObservedErrorSeverity is AdapterObservedErrorSeverity
    assert infrastructure.AdapterReadiness is AdapterReadiness
