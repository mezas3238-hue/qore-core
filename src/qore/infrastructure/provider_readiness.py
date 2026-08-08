from __future__ import annotations

import dataclasses

import qore.core.application as core_application
import qore.infrastructure.composition as infrastructure_composition
import qore.infrastructure.market_data_provider_harness as market_data_harness
import qore.infrastructure.persistence_backend_harness as persistence_harness
import qore.infrastructure.ports as ports_contract
import qore.kernel.result as result_contract


class ProviderReadinessEndToEndError(ports_contract.ExternalPortError):
    """Base error for provider readiness end-to-end composition."""

    __slots__ = ()


class ProviderReadinessEndToEndValidationError(ProviderReadinessEndToEndError):
    """Invalid provider readiness end-to-end composition boundary."""

    __slots__ = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ProviderReadinessEndToEndConfiguration[PersistenceValueT]:
    """Explicit provider-readiness inputs for market data and persistence."""

    market_data: market_data_harness.ReadOnlyMarketDataProviderHarnessConfiguration
    persistence: persistence_harness.PersistenceBackendHarnessConfiguration[
        PersistenceValueT
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.market_data,
            market_data_harness.ReadOnlyMarketDataProviderHarnessConfiguration,
        ):
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness market_data must be "
                "ReadOnlyMarketDataProviderHarnessConfiguration"
            )
        if not isinstance(
            self.persistence,
            persistence_harness.PersistenceBackendHarnessConfiguration,
        ):
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness persistence must be "
                "PersistenceBackendHarnessConfiguration"
            )

    def logical_values(self) -> tuple[object, ...]:
        """Return deterministic readiness inputs without sensitive payload values."""
        return (
            self.market_data.logical_values(),
            self.persistence.logical_values(),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ProviderReadinessEndToEndComposition[PersistenceValueT]:
    """Provider-readiness root binding harnesses to one Core instance."""

    core: core_application.CoreApplication
    market_data: market_data_harness.ReadOnlyMarketDataProviderHarness
    persistence: persistence_harness.PersistenceBackendHarness[PersistenceValueT]
    infrastructure: infrastructure_composition.ReferenceInfrastructureComposition[
        PersistenceValueT
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.core, core_application.CoreApplication):
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness core must be CoreApplication"
            )
        if not isinstance(
            self.market_data,
            market_data_harness.ReadOnlyMarketDataProviderHarness,
        ):
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness market_data must be "
                "ReadOnlyMarketDataProviderHarness"
            )
        if not isinstance(
            self.persistence,
            persistence_harness.PersistenceBackendHarness,
        ):
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness persistence must be PersistenceBackendHarness"
            )
        if not isinstance(
            self.infrastructure,
            infrastructure_composition.ReferenceInfrastructureComposition,
        ):
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness infrastructure must be "
                "ReferenceInfrastructureComposition"
            )
        if self.infrastructure.core is not self.core:
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness composition must preserve the same CoreApplication"
            )
        if self.infrastructure.adapters.market_data is not self.market_data.market_data:
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness market-data adapter must come from the harness"
            )
        if self.infrastructure.adapters.persistence is not self.persistence.persistence:
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness persistence adapter must come from the harness"
            )
        if self.infrastructure.ports.market_data is not self.market_data.market_data:
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness market-data port must expose the harness adapter"
            )
        if self.infrastructure.ports.persistence is not self.persistence.persistence:
            raise ProviderReadinessEndToEndValidationError(
                "provider readiness persistence port must expose the harness adapter"
            )

    @property
    def adapters(
        self,
    ) -> infrastructure_composition.ReferenceInfrastructureAdapters[PersistenceValueT]:
        """Expose canonical adapters retained outside the Core object graph."""
        return self.infrastructure.adapters

    @property
    def ports(
        self,
    ) -> infrastructure_composition.InfrastructurePorts[PersistenceValueT]:
        """Expose canonical infrastructure ports for application-level consumption."""
        return self.infrastructure.ports


def _validation_failure(
    message: str,
) -> result_contract.Failure[ports_contract.ExternalPortError]:
    return result_contract.Failure(ProviderReadinessEndToEndValidationError(message))


def compose_provider_readiness_end_to_end[PersistenceValueT](
    core: core_application.CoreApplication,
    configuration: ProviderReadinessEndToEndConfiguration[PersistenceValueT],
) -> result_contract.Result[
    ProviderReadinessEndToEndComposition[PersistenceValueT],
    ports_contract.ExternalPortError,
]:
    """Compose provider harnesses into canonical ports above one Core instance."""
    if not isinstance(core, core_application.CoreApplication):
        return _validation_failure("core must be CoreApplication")
    if not isinstance(configuration, ProviderReadinessEndToEndConfiguration):
        return _validation_failure(
            "configuration must be ProviderReadinessEndToEndConfiguration"
        )

    market_data_result = (
        market_data_harness.compose_read_only_market_data_provider_harness(
            configuration.market_data
        )
    )
    if isinstance(market_data_result, result_contract.Failure):
        return market_data_result

    persistence_result: result_contract.Result[
        persistence_harness.PersistenceBackendHarness[PersistenceValueT],
        ports_contract.ExternalPortError,
    ] = persistence_harness.compose_persistence_backend_harness(
        configuration.persistence
    )
    if isinstance(persistence_result, result_contract.Failure):
        return persistence_result

    try:
        adapters = infrastructure_composition.ReferenceInfrastructureAdapters(
            market_data=market_data_result.value.market_data,
            persistence=persistence_result.value.persistence,
        )
        infrastructure = infrastructure_composition.ReferenceInfrastructureComposition(
            core=core,
            adapters=adapters,
            ports=adapters.as_ports(),
        )
        composition = ProviderReadinessEndToEndComposition(
            core=core,
            market_data=market_data_result.value,
            persistence=persistence_result.value,
            infrastructure=infrastructure,
        )
    except ports_contract.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(composition)
