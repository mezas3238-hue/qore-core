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
    ReferenceInfrastructureComposition,
    ReferenceInfrastructureConfiguration,
    compose_reference_infrastructure,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataPort,
    MarketDataSnapshotId,
    OhlcSnapshot,
    QuoteRequest,
    QuoteSnapshot,
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
from qore.infrastructure.reference_adapters import ReferenceAdapterValidationError
from qore.kernel.result import Failure, Result, Success
from qore.specialized_governance.composition import compose_specialized_governance

_NOW = datetime(2026, 8, 8, 0, 15, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_MARKET_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.reference-composition"),
)
_PERSISTENCE_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000004")),
    port_name=PortName("persistence.reference-composition"),
)
_CORRELATION = CorrelationId(UUID("f1000000-0000-0000-0000-000000000005"))
_CAUSATION = CausationId(UUID("f1000000-0000-0000-0000-000000000006"))
_KEY = PersistenceKey("infra.composition", "snapshot/reference")
_VERSION_ZERO = PersistenceVersion(0)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _core(name: str = "qore-infra-composition-test") -> CoreApplication:
    boot = bootstrap(Configuration(application_name=name))
    assert isinstance(boot, Success)
    return boot.value


def _quote() -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("f1000000-0000-0000-0000-000000000010")
        ),
        instrument=_INSTRUMENT,
        source=_MARKET_DESCRIPTOR,
        observed_at=_NOW,
        bid=1.16,
        ask=1.1602,
    )


def _ohlc() -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("f1000000-0000-0000-0000-000000000011")
        ),
        instrument=_INSTRUMENT,
        source=_MARKET_DESCRIPTOR,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open=1.155,
        high=1.165,
        low=1.15,
        close=1.16,
    )


def _configuration() -> ReferenceInfrastructureConfiguration:
    return ReferenceInfrastructureConfiguration(
        market_data_descriptor=_MARKET_DESCRIPTOR,
        persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
        quote_snapshots=(_quote(),),
        ohlc_snapshots=(_ohlc(),),
    )


def _composition() -> ReferenceInfrastructureComposition[dict[str, int]]:
    composed: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(_core(), _configuration())
    assert isinstance(composed, Success)
    return composed.value


def _save_request(value: dict[str, int]) -> SavePersistenceRequest[dict[str, int]]:
    return SavePersistenceRequest(
        key=_KEY,
        version=_VERSION_ZERO,
        value=value,
        stored_at=_NOW,
    )


def test_reference_infrastructure_composes_above_one_core_instance() -> None:
    core = _core()
    before_snapshot = core.runtime_snapshot()
    composed: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(core, _configuration())

    assert isinstance(composed, Success)
    assert composed.value.core is core
    assert composed.value.adapters.market_data is composed.value.ports.market_data
    assert composed.value.adapters.persistence is composed.value.ports.persistence
    assert core.runtime_snapshot() == before_snapshot
    assert len(core.runtime_plan.components) == 1
    assert core.runtime_plan.components[0].component is core.engine


def test_reference_infrastructure_exposes_adapters_through_ports() -> None:
    application = _composition()
    market_port: MarketDataPort = application.ports.market_data
    persistence_port: PersistencePort[dict[str, int]] = application.ports.persistence

    quote = market_port.read_quote(QuoteRequest(_INSTRUMENT), metadata=_metadata())
    saved = persistence_port.save(_save_request({"score": 1}), metadata=_metadata())
    loaded = persistence_port.load(LoadPersistenceRequest(_KEY), metadata=_metadata())

    assert isinstance(quote, Success)
    assert quote.value.logical_values() == _quote().logical_values()
    assert isinstance(saved, Success)
    assert isinstance(loaded, Success)
    assert loaded.value is not None
    assert loaded.value.value == {"score": 1}


def test_reference_infrastructure_compositions_are_isolated_by_instance() -> None:
    first = _composition()
    second = _composition()

    save_result = first.ports.persistence.save(
        _save_request({"score": 10}),
        metadata=_metadata(),
    )
    second_load = second.ports.persistence.load(
        LoadPersistenceRequest(_KEY),
        metadata=_metadata(),
    )

    assert isinstance(save_result, Success)
    assert first.core is not second.core
    assert first.adapters.market_data is not second.adapters.market_data
    assert first.adapters.persistence is not second.adapters.persistence
    assert isinstance(second_load, Success)
    assert second_load.value is None


def test_reference_infrastructure_rejects_invalid_boundaries() -> None:
    wrong_market_descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000020")),
        source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000021")),
        port_name=PortName("persistence.reference-composition"),
    )
    other_market_descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000022")),
        source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000023")),
        port_name=PortName("market-data.other"),
    )

    with pytest.raises(
        InfrastructureCompositionValidationError,
        match="market_data_descriptor",
    ):
        ReferenceInfrastructureConfiguration(
            market_data_descriptor=wrong_market_descriptor,
            persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
        )

    configuration = ReferenceInfrastructureConfiguration(
        market_data_descriptor=_MARKET_DESCRIPTOR,
        persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
        quote_snapshots=(
            QuoteSnapshot(
                snapshot_id=MarketDataSnapshotId(
                    UUID("f1000000-0000-0000-0000-000000000030")
                ),
                instrument=_INSTRUMENT,
                source=other_market_descriptor,
                observed_at=_NOW,
                bid=1.16,
                ask=1.1602,
            ),
        ),
    )
    result: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(_core(), configuration)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterValidationError)


def test_reference_infrastructure_rejects_runtime_bypasses() -> None:
    invalid_core: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(
        cast(CoreApplication, object()),
        _configuration(),
    )
    invalid_configuration: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(
        _core(),
        cast(ReferenceInfrastructureConfiguration, object()),
    )

    assert isinstance(invalid_core, Failure)
    assert isinstance(invalid_core.error, InfrastructureCompositionValidationError)
    assert isinstance(invalid_configuration, Failure)
    assert isinstance(
        invalid_configuration.error,
        InfrastructureCompositionValidationError,
    )


def test_functional_and_specialized_governance_still_compose_without_infra() -> None:
    functional = compose_functional_governance(
        Configuration(application_name="qore-functional-after-infra-composition")
    )
    specialized = compose_specialized_governance(
        Configuration(application_name="qore-specialized-after-infra-composition")
    )

    assert isinstance(functional, Success)
    assert isinstance(specialized, Success)
    assert len(functional.value.core.runtime_plan.components) == 1
    assert len(specialized.value.core.runtime_plan.components) == 1


def test_public_exports_include_reference_infrastructure_composition() -> None:
    import qore.infrastructure as infrastructure

    assert (
        infrastructure.ReferenceInfrastructureConfiguration
        is ReferenceInfrastructureConfiguration
    )
    assert (
        infrastructure.compose_reference_infrastructure
        is compose_reference_infrastructure
    )
    assert issubclass(
        infrastructure.InfrastructureCompositionValidationError,
        ExternalPortError,
    )
