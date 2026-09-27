from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.ingestion import ExternalQuotePayload
from qore.infrastructure.market_data import Instrument
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
from qore.infrastructure.qualified_quote_evidence import (
    QualifiedQuoteEvidenceError,
    qualify_external_quote_evidence,
)


_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("76000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("76000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo"),
)
_OBSERVATION_ID = MarketObservationId(
    UUID("76000000-0000-0000-0000-000000000003")
)
_EVIDENCE_REF = MarketObservationEvidenceReference(
    UUID("76000000-0000-0000-0000-000000000004")
)


def _payload(*, bid: str | float = "20123.40", ask: str | float = "20124.10"):
    return ExternalQuotePayload(
        source=_SOURCE,
        instrument="nas100",
        observed_at=datetime(2026, 9, 27, 14, 0, tzinfo=UTC),
        bid=bid,
        ask=ask,
    )


def test_qualifies_exact_provider_decimal_quote() -> None:
    quote = qualify_external_quote_evidence(
        payload=_payload(),
        observation_id=_OBSERVATION_ID,
        evidence_ref=_EVIDENCE_REF,
        expected_instrument=Instrument("NAS100"),
    )

    assert quote.instrument == Instrument("NAS100")
    assert quote.bid.canonical == "20123.4"
    assert quote.ask.canonical == "20124.1"
    assert quote.canonical_spread == "0.7"
    assert quote.source == _SOURCE


def test_rejects_float_when_exact_provider_decimal_is_unproven() -> None:
    with pytest.raises(QualifiedQuoteEvidenceError, match="decimal string"):
        qualify_external_quote_evidence(
            payload=_payload(bid=20123.4),
            observation_id=_OBSERVATION_ID,
            evidence_ref=_EVIDENCE_REF,
        )


def test_rejects_wrong_expected_instrument() -> None:
    with pytest.raises(QualifiedQuoteEvidenceError, match="expected instrument"):
        qualify_external_quote_evidence(
            payload=_payload(),
            observation_id=_OBSERVATION_ID,
            evidence_ref=_EVIDENCE_REF,
            expected_instrument=Instrument("SP500"),
        )


def test_quote_observation_rejects_crossed_market() -> None:
    with pytest.raises(Exception, match="bid must not exceed ask"):
        qualify_external_quote_evidence(
            payload=_payload(bid="20125.00", ask="20124.00"),
            observation_id=_OBSERVATION_ID,
            evidence_ref=_EVIDENCE_REF,
        )
