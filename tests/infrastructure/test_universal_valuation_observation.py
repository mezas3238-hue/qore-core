from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoPerpetualPriceRole,
    CryptoPerpetualPricingTerms,
)
from qore.infrastructure.equity_fund_corporate_action_semantics import (
    EquityFundEvidenceRef,
    FundNavBasis,
    FundNavBasisCode,
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
    FixedIncomePrice,
    FixedIncomePriceBasisCode,
    FixedIncomePriceKind,
    FixedIncomeSpread,
    FixedIncomeYield,
    FixedIncomeYieldCode,
    YieldConvention,
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
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.rate_term_structure import (
    DiscountFactor,
    ForwardRate,
    ForwardRatePeriod,
    ParRate,
    RateCurveConvention,
    ZeroRate,
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
    ComputedValuationObservation,
    ComputedValuationProvenance,
    CryptoPerpetualPriceMeasure,
    CryptoPerpetualPriceValue,
    D05MarketPriceMeasure,
    D05OhlcPriceField,
    D05OhlcValuationSource,
    D05QuoteValuationSource,
    DiscountFactorMeasure,
    FixedIncomeCashFlowValueMeasure,
    FixedIncomePriceMeasure,
    FixedIncomeSpreadMeasure,
    FixedIncomeYieldMeasure,
    FundNavMeasure,
    FundNavValue,
    ImpliedVolatility,
    ModelValueMeasure,
    ObservedValuationObservation,
    PublishedValuationSource,
    QuotedValuationValue,
    StandaloneRateMeasure,
    UniversalValuationObservationValidationError,
    ValuationAsOfDate,
    ValuationAsOfInstant,
    ValuationAsOfInterval,
    ValuationComputedInput,
    ValuationEvidenceRef,
    ValuationIdentityBinding,
    ValuationInputRoleCode,
    ValuationMethodologyFamily,
    ValuationMethodologyIdentity,
    ValuationMethodologySchemaVersion,
    ValuationModelOutputCode,
    ValuationObservationId,
    ValuationQuoteBasisCode,
    ValuationSoftwareRevision,
    ValuationSourceEvidenceRef,
    ValuationSourceObservationId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _economic_id(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _source(value: int = 1, port: str = "market-data.test") -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1000 + value)),
        source_id=SourceId(_uuid(2000 + value)),
        port_name=PortName(port),
    )


def _legacy_binding(
    *,
    symbol: str = "EURUSD",
    economic_id: EconomicIdentityId | None = None,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> ValuationIdentityBinding:
    target = economic_id or _economic_id(10)
    start = effective_from or datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(3001)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.LEGACY_QORE,
            namespace=ExternalIdentifierNamespace("market-data.instrument"),
            value=ExternalIdentifierValue(symbol),
        ),
        target=CanonicalIdentityRef(target),
        effective_from=start,
        effective_until=effective_until,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(3002)),
    )
    return ValuationIdentityBinding(mapping=mapping, economic_identity_id=target)


def _listing_binding(
    *,
    symbol: str = "EURUSD",
    economic_id: EconomicIdentityId | None = None,
) -> ValuationIdentityBinding:
    target_economic = economic_id or _economic_id(20)
    listing_id = ListingIdentityId(_uuid(4001))
    start = datetime(2025, 1, 1, tzinfo=UTC)
    listing = ListingIdentity(
        listing_id=listing_id,
        economic_identity_id=target_economic,
        venue=MarketVenueCode("test-venue"),
        display_symbol=symbol,
        valid_from=start,
        valid_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(4002)),
    )
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(4003)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.LEGACY_QORE,
            namespace=ExternalIdentifierNamespace("market-data.instrument"),
            value=ExternalIdentifierValue(symbol),
        ),
        target=CanonicalIdentityRef(listing_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(4004)),
    )
    return ValuationIdentityBinding(
        mapping=mapping,
        economic_identity_id=target_economic,
        listing=listing,
    )


