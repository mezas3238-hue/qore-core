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
    OhlcRequest,
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
)\nfrom qore.infrastructure.reference_adapters import ReferenceAdapterValidationError
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


def _quote(
    *,
    source: ExternalSourceDescriptor = _MARKET_DESCRIPTOR,
) -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("f1000000-0000-0000-0000-000000000010")
        ),
        instrument=_INSTRUMENT,
        source=source,
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
    return cast(ReferenceInfrastructureComposition[dict[str, int]], composed.value)


def _save_request(
    value: dict[str, int],
    *,
    version: PersistenceVersion = _VERSION_ZERO,
    expected_version: PersistenceVersion | None = None,
) -> SavePersistenceRequest[dict[str, int]]:
    return SavePersistenceRequest(
        key=_KEY,
        version=version,
        value=value,
        stored_at=_NOW,
        expected_version=expected_version,
    )


def test_reference_infrastructure_composes_ports_above_one_core_instance() -> None:
    core = _core()
    before_snapshot = core.runtime_snapshot()
    before_health = core.runtime_health()

    composed: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(core, _configuration())

    assert isinstance(composed, Success)
    application = cast(ReferenceInfrastructureComposition[dict[str, int]], composed.value)
    assert application.core is core
    assert application.adapters.market_data is application.ports.market_data
    assert application.adapters.persistence is application.ports.persistence
    assert core.runtime_snapshot() == before_snapshot
    assert core.runtime_health() == before_health
    assert len(core.runtime_plan.components) == 1
    assert core.runtime_plan.components[0].component is core.engine


def test_reference_infrastructure_exposes_market_data_through_port_contract() -> None:
    application = _composition()
    port: MarketDataPort = application.ports.market_data

    quote_result = port.read_quote(QuoteRequest(_INSTRUMENT), metadata=_metadata())
    ohlc_result = port.read_ohlc(
        OhlcRequest(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
        ),
        metadata=_metadata(),
    )

    assert isinstance(quote_result, Success)
    assert quote_result.value.logical_values() == _quote().logical_values()
    assert isinstance(ohlc_result, Success)
    assert ohlc_result.value.logical_values() == _ohlc().logical_values()


def test_reference_infrastructure_exposes_persistence_through_port_contract() -> None:
    application = _composition()
    port: PersistencePort[dict[str, int]] = application.ports.persistence

    saved = port.save(_save_request({"score": 1}), metadata=_metadata())
    loaded = port.load(LoadPersistenceRequest(_KEY), metadata=_metadata())

    assert isinstance(saved, Success)
    assert saved.value.source is _PERSISTENCE_DESCRIPTOR
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


def test_reference_infrastructure_rejects_implicit_or_wrong_boundaries() -> None:
    wrong_market_descriptor = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000020")),
        source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000021")),
        port_name=PortName("persistence.reference-composition"),
    )

    with pytest.raises(
        InfrastructureCompositionValidationError,
        match="market_data_descriptor",
    ):
        ReferenceInfrastructureConfiguration(
            market_data_descriptor=wrong_market_descriptor,
            persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
        )

    with pytest.raises(
        InfrastructureCompositionValidationError,
        match="quote_snapshots",
    ):
        ReferenceInfrastructureConfiguration(
            market_data_descriptor=_MARKET_DESCRIPTOR,
            persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
            quote_snapshots=cast(tuple[QuoteSnapshot, ...], object()),
        )


def test_reference_infrastructure_propagates_adapter_configuration_failure() -> None:
    other_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000030")),
        source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000031")),
        port_name=PortName("market-data.other"),
    )
    configuration = ReferenceInfrastructureConfiguration(
        market_data_descriptor=_MARKET_DESCRIPTOR,
        persistence_descriptor=_PERSISTENCE_DESCRIPTOR,
        quote_snapshots=(_quote(source=other_source),),
    )

    result: Result[
        ReferenceInfrastructureComposition[dict[str, int]],
        ExternalPortError,
    ] = compose_reference_infrastructure(_core(), configuration)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReferenceAdapterValidationError)


def test_reference_infrastructure_rejects_runtime_bypasses_without_mutating_core() -> None:
    core = _core()
    before_snapshot = core.runtime_snapshot()

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
        core,
        cast(ReferenceInfrastructureConfiguration, object()),
    )

    assert isinstance(invalid_core, Failure)
    assert isinstance(invalid_core.error, InfrastructureCompositionValidationError)
    assert isinstance(invalid_configuration, Failure)
    assert isinstance(
        invalid_configuration.error,
        InfrastructureCompositionValidationError,
    )
    assert core.runtime_snapshot() == before_snapshot


def test_functional_and_specialized_governance_still_compose_without_infrastructure() -> None:
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
    assert (
        functional.value.core.runtime_plan.components[0].component
        is functional.value.core.engine
    )
    assert (
        specialized.value.core.runtime_plan.components[0].component
        is specialized.value.core.engine
    )


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
