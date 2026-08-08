from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.activation_policy import (
    ProviderActivationEvaluation,
    ProviderActivationMode,
    ProviderActivationPolicy,
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
from qore.infrastructure.connectivity import (
    ProviderConnectivityMode,
    ProviderEndpoint,
    ReadOnlyProviderConnectivityIntent,
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
from qore.infrastructure.read_only_provider_adapter import (
    ReadOnlyExternalProviderAdapter,
    ReadOnlyProviderAdapterBlockedError,
    ReadOnlyProviderAdapterConfiguration,
    ReadOnlyProviderAdapterValidationError,
)
from qore.infrastructure.secret_resolution import (
    MappingSecretMaterialResolver,
    SecretMaterial,
)
from qore.infrastructure.secrets import (
    SecretExternalReference,
    SecretNotFoundError,
    SecretRef,
    SecretRefId,
)
from qore.infrastructure.transport import (
    ExternalTransportBoundary,
    ExternalTransportError,
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 4, 40, tzinfo=UTC)
_PROVIDER_ID = ProviderId(UUID("c9000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("c9000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("c9000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("c9000000-0000-0000-0000-000000000004"))
_CAUSATION_ID = CausationId(UUID("c9000000-0000-0000-0000-000000000005"))
_SECRET_REF_ID = SecretRefId(UUID("c9000000-0000-0000-0000-000000000006"))
_ENDPOINT = ProviderEndpoint("data.example.test", base_path="/v1")
_SECRET_REFERENCE = SecretExternalReference("provider/reference/api-key")
_SECRET_BYTES = b"opaque-provider-test-secret"


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference.readonly"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (ProviderCapability.HEALTH, ProviderCapability.MARKET_DATA_READ)
        ),
    )


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("market-data.live"),
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"workflow": "phase-09"},
    )


def _secret_ref() -> SecretRef:
    return SecretRef(
        ref_id=_SECRET_REF_ID,
        name=AdapterSecretName("api-key"),
        external_reference=_SECRET_REFERENCE,
    )


def _lifecycle(*, ready: bool = True) -> AdapterLifecycleSnapshot:
    declared = declare_adapter_lifecycle(
        descriptor=_source(),
        provider=_provider(),
        declared_at=_NOW,
        actor=AdapterLifecycleActor("phase09.supervisor"),
        metadata=_metadata(),
    )
    assert isinstance(declared, Success)
    snapshot = declared.value
    if not ready:
        return snapshot
    for offset, state, reason in (
        (1, AdapterLifecycleState.CONFIGURED, AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED),
        (2, AdapterLifecycleState.INITIALIZED, AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED),
    ):
        result = apply_adapter_lifecycle_transition(
            snapshot,
            AdapterLifecycleTransitionRequest(
                to_state=state,
                reason=reason,
                transitioned_at=_NOW + timedelta(seconds=offset),
                actor=AdapterLifecycleActor("phase09.supervisor"),
                metadata=_metadata(),
            ),
        )
        assert isinstance(result, Success)
        snapshot = result.value
    return snapshot


def _activation(*, ready: bool = True, secret: SecretRef | None = None):
    requirements = (
        AdapterSecretRequirements((AdapterSecretRequirement(secret.name),))
        if secret is not None
        else AdapterSecretRequirements()
    )
    configuration = ExternalAdapterConfiguration(
        provider=_provider(),
        source=_source(),
        mode=AdapterConfigurationMode.READ_ONLY,
        secret_requirements=requirements,
    )
    policy = ProviderActivationPolicy(
        provider=_provider(),
        source=_source(),
        mode=ProviderActivationMode.READ_ONLY,
        required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
    )
    result = evaluate_provider_activation_policy(
        ProviderActivationEvaluation(
            policy=policy,
            configuration=configuration,
            lifecycle=_lifecycle(ready=ready),
            secrets=ProviderActivationSecretReferences(
                (secret,) if secret is not None else ()
            ),
            evaluated_at=_NOW + timedelta(seconds=3),
            metadata=_metadata(),
        )
    )
    assert isinstance(result, Success)
    return result.value


def _connectivity() -> ReadOnlyProviderConnectivityIntent:
    return ReadOnlyProviderConnectivityIntent(
        provider=_provider(),
        endpoint=_ENDPOINT,
        mode=ProviderConnectivityMode.NETWORK_READ_ONLY,
        capability=ProviderCapability.MARKET_DATA_READ,
    )


def _request(endpoint: ProviderEndpoint = _ENDPOINT) -> ExternalTransportRequest:
    return ExternalTransportRequest(
        endpoint=endpoint,
        method=ExternalTransportMethod.GET,
        path="/quotes/latest",
        timeout=ExternalTransportTimeout(1000),
        query=(("instrument", "EURUSD"),),
    )


class _PlainTransport:
    def execute(
        self,
        request: ExternalTransportRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        assert request.method is ExternalTransportMethod.GET
        assert metadata == _metadata()
        return Success(
            ExternalTransportResponse(
                status_code=200,
                received_at=_NOW + timedelta(seconds=4),
                payload=b'{"bid":1.1,"ask":1.2}',
            )
        )


class _AuthenticatedTransport:
    def execute_authenticated(
        self,
        request: ExternalTransportRequest,
        *,
        secret: SecretMaterial,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExternalTransportError]:
        assert request.endpoint == _ENDPOINT
        assert secret.reveal_bytes() == _SECRET_BYTES
        assert metadata == _metadata()
        return Success(
            ExternalTransportResponse(
                status_code=200,
                received_at=_NOW + timedelta(seconds=4),
                payload=b'{"bid":1.1,"ask":1.2}',
            )
        )


def test_plain_read_only_adapter_executes_allowed_read() -> None:
    transport: ExternalTransportBoundary = _PlainTransport()
    adapter = ReadOnlyExternalProviderAdapter(
        configuration=ReadOnlyProviderAdapterConfiguration(
            connectivity=_connectivity(),
            activation=_activation(),
        ),
        transport=transport,
    )

    result = adapter.read(_request(), metadata=_metadata(), resolved_at=_NOW)

    assert isinstance(result, Success)
    assert result.value.status_code == 200
    assert adapter.source == _source()
    assert not hasattr(adapter, "write")


def test_blocked_activation_never_calls_transport() -> None:
    adapter = ReadOnlyExternalProviderAdapter(
        configuration=ReadOnlyProviderAdapterConfiguration(
            connectivity=_connectivity(),
            activation=_activation(ready=False),
        ),
        transport=_PlainTransport(),
    )

    result = adapter.read(_request(), metadata=_metadata(), resolved_at=_NOW)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReadOnlyProviderAdapterBlockedError)


def test_endpoint_identity_mismatch_is_rejected() -> None:
    adapter = ReadOnlyExternalProviderAdapter(
        configuration=ReadOnlyProviderAdapterConfiguration(
            connectivity=_connectivity(),
            activation=_activation(),
        ),
        transport=_PlainTransport(),
    )

    result = adapter.read(
        _request(ProviderEndpoint("other.example.test")),
        metadata=_metadata(),
        resolved_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReadOnlyProviderAdapterValidationError)


def test_secret_backed_adapter_resolves_material_out_of_band() -> None:
    ref = _secret_ref()
    adapter = ReadOnlyExternalProviderAdapter(
        configuration=ReadOnlyProviderAdapterConfiguration(
            connectivity=_connectivity(),
            activation=_activation(secret=ref),
            secret_ref=ref,
        ),
        authenticated_transport=_AuthenticatedTransport(),
        secret_resolver=MappingSecretMaterialResolver({_SECRET_REFERENCE: _SECRET_BYTES}),
    )

    result = adapter.read(_request(), metadata=_metadata(), resolved_at=_NOW)

    assert isinstance(result, Success)
    assert _SECRET_BYTES.decode() not in repr(adapter.configuration)


def test_missing_secret_propagates_typed_failure_without_transport() -> None:
    ref = _secret_ref()
    adapter = ReadOnlyExternalProviderAdapter(
        configuration=ReadOnlyProviderAdapterConfiguration(
            connectivity=_connectivity(),
            activation=_activation(secret=ref),
            secret_ref=ref,
        ),
        authenticated_transport=_AuthenticatedTransport(),
        secret_resolver=MappingSecretMaterialResolver({}),
    )

    result = adapter.read(_request(), metadata=_metadata(), resolved_at=_NOW)

    assert isinstance(result, Failure)
    assert isinstance(result.error, SecretNotFoundError)
    assert _SECRET_BYTES.decode() not in str(result.error)


def test_adapter_configuration_rejects_secret_not_present_in_activation() -> None:
    with pytest.raises(ReadOnlyProviderAdapterValidationError):
        ReadOnlyProviderAdapterConfiguration(
            connectivity=_connectivity(),
            activation=_activation(),
            secret_ref=_secret_ref(),
        )