def _provider_binding(
    source: ExternalSourceDescriptor,
    *,
    economic_id: EconomicIdentityId | None = None,
    effective_from: datetime | None = None,
    effective_until: datetime | None = None,
) -> ValuationIdentityBinding:
    target = economic_id or _economic_id(30)
    start = effective_from or datetime(2025, 1, 1, tzinfo=UTC)
    mapping = ExternalIdentityMappingRevision(
        mapping_id=IdentityMappingId(_uuid(5001)),
        revision=IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=ExternalIdentifier(
            kind=ExternalIdentifierKind.PROVIDER_NATIVE,
            namespace=ExternalIdentifierNamespace("valuation.instrument"),
            value=ExternalIdentifierValue("provider-asset-1"),
            source=source,
        ),
        target=CanonicalIdentityRef(target),
        effective_from=start,
        effective_until=effective_until,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=IdentityEvidenceRef(_uuid(5002)),
    )
    return ValuationIdentityBinding(mapping=mapping, economic_identity_id=target)


def _quote(
    *,
    symbol: str = "EURUSD",
    observed_at: datetime | None = None,
    bid: str = "1.1000",
    ask: str = "1.1002",
) -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(6001)),
        instrument=Instrument(symbol),
        source=_source(),
        observed_at=observed_at or datetime(2026, 1, 2, 12, tzinfo=UTC),
        bid=MarketPrice(Decimal(bid)),
        ask=MarketPrice(Decimal(ask)),
        evidence_ref=MarketObservationEvidenceReference(_uuid(6002)),
    )


def _valid_field(value: str) -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=MarketPrice(Decimal(value)),
    )


def _ohlc(
    *,
    opened_at: datetime | None = None,
    symbol: str = "EURUSD",
    close_field: MarketOhlcField | None = None,
) -> QualifiedOhlcBarObservation:
    opened = opened_at or datetime(2026, 1, 2, 12, tzinfo=UTC)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(6101)),
        instrument=Instrument(symbol),
        source=_source(),
        timeframe=MarketTimeframe(MarketTimeframeCode.M1),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=_valid_field("1.10"),
        high=_valid_field("1.14"),
        low=_valid_field("1.09"),
        close=close_field or _valid_field("1.12"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(6102)),
    )


def _tenor(years: int = 1) -> FinancialTenor:
    return FinancialTenor(years, FinancialTenorUnit.YEAR)


def _rate_convention() -> RateCurveConvention:
    return RateCurveConvention(
        day_count=DayCountConventionCode("act-365"),
        compounding=CompoundingConventionCode("simple"),
    )


def _yield_convention() -> YieldConvention:
    return YieldConvention(
        yield_code=FixedIncomeYieldCode("yield-to-maturity"),
        day_count=DayCountConventionCode("act-365"),
        compounding=CompoundingConventionCode("simple"),
    )


def _nav_measure(value: str = "25.5") -> FundNavMeasure:
    return FundNavMeasure(
        value=FundNavValue(Decimal(value)),
        basis=FundNavBasis(
            currency_identity_id=_economic_id(701),
            unit_identity_id=_economic_id(702),
            basis=FundNavBasisCode("per-unit"),
            evidence_ref=EquityFundEvidenceRef(_uuid(703)),
        ),
    )


def _published_source(
    *,
    role_seed: int = 0,
    measure: Any | None = None,
    as_of: Any | None = None,
    source: ExternalSourceDescriptor | None = None,
    binding: ValuationIdentityBinding | None = None,
) -> PublishedValuationSource:
    external_source = source or _source(10 + role_seed, "valuation.external")
    selected_binding = binding or _provider_binding(
        external_source,
        economic_id=_economic_id(800 + role_seed),
    )
    return PublishedValuationSource(
        source_observation_id=ValuationSourceObservationId(_uuid(8000 + role_seed)),
        source=external_source,
        identity_binding=selected_binding,
        as_of=as_of or ValuationAsOfDate(date(2026, 1, 2)),
        measure=measure or _nav_measure(str(25 + role_seed)),
        evidence_ref=ValuationSourceEvidenceRef(_uuid(8100 + role_seed)),
    )


