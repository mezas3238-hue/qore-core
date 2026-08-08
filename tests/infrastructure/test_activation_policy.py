from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationDecision,
    ProviderActivationDecisionReason,
    ProviderActivationDecisionSnapshot,
    ProviderActivationEvaluation,
    ProviderActivationMode,
    ProviderActivationPolicy,
    ProviderActivationPolicyBoundary,
    ProviderActivationPolicyError,
    ProviderActivationPolicyValidationError,
    ProviderActivationSecretReferences,
    evaluate_provider_activation_policy,
)
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    AdapterSecretName,
    AdapterSecretRequirement,
    AdapterSecretRequirements,
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
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
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
from qore.infrastructure.secrets import (
    SecretExternalReference,
    SecretRef,
    SecretRefId,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 2, 45, tzinfo=UTC)
_DECLARED_AT = _NOW - timedelta(minutes=3)
_CONFIGURED_AT = _NOW - timedelta(minutes=2)
_INITIALIZED_AT = _NOW - timedelta(minutes=1)
_PROVIDER_ID = ProviderId(UUID("a7000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("a7000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("a7000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("a7000000-0000-0000-0000-000000000004"))
_CAUSATION_ID = CausationId(UUID("a7000000-0000-0000-0000-000000000005"))
_SECRET_REF_ID = SecretRefId(UUID("a7000000-0000-0000-0000-000000000006"))
_UNKNOWN_SECRET_REF_ID = SecretRefId(UUID("a7000000-0000-0000-0000-000000000007"))
_ACTOR = AdapterLifecycleActor("supervisor")
_API_KEY = AdapterSecretName("api_key")
_UNKNOWN_SECRET = AdapterSecretName("unknown_key")


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"request": "activation-policy"},
    )


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("market-data.activation-policy"),
    )


def _provider(
    *,
    enablement: ProviderEnablement = ProviderEnablement.READ_ONLY,
    capabilities: tuple[ProviderCapability, ...] = (
        ProviderCapability.HEALTH,
        ProviderCapability.MARKET_DATA_READ,
    ),
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("activation-provider"),
        enablement=enablement,
        capabilities=ProviderCapabilitySet(capabilities),
    )


def _configuration(
    *,
    provider: ProviderDescriptor | None = None,
    mode: AdapterConfigurationMode = AdapterConfigurationMode.READ_ONLY,
    secret_requirements: AdapterSecretRequirements | None = None,
) -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=provider or _provider(),
        source=_source(),
        mode=mode,
        secret_requirements=secret_requirements
        or AdapterSecretRequirements((AdapterSecretRequirement(_API_KEY),)),
    )


def _policy(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    mode: ProviderActivationMode = ProviderActivationMode.READ_ONLY,
    required_capabilities: tuple[ProviderCapability, ...] = (
        ProviderCapability.HEALTH,
        ProviderCapability.MARKET_DATA_READ,
    ),
) -> ProviderActivationPolicy:
    return ProviderActivationPolicy(
        provider=provider or _provider(),
        source=source or _source(),
        mode=mode,
        required_capabilities=required_capabilities,
        metadata={"scope": "market-data"},
    )


def _secret_refs(*, include_unknown: bool = False) -> ProviderActivationSecretReferences:
    refs = [
        SecretRef(
            ref_id=_SECRET_REF_ID,
            name=_API_KEY,
            external_reference=SecretExternalReference("vault/provider/api_key"),
        )
    ]
    if include_unknown:
        refs.append(
            SecretRef(
                ref_id=_UNKNOWN_SECRET_REF_ID,
                name=_UNKNOWN_SECRET,
                external_reference=SecretExternalReference("vault/provider/unknown_key"),
            )
        )
    return ProviderActivationSecretReferences(tuple(refs))


def _declared_lifecycle(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
) -> AdapterLifecycleSnapshot:
    declared = declare_adapter_lifecycle(
        descriptor=source or _source(),
        provider=provider or _provider(),
        declared_at=_DECLARED_AT,
        actor=_ACTOR,
        metadata=_metadata(),
    )
    assert isinstance(declared, Success)
    return declared.value


def _initialized_lifecycle(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
) -> AdapterLifecycleSnapshot:
    declared = _declared_lifecycle(provider=provider, source=source)
    configured = apply_adapter_lifecycle_transition(
        declared,
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
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    readiness: AdapterReadiness = AdapterReadiness.READY,
) -> AdapterObservabilitySnapshot:
    return AdapterObservabilitySnapshot(
        provider=provider or _provider(),
        source=source or _source(),
        readiness=readiness,
        observed_at=_NOW,
        message="provider is not fully ready" if readiness is not AdapterReadiness.READY else None,
    )


