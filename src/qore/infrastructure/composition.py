from __future__ import annotations

import dataclasses

import qore.core.application as core_application
import qore.infrastructure.ingestion as ingestion
import qore.infrastructure.market_data as market_data
import qore.infrastructure.persistence as persistence
import qore.infrastructure.ports as ports
import qore.infrastructure.reference_adapters as reference_adapters
import qore.infrastructure.reference_payload_adapters as reference_payload_adapters
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


def _validate_item_tuple(
    value: object,
    *,
    item_type: type[object],
    field_name: str,
) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        raise InfrastructureCompositionValidationError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, item_type):
            raise InfrastructureCompositionValidationError(
                f"{field_name} entries must be {item_type.__name__}"
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
        _validate_item_tuple(
            self.quote_snapshots,
            item_type=market_data.QuoteSnapshot,
            field_name="quote_snapshots",
        )
        _validate_item_tuple(
            self.ohlc_snapshots,
            item_type=market_data.OhlcSnapshot,
            field_name="ohlc_snapshots",
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceQuoteIngestionRequest:
    """Explicit quote normalization request for an end-to-end composition."""

    request: market_data.QuoteRequest
    snapshot_id: market_data.MarketDataSnapshotId

    def __post_init__(self) -> None:
        if not isinstance(self.request, market_data.QuoteRequest):
            raise InfrastructureCompositionValidationError(
                "quote ingestion request must be QuoteRequest"
            )
        if not isinstance(self.snapshot_id, market_data.MarketDataSnapshotId):
            raise InfrastructureCompositionValidationError(
                "quote ingestion snapshot_id must be MarketDataSnapshotId"
            )


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceOhlcIngestionRequest:
    """Explicit OHLC normalization request for an end-to-end composition."""

    request: market_data.OhlcRequest
    snapshot_id: market_data.MarketDataSnapshotId

    def __post_init__(self) -> None:
        if not isinstance(self.request, market_data.OhlcRequest):
            raise InfrastructureCompositionValidationError(
                "OHLC ingestion request must be OhlcRequest"
            )
        if not isinstance(self.snapshot_id, market_data.MarketDataSnapshotId):
            raise InfrastructureCompositionValidationError(
                "OHLC ingestion snapshot_id must be MarketDataSnapshotId"
            )


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceInfrastructureEndToEndConfiguration:
    """Explicit deterministic inputs for reference infrastructure E2E composition."""

    market_data_descriptor: ports.ExternalSourceDescriptor
    persistence_descriptor: ports.ExternalSourceDescriptor
    metadata: ports.ExternalRequestMetadata
    quote_payloads: tuple[ingestion.ExternalQuotePayload, ...] = ()
    ohlc_payloads: tuple[ingestion.ExternalOhlcPayload, ...] = ()
    quote_ingestions: tuple[ReferenceQuoteIngestionRequest, ...] = ()
    ohlc_ingestions: tuple[ReferenceOhlcIngestionRequest, ...] = ()

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
        if not isinstance(self.metadata, ports.ExternalRequestMetadata):
            raise InfrastructureCompositionValidationError(
                "metadata must be ExternalRequestMetadata"
            )
        _validate_item_tuple(
            self.quote_payloads,
            item_type=ingestion.ExternalQuotePayload,
            field_name="quote_payloads",
        )
        _validate_item_tuple(
            self.ohlc_payloads,
            item_type=ingestion.ExternalOhlcPayload,
            field_name="ohlc_payloads",
        )
        _validate_item_tuple(
            self.quote_ingestions,
            item_type=ReferenceQuoteIngestionRequest,
            field_name="quote_ingestions",
        )
        _validate_item_tuple(
            self.ohlc_ingestions,
            item_type=ReferenceOhlcIngestionRequest,
            field_name="ohlc_ingestions",
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
                "infrastructure composition adapters must be "
                "ReferenceInfrastructureAdapters"
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


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceInfrastructureEndToEndComposition[PersistenceValueT]:
    """E2E root from external payload adapter to canonical infrastructure ports."""

    core: core_application.CoreApplication
    external_market_data: (
        reference_payload_adapters.ReferenceExternalMarketDataPayloadAdapter
    )
    ingestion: ingestion.MarketDataIngestionFlow
    infrastructure: ReferenceInfrastructureComposition[PersistenceValueT]

    def __post_init__(self) -> None:
        if not isinstance(self.core, core_application.CoreApplication):
            raise InfrastructureCompositionValidationError(
                "end-to-end composition core must be CoreApplication"
            )
        if not isinstance(
            self.external_market_data,
            reference_payload_adapters.ReferenceExternalMarketDataPayloadAdapter,
        ):
            raise InfrastructureCompositionValidationError(
                "external_market_data must be ReferenceExternalMarketDataPayloadAdapter"
            )
        if not isinstance(self.ingestion, ingestion.MarketDataIngestionFlow):
            raise InfrastructureCompositionValidationError(
                "ingestion must be MarketDataIngestionFlow"
            )
        if not isinstance(self.infrastructure, ReferenceInfrastructureComposition):
            raise InfrastructureCompositionValidationError(
                "infrastructure must be ReferenceInfrastructureComposition"
            )
        if self.infrastructure.core is not self.core:
            raise InfrastructureCompositionValidationError(
                "end-to-end composition must preserve the same CoreApplication"
            )
        if self.ingestion.port is not self.external_market_data:
            raise InfrastructureCompositionValidationError(
                "ingestion must use the composed external market-data adapter"
            )

    @property
    def adapters(self) -> ReferenceInfrastructureAdapters[PersistenceValueT]:
        """Expose canonical adapters while retaining E2E adapters outside Core."""
        return self.infrastructure.adapters

    @property
    def ports(self) -> InfrastructurePorts[PersistenceValueT]:
        """Expose canonical infrastructure ports to consumers above Core."""
        return self.infrastructure.ports


def _validation_failure(
    message: str,
) -> result_contract.Failure[ports.ExternalPortError]:
    return result_contract.Failure(InfrastructureCompositionValidationError(message))


def _ingest_quotes(
    flow: ingestion.MarketDataIngestionFlow,
    requests: tuple[ReferenceQuoteIngestionRequest, ...],
    *,
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[
    tuple[market_data.QuoteSnapshot, ...],
    ports.ExternalPortError,
]:
    snapshots: list[market_data.QuoteSnapshot] = []
    for request in requests:
        result = flow.ingest_quote(
            request.request,
            snapshot_id=request.snapshot_id,
            metadata=metadata,
        )
        if isinstance(result, result_contract.Failure):
            return result
        snapshots.append(result.value)
    return result_contract.Success(tuple(snapshots))


def _ingest_ohlc(
    flow: ingestion.MarketDataIngestionFlow,
    requests: tuple[ReferenceOhlcIngestionRequest, ...],
    *,
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[
    tuple[market_data.OhlcSnapshot, ...],
    ports.ExternalPortError,
]:
    snapshots: list[market_data.OhlcSnapshot] = []
    for request in requests:
        result = flow.ingest_ohlc(
            request.request,
            snapshot_id=request.snapshot_id,
            metadata=metadata,
        )
        if isinstance(result, result_contract.Failure):
            return result
        snapshots.append(result.value)
    return result_contract.Success(tuple(snapshots))


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


def compose_reference_infrastructure_end_to_end[PersistenceValueT](
    core: core_application.CoreApplication,
    configuration: ReferenceInfrastructureEndToEndConfiguration,
) -> result_contract.Result[
    ReferenceInfrastructureEndToEndComposition[PersistenceValueT],
    ports.ExternalPortError,
]:
    """Compose external payload adapter, normalization flow, and canonical ports."""
    if not isinstance(core, core_application.CoreApplication):
        return _validation_failure("core must be CoreApplication")
    if not isinstance(configuration, ReferenceInfrastructureEndToEndConfiguration):
        return _validation_failure(
            "configuration must be ReferenceInfrastructureEndToEndConfiguration"
        )

    try:
        external_market_data = (
            reference_payload_adapters.ReferenceExternalMarketDataPayloadAdapter(
                configuration.market_data_descriptor,
                quotes=configuration.quote_payloads,
                ohlc=configuration.ohlc_payloads,
            )
        )
        flow = ingestion.MarketDataIngestionFlow(external_market_data)
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)

    quote_result = _ingest_quotes(
        flow,
        configuration.quote_ingestions,
        metadata=configuration.metadata,
    )
    if isinstance(quote_result, result_contract.Failure):
        return quote_result

    ohlc_result = _ingest_ohlc(
        flow,
        configuration.ohlc_ingestions,
        metadata=configuration.metadata,
    )
    if isinstance(ohlc_result, result_contract.Failure):
        return ohlc_result

    canonical_configuration = ReferenceInfrastructureConfiguration(
        market_data_descriptor=configuration.market_data_descriptor,
        persistence_descriptor=configuration.persistence_descriptor,
        quote_snapshots=quote_result.value,
        ohlc_snapshots=ohlc_result.value,
    )
    infrastructure_result: result_contract.Result[
        ReferenceInfrastructureComposition[PersistenceValueT],
        ports.ExternalPortError,
    ] = compose_reference_infrastructure(core, canonical_configuration)
    if isinstance(infrastructure_result, result_contract.Failure):
        return infrastructure_result

    try:
        composition = ReferenceInfrastructureEndToEndComposition(
            core=core,
            external_market_data=external_market_data,
            ingestion=flow,
            infrastructure=infrastructure_result.value,
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(composition)
