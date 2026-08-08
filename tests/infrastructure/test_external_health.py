from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure as infrastructure
from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationDecision,
    ProviderActivationDecisionReason,
    ProviderActivationDecisionSnapshot,
    ProviderActivationMode,
    ProviderActivationPolicy,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_lifecycle import (
    AdapterLifecycleActor,
    AdapterLifecycleSnapshot,
    AdapterLifecycleState,
    AdapterLifecycleTransitionReason,
    AdapterLifecycleTransitionRequest,
    apply_adapter_lifecycle_transition,
    declare_adapter_lifecycle,
)
from qore.infrastructure.adapter_observability import (
    AdapterObservabilitySnapshot,
    AdapterReadiness,
)
from qore.infrastructure.adapter_resilience import (
    AdapterCircuitBreakerSnapshot,
    AdapterCircuitBreakerState,
    AdapterResiliencePolicy,
    AdapterResilienceSnapshot,
    AdapterRetryDelay,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.external_health import (
    ExternalHealthAggregationBoundary,
    ExternalHealthAggregationError,
    ExternalHealthAggregationValidationError,
    ExternalHealthIssue,
    ExternalHealthIssueSeverity,
    ExternalHealthIssueSource,
    ExternalProviderHealthAggregateSnapshot,
    ExternalProviderHealthInput,
    ExternalProviderHealthSnapshot,
    ExternalProviderReadiness,
    aggregate_external_provider_health,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
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
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 3, 15, tzinfo=UTC)
_DECLARED_AT = _NOW - timedelta(minutes=3)
_CONFIGURED_AT = _NOW - timedelta(minutes=2)
_INITIALIZED_AT = _NOW - timedelta(minutes=1)
_OBSERVED_AT = _NOW + timedelta(seconds=1)
_PROVIDER_ID = ProviderId(UUID("c9000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("c9000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("c9000000-0000-0000-0000-000000000003"))
_OTHER_SOURCE_ID = SourceId(UUID("c9000000-0000-0000-0000-000000000004"))
_CORRELATION_ID = CorrelationId(UUID("c9000000-0000-0000-0000-000000000005"))
_CAUSATION_ID = CausationId(UUID("c9000000-0000-0000-0000-000000000006"))
_ACTOR = AdapterLifecycleActor("supervisor")


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"request": "external-health"},
    )


def _provider(
    *,
    provider_id: ProviderId = _PROVIDER_ID,
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        provider_name=ProviderName("external-health-provider"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.MARKET_DATA_READ,
            )
        ),
    )


def _source(
    *,
    source_id: SourceId = _SOURCE_ID,
    port_name: str = "market-data.external-health",
) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=source_id,
        port_name=PortName(port_name),
    )


def _policy(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    mode: ProviderActivationMode = ProviderActivationMode.READ_ONLY,
) -> ProviderActivationPolicy:
    return ProviderActivationPolicy(
        provider=provider or _provider(),
        source=source or _source(),
        mode=mode,
        required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
    )


def _configuration(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
) -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=provider or _provider(),
        source=source or _source(),
        mode=AdapterConfigurationMode.READ_ONLY,
    )


def _initialized_lifecycle(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
) -> AdapterLifecycleSnapshot:
    resolved_provider = provider or _provider()
    resolved_source = source or _source()
    declared = declare_adapter_lifecycle(
        descriptor=resolved_source,
        provider=resolved_provider,
        declared_at=_DECLARED_AT,
        actor=_ACTOR,
        metadata=_metadata(),
    )
    assert isinstance(declared, Success)
    configured = apply_adapter_lifecycle_transition(
        declared.value,
        AdapterLifecycleTransitionRequest(
            to_state=AdapterLifecycleState.CONFIGURED,
            reason=AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
            transitioned_at=_CONFIGURED_AT,
            actor=_ACTOR,
            metadata=_metadata(),
        ),
    )
    assert isinstance(configured, Success)
    initialized = apply_adapter_lifecycle_transition(
        configured.value,
        AdapterLifecycleTransitionRequest(
            to_state=AdapterLifecycleState.INITIALIZED,
            reason=AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
            transitioned_at=_INITIALIZED_AT,
            actor=_ACTOR,
            metadata=_metadata(),
        ),
    )
    assert isinstance(initialized, Success)
    return initialized.value


def _observability(
    readiness: AdapterReadiness = AdapterReadiness.READY,
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
) -> AdapterObservabilitySnapshot:
    message = None
    if readiness is AdapterReadiness.DEGRADED:
        message = "external provider degraded"
    if readiness is AdapterReadiness.UNAVAILABLE:
        message = "external provider unavailable"
    return AdapterObservabilitySnapshot(
        provider=provider or _provider(),
        source=source or _source(),
        readiness=readiness,
        observed_at=_NOW,
        message=message,
    )


