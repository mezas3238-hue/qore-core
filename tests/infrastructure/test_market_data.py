from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataPort,
    MarketDataSnapshotId,
    MarketDataValidationError,
    OhlcRequest,
    OhlcSnapshot,
    QuoteRequest,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.kernel.result import Result, Success

_OPENED_AT = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_QUOTE_AT = datetime(2026, 8, 7, 12, 7, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("b1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("b1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.reference"),
)
_CORRELATION = CorrelationId(UUID("b1000000-0000-0000-0000-000000000003"))
_CAUSATION = CausationId(UUID("b1000000-0000-0000-0000-000000000004"))
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(900)
_QUOTE_ID = MarketDataSnapshotId(UUID("b1000000-0000-0000-0000-000000000005"))
_OHLC_ID = MarketDataSnapshotId(UUID("b1000000-0000-0000-0000-000000000006"))


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _quote() -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=_QUOTE_ID,
        instrument=_INSTRUMENT,
        source=_SOURCE,
        observed_at=_QUOTE_AT,
        bid=1.165,
        ask=1.1652,
    )


def _ohlc() -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=_OHLC_ID,
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open=1.16,
        high=1.17,
        low=1.155,
        close=1.165,
    )


class FakeMarketDataPort:
    def __init__(self, descriptor: ExternalSourceDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[QuoteSnapshot, ExternalPortError]:
        del metadata
        assert request.instrument == _INSTRUMENT
        return Success(_quote())

    def read_ohlc(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OhlcSnapshot, ExternalPortError]:
        del metadata
        assert request.instrument == _INSTRUMENT
        assert request.timeframe == _TIMEFRAME
        return Success(_ohlc())


def _read_quote_through(port: MarketDataPort) -> Result[QuoteSnapshot, ExternalPortError]:
    return port.read_quote(QuoteRequest(_INSTRUMENT), metadata=_metadata())


def test_instrument_and_timeframe_are_canonical_and_explicit() -> None:
    assert Instrument("GBPUSD").symbol == "GBPUSD"
    assert Timeframe(300).seconds == 300

    with pytest.raises(MarketDataValidationError, match="canonical uppercase"):
        Instrument("eurusd")
    with pytest.raises(MarketDataValidationError, match="canonical uppercase"):
        Instrument("EUR USD")
    with pytest.raises(MarketDataValidationError, match="positive int"):
        Timeframe(0)
    with pytest.raises(MarketDataValidationError, match="positive int"):
        Timeframe(cast(int, True))


def test_quote_snapshot_is_immutable_canonical_and_stable() -> None:
    first = _quote()
    second = QuoteSnapshot(
        snapshot_id=_QUOTE_ID,
        instrument=Instrument("EURUSD"),
        source=_SOURCE,
        observed_at=_QUOTE_AT,
        bid=1.165,
        ask=1.1652,
    )

    assert first.logical_values() == second.logical_values()
    assert first.source is _SOURCE
    assert first.snapshot_id is _QUOTE_ID


def test_snapshots_reject_non_market_data_source_namespace() -> None:
    wrong_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("b1000000-0000-0000-0000-000000000011")),
        source_id=SourceId(UUID("b1000000-0000-0000-0000-000000000012")),
        port_name=PortName("persistence.reference"),
    )
    with pytest.raises(MarketDataValidationError, match="market-data namespace"):
        QuoteSnapshot(
            snapshot_id=_QUOTE_ID,
            instrument=_INSTRUMENT,
            source=wrong_source,
            observed_at=_QUOTE_AT,
            bid=1.0,
            ask=1.1,
        )
    with pytest.raises(MarketDataValidationError, match="market-data namespace"):
        OhlcSnapshot(
            snapshot_id=_OHLC_ID,
            instrument=_INSTRUMENT,
            source=wrong_source,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            open=1.0,
            high=1.1,
            low=0.9,
            close=1.05,
        )