def _resilience(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    circuit_breaker: AdapterCircuitBreakerSnapshot | None = None,
) -> AdapterResilienceSnapshot:
    policy = AdapterResiliencePolicy(
        provider=provider or _provider(),
        source=source or _source(),
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(1000)),
    )
    return AdapterResilienceSnapshot(
        policy=policy,
        observed_at=_NOW,
        circuit_breaker=circuit_breaker,
    )


def _evaluation(
    *,
    policy: ProviderActivationPolicy | None = None,
    configuration: ExternalAdapterConfiguration | None = None,
    lifecycle: AdapterLifecycleSnapshot | None = None,
    observability: AdapterObservabilitySnapshot | None = None,
    resilience: AdapterResilienceSnapshot | None = None,
    secrets: ProviderActivationSecretReferences | None = None,
) -> ProviderActivationEvaluation:
    return ProviderActivationEvaluation(
        policy=policy or _policy(),
        configuration=configuration or _configuration(),
        lifecycle=lifecycle or _initialized_lifecycle(),
        observability=observability if observability is not None else _observability(),
        resilience=resilience if resilience is not None else _resilience(),
        secrets=secrets or _secret_refs(),
        evaluated_at=_NOW,
        metadata=_metadata(),
    )


def test_activation_policy_allows_read_only_activation_when_ready() -> None:
    result: Result[
        ProviderActivationDecisionSnapshot,
        ProviderActivationPolicyError,
    ] = evaluate_provider_activation_policy(_evaluation())

    assert isinstance(result, Success)
    decision = result.value
    assert decision.decision is ProviderActivationDecision.ALLOWED
    assert decision.reasons == ()
    assert decision.can_activate is True
    assert decision.policy.mode is ProviderActivationMode.READ_ONLY
    assert decision.secret_references.names() == ("api_key",)
    logical_values = str(decision.logical_values()).lower()
    assert "sk-" not in logical_values
    assert "password=" not in logical_values
    assert "token=" not in logical_values


def test_activation_policy_blocks_when_policy_disabled() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(policy=_policy(mode=ProviderActivationMode.DISABLED))
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert result.value.can_activate is False
    assert ProviderActivationDecisionReason.POLICY_DISABLED in result.value.reasons


def test_activation_policy_blocks_when_configuration_disabled() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(configuration=_configuration(mode=AdapterConfigurationMode.DISABLED))
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert ProviderActivationDecisionReason.CONFIGURATION_DISABLED in result.value.reasons
    assert (
        ProviderActivationDecisionReason.MODE_EXCEEDS_CONFIGURATION
        in result.value.reasons
    )


def test_activation_policy_blocks_when_mode_exceeds_configuration() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(
            configuration=_configuration(mode=AdapterConfigurationMode.SIMULATION),
            policy=_policy(mode=ProviderActivationMode.READ_ONLY),
        )
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert (
        ProviderActivationDecisionReason.MODE_EXCEEDS_CONFIGURATION
        in result.value.reasons
    )


def test_activation_policy_blocks_missing_capability() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(
            policy=_policy(
                required_capabilities=(
                    ProviderCapability.MARKET_DATA_READ,
                    ProviderCapability.PERSISTENCE_WRITE,
                )
            )
        )
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert ProviderActivationDecisionReason.MISSING_CAPABILITY in result.value.reasons


def test_activation_policy_blocks_missing_required_secret_reference() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(secrets=ProviderActivationSecretReferences())
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert (
        ProviderActivationDecisionReason.MISSING_SECRET_REFERENCE
        in result.value.reasons
    )


def test_activation_policy_blocks_unknown_secret_reference() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(secrets=_secret_refs(include_unknown=True))
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert ProviderActivationDecisionReason.UNKNOWN_SECRET_REFERENCE in result.value.reasons


def test_activation_policy_blocks_lifecycle_not_ready() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(lifecycle=_declared_lifecycle())
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert ProviderActivationDecisionReason.LIFECYCLE_NOT_READY in result.value.reasons


def test_activation_policy_degrades_when_observability_degraded() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(observability=_observability(readiness=AdapterReadiness.DEGRADED))
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.DEGRADED
    assert result.value.can_activate is False
    assert (
        ProviderActivationDecisionReason.OBSERVABILITY_DEGRADED
        in result.value.reasons
    )


