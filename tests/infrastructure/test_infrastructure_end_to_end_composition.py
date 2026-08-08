from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CausationId, CorrelationId
from qore.governance.composition import compose_functional_governance
from qore.infrastructure.composition import (
    InfrastructureCompositionValidationError,
    ReferenceInfrastructureEndToEndComposition,
    ReferenceInfrastructureEndToEndConfiguration,
    ReferenceOhlcIngestionRequest,
    ReferenceQuoteIngestionRequest,
    compose_reference_infrastructure_end_to_end,
)
from qore.infrastructure.ingestion import (
    ExternalOhlcPayload,
    ExternalQuotePayload,
    IngestionValidationError,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataPort,
    MarketDataSnapshotId,
    OhlcRequest,
    QuoteRequest,
    Timeframe,
)
from qore.infrastructure.persistence import (
    LoadPersistenceRequest,
    PersistenceKey,
    PersistencePort,
    PersistenceVersion,
    SavePersistenceRequest,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success
from qore.specialized_governance.composition import compose_specialized_governance

_OBSERVED_AT = datetime(2026, 8, 8, 0, 30, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_MARKET_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f2000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("f2000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.e2e-reference"),
)
_PERSISTENCE_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f2000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("f2000000-0000-0000-0000-000000000004")),
    port_name=PortName("persistence.e2e-reference"),
)
_CORRELATION = CorrelationId(UUID("f2000000-0000-0000-0000-000000000005"))
_CAUSATION = CausationId(UUID("f2000000-0000-0000-0000-000000000006"))
_QUOTE_ID = MarketDataSnapshotId(UUID("f2000000-0000-0000-0000-000000000010"))
_OHLC_ID = MarketDataSnapshotId(UUID("f2000000-0000-0000-0000-000000000011"))
_KEY = PersistenceKey("infra.e2e", "snapshot/reference")
_VERSION_ZERO = PersistenceVersion(0)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _core(name: str = "qore-infra-e2e-test") -> CoreApplication:
    boot = bootstrap(Configuration(application_name=name))
    assert isinstance(boot, Success)
    return boot.value


def _quote_request() -> QuoteRequest:
    return QuoteRequest(_INSTRUMENT)


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def _quote_payload() -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=_MARKET_DESCRIPTOR,
        instrument=" eurusd ",
        observed_at=_OBSERVED_AT,
        bid="1.1600",
        ask="1.1602",
    )


def _ohlc_payload() -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=_MARKET_DESCRIPTOR,
        instrument="eurusd",
        timeframe_seconds="900",
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open="1.1550",
        high="1.1650",
        low="1.1500",
        close="1.1600",
    )


def _configuration(
    *,
    quote_payloads: tuple[ExternalQuotePayload, ...] | None = None,
    ohlc_payloads: tuple[ExternalOhlcPayload, ...] | None = None,
) -> ReferenceInfrastructureEndToEndConfiguration:
    return ReferenceInfrastructureEndToEndConfiguration(
        market_data_descriptor=_MARKET_DESCRIPTOR,
        persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
        metadata=_metadata(),
        quote_payloads=(
            (_quote_payload(),) if quote_payloads is None else quote_payloads
        ),
        ohlc_payloads=(_ohlc_payload(),) if ohlc_payloads is None else ohlc_payloads,
        quote_ingestions=(
            ReferenceQuoteIngestionRequest(
                request=_quote_request(),
                snapshot_id=_QUOTE_ID,
            ),
        ),
        ohlc_ingestions=(
            ReferenceOhlcIngestionRequest(
                request=_ohlc_request(),
                snapshot_id=_OHLC_ID,
            ),
        ),
    )


