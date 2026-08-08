from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationError,
    AdapterConfigurationMode,
    AdapterConfigurationValidationError,
    AdapterPublicSettings,
    AdapterSecretName,
    AdapterSecretRequirement,
    AdapterSecretRequirements,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
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

_PROVIDER_ID = ProviderId(UUID("f4000000-0000-0000-0000-000000000001"))
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f4000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("f4000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.reference"),
)


def _provider(
    *,
    enablement: ProviderEnablement = ProviderEnablement.READ_ONLY,
    capabilities: tuple[ProviderCapability, ...] = (
        ProviderCapability.MARKET_DATA_READ,
        ProviderCapability.HEALTH,
    ),
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference-provider"),
        enablement=enablement,
        capabilities=ProviderCapabilitySet(capabilities),
    )


def _configuration(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor = _SOURCE,
    mode: AdapterConfigurationMode = AdapterConfigurationMode.READ_ONLY,
) -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_provider() if provider is None else provider,
        source=source,
        mode=mode,
        public_settings=AdapterPublicSettings(
            {
                "endpoint": "reference-feed",
                "region": "ny",
                "retries": 0,
            }
        ),
        secret_requirements=AdapterSecretRequirements(
            (
                AdapterSecretRequirement(AdapterSecretName("api-token")),
                AdapterSecretRequirement(
                    AdapterSecretName("client-cert"),
                    required=False,
                ),
            )
        ),
    )


def test_external_adapter_configuration_is_canonical_and_separates_secrets() -> None:
    configuration = _configuration()

    assert configuration.is_enabled is True
    assert configuration.public_settings.logical_values() == (
        ("endpoint", "reference-feed"),
        ("region", "ny"),
        ("retries", 0),
    )
    assert configuration.secret_requirements.logical_values() == (
        ("api-token", True),
        ("client-cert", False),
    )
    assert "super-secret-value" not in repr(configuration)
    assert configuration.logical_values()[1] == _SOURCE.logical_values()
    assert configuration.logical_values()[2] == "read_only"


def test_public_settings_are_immutable_and_reject_secret_like_values() -> None:
    settings = AdapterPublicSettings(
        {
            "z_region": "ldn",
            "a_endpoint": "reference-feed",
            "feature_flags": ("quotes", "ohlc"),
        }
    )

    assert settings.logical_values() == (
        ("a_endpoint", "reference-feed"),
        ("feature_flags", ("quotes", "ohlc")),
        ("z_region", "ldn"),
    )
    with pytest.raises(TypeError):
        cast(dict[str, DomainMetadataValue], settings.values)["new"] = "x"

    with pytest.raises(AdapterConfigurationValidationError, match="secret-like"):
        AdapterPublicSettings({"api_token": "inline-value"})
    with pytest.raises(AdapterConfigurationValidationError, match="reserved"):
        AdapterPublicSettings({"provider_id": "inline"})
    with pytest.raises(AdapterConfigurationValidationError, match="finite"):
        AdapterPublicSettings({"latency": float("nan")})
    with pytest.raises(AdapterConfigurationValidationError, match="immutable"):
        AdapterPublicSettings({"payload": cast(DomainMetadataValue, object())})
    with pytest.raises(AdapterConfigurationValidationError, match="lowercase"):
        AdapterPublicSettings({"Endpoint": "reference-feed"})
    with pytest.raises(AdapterConfigurationValidationError, match="mapping"):
        AdapterPublicSettings(cast(dict[str, DomainMetadataValue], object()))


def test_secret_requirements_are_names_only_and_canonical() -> None:
    requirements = AdapterSecretRequirements(
        (
            AdapterSecretRequirement(AdapterSecretName("client-secret")),
            AdapterSecretRequirement(AdapterSecretName("api-key"), required=False),
        )
    )

    assert requirements.logical_values() == (
        ("api-key", False),
        ("client-secret", True),
    )
    assert "super-secret-value" not in repr(requirements)

    with pytest.raises(AdapterConfigurationValidationError, match="lowercase"):
        AdapterSecretName("APIKey")
    with pytest.raises(AdapterConfigurationValidationError, match="must be a tuple"):
        AdapterSecretRequirements(
            cast(
                tuple[AdapterSecretRequirement, ...],
                [AdapterSecretRequirement(AdapterSecretName("api-key"))],
            )
        )
    with pytest.raises(AdapterConfigurationValidationError, match="duplicates"):
        AdapterSecretRequirements(
            (
                AdapterSecretRequirement(AdapterSecretName("api-key")),
                AdapterSecretRequirement(AdapterSecretName("api-key")),
            )
        )
    with pytest.raises(AdapterConfigurationValidationError, match="entries"):
        AdapterSecretRequirements(cast(tuple[AdapterSecretRequirement, ...], (object(),)))
    with pytest.raises(AdapterConfigurationValidationError, match="name"):
        AdapterSecretRequirement(cast(AdapterSecretName, object()))
    with pytest.raises(AdapterConfigurationValidationError, match="required flag"):
        AdapterSecretRequirement(
            AdapterSecretName("api-key"),
            required=cast(bool, "yes"),
        )


