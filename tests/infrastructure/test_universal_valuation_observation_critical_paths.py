from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoPerpetualPriceRole,
    CryptoPerpetualPricingTerms,
)
from qore.infrastructure.fixed_income_economics import (
    CompoundingConventionCode,
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
    FixedIncomeCashAmount,
    FixedIncomeCashFlow,
    FixedIncomeCashFlowDirection,
    FixedIncomeCashFlowId,
    FixedIncomeCashFlowKind,
    FixedIncomeEvidenceRef,
)
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
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.rate_term_structure import (
    ForwardRate,
    RateCurveConvention,
)
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
    IdentityRelationshipId,
    ListingIdentity,
    ListingIdentityId,
    MarketVenueCode,
)
from qore.infrastructure.universal_valuation_observation import (
    CryptoPerpetualPriceMeasure,
    CryptoPerpetualPriceValue,
    D05OhlcPriceField,
    D05OhlcValuationSource,
    FixedIncomeCashFlowValueMeasure,
    ModelValueMeasure,
    PublishedValuationSource,
    QuotedValuationValue,
    StandaloneRateMeasure,
    UniversalValuationObservationValidationError,
    ValuationAsOfInterval,
    ValuationIdentityBinding,
    ValuationModelOutputCode,
    ValuationQuoteBasisCode,
    ValuationSourceEvidenceRef,
    ValuationSourceObservationId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _economic_id(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _source(seed: int, port: str) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1000 + seed)),
        source_id=SourceId(_uuid(2000 + seed)),
        port_name=PortName(port),
    )


def _legacy_binding(
    *,
    effective_from: datetime | None = None,
) -> ValuationIdentityBinding:
    economic_id = _economic_id(10)
    start = effective_from or datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(3001)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.LEGACY_QORE,
            namespace=ExternalIdentifierNamespace("market-data.instrument"),
            value=ExternalIdentifierValue("EURUSD"),
        ),
        target=CanonicalIdentityRef(economic_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(3002)),
    )
    return ValuationIdentityBinding(mapping, economic_id)


def _provider_binding(source: ExternalSourceDescriptor) -> ValuationIdentityBinding:
    economic_id = _economic_id(20)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(4001)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.PROVIDER_NATIVE,
            namespace=ExternalIdentifierNamespace("valuation.instrument"),
            value=ExternalIdentifierValue("asset-20"),
            source=source,
        ),
        target=CanonicalIdentityRef(economic_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(4002)),
    )
    return ValuationIdentityBinding(mapping, economic_id)


def _valid_field(value: str) -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=MarketPrice(Decimal(value)),
    )


def _bar(*, opened_at: datetime | None = None) -> QualifiedOhlcBarObservation:
    opened = opened_at or datetime(2026, 1, 2, 12, tzinfo=UTC)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(5001)),
        instrument=Instrument("EURUSD"),
        source=_source(1, "market-data.test"),
        timeframe=MarketTimeframe(MarketTimeframeCode.M1),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=_valid_field("1.10"),
        high=_valid_field("1.14"),
        low=_valid_field("1.09"),
        close=_valid_field("1.12"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(5002)),
    )


def _quoted_value(value: str, quote_identity_id: EconomicIdentityId) -> QuotedValuationValue:
    return QuotedValuationValue(
        Decimal(value),
        quote_identity_id,
        ValuationQuoteBasisCode("currency-per-unit"),
    )


def test_critical_acceptance_logical_values_are_fully_materialized() -> None:
    pricing_terms = CryptoPerpetualPricingTerms(
        index_relationship_id=IdentityRelationshipId(_uuid(6001)),
        roles=(
            CryptoPerpetualPriceRole.MARK_PRICE,
            CryptoPerpetualPriceRole.INDEX_PRICE,
            CryptoPerpetualPriceRole.LAST_PRICE,
        ),
        evidence_ref=CryptoEvidenceRef(_uuid(6002)),
    )
    crypto_value = CryptoPerpetualPriceValue(
        Decimal("100.00"),
        _economic_id(6010),
        ValuationQuoteBasisCode("currency-per-unit"),
    )
    crypto_measure = CryptoPerpetualPriceMeasure(
        crypto_value,
        CryptoPerpetualPriceRole.MARK_PRICE,
        pricing_terms,
    )
    assert crypto_value.logical_values()[0] == "100"
    assert crypto_measure.logical_values()[0] == "crypto-perpetual-price"

    currency = _economic_id(6020)
    cash_flow = FixedIncomeCashFlow(
        cash_flow_id=FixedIncomeCashFlowId(_uuid(6021)),
        instrument_identity_id=_economic_id(6022),
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        direction=FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=FixedIncomeCashAmount(Decimal("100")),
        currency_identity_id=currency,
        payment_date=date(2030, 1, 1),
        evidence_ref=FixedIncomeEvidenceRef(_uuid(6023)),
    )
    cash_flow_value = FixedIncomeCashFlowValueMeasure(
        cash_flow,
        _quoted_value("95", currency),
    )
    assert cash_flow_value.logical_values()[0] == "fixed-income-cash-flow-value"

    ohlc_source = D05OhlcValuationSource(
        _bar(),
        D05OhlcPriceField.HIGH,
        _legacy_binding(),
    )
    logical = ohlc_source.logical_values()
    assert logical[0] == "d05-ohlc"
    assert ohlc_source.measure.logical_values() in logical


