from __future__ import annotations

import dataclasses

import qore.core.application as core_application
import qore.infrastructure.market_data as market_data
import qore.infrastructure.persistence as persistence
import qore.infrastructure.ports as ports
import qore.infrastructure.reference_adapters as reference_adapters
import qore.kernel.result as result_contract


class InfrastructureCompositionError(ports.ExternalPortError):
    """Base error for explicit infrastructure composition boundaries."""

    __slots__ = ()


class InfrastructureCompositionValidationError(InfrastructureCompositionError):
    """Invalid explicit infrastructure composition configuration."""

    __slots__ = ()


def _validate_descriptor_namespace(
    descriptor: object,
    *,
    namespace: str,
    field_name: str,
) -> ports.ExternalSourceDescriptor:
    if not isinstance(descriptor, ports.ExternalSourceDescriptor):
        raise InfrastructureCompositionValidationError(
            f"{field_name} must be ExternalSourceDescriptor"
        )
    name = descriptor.port_name.value
    if name != namespace and not name.startswith(f"{namespace}."):
        raise InfrastructureCompositionValidationError(
            f"{field_name} must use the {namespace} namespace"
        )
    return descriptor


def _validate_snapshot_tuple(
    value: object,
    *,
    snapshot_type: type[object],
    field_name: str,
) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        raise InfrastructureCompositionValidationError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, snapshot_type):
            raise InfrastructureCompositionValidationError(
                f"{field_name} entries must be {snapshot_type.__name__}"
            )
    return value


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceInfrastructureConfiguration:
    """Explicit immutable inputs for deterministic reference infrastructure."""

    market_data_descriptor: ports.ExternalSourceDescriptor
    persistence_descriptor: ports.ExternalSourceDescriptor
    quote_snapshots: tuple[market_data.QuoteSnapshot, ...] = ()
    ohlc_snapshots: tuple[market_data.OhlcSnapshot, ...] = ()

    def __post_init__(self) -> None:
        _validate_descriptor_namespace(
            self.market_data_descriptor,
            namespace="market-data",
            field_name="market_data_descriptor",
        )
        _validate_descriptor_namespace(
            self.persistence_descriptor,
            namespace="persistence",
            field_name="persistence_descriptor",
        )
        _validate_snapshot_tuple(
            self.quote_snapshots,
            snapshot_type=market_data.QuoteSnapshot,
            field_name="quote_snapshots",
        )
        _validate_snapshot_tuple(
            self.ohlc_snapshots,
            snapshot_type=market_data.OhlcSnapshot,
            field_name="ohlc_snapshots",
        )


@dataclasses.dataclass(frozen=True, slots=True)
class InfrastructurePorts[PersistenceValueT]:
    """Typed infrastructure ports exposed above the Core boundary."""

    market_data: market_data.MarketDataPort
    persistence: persistence.PersistencePort[PersistenceValueT]


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceInfrastructureAdapters[PersistenceValueT]:
    """Concrete deterministic adapters retained outside the Core object graph."""

    market_data: reference_adapters.ReferenceMarketDataAdapter
    persistence: reference_adapters.ReferencePersistenceAdapter[PersistenceValueT]

    def __post_init__(self) -> None:
        if not isinstance(
            self.market_data,
            reference_adapters.ReferenceMarketDataAdapter,
        ):
            raise InfrastructureCompositionValidationError(
                "market_data adapter must be ReferenceMarketDataAdapter"
            )
        if not isinstance(
            self.persistence,
            reference_adapters.ReferencePersistenceAdapter,
        ):
            raise InfrastructureCompositionValidationError(
                "persistence adapter must be ReferencePersistenceAdapter"
            )

    def as_ports(self) -> InfrastructurePorts[PersistenceValueT]:
        """Expose concrete adapters only through their typed port contracts."""
        return InfrastructurePorts(
            market_data=self.market_data,
            persistence=self.persistence,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceInfrastructureComposition[PersistenceValueT]:
    """Composition root that binds one Core instance to explicit infrastructure."""

    core: core_application.CoreApplication
    adapters: ReferenceInfrastructureAdapters[PersistenceValueT]
    ports: InfrastructurePorts[PersistenceValueT]

    def __post_init__(self) -> None:
        if not isinstance(self.core, core_application.CoreApplication):
            raise InfrastructureCompositionValidationError(
                "infrastructure composition core must be CoreApplication"
            )
        if not isinstance(self.adapters, ReferenceInfrastructureAdapters):
            raise InfrastructureCompositionValidationError(
                "infrastructure composition adapters must be ReferenceInfrastructureAdapters"
            )
        if not isinstance(self.ports, InfrastructurePorts):
            raise InfrastructureCompositionValidationError(
                "infrastructure composition ports must be InfrastructurePorts"
            )
        if self.ports.market_data is not self.adapters.market_data:
            raise InfrastructureCompositionValidationError(
                "market_data port must expose the composed reference adapter"
            )
        if self.ports.persistence is not self.adapters.persistence:
            raise InfrastructureCompositionValidationError(
                "persistence port must expose the composed reference adapter"
            )


def _validation_failure(message: str) -> result_contract.Failure[ports.ExternalPortError]:
    return result_contract.Failure(InfrastructureCompositionValidationError(message))


def compose_reference_infrastructure[PersistenceValueT](
    core: core_application.CoreApplication,
    configuration: ReferenceInfrastructureConfiguration,
) -> result_contract.Result[
    ReferenceInfrastructureComposition[PersistenceValueT],
    ports.ExternalPortError,
]:
    """Compose deterministic reference adapters above one existing Core instance."""
    if not isinstance(core, core_application.CoreApplication):
        return _validation_failure("core must be CoreApplication")
    if not isinstance(configuration, ReferenceInfrastructureConfiguration):
        return _validation_failure(
            "configuration must be ReferenceInfrastructureConfiguration"
        )

    try:
        market_data_adapter = reference_adapters.ReferenceMarketDataAdapter(
            configuration.market_data_descriptor,
            quotes=configuration.quote_snapshots,
            ohlc=configuration.ohlc_snapshots,
        )
        persistence_adapter: reference_adapters.ReferencePersistenceAdapter[
            PersistenceValueT
        ] = reference_adapters.ReferencePersistenceAdapter(
            configuration.persistence_descriptor,
        )
        adapters = ReferenceInfrastructureAdapters(
            market_data=market_data_adapter,
            persistence=persistence_adapter,
        )
        composition = ReferenceInfrastructureComposition(
            core=core,
            adapters=adapters,
            ports=adapters.as_ports(),
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(composition)
