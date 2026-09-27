"""Pure qualification of provider quote payloads into exact retained evidence.

The ordinary ingestion flow normalizes provider quotes into floating-point
runtime snapshots. Scientific replay needs a stronger contract: exact decimal
Bid/Ask evidence with explicit source, timestamp and evidence identity.

This module performs that stronger qualification without IO, hidden clocks,
generated UUIDs, capture ordering or trading authority. Capture chronology is
owned by market_event_replay once the quote has been qualified.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from qore.infrastructure.ingestion import ExternalQuotePayload
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    QualifiedQuoteTickObservation,
)


class QualifiedQuoteEvidenceError(ValueError):
    """External quote cannot form exact retained market evidence."""


def _exact_decimal(value: object, *, field_name: str) -> Decimal:
    # Float inputs may be acceptable for low-level runtime normalization but
    # cannot prove the provider's exact decimal representation for retained
    # scientific evidence.
    if not isinstance(value, str):
        raise QualifiedQuoteEvidenceError(
            f"{field_name} exact evidence requires provider decimal string"
        )
    candidate = value.strip()
    if not candidate:
        raise QualifiedQuoteEvidenceError(
            f"{field_name} exact evidence cannot be empty"
        )
    try:
        result = Decimal(candidate)
    except InvalidOperation as error:
        raise QualifiedQuoteEvidenceError(
            f"{field_name} exact evidence is not decimal"
        ) from error
    if not result.is_finite() or result <= 0:
        raise QualifiedQuoteEvidenceError(
            f"{field_name} exact evidence must be positive and finite"
        )
    return result


def qualify_external_quote_evidence(
    *,
    payload: ExternalQuotePayload,
    observation_id: MarketObservationId,
    evidence_ref: MarketObservationEvidenceReference,
    expected_instrument: Instrument | None = None,
) -> QualifiedQuoteTickObservation:
    """Create one exact quote observation from provider-neutral payload evidence.

    All identities are caller supplied. No arrival chronology is fabricated here.
    """

    if not isinstance(payload, ExternalQuotePayload):
        raise QualifiedQuoteEvidenceError(
            "payload must be ExternalQuotePayload"
        )
    if not isinstance(observation_id, MarketObservationId):
        raise QualifiedQuoteEvidenceError(
            "observation_id must be MarketObservationId"
        )
    if not isinstance(evidence_ref, MarketObservationEvidenceReference):
        raise QualifiedQuoteEvidenceError(
            "evidence_ref must be MarketObservationEvidenceReference"
        )
    if payload.observed_at.tzinfo is None or payload.observed_at.utcoffset() is None:
        raise QualifiedQuoteEvidenceError(
            "quote evidence timestamp must be timezone-aware"
        )

    raw_instrument = payload.instrument
    if not isinstance(raw_instrument, str):
        raise QualifiedQuoteEvidenceError(
            "quote evidence instrument must be string"
        )
    normalized = raw_instrument.strip().upper()
    if not normalized:
        raise QualifiedQuoteEvidenceError(
            "quote evidence instrument cannot be empty"
        )
    instrument = Instrument(normalized)
    if expected_instrument is not None and instrument != expected_instrument:
        raise QualifiedQuoteEvidenceError(
            "quote evidence instrument does not match expected instrument"
        )

    bid = MarketPrice(_exact_decimal(payload.bid, field_name="bid"))
    ask = MarketPrice(_exact_decimal(payload.ask, field_name="ask"))

    return QualifiedQuoteTickObservation(
        observation_id=observation_id,
        instrument=instrument,
        source=payload.source,
        observed_at=payload.observed_at,
        bid=bid,
        ask=ask,
        evidence_ref=evidence_ref,
    )
