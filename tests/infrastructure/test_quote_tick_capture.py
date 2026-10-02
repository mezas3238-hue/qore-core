from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.ingestion import ExternalQuotePayload
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketIngressSequence,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.quote_tick_capture import retain_external_quote_tick


_BASE = datetime(2026, 9, 27, 14, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("77000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo"),
)


def _uuid(value: int) -> UUID:
    return UUID(f"77000000-0000-0000-0000-{value:012d}")


def _retain(*, received_at: datetime | None = None):
    payload = ExternalQuotePayload(
        source=_SOURCE,
        instrument="NAS100",
        observed_at=_BASE,
        bid="20123.40",
        ask="20124.10",
    )
    receipt = received_at or _BASE + timedelta(milliseconds=5)
    ingress = receipt + timedelta(milliseconds=1)
    return retain_external_quote_tick(
        payload=payload,
        expected_instrument=Instrument("NAS100"),
        observation_id=MarketObservationId(_uuid(3)),
        quote_evidence_ref=MarketObservationEvidenceReference(_uuid(4)),
        event_id=MarketEventObservationId(_uuid(5)),
        capture_lineage_id=MarketCaptureLineageId(_uuid(6)),
        capture_session_id=MarketCaptureSessionId(_uuid(7)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(0),
        ingress_sequence=MarketIngressSequence(11),
        boundary_received_at=receipt,
        core_ingress_at=ingress,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            _uuid(8)
        ),
    )


def test_retains_exact_quote_with_core_ingress_availability() -> None:
    event = _retain()

    assert event.payload_kind == "quote"
    assert event.payload.instrument == Instrument("NAS100")
    assert event.payload.canonical_spread == "0.7"
    assert event.availability_basis is MarketEventAvailabilityBasis.CORE_INGRESS
    assert event.available_at == event.core_ingress_at
    assert event.ingress_sequence == MarketIngressSequence(11)


def test_capture_cannot_claim_receipt_before_provider_quote_boundary() -> None:
    with pytest.raises(Exception, match="receipt cannot predate"):
        _retain(received_at=_BASE - timedelta(microseconds=1))


def test_capture_has_no_generated_identity_or_hidden_clock() -> None:
    first = _retain()
    second = _retain()

    assert first.logical_values() == second.logical_values()
