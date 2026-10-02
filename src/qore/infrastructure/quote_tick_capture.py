"""Pure construction of retained quote-tick capture events.

This module bridges exact provider quote qualification into Market Event Replay
without performing network IO, storage, clock reads or identity generation.
Every provenance field is supplied explicitly by the capture boundary.

It is suitable for future Active Perception capture, but does not itself enable
or deploy any live provider.
"""

from __future__ import annotations

from datetime import datetime

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
    RetainedMarketEventObservation,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
)
from qore.infrastructure.qualified_quote_evidence import (
    qualify_external_quote_evidence,
)


def retain_external_quote_tick(
    *,
    payload: ExternalQuotePayload,
    expected_instrument: Instrument,
    observation_id: MarketObservationId,
    quote_evidence_ref: MarketObservationEvidenceReference,
    event_id: MarketEventObservationId,
    capture_lineage_id: MarketCaptureLineageId,
    capture_session_id: MarketCaptureSessionId,
    capture_session_ordinal: MarketCaptureSessionOrdinal,
    ingress_sequence: MarketIngressSequence,
    boundary_received_at: datetime,
    core_ingress_at: datetime,
    availability_evidence_ref: MarketEventAvailabilityEvidenceReference,
) -> RetainedMarketEventObservation:
    """Qualify and retain one exact quote event with explicit arrival provenance."""

    quote = qualify_external_quote_evidence(
        payload=payload,
        observation_id=observation_id,
        evidence_ref=quote_evidence_ref,
        expected_instrument=expected_instrument,
    )
    return RetainedMarketEventObservation(
        event_id=event_id,
        payload=quote,
        capture_lineage_id=capture_lineage_id,
        capture_session_id=capture_session_id,
        capture_session_ordinal=capture_session_ordinal,
        ingress_sequence=ingress_sequence,
        boundary_received_at=boundary_received_at,
        core_ingress_at=core_ingress_at,
        availability_evidence_at=core_ingress_at,
        available_at=core_ingress_at,
        availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
        availability_evidence_ref=availability_evidence_ref,
    )