def _methodology() -> ValuationMethodologyIdentity:
    return ValuationMethodologyIdentity(
        family=ValuationMethodologyFamily("fixed.income.present.value"),
        schema_version=ValuationMethodologySchemaVersion("v1.2"),
        software_revision=ValuationSoftwareRevision("abc1234"),
    )


def test_quote_source_retains_exact_d05_observation_selector_identity_and_instant() -> None:
    quote = _quote()
    source = D05QuoteValuationSource(
        observation=quote,
        side=MarketPriceSide.BID,
        identity_binding=_legacy_binding(),
    )

    assert source.observation is quote
    assert source.measure.price == quote.bid
    assert source.measure.side is MarketPriceSide.BID
    assert source.economic_identity_id == _economic_id(10)
    assert source.as_of.logical_values() == (
        "instant",
        "2026-01-02T12:00:00.000000+00:00",
    )


def test_quote_source_rejects_midpoint_laundering_and_symbol_mismatch() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="BID or ASK"):
        D05QuoteValuationSource(
            observation=_quote(),
            side=MarketPriceSide.MID,
            identity_binding=_legacy_binding(),
        )

    with pytest.raises(
        UniversalValuationObservationValidationError,
        match="Instrument.symbol",
    ):
        D05QuoteValuationSource(
            observation=_quote(symbol="EURUSD"),
            side=MarketPriceSide.BID,
            identity_binding=_legacy_binding(symbol="GBPUSD"),
        )


def test_quote_source_rejects_selected_mapping_outside_effective_window() -> None:
    observed = datetime(2026, 1, 2, 12, tzinfo=UTC)
    binding = _legacy_binding(
        effective_from=observed + timedelta(seconds=1),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="predates"):
        D05QuoteValuationSource(
            observation=_quote(observed_at=observed),
            side=MarketPriceSide.ASK,
            identity_binding=binding,
        )


def test_listing_target_mapping_retains_exact_listing_to_economic_binding() -> None:
    source = D05QuoteValuationSource(
        observation=_quote(),
        side=MarketPriceSide.ASK,
        identity_binding=_listing_binding(),
    )
    assert source.identity_binding.listing is not None
    assert (
        source.identity_binding.listing.economic_identity_id
        == source.economic_identity_id
    )


def test_listing_target_mapping_requires_listing_binding() -> None:
    valid = _listing_binding()
    with pytest.raises(UniversalValuationObservationValidationError, match="ListingIdentity"):
        ValuationIdentityBinding(
            mapping=valid.mapping,
            economic_identity_id=valid.economic_identity_id,
            listing=None,
        )


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (D05OhlcPriceField.OPEN, Decimal("1.10")),
        (D05OhlcPriceField.HIGH, Decimal("1.14")),
        (D05OhlcPriceField.LOW, Decimal("1.09")),
        (D05OhlcPriceField.CLOSE, Decimal("1.12")),
    ],
)
def test_ohlc_source_selects_exact_field_and_retains_interval(
    field: D05OhlcPriceField,
    expected: Decimal,
) -> None:
    bar = _ohlc()
    source = D05OhlcValuationSource(
        observation=bar,
        field=field,
        identity_binding=_legacy_binding(),
    )
    assert source.measure.price.value == expected
    assert source.measure.ohlc_field is field
    assert source.as_of.logical_values() == (
        "interval",
        "2026-01-02T12:00:00.000000+00:00",
        "2026-01-02T12:01:00.000000+00:00",
    )


def test_ohlc_source_rejects_invalid_selected_field() -> None:
    invalid = MarketOhlcField(
        validity=MarketOhlcFieldValidity.MISSING,
        price=None,
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="VALID"):
        D05OhlcValuationSource(
            observation=_ohlc(close_field=invalid),
            field=D05OhlcPriceField.CLOSE,
            identity_binding=_legacy_binding(),
        )