def _resilience(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    breaker_state: AdapterCircuitBreakerState | None = None,
) -> AdapterResilienceSnapshot:
    resolved_provider = provider or _provider()
    resolved_source = source or _source()
    breaker = None
    if breaker_state is not None:
        breaker = AdapterCircuitBreakerSnapshot(
            state=breaker_state,
            observed_at=_NOW,
            failure_count=1 if breaker_state is not AdapterCircuitBreakerState.CLOSED else 0,
            recovery_delay=AdapterRetryDelay(1_000)
            if breaker_state is AdapterCircuitBreakerState.OPEN
            else None,
            message="resilience circuit state changed",
        )
    return AdapterResilienceSnapshot(
        policy=AdapterResiliencePolicy(
            provider=resolved_provider,
            source=resolved_source,
            timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1_000)),
        ),
        observed_at=_NOW,
        circuit_breaker=breaker,
    )


def _activation(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    decision: ProviderActivationDecision = ProviderActivationDecision.ALLOWED,
    reasons: tuple[ProviderActivationDecisionReason, ...] = (),
    observability: AdapterObservabilitySnapshot | None = None,
    resilience: AdapterResilienceSnapshot | None = None,
) -> ProviderActivationDecisionSnapshot:
    resolved_provider = provider or _provider()
    resolved_source = source or _source()
    return ProviderActivationDecisionSnapshot(
        policy=_policy(provider=resolved_provider, source=resolved_source),
        configuration=_configuration(provider=resolved_provider, source=resolved_source),
        decision=decision,
        reasons=reasons,
        evaluated_at=_NOW,
        lifecycle=_initialized_lifecycle(
            provider=resolved_provider,
            source=resolved_source,
        ),
        observability=observability,
        resilience=resilience,
        metadata=_metadata(),
    )


