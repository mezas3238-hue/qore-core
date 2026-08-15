from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    MarketBarOrigin,
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketOhlcField,
    MarketOhlcFieldValidity,
    MarketPrice,
    MarketPriceSide,
    MarketTimeframe,
    MarketTimeframeCode,
    QualifiedOhlcBarObservation,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.universal_instrument_identity import (
    CanonicalIdentityRef,
    EconomicIdentityId,
    ExternalIdentifier,
    ExternalIdentifierKind,
    ExternalIdentifierNamespace,
    ExternalIdentifierValue,
    ExternalIdentityMappingRevision,
    IdentityEvidenceRef,
    IdentityMappingId,
    IdentityMappingRevision,
)
from qore.infrastructure.universal_valuation_observation import (
    D05OhlcPriceField,
    D05OhlcValuationSource,
    ValuationIdentityBinding,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def test_ohlc_source_projects_exact_bound_economic_identity() -> None:
    economic_identity_id = EconomicIdentityId(_uuid(1))
    start = datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(2)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.LEGACY_QORE,
            namespace=ExternalIdentifierNamespace("market-data.instrument"),
            value=ExternalIdentifierValue("EURUSD"),
        ),
        target=CanonicalIdentityRef(economic_identity_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(3)),
    )
    binding = ValuationIdentityBinding(mapping, economic_identity_id)
    opened_at = datetime(2026, 1, 2, 12, tzinfo=UTC)
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(4)),
        source_id=SourceId(_uuid(5)),
        port_name=PortName("market-data.test"),
    )

    def field(value: str) -> MarketOhlcField:
        return MarketOhlcField(
            validity=MarketOhlcFieldValidity.VALID,
            price=MarketPrice(Decimal(value)),
        )

    observation = QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(6)),
        instrument=Instrument("EURUSD"),
        source=source,
        timeframe=MarketTimeframe(MarketTimeframeCode.M1),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=field("1.10"),
        high=field("1.14"),
        low=field("1.09"),
        close=field("1.12"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(7)),
    )
    valuation_source = D05OhlcValuationSource(
        observation,
        D05OhlcPriceField.HIGH,
        binding,
    )

    assert valuation_source.economic_identity_id == economic_identity_id
    assert valuation_source.economic_identity_id is binding.economic_identity_id