def test_ohlc_mapping_must_cover_entire_interval() -> None:
    opened = datetime(2026, 1, 2, 12, tzinfo=UTC)
    binding = _legacy_binding(
        effective_from=datetime(2025, 1, 1, tzinfo=UTC),
        effective_until=opened + timedelta(seconds=30),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="ends after"):
        D05OhlcValuationSource(
            observation=_ohlc(opened_at=opened),
            field=D05OhlcPriceField.HIGH,
            identity_binding=binding,
        )


def test_temporal_variants_do_not_launder_date_and_canonicalize_equal_instants() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="must be date"):
        ValuationAsOfDate(cast(Any, datetime(2026, 1, 2, tzinfo=UTC)))

    utc_value = ValuationAsOfInstant(datetime(2026, 1, 2, 12, tzinfo=UTC))
    offset_value = ValuationAsOfInstant(
        datetime(2026, 1, 2, 7, tzinfo=timezone(timedelta(hours=-5)))
    )
    assert utc_value.logical_values() == offset_value.logical_values()


def test_interval_requires_positive_span() -> None:
    instant = datetime(2026, 1, 2, 12, tzinfo=UTC)
    with pytest.raises(UniversalValuationObservationValidationError, match="after opened_at"):
        ValuationAsOfInterval(instant, instant)


def test_fixed_income_price_yield_and_spread_are_distinct_and_allow_negative_rates() -> None:
    price = FixedIncomePriceMeasure(
        FixedIncomePrice(
            Decimal("99.5"),
            FixedIncomePriceKind.CLEAN,
            FixedIncomePriceBasisCode("percent-of-par"),
        )
    )
    yield_measure = FixedIncomeYieldMeasure(
        FixedIncomeYield(Decimal("-0.0025")),
        _yield_convention(),
    )
    spread = FixedIncomeSpreadMeasure(
        FixedIncomeSpread(Decimal("-0.0005")),
        _economic_id(900),
    )

    assert price.logical_values()[0] == "fixed-income-price"
    assert yield_measure.logical_values()[0] == "fixed-income-yield"
    assert spread.logical_values()[0] == "fixed-income-spread"
    kinds = {
        price.logical_values()[0],
        yield_measure.logical_values()[0],
        spread.logical_values()[0],
    }
    assert len(kinds) == 3


def test_standalone_rate_preserves_coordinate_without_fabricating_curve_node() -> None:
    zero = StandaloneRateMeasure(ZeroRate(Decimal("-0.01")), _rate_convention(), _tenor())
    par = StandaloneRateMeasure(ParRate(Decimal("0")), _rate_convention(), _tenor(2))
    forward = StandaloneRateMeasure(
        ForwardRate(Decimal("0.02")),
        _rate_convention(),
        ForwardRatePeriod(start_tenor=_tenor(), period_tenor=_tenor(1)),
    )
    assert zero.logical_values()[0] == "zero-rate"
    assert par.logical_values()[0] == "par-rate"
    assert forward.logical_values()[0] == "forward-rate"
    for value in (zero, par, forward):
        assert not hasattr(value, "node_id")
        assert not hasattr(value, "ordinal")


def test_standalone_rate_rejects_wrong_coordinate_semantics() -> None:
    with pytest.raises(UniversalValuationObservationValidationError, match="FinancialTenor"):
        StandaloneRateMeasure(
            ZeroRate(Decimal("0.01")),
            _rate_convention(),
            ForwardRatePeriod(start_tenor=None, period_tenor=_tenor()),
        )


def test_discount_factor_reuses_certified_value_and_coordinate() -> None:
    measure = DiscountFactorMeasure(DiscountFactor(Decimal("0.97")), _tenor(3))
    assert measure.logical_values()[0] == "discount-factor"


def test_nav_is_not_market_price_and_does_not_gain_blanket_positivity() -> None:
    nav = _nav_measure("-1.25")
    assert nav.logical_values()[0] == "fund-nav"
    assert not isinstance(nav.value, MarketPrice)


def test_implied_volatility_allows_zero_and_rejects_negative() -> None:
    zero = ImpliedVolatility(Decimal("0.000"))
    assert zero.logical_values() == ("0",)
    with pytest.raises(UniversalValuationObservationValidationError, match="non-negative"):
        ImpliedVolatility(Decimal("-0.01"))