def test_quote_rejects_invalid_prices_time_and_runtime_types() -> None:
    with pytest.raises(MarketDataValidationError, match="bid must not exceed ask"):
        QuoteSnapshot(
            snapshot_id=_QUOTE_ID,
            instrument=_INSTRUMENT,
            source=_SOURCE,
            observed_at=_QUOTE_AT,
            bid=1.2,
            ask=1.1,
        )
    for invalid in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(MarketDataValidationError, match="positive finite"):
            QuoteSnapshot(
                snapshot_id=_QUOTE_ID,
                instrument=_INSTRUMENT,
                source=_SOURCE,
                observed_at=_QUOTE_AT,
                bid=invalid,
                ask=1.2,
            )
    with pytest.raises(MarketDataValidationError, match="timezone-aware"):
        QuoteSnapshot(
            snapshot_id=_QUOTE_ID,
            instrument=_INSTRUMENT,
            source=_SOURCE,
            observed_at=datetime(2026, 8, 7, 12, 0),
            bid=1.0,
            ask=1.1,
        )
    with pytest.raises(MarketDataValidationError, match="instrument"):
        QuoteSnapshot(
            snapshot_id=_QUOTE_ID,
            instrument=cast(Instrument, object()),
            source=_SOURCE,
            observed_at=_QUOTE_AT,
            bid=1.0,
            ask=1.1,
        )


def test_ohlc_snapshot_requires_exact_interval_and_price_consistency() -> None:
    snapshot = _ohlc()
    assert snapshot.timeframe.seconds == 900
    assert snapshot.closed_at - snapshot.opened_at == timedelta(minutes=15)

    with pytest.raises(MarketDataValidationError, match="exactly match timeframe"):
        OhlcSnapshot(
            snapshot_id=_OHLC_ID,
            instrument=_INSTRUMENT,
            source=_SOURCE,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_OPENED_AT + timedelta(minutes=10),
            open=1.16,
            high=1.17,
            low=1.15,
            close=1.16,
        )
    with pytest.raises(MarketDataValidationError, match="open must be within"):
        OhlcSnapshot(
            snapshot_id=_OHLC_ID,
            instrument=_INSTRUMENT,
            source=_SOURCE,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            open=1.18,
            high=1.17,
            low=1.15,
            close=1.16,
        )
    with pytest.raises(MarketDataValidationError, match="close must be within"):
        OhlcSnapshot(
            snapshot_id=_OHLC_ID,
            instrument=_INSTRUMENT,
            source=_SOURCE,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            open=1.16,
            high=1.17,
            low=1.15,
            close=1.18,
        )
    with pytest.raises(MarketDataValidationError, match="low must not exceed high"):
        OhlcSnapshot(
            snapshot_id=_OHLC_ID,
            instrument=_INSTRUMENT,
            source=_SOURCE,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
            open=1.16,
            high=1.15,
            low=1.17,
            close=1.16,
        )


def test_ohlc_request_has_same_temporal_contract_as_snapshot() -> None:
    request = OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=_TIMEFRAME,
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )
    assert request.closed_at > request.opened_at

    with pytest.raises(MarketDataValidationError, match="exactly match timeframe"):
        OhlcRequest(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_OPENED_AT + timedelta(minutes=5),
        )


def test_market_data_port_is_structural_and_provider_neutral() -> None:
    port = FakeMarketDataPort(_SOURCE)
    quote_result = _read_quote_through(port)
    ohlc_result = port.read_ohlc(
        OhlcRequest(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_OPENED_AT,
            closed_at=_CLOSED_AT,
        ),
        metadata=_metadata(),
    )
    health_result = port.health(checked_at=_QUOTE_AT, metadata=_metadata())

    assert isinstance(quote_result, Success)
    assert quote_result.value.source is port.descriptor
    assert isinstance(ohlc_result, Success)
    assert ohlc_result.value.source is port.descriptor
    assert isinstance(health_result, Success)
    assert health_result.value.descriptor is port.descriptor


def test_market_data_contracts_never_generate_identity_source_or_time() -> None:
    quote = _quote()
    ohlc = _ohlc()

    assert quote.snapshot_id is _QUOTE_ID
    assert quote.source is _SOURCE
    assert quote.observed_at is _QUOTE_AT
    assert ohlc.snapshot_id is _OHLC_ID
    assert ohlc.source is _SOURCE
    assert ohlc.opened_at is _OPENED_AT
    assert ohlc.closed_at is _CLOSED_AT