def test_published_interval_executes_exact_mapping_interval_validation_branch() -> None:
    source = _source(2, "valuation.external")
    binding = _provider_binding(source)
    opened = datetime(2026, 1, 2, 12, tzinfo=UTC)
    published = PublishedValuationSource(
        source_observation_id=ValuationSourceObservationId(_uuid(6101)),
        source=source,
        identity_binding=binding,
        as_of=ValuationAsOfInterval(opened, opened + timedelta(minutes=1)),
        measure=ModelValueMeasure(
            _quoted_value("42", _economic_id(6102)),
            ValuationModelOutputCode("provider-model-value"),
        ),
        evidence_ref=ValuationSourceEvidenceRef(_uuid(6103)),
    )
    assert published.logical_values()[0] == "published"
    assert published.as_of.logical_values()[0] == "interval"


def test_crypto_perpetual_price_rejects_zero_under_certified_positive_semantics() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="positive"):
        CryptoPerpetualPriceValue(
            Decimal("0"),
            _economic_id(6201),
            ValuationQuoteBasisCode("currency-per-unit"),
        )


def test_listing_mapping_rejects_wrong_listing_id_and_wrong_economic_binding() -> None:
    mapping_listing_id = ListingIdentityId(_uuid(6301))
    expected_economic_id = _economic_id(6302)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(6303)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.PROVIDER_NATIVE,
            namespace=ExternalIdentifierNamespace("valuation.instrument"),
            value=ExternalIdentifierValue("listing-asset"),
            source=_source(3, "valuation.external"),
        ),
        target=CanonicalIdentityRef(mapping_listing_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(6304)),
    )

    wrong_listing_id = ListingIdentity(
        listing_id=ListingIdentityId(_uuid(6305)),
        economic_identity_id=expected_economic_id,
        venue=MarketVenueCode("test-venue"),
        display_symbol="ASSET",
        valid_from=start,
        valid_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(6306)),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="listing binding id"):
        ValuationIdentityBinding(mapping, expected_economic_id, wrong_listing_id)

    wrong_economic = ListingIdentity(
        listing_id=mapping_listing_id,
        economic_identity_id=_economic_id(6307),
        venue=MarketVenueCode("test-venue"),
        display_symbol="ASSET",
        valid_from=start,
        valid_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(6308)),
    )
    with pytest.raises(
        UniversalValuationObservationValidationError,
        match="listing binding economic identity",
    ):
        ValuationIdentityBinding(mapping, expected_economic_id, wrong_economic)


def test_bar_interval_rejects_mapping_that_begins_after_bar_open() -> None:
    opened = datetime(2026, 1, 2, 12, tzinfo=UTC)
    binding = _legacy_binding(effective_from=opened + timedelta(seconds=1))
    with pytest.raises(UniversalValuationObservationValidationError, match="starts before"):
        D05OhlcValuationSource(
            _bar(opened_at=opened),
            D05OhlcPriceField.OPEN,
            binding,
        )


def test_forward_rate_rejects_tenor_coordinate_without_forward_period() -> None:
    convention = RateCurveConvention(
        day_count=DayCountConventionCode("act-365"),
        compounding=CompoundingConventionCode("simple"),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="ForwardRatePeriod"):
        StandaloneRateMeasure(
            ForwardRate(Decimal("0.01")),
            convention,
            FinancialTenor(1, FinancialTenorUnit.YEAR),
        )