def test_model_value_is_output_carrier_not_pricing_engine() -> None:
    measure = ModelValueMeasure(
        QuotedValuationValue(
            Decimal("-2.5"),
            _economic_id(910),
            ValuationQuoteBasisCode("currency-per-unit"),
        ),
        ValuationModelOutputCode("theoretical-value"),
    )
    for name in ("calculate", "price", "evaluate", "execute", "settle"):
        assert not hasattr(measure, name)


def test_crypto_perpetual_price_reuses_umi08_role_vocabulary() -> None:
    terms = CryptoPerpetualPricingTerms(
        index_relationship_id=IdentityRelationshipId(_uuid(920)),
        roles=(
            CryptoPerpetualPriceRole.LAST_PRICE,
            CryptoPerpetualPriceRole.MARK_PRICE,
            CryptoPerpetualPriceRole.INDEX_PRICE,
        ),
        evidence_ref=CryptoEvidenceRef(_uuid(921)),
    )
    measure = CryptoPerpetualPriceMeasure(
        CryptoPerpetualPriceValue(
            Decimal("100"),
            _economic_id(922),
            ValuationQuoteBasisCode("currency-per-unit"),
        ),
        CryptoPerpetualPriceRole.MARK_PRICE,
        terms,
    )
    assert measure.role is CryptoPerpetualPriceRole.MARK_PRICE
    assert set(terms.roles) == set(CryptoPerpetualPriceRole)


def test_cash_flow_valuation_retains_contract_and_cannot_mutate_settlement() -> None:
    currency = _economic_id(930)
    cash_flow = FixedIncomeCashFlow(
        cash_flow_id=FixedIncomeCashFlowId(_uuid(931)),
        instrument_identity_id=_economic_id(932),
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        direction=FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=FixedIncomeCashAmount(Decimal("100")),
        currency_identity_id=currency,
        payment_date=date(2030, 1, 1),
        evidence_ref=FixedIncomeEvidenceRef(_uuid(933)),
    )
    measure = FixedIncomeCashFlowValueMeasure(
        cash_flow,
        QuotedValuationValue(
            Decimal("95"),
            currency,
            ValuationQuoteBasisCode("currency-amount"),
        ),
    )
    assert measure.cash_flow is cash_flow
    for name in ("settle", "book", "adjust_balance", "pay"):
        assert not hasattr(measure, name)


def test_cash_flow_valuation_rejects_quote_currency_mismatch() -> None:
    cash_flow = FixedIncomeCashFlow(
        cash_flow_id=FixedIncomeCashFlowId(_uuid(940)),
        instrument_identity_id=_economic_id(941),
        kind=FixedIncomeCashFlowKind.REDEMPTION,
        direction=FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=FixedIncomeCashAmount(Decimal("100")),
        currency_identity_id=_economic_id(942),
        payment_date=date(2030, 1, 1),
        evidence_ref=FixedIncomeEvidenceRef(_uuid(943)),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="currency"):
        FixedIncomeCashFlowValueMeasure(
            cash_flow,
            QuotedValuationValue(
                Decimal("90"),
                _economic_id(944),
                ValuationQuoteBasisCode("currency-amount"),
            ),
        )


def test_published_source_retains_typed_value_identity_and_date_without_midnight() -> None:
    source = _published_source()
    observation = ObservedValuationObservation(
        observation_id=ValuationObservationId(_uuid(950)),
        source=source,
        recorded_at=datetime(2026, 1, 3, tzinfo=UTC),
        evidence_ref=ValuationEvidenceRef(_uuid(951)),
    )
    assert observation.measure is source.measure
    assert observation.economic_identity_id == source.economic_identity_id
    assert observation.as_of.logical_values() == ("date", "2026-01-02")


def test_published_date_does_not_invent_midnight_mapping_check() -> None:
    source_descriptor = _source(20, "valuation.external")
    binding = _provider_binding(
        source_descriptor,
        effective_from=datetime(2026, 1, 2, 12, tzinfo=UTC),
    )
    source = _published_source(
        source=source_descriptor,
        binding=binding,
        as_of=ValuationAsOfDate(date(2026, 1, 2)),
    )
    assert source.as_of.logical_values() == ("date", "2026-01-02")