def test_external_health_aggregation_ready_snapshot_is_deterministic() -> None:
    activation = _activation(
        observability=_observability(),
        resilience=_resilience(),
    )

    result = aggregate_external_provider_health(
        inputs=(ExternalProviderHealthInput(activation=activation),),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.readiness is ExternalProviderReadiness.READY
    assert snapshot.issues == ()
    assert snapshot.providers[0].readiness is ExternalProviderReadiness.READY
    assert snapshot.snapshot_for(_source()) == snapshot.providers[0]
    assert snapshot.logical_values() == snapshot.logical_values()


def test_external_health_aggregation_blocks_when_activation_is_blocked() -> None:
    activation = _activation(
        decision=ProviderActivationDecision.BLOCKED,
        reasons=(ProviderActivationDecisionReason.POLICY_DISABLED,),
    )

    result = aggregate_external_provider_health(
        inputs=(ExternalProviderHealthInput(activation=activation),),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.readiness is ExternalProviderReadiness.BLOCKED
    assert result.value.providers[0].readiness is ExternalProviderReadiness.BLOCKED
    assert result.value.issues[0].source is ExternalHealthIssueSource.ACTIVATION_POLICY
    assert result.value.issues[0].code == "activation.policy_disabled"


def test_external_health_aggregation_degrades_from_observability() -> None:
    observability = _observability(AdapterReadiness.DEGRADED)
    activation = _activation(
        decision=ProviderActivationDecision.DEGRADED,
        reasons=(ProviderActivationDecisionReason.OBSERVABILITY_DEGRADED,),
        observability=observability,
    )

    result = aggregate_external_provider_health(
        inputs=(ExternalProviderHealthInput(activation=activation),),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.readiness is ExternalProviderReadiness.DEGRADED
    assert {issue.code for issue in result.value.issues} == {
        "activation.observability_degraded",
        "observability.degraded",
    }


def test_external_health_aggregation_marks_unavailable_from_resilience() -> None:
    resilience = _resilience(breaker_state=AdapterCircuitBreakerState.OPEN)
    activation = _activation(resilience=resilience)

    result = aggregate_external_provider_health(
        inputs=(ExternalProviderHealthInput(activation=activation),),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.readiness is ExternalProviderReadiness.UNAVAILABLE
    assert result.value.issues[0].source is ExternalHealthIssueSource.RESILIENCE
    assert result.value.issues[0].code == "resilience.circuit_open"


def test_external_health_aggregation_rolls_up_worst_readiness_and_orders_providers() -> None:
    first_provider = _provider()
    first_source = _source()
    second_source = _source(
        source_id=_OTHER_SOURCE_ID,
        port_name="market-data.external-health-alt",
    )
    ready_activation = _activation(provider=first_provider, source=first_source)
    blocked_activation = _activation(
        provider=first_provider,
        source=second_source,
        decision=ProviderActivationDecision.BLOCKED,
        reasons=(ProviderActivationDecisionReason.CONFIGURATION_DISABLED,),
    )

    result = aggregate_external_provider_health(
        inputs=(
            ExternalProviderHealthInput(activation=blocked_activation),
            ExternalProviderHealthInput(activation=ready_activation),
        ),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.readiness is ExternalProviderReadiness.BLOCKED
    assert tuple(provider.source.port_name.value for provider in result.value.providers) == (
        "market-data.external-health",
        "market-data.external-health-alt",
    )


def test_external_health_aggregation_rejects_duplicate_provider_source() -> None:
    activation = _activation()

    result = aggregate_external_provider_health(
        inputs=(
            ExternalProviderHealthInput(activation=activation),
            ExternalProviderHealthInput(activation=activation),
        ),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExternalHealthAggregationValidationError)


def test_external_health_metadata_is_safe_and_immutable() -> None:
    issue = ExternalHealthIssue(
        source=ExternalHealthIssueSource.OBSERVABILITY,
        severity=ExternalHealthIssueSeverity.WARNING,
        code="observability.degraded",
        message="provider reported degraded health",
        observed_at=_NOW,
        metadata={"scope": "market-data"},
    )

    assert tuple(issue.metadata.items()) == (("scope", "market-data"),)
    with pytest.raises(TypeError):
        cast(dict[str, object], issue.metadata)["unsafe"] = "mutation"

    with pytest.raises(ExternalHealthAggregationValidationError):
        ExternalHealthIssue(
            source=ExternalHealthIssueSource.OBSERVABILITY,
            severity=ExternalHealthIssueSeverity.WARNING,
            code="observability.degraded",
            message="provider reported degraded health",
            observed_at=_NOW,
            metadata={"token": "redacted"},
        )

    with pytest.raises(ExternalHealthAggregationValidationError):
        ExternalHealthIssue(
            source=ExternalHealthIssueSource.OBSERVABILITY,
            severity=ExternalHealthIssueSeverity.WARNING,
            code="observability.degraded",
            message="api_key=inline-secret",
            observed_at=_NOW,
        )


def test_external_health_rejects_runtime_type_bypasses() -> None:
    with pytest.raises(ExternalHealthAggregationValidationError):
        ExternalProviderHealthInput(activation=cast(ProviderActivationDecisionSnapshot, "bad"))

    activation = _activation()
    with pytest.raises(ExternalHealthAggregationValidationError):
        ExternalProviderHealthSnapshot(
            provider=cast(ProviderDescriptor, "bad"),
            source=_source(),
            readiness=ExternalProviderReadiness.READY,
            observed_at=_OBSERVED_AT,
            activation=activation,
            lifecycle=activation.lifecycle,
        )

    with pytest.raises(ExternalHealthAggregationValidationError):
        ExternalProviderHealthAggregateSnapshot(
            readiness=ExternalProviderReadiness.READY,
            observed_at=_OBSERVED_AT,
            providers=cast(tuple[ExternalProviderHealthSnapshot, ...], ["bad"]),
            metadata=_metadata(),
        )

    result = aggregate_external_provider_health(
        inputs=cast(tuple[ExternalProviderHealthInput, ...], ["bad"]),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExternalHealthAggregationError)


def test_external_health_boundary_is_structural() -> None:
    activation = _activation()
    aggregate = aggregate_external_provider_health(
        inputs=(ExternalProviderHealthInput(activation=activation),),
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )
    assert isinstance(aggregate, Success)

    class Boundary:
        def __init__(self, snapshot: ExternalProviderHealthAggregateSnapshot) -> None:
            self._snapshot = snapshot

        def external_health_snapshot(
            self,
            *,
            observed_at: datetime,
            metadata: ExternalRequestMetadata,
        ) -> Result[ExternalProviderHealthAggregateSnapshot, ExternalHealthAggregationError]:
            assert observed_at == _OBSERVED_AT
            assert metadata == _metadata()
            return Success(self._snapshot)

    boundary: ExternalHealthAggregationBoundary = Boundary(aggregate.value)

    observed = boundary.external_health_snapshot(
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )
    assert isinstance(observed, Success)
    assert observed.value == aggregate.value


def test_public_exports() -> None:
    assert infrastructure.ExternalProviderReadiness is ExternalProviderReadiness
    assert infrastructure.ExternalHealthIssueSource is ExternalHealthIssueSource
    assert infrastructure.ExternalHealthIssueSeverity is ExternalHealthIssueSeverity
    assert infrastructure.ExternalHealthIssue is ExternalHealthIssue
    assert infrastructure.ExternalProviderHealthInput is ExternalProviderHealthInput
    assert infrastructure.ExternalProviderHealthSnapshot is ExternalProviderHealthSnapshot
    assert (
        infrastructure.ExternalProviderHealthAggregateSnapshot
        is ExternalProviderHealthAggregateSnapshot
    )
    assert infrastructure.ExternalHealthAggregationBoundary is ExternalHealthAggregationBoundary
    assert infrastructure.ExternalHealthAggregationError is ExternalHealthAggregationError
    assert (
        infrastructure.ExternalHealthAggregationValidationError
        is ExternalHealthAggregationValidationError
    )
    assert (
        infrastructure.aggregate_external_provider_health
        is aggregate_external_provider_health
    )