def test_adapter_mode_cannot_exceed_provider_enablement() -> None:
    disabled_provider = _provider(enablement=ProviderEnablement.DISABLED)
    simulation_provider = _provider(enablement=ProviderEnablement.SIMULATION)

    disabled_configuration = _configuration(
        provider=disabled_provider,
        mode=AdapterConfigurationMode.DISABLED,
    )
    simulation_configuration = _configuration(
        provider=simulation_provider,
        mode=AdapterConfigurationMode.SIMULATION,
    )

    assert disabled_configuration.is_enabled is False
    assert simulation_configuration.is_enabled is True
    with pytest.raises(AdapterConfigurationValidationError, match="enablement"):
        _configuration(
            provider=disabled_provider,
            mode=AdapterConfigurationMode.SIMULATION,
        )
    with pytest.raises(AdapterConfigurationValidationError, match="enablement"):
        _configuration(
            provider=simulation_provider,
            mode=AdapterConfigurationMode.READ_ONLY,
        )


def test_source_namespace_must_match_provider_capabilities() -> None:
    persistence_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f4000000-0000-0000-0000-000000000004")),
        source_id=SourceId(UUID("f4000000-0000-0000-0000-000000000005")),
        port_name=PortName("persistence.reference"),
    )
    provider_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f4000000-0000-0000-0000-000000000006")),
        source_id=SourceId(UUID("f4000000-0000-0000-0000-000000000007")),
        port_name=PortName("provider.health"),
    )
    unsupported_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f4000000-0000-0000-0000-000000000008")),
        source_id=SourceId(UUID("f4000000-0000-0000-0000-000000000009")),
        port_name=PortName("orders.reference"),
    )

    assert _configuration(
        provider=_provider(capabilities=(ProviderCapability.PERSISTENCE_WRITE,)),
        source=persistence_source,
    ).source is persistence_source
    assert _configuration(
        provider=_provider(capabilities=(ProviderCapability.HEALTH,)),
        source=provider_source,
    ).source is provider_source
    with pytest.raises(AdapterConfigurationValidationError, match="market-data"):
        _configuration(provider=_provider(capabilities=(ProviderCapability.HEALTH,)))
    with pytest.raises(AdapterConfigurationValidationError, match="persistence"):
        _configuration(
            provider=_provider(capabilities=(ProviderCapability.MARKET_DATA_READ,)),
            source=persistence_source,
        )
    with pytest.raises(AdapterConfigurationValidationError, match="namespace"):
        _configuration(source=unsupported_source)


def test_external_adapter_configuration_rejects_runtime_type_bypasses() -> None:
    with pytest.raises(AdapterConfigurationValidationError, match="provider"):
        ExternalAdapterConfiguration(
            provider=cast(ProviderDescriptor, object()),
            source=_SOURCE,
            mode=AdapterConfigurationMode.READ_ONLY,
        )
    with pytest.raises(AdapterConfigurationValidationError, match="source"):
        ExternalAdapterConfiguration(
            provider=_provider(),
            source=cast(ExternalSourceDescriptor, object()),
            mode=AdapterConfigurationMode.READ_ONLY,
        )
    with pytest.raises(AdapterConfigurationValidationError, match="mode"):
        ExternalAdapterConfiguration(
            provider=_provider(),
            source=_SOURCE,
            mode=cast(AdapterConfigurationMode, "read_only"),
        )
    with pytest.raises(AdapterConfigurationValidationError, match="public_settings"):
        ExternalAdapterConfiguration(
            provider=_provider(),
            source=_SOURCE,
            mode=AdapterConfigurationMode.READ_ONLY,
            public_settings=cast(AdapterPublicSettings, object()),
        )
    with pytest.raises(AdapterConfigurationValidationError, match="secret_requirements"):
        ExternalAdapterConfiguration(
            provider=_provider(),
            source=_SOURCE,
            mode=AdapterConfigurationMode.READ_ONLY,
            secret_requirements=cast(AdapterSecretRequirements, object()),
        )


def test_public_exports_include_adapter_configuration_contracts() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.AdapterConfigurationError is AdapterConfigurationError
    assert issubclass(AdapterConfigurationError, ExternalPortError)
    assert (
        infrastructure.AdapterConfigurationValidationError
        is AdapterConfigurationValidationError
    )
    assert infrastructure.AdapterConfigurationMode is AdapterConfigurationMode
    assert infrastructure.AdapterPublicSettings is AdapterPublicSettings
    assert infrastructure.AdapterSecretName is AdapterSecretName
    assert infrastructure.AdapterSecretRequirement is AdapterSecretRequirement
    assert infrastructure.AdapterSecretRequirements is AdapterSecretRequirements
    assert infrastructure.ExternalAdapterConfiguration is ExternalAdapterConfiguration