def test_published_instant_rejects_selected_mapping_outside_window() -> None:
    descriptor = _source(21, "valuation.external")
    instant = datetime(2026, 1, 2, 12, tzinfo=UTC)
    binding = _provider_binding(
        descriptor,
        effective_from=instant + timedelta(seconds=1),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="predates"):
        _published_source(
            source=descriptor,
            binding=binding,
            as_of=ValuationAsOfInstant(instant),
        )


def test_provider_scoped_mapping_source_must_match_published_source() -> None:
    mapping_source = _source(30, "valuation.external")
    published_source = _source(31, "valuation.external")
    binding = _provider_binding(mapping_source)
    with pytest.raises(UniversalValuationObservationValidationError, match="must equal"):
        _published_source(source=published_source, binding=binding)


def test_published_source_cannot_masquerade_as_exact_d05_market_evidence() -> None:
    descriptor = _source(40, "valuation.external")
    with pytest.raises(UniversalValuationObservationValidationError, match="D05"):
        _published_source(
            source=descriptor,
            binding=_provider_binding(descriptor),
            measure=D05MarketPriceMeasure(
                MarketPrice(Decimal("1.2")),
                MarketPriceSide.BID,
            ),
        )


def test_provider_computed_external_model_value_is_still_observed_by_qore() -> None:
    measure = ModelValueMeasure(
        QuotedValuationValue(
            Decimal("42"),
            _economic_id(960),
            ValuationQuoteBasisCode("currency-per-unit"),
        ),
        ValuationModelOutputCode("provider-model-value"),
    )
    source = _published_source(measure=measure)
    observation = ObservedValuationObservation(
        ValuationObservationId(_uuid(961)),
        source,
        datetime(2026, 1, 3, tzinfo=UTC),
        ValuationEvidenceRef(_uuid(962)),
    )
    assert observation.logical_values()[0] == "observed"


def test_computed_provenance_canonicalizes_inputs_and_derives_same_fingerprint() -> None:
    left = ValuationComputedInput(
        ValuationInputRoleCode("discount-factor"),
        _published_source(role_seed=1),
    )
    right = ValuationComputedInput(
        ValuationInputRoleCode("cash-flow"),
        _published_source(role_seed=2),
    )
    first = ComputedValuationProvenance(
        _methodology(),
        (left, right),
        ValuationEvidenceRef(_uuid(970)),
    )
    second = ComputedValuationProvenance(
        _methodology(),
        (right, left),
        ValuationEvidenceRef(_uuid(970)),
    )
    assert first.inputs == second.inputs
    assert first.input_fingerprint == second.input_fingerprint
    assert first.inputs[0].role.value == "cash-flow"


def test_computed_fingerprint_changes_when_retained_input_changes() -> None:
    first_input = ValuationComputedInput(
        ValuationInputRoleCode("source-nav"),
        _published_source(role_seed=3, measure=_nav_measure("25")),
    )
    second_input = ValuationComputedInput(
        ValuationInputRoleCode("source-nav"),
        _published_source(role_seed=3, measure=_nav_measure("26")),
    )
    first = ComputedValuationProvenance(
        _methodology(),
        (first_input,),
        ValuationEvidenceRef(_uuid(980)),
    )
    second = ComputedValuationProvenance(
        _methodology(),
        (second_input,),
        ValuationEvidenceRef(_uuid(980)),
    )
    assert first.input_fingerprint != second.input_fingerprint


def test_computed_provenance_rejects_duplicate_roles_and_more_than_64_inputs() -> None:
    source = _published_source(role_seed=4)
    duplicate = (
        ValuationComputedInput(ValuationInputRoleCode("same"), source),
        ValuationComputedInput(ValuationInputRoleCode("same"), source),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="unique"):
        ComputedValuationProvenance(
            _methodology(),
            duplicate,
            ValuationEvidenceRef(_uuid(990)),
        )

    many = tuple(
        ValuationComputedInput(
            ValuationInputRoleCode(f"input-{index}"),
            _published_source(role_seed=100 + index),
        )
        for index in range(65)
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="bounded"):
        ComputedValuationProvenance(
            _methodology(),
            many,
            ValuationEvidenceRef(_uuid(991)),
        )