def test_activation_policy_blocks_when_observability_unavailable() -> None:
    result = evaluate_provider_activation_policy(
        _evaluation(observability=_observability(readiness=AdapterReadiness.UNAVAILABLE))
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert (
        ProviderActivationDecisionReason.OBSERVABILITY_UNAVAILABLE
        in result.value.reasons
    )


def test_activation_policy_blocks_when_circuit_breaker_open() -> None:
    breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_NOW,
        failure_count=3,
        recovery_delay=AdapterRetryDelay(500),
        message="provider temporarily unavailable",
    )
    result = evaluate_provider_activation_policy(
        _evaluation(resilience=_resilience(circuit_breaker=breaker))
    )

    assert isinstance(result, Success)
    assert result.value.decision is ProviderActivationDecision.BLOCKED
    assert (
        ProviderActivationDecisionReason.RESILIENCE_UNAVAILABLE
        in result.value.reasons
    )


def test_activation_policy_returns_failure_for_identity_mismatch() -> None:
    mismatched_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("a7000000-0000-0000-0000-000000000010")),
        source_id=SourceId(UUID("a7000000-0000-0000-0000-000000000011")),
        port_name=PortName("market-data.other"),
    )
    result = evaluate_provider_activation_policy(
        _evaluation(policy=_policy(source=mismatched_source))
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderActivationPolicyValidationError)


def test_activation_policy_requires_explicit_evaluation_time_and_metadata() -> None:
    missing_time = ProviderActivationEvaluation(
        policy=_policy(),
        configuration=_configuration(),
        lifecycle=_initialized_lifecycle(),
        observability=_observability(),
        resilience=_resilience(),
        secrets=_secret_refs(),
        metadata=_metadata(),
    )
    missing_metadata = ProviderActivationEvaluation(
        policy=_policy(),
        configuration=_configuration(),
        lifecycle=_initialized_lifecycle(),
        observability=_observability(),
        resilience=_resilience(),
        secrets=_secret_refs(),
        evaluated_at=_NOW,
    )

    assert isinstance(evaluate_provider_activation_policy(missing_time), Failure)
    assert isinstance(evaluate_provider_activation_policy(missing_metadata), Failure)


def test_activation_policy_rejects_runtime_bypasses() -> None:
    with pytest.raises(ProviderActivationPolicyValidationError):
        ProviderActivationPolicy(
            provider=cast(ProviderDescriptor, object()),
            source=_source(),
        )
    with pytest.raises(ProviderActivationPolicyValidationError):
        ProviderActivationPolicy(
            provider=_provider(),
            source=_source(),
            mode=cast(ProviderActivationMode, "read_only"),
        )
    with pytest.raises(ProviderActivationPolicyValidationError):
        ProviderActivationPolicy(
            provider=_provider(),
            source=_source(),
            required_capabilities=cast(
                tuple[ProviderCapability, ...],
                [ProviderCapability.HEALTH],
            ),
        )
    with pytest.raises(ProviderActivationPolicyValidationError):
        ProviderActivationSecretReferences(cast(tuple[SecretRef, ...], [_secret_refs().refs[0]]))
    with pytest.raises(ProviderActivationPolicyValidationError):
        ProviderActivationPolicy(
            provider=_provider(),
            source=_source(),
            metadata={"token": "not-allowed"},
        )


def test_activation_policy_boundary_is_structural() -> None:
    class Boundary:
        @property
        def activation_policy(self) -> ProviderActivationPolicy:
            return _policy()

        def evaluate_activation(
            self,
            evaluation: ProviderActivationEvaluation,
        ) -> Result[ProviderActivationDecisionSnapshot, ProviderActivationPolicyError]:
            return evaluate_provider_activation_policy(evaluation)

    boundary: ProviderActivationPolicyBoundary = Boundary()
    result = boundary.evaluate_activation(_evaluation(policy=boundary.activation_policy))

    assert isinstance(result, Success)
    assert result.value.can_activate is True


def test_activation_policy_public_exports() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.ProviderActivationPolicy is ProviderActivationPolicy
    assert infrastructure.ProviderActivationMode is ProviderActivationMode
    assert infrastructure.ProviderActivationDecision is ProviderActivationDecision
    assert (
        infrastructure.ProviderActivationDecisionReason
        is ProviderActivationDecisionReason
    )
    assert (
        infrastructure.ProviderActivationDecisionSnapshot
        is ProviderActivationDecisionSnapshot
    )
    assert infrastructure.ProviderActivationEvaluation is ProviderActivationEvaluation
    assert (
        infrastructure.ProviderActivationSecretReferences
        is ProviderActivationSecretReferences
    )
    assert infrastructure.ProviderActivationPolicyError is ProviderActivationPolicyError
    assert issubclass(ProviderActivationPolicyError, ExternalPortError)
    assert (
        infrastructure.ProviderActivationPolicyValidationError
        is ProviderActivationPolicyValidationError
    )
    assert infrastructure.evaluate_provider_activation_policy is evaluate_provider_activation_policy