def _composition() -> ReferenceInfrastructureEndToEndComposition[dict[str, int]]:
    composed: Result[
        ReferenceInfrastructureEndToEndComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure_end_to_end(_core(), _configuration())
    assert isinstance(composed, Success)
    return composed.value


def _save_request(value: dict[str, int]) -> SavePersistenceRequest[dict[str, int]]:
    return SavePersistenceRequest(
        key=_KEY,
        version=_VERSION_ZERO,
        value=value,
        stored_at=_OBSERVED_AT,
    )


def test_reference_infrastructure_end_to_end_composes_above_core() -> None:
    core = _core()
    before_snapshot = core.runtime_snapshot()
    before_health = core.runtime_health()

    composed: Result[
        ReferenceInfrastructureEndToEndComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure_end_to_end(core, _configuration())

    assert isinstance(composed, Success)
    application = composed.value
    assert application.core is core
    assert application.infrastructure.core is core
    assert application.ingestion.port is application.external_market_data
    assert application.adapters is application.infrastructure.adapters
    assert application.ports is application.infrastructure.ports
    assert core.runtime_snapshot() == before_snapshot
    assert core.runtime_health() == before_health
    assert len(core.runtime_plan.components) == 1
    assert core.runtime_plan.components[0].component is core.engine


def test_reference_infrastructure_end_to_end_consumes_canonical_ports() -> None:
    application = _composition()
    market_port: MarketDataPort = application.ports.market_data
    persistence_port: PersistencePort[dict[str, int]] = application.ports.persistence

    quote = market_port.read_quote(_quote_request(), metadata=_metadata())
    ohlc = market_port.read_ohlc(_ohlc_request(), metadata=_metadata())
    saved = persistence_port.save(_save_request({"score": 42}), metadata=_metadata())
    loaded = persistence_port.load(LoadPersistenceRequest(_KEY), metadata=_metadata())

    assert isinstance(quote, Success)
    assert quote.value.snapshot_id is _QUOTE_ID
    assert quote.value.source is _MARKET_DESCRIPTOR
    assert quote.value.instrument == _INSTRUMENT
    assert quote.value.observed_at is _OBSERVED_AT
    assert quote.value.bid == 1.16
    assert quote.value.ask == 1.1602
    assert isinstance(ohlc, Success)
    assert ohlc.value.snapshot_id is _OHLC_ID
    assert ohlc.value.source is _MARKET_DESCRIPTOR
    assert ohlc.value.timeframe == _TIMEFRAME
    assert ohlc.value.open == 1.155
    assert ohlc.value.high == 1.165
    assert ohlc.value.low == 1.15
    assert ohlc.value.close == 1.16
    assert isinstance(saved, Success)
    assert isinstance(loaded, Success)
    assert loaded.value is not None
    assert loaded.value.value == {"score": 42}


def test_reference_infrastructure_end_to_end_compositions_are_isolated() -> None:
    first = _composition()
    second = _composition()

    saved = first.ports.persistence.save(
        _save_request({"score": 7}),
        metadata=_metadata(),
    )
    second_load = second.ports.persistence.load(
        LoadPersistenceRequest(_KEY),
        metadata=_metadata(),
    )

    assert isinstance(saved, Success)
    assert first.core is not second.core
    assert first.external_market_data is not second.external_market_data
    assert first.ingestion is not second.ingestion
    assert first.adapters.market_data is not second.adapters.market_data
    assert first.adapters.persistence is not second.adapters.persistence
    assert isinstance(second_load, Success)
    assert second_load.value is None


def test_reference_infrastructure_end_to_end_propagates_normalization_failure() -> None:
    core = _core()
    before_snapshot = core.runtime_snapshot()
    invalid_quote = ExternalQuotePayload(
        source=_MARKET_DESCRIPTOR,
        instrument="EURUSD",
        observed_at=_OBSERVED_AT,
        bid="1.1600",
        ask="0",
    )
    configuration = _configuration(quote_payloads=(invalid_quote,))

    result: Result[
        ReferenceInfrastructureEndToEndComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure_end_to_end(core, configuration)

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert core.runtime_snapshot() == before_snapshot


def test_reference_infrastructure_end_to_end_rejects_invalid_boundaries() -> None:
    with pytest.raises(
        InfrastructureCompositionValidationError,
        match="metadata",
    ):
        ReferenceInfrastructureEndToEndConfiguration(
            market_data_descriptor=_MARKET_DESCRIPTOR,
            persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
            metadata=cast(ExternalRequestMetadata, object()),
        )

    invalid_core: Result[
        ReferenceInfrastructureEndToEndComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure_end_to_end(
        cast(CoreApplication, object()),
        _configuration(),
    )
    invalid_configuration: Result[
        ReferenceInfrastructureEndToEndComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure_end_to_end(
        _core(),
        cast(ReferenceInfrastructureEndToEndConfiguration, object()),
    )

    assert isinstance(invalid_core, Failure)
    assert isinstance(invalid_core.error, InfrastructureCompositionValidationError)
    assert isinstance(invalid_configuration, Failure)
    assert isinstance(
        invalid_configuration.error,
        InfrastructureCompositionValidationError,
    )


def test_functional_and_specialized_governance_remain_without_e2e_infra() -> None:
    functional = compose_functional_governance(
        Configuration(application_name="qore-functional-after-infra-e2e")
    )
    specialized = compose_specialized_governance(
        Configuration(application_name="qore-specialized-after-infra-e2e")
    )

    assert isinstance(functional, Success)
    assert isinstance(specialized, Success)
    assert len(functional.value.core.runtime_plan.components) == 1
    assert len(specialized.value.core.runtime_plan.components) == 1


def test_public_exports_include_reference_infrastructure_end_to_end() -> None:
    import qore.infrastructure as infrastructure

    assert (
        infrastructure.ReferenceInfrastructureEndToEndConfiguration
        is ReferenceInfrastructureEndToEndConfiguration
    )
    assert (
        infrastructure.ReferenceQuoteIngestionRequest
        is ReferenceQuoteIngestionRequest
    )
    assert (
        infrastructure.ReferenceOhlcIngestionRequest
        is ReferenceOhlcIngestionRequest
    )
    assert (
        infrastructure.compose_reference_infrastructure_end_to_end
        is compose_reference_infrastructure_end_to_end
    )