def test_computed_input_graph_is_non_recursive() -> None:
    source = _published_source(role_seed=5)
    observation = ObservedValuationObservation(
        ValuationObservationId(_uuid(1001)),
        source,
        datetime(2026, 1, 3, tzinfo=UTC),
        ValuationEvidenceRef(_uuid(1002)),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="leaf source"):
        ValuationComputedInput(
            ValuationInputRoleCode("nested"),
            cast(Any, observation),
        )


def test_computed_observation_retains_lineage_without_engine_authority() -> None:
    input_value = ValuationComputedInput(
        ValuationInputRoleCode("published-nav"),
        _published_source(role_seed=6),
    )
    provenance = ComputedValuationProvenance(
        _methodology(),
        (input_value,),
        ValuationEvidenceRef(_uuid(1010)),
    )
    observation = ComputedValuationObservation(
        observation_id=ValuationObservationId(_uuid(1011)),
        economic_identity_id=_economic_id(1012),
        as_of=ValuationAsOfDate(date(2026, 1, 2)),
        measure=_nav_measure("24.5"),
        provenance=provenance,
        recorded_at=datetime(2026, 1, 3, tzinfo=UTC),
        evidence_ref=ValuationEvidenceRef(_uuid(1013)),
    )
    assert observation.provenance.inputs[0].source is input_value.source
    assert len(observation.provenance.input_fingerprint.value) == 64
    for name in ("calculate", "price", "evaluate", "run", "execute", "settle"):
        assert not hasattr(observation, name)


def test_computed_observation_cannot_claim_exact_d05_observed_price() -> None:
    provenance = ComputedValuationProvenance(
        _methodology(),
        (
            ValuationComputedInput(
                ValuationInputRoleCode("quote"),
                D05QuoteValuationSource(
                    _quote(),
                    MarketPriceSide.BID,
                    _legacy_binding(),
                ),
            ),
        ),
        ValuationEvidenceRef(_uuid(1020)),
    )
    with pytest.raises(UniversalValuationObservationValidationError, match="D05"):
        ComputedValuationObservation(
            ValuationObservationId(_uuid(1021)),
            _economic_id(1022),
            ValuationAsOfInstant(datetime(2026, 1, 2, 12, tzinfo=UTC)),
            D05MarketPriceMeasure(MarketPrice(Decimal("1.1")), MarketPriceSide.BID),
            provenance,
            datetime(2026, 1, 2, 12, 1, tzinfo=UTC),
            ValuationEvidenceRef(_uuid(1023)),
        )


def test_methodology_identity_is_versioned_and_not_algorithm_implementation() -> None:
    methodology = _methodology()
    assert methodology.family.value == "fixed.income.present.value"
    assert methodology.schema_version.value == "v1.2"
    assert methodology.software_revision.value == "abc1234"
    for name in ("calculate", "evaluate", "price", "run"):
        assert not hasattr(methodology, name)

    with pytest.raises(UniversalValuationObservationValidationError, match="v<integer>"):
        ValuationMethodologySchemaVersion("1.2")


def test_certified_state_is_frozen_and_has_no_currentness_or_mutation_authority() -> None:
    source = _published_source(role_seed=7)
    with pytest.raises(FrozenInstanceError):
        source.measure = _nav_measure("99")  # type: ignore[misc]

    for obj in (
        source,
        source.identity_binding,
        _nav_measure(),
        _methodology(),
    ):
        for name in (
            "is_current",
            "resolve_current",
            "latest_revision",
            "refresh",
            "execute",
            "settle",
            "adjust_balance",
            "detect_barrier",
            "trigger_autocall",
        ):
            assert not hasattr(obj, name)
