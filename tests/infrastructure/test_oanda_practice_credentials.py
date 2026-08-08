from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.adapter_configuration import AdapterSecretName
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.oanda_practice_credentials import (
    OandaPracticeCredentialActivationValidationError,
    activate_oanda_practice_credentials,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.secret_resolution import MappingSecretMaterialResolver
from qore.infrastructure.secrets import (
    SecretExternalReference,
    SecretNotFoundError,
    SecretRef,
    SecretRefId,
)
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 11, 30, tzinfo=UTC)
_SECRET_BYTES = b"deterministic-oanda-practice-test-material"
_REFERENCE = SecretExternalReference("oanda/practice/personal-access-token")


def _configuration() -> OandaPracticeRuntimeConfiguration:
    account = MarketTestAccountIdentity(
        provider_key="oanda-v20",
        account_ref="practice-001",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    return OandaPracticeRuntimeConfiguration(
        provider_key="oanda-v20",
        environment=MarketRuntimeEnvironment.DEMO,
        rest_endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=account,
        symbols=("EUR_USD", "GBP_USD"),
        capabilities=(
            OandaPracticeCapability.ACCOUNT,
            OandaPracticeCapability.ORDERS,
            OandaPracticeCapability.PRICING,
            OandaPracticeCapability.TRANSACTIONS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        stream_connect_timeout=ExternalTransportTimeout(milliseconds=5000),
        limits=OandaPracticeOperationalLimits(
            rest_requests_per_second=60,
            active_streams=2,
            new_connections_per_second=1,
        ),
        secret_requirements=oanda_practice_secret_requirements(),
    )


def _ref(
    *,
    name: str = "oanda-personal-access-token",
    reference: SecretExternalReference = _REFERENCE,
    provider: str = "oanda-v20",
    environment: str = "demo",
    account_ref: str = "practice-001",
) -> SecretRef:
    return SecretRef(
        ref_id=SecretRefId(UUID("c1000000-0000-0000-0000-000000000001")),
        name=AdapterSecretName(name),
        external_reference=reference,
        metadata={
            "account-ref": account_ref,
            "environment": environment,
            "provider": provider,
        },
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(UUID("c1000000-0000-0000-0000-000000000002")),
        causation_id=CausationId(UUID("c1000000-0000-0000-0000-000000000003")),
        attributes={"workflow": "mission-03"},
    )


def test_practice_credential_activation_returns_opaque_material() -> None:
    ref = _ref()
    resolver = MappingSecretMaterialResolver({_REFERENCE: _SECRET_BYTES})

    result = activate_oanda_practice_credentials(
        _configuration(),
        ref,
        resolver=resolver,
        metadata=_metadata(),
        activated_at=_NOW,
    )

    assert isinstance(result, Success)
    activation = result.value
    assert activation.material.reveal_bytes() == _SECRET_BYTES
    assert _SECRET_BYTES.decode() not in repr(activation)
    assert _SECRET_BYTES not in activation.logical_values()
    assert activation.logical_values()[-1] == _NOW.isoformat()


def test_activation_rejects_non_oanda_secret_name_before_resolution() -> None:
    result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(name="api-key"),
        resolver=MappingSecretMaterialResolver({}),
        metadata=_metadata(),
        activated_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeCredentialActivationValidationError)


def test_activation_rejects_production_scoped_reference_before_resolution() -> None:
    result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(
            reference=SecretExternalReference(
                "oanda/production/personal-access-token"
            )
        ),
        resolver=MappingSecretMaterialResolver({}),
        metadata=_metadata(),
        activated_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeCredentialActivationValidationError)
    assert "oanda/practice" in str(result.error)


def test_activation_rejects_non_demo_secret_metadata() -> None:
    result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(environment="production"),
        resolver=MappingSecretMaterialResolver({}),
        metadata=_metadata(),
        activated_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeCredentialActivationValidationError)
    assert "environment" in str(result.error)


def test_activation_rejects_provider_or_account_mismatch() -> None:
    provider_result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(provider="other-provider"),
        resolver=MappingSecretMaterialResolver({}),
        metadata=_metadata(),
        activated_at=_NOW,
    )
    account_result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(account_ref="practice-002"),
        resolver=MappingSecretMaterialResolver({}),
        metadata=_metadata(),
        activated_at=_NOW,
    )

    assert isinstance(provider_result, Failure)
    assert isinstance(
        provider_result.error,
        OandaPracticeCredentialActivationValidationError,
    )
    assert isinstance(account_result, Failure)
    assert isinstance(
        account_result.error,
        OandaPracticeCredentialActivationValidationError,
    )


def test_activation_preserves_missing_secret_as_typed_failure() -> None:
    result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(),
        resolver=MappingSecretMaterialResolver({}),
        metadata=_metadata(),
        activated_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, SecretNotFoundError)
    assert _SECRET_BYTES.decode() not in str(result.error)


def test_activation_rejects_naive_timestamp_before_resolution() -> None:
    result = activate_oanda_practice_credentials(
        _configuration(),
        _ref(),
        resolver=MappingSecretMaterialResolver({_REFERENCE: _SECRET_BYTES}),
        metadata=_metadata(),
        activated_at=datetime(2026, 8, 8, 11, 30),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeCredentialActivationValidationError)
    assert "timezone-aware" in str(result.error)
