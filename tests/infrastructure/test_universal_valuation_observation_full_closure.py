from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.crypto_perpetual_funding_semantics as crypto
import qore.infrastructure.equity_fund_corporate_action_semantics as equity
import qore.infrastructure.fixed_income_economics as fixed
import qore.infrastructure.market_data as market_data
import qore.infrastructure.market_observation as market
import qore.infrastructure.ports as ports
import qore.infrastructure.rate_term_structure as rates
import qore.infrastructure.universal_instrument_identity as identity
import qore.infrastructure.universal_valuation_observation as valuation


def _uuid(seed: int) -> UUID:
    return UUID(int=seed)


def _uuid_material(seed: int) -> tuple[str, ...]:
    return (str(UUID(int=seed)),)


def _economic_id(seed: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(_uuid(seed))


def _source(
    seed: int = 1,
    port_name: str = "market-data.test",
) -> ports.ExternalSourceDescriptor:
    return ports.ExternalSourceDescriptor(
        adapter_id=ports.AdapterId(_uuid(1000 + seed)),
        source_id=ports.SourceId(_uuid(2000 + seed)),
        port_name=ports.PortName(port_name),
    )


def _source_material(
    seed: int = 1,
    port_name: str = "market-data.test",
) -> tuple[object, ...]:
    return (
        str(UUID(int=1000 + seed)),
        str(UUID(int=2000 + seed)),
        port_name,
    )


def _legacy_binding() -> valuation.ValuationIdentityBinding:
    economic_id = _economic_id(10)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    mapping = identity.ExternalIdentityMappingRevision(
        mapping_id=identity.IdentityMappingId(_uuid(3001)),
        revision=identity.IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=identity.ExternalIdentifier(
            kind=identity.ExternalIdentifierKind.LEGACY_QORE,
            namespace=identity.ExternalIdentifierNamespace("market-data.instrument"),
            value=identity.ExternalIdentifierValue("EURUSD"),
        ),
        target=identity.CanonicalIdentityRef(economic_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=identity.IdentityEvidenceRef(_uuid(3002)),
    )
    return valuation.ValuationIdentityBinding(
        mapping=mapping,
        economic_identity_id=economic_id,
    )


_EXPECTED_LEGACY_MAPPING: tuple[object, ...] = (
    _uuid_material(3001),
    (1,),
    None,
    (
        "legacy-qore",
        ("market-data.instrument",),
        ("EURUSD",),
        None,
        None,
    ),
    ("economic", _uuid_material(10)),
    "2025-01-01T00:00:00.000000+00:00",
    None,
    "2025-01-01T01:00:00.000000+00:00",
    _uuid_material(3002),
)

_EXPECTED_LEGACY_BINDING: tuple[object, ...] = (
    _EXPECTED_LEGACY_MAPPING,
    _uuid_material(10),
    None,
)


def _listing_binding() -> valuation.ValuationIdentityBinding:
    economic_id = _economic_id(20)
    listing_id = identity.ListingIdentityId(_uuid(4001))
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = datetime(2027, 1, 1, tzinfo=UTC)
    listing = identity.ListingIdentity(
        listing_id=listing_id,
        economic_identity_id=economic_id,
        venue=identity.MarketVenueCode("test-venue"),
        display_symbol="EURUSD",
        valid_from=start,
        valid_until=end,
        evidence_ref=identity.IdentityEvidenceRef(_uuid(4002)),
    )
    mapping = identity.ExternalIdentityMappingRevision(
        mapping_id=identity.IdentityMappingId(_uuid(4003)),
        revision=identity.IdentityMappingRevision(2),
        parent_revision=identity.IdentityMappingRevision(1),
        external_identity=identity.ExternalIdentifier(
            kind=identity.ExternalIdentifierKind.LEGACY_QORE,
            namespace=identity.ExternalIdentifierNamespace("market-data.instrument"),
            value=identity.ExternalIdentifierValue("EURUSD"),
        ),
        target=identity.CanonicalIdentityRef(listing_id),
        effective_from=start,
        effective_until=end,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=identity.IdentityEvidenceRef(_uuid(4004)),
    )
    return valuation.ValuationIdentityBinding(
        mapping=mapping,
        economic_identity_id=economic_id,
        listing=listing,
    )


_EXPECTED_LISTING: tuple[object, ...] = (
    _uuid_material(4001),
    _uuid_material(20),
    ("test-venue",),
    "EURUSD",
    "2025-01-01T00:00:00.000000+00:00",
    "2027-01-01T00:00:00.000000+00:00",
    _uuid_material(4002),
)

_EXPECTED_LISTING_MAPPING: tuple[object, ...] = (
    _uuid_material(4003),
    (2,),
    (1,),
    (
        "legacy-qore",
        ("market-data.instrument",),
        ("EURUSD",),
        None,
        None,
    ),
    ("listing", _uuid_material(4001)),
    "2025-01-01T00:00:00.000000+00:00",
    "2027-01-01T00:00:00.000000+00:00",
    "2025-01-01T01:00:00.000000+00:00",
    _uuid_material(4004),
)

_EXPECTED_LISTING_BINDING: tuple[object, ...] = (
    _EXPECTED_LISTING_MAPPING,
    _uuid_material(20),
    _EXPECTED_LISTING,
)


def _provider_binding(
    source: ports.ExternalSourceDescriptor,
    *,
    seed: int,
    economic_seed: int,
    symbol: str,
) -> valuation.ValuationIdentityBinding:
    economic_id = _economic_id(economic_seed)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    mapping = identity.ExternalIdentityMappingRevision(
        mapping_id=identity.IdentityMappingId(_uuid(5000 + seed)),
        revision=identity.IdentityMappingRevision(1),
        parent_revision=None,
        external_identity=identity.ExternalIdentifier(
            kind=identity.ExternalIdentifierKind.PROVIDER_NATIVE,
            namespace=identity.ExternalIdentifierNamespace("valuation.instrument"),
            value=identity.ExternalIdentifierValue(symbol),
            source=source,
        ),
        target=identity.CanonicalIdentityRef(economic_id),
        effective_from=start,
        effective_until=None,
        recorded_at=start + timedelta(hours=1),
        evidence_ref=identity.IdentityEvidenceRef(_uuid(5100 + seed)),
    )
    return valuation.ValuationIdentityBinding(
        mapping=mapping,
        economic_identity_id=economic_id,
    )


def _provider_binding_material(
    *,
    source_seed: int,
    seed: int,
    economic_seed: int,
    symbol: str,
) -> tuple[object, ...]:
    source_material = _source_material(source_seed, "valuation.external")
    mapping_material: tuple[object, ...] = (
        _uuid_material(5000 + seed),
        (1,),
        None,
        (
            "provider-native",
            ("valuation.instrument",),
            (symbol,),
            source_material,
            None,
        ),
        ("economic", _uuid_material(economic_seed)),
        "2025-01-01T00:00:00.000000+00:00",
        None,
        "2025-01-01T01:00:00.000000+00:00",
        _uuid_material(5100 + seed),
    )
    return (
        mapping_material,
        _uuid_material(economic_seed),
        None,
    )


def _quote() -> market.QualifiedQuoteTickObservation:
    return market.QualifiedQuoteTickObservation(
        observation_id=market.MarketObservationId(_uuid(6001)),
        instrument=market_data.Instrument("EURUSD"),
        source=_source(),
        observed_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
        bid=market.MarketPrice(Decimal("1.1000")),
        ask=market.MarketPrice(Decimal("1.1002")),
        evidence_ref=market.MarketObservationEvidenceReference(_uuid(6002)),
    )


_EXPECTED_QUOTE: tuple[object, ...] = (
    _uuid_material(6001),
    "EURUSD",
    _source_material(),
    "2026-01-02T12:00:00.000000+00:00",
    ("1.1",),
    ("1.1002",),
    "0.0002",
    _uuid_material(6002),
)


def _valid_field(value: str) -> market.MarketOhlcField:
    return market.MarketOhlcField(
        validity=market.MarketOhlcFieldValidity.VALID,
        price=market.MarketPrice(Decimal(value)),
    )


def _ohlc() -> market.QualifiedOhlcBarObservation:
    opened_at = datetime(2026, 1, 2, 12, tzinfo=UTC)
    return market.QualifiedOhlcBarObservation(
        observation_id=market.MarketObservationId(_uuid(6101)),
        instrument=market_data.Instrument("EURUSD"),
        source=_source(),
        timeframe=market.MarketTimeframe(market.MarketTimeframeCode.M1),
        price_side=market.MarketPriceSide.BID,
        origin=market.MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=_valid_field("1.10"),
        high=_valid_field("1.14"),
        low=_valid_field("1.09"),
        close=_valid_field("1.12"),
        evidence_ref=market.MarketObservationEvidenceReference(_uuid(6102)),
    )


_EXPECTED_OHLC: tuple[object, ...] = (
    _uuid_material(6101),
    "EURUSD",
    _source_material(),
    ("M1", 60),
    "bid",
    "native",
    "2026-01-02T12:00:00.000000+00:00",
    "2026-01-02T12:01:00.000000+00:00",
    ("valid", ("1.1",)),
    ("valid", ("1.14",)),
    ("valid", ("1.09",)),
    ("valid", ("1.12",)),
    _uuid_material(6102),
)


def _tenor(
    value: int = 1,
    unit: fixed.FinancialTenorUnit = fixed.FinancialTenorUnit.YEAR,
) -> fixed.FinancialTenor:
    return fixed.FinancialTenor(value, unit)


def _rate_convention() -> rates.RateCurveConvention:
    return rates.RateCurveConvention(
        day_count=fixed.DayCountConventionCode("act-365"),
        compounding=fixed.CompoundingConventionCode("simple"),
    )


_EXPECTED_RATE_CONVENTION: tuple[object, ...] = (
    "rate-convention",
    ("act-365",),
    ("simple",),
    None,
)


def _yield_convention() -> fixed.YieldConvention:
    return fixed.YieldConvention(
        yield_code=fixed.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=fixed.DayCountConventionCode("act-365"),
        compounding=fixed.CompoundingConventionCode("simple"),
    )


_EXPECTED_YIELD_CONVENTION: tuple[object, ...] = (
    ("yield-to-maturity",),
    ("act-365",),
    ("simple",),
    None,
    None,
)


def _nav_measure(value: str = "25.5") -> valuation.FundNavMeasure:
    return valuation.FundNavMeasure(
        value=valuation.FundNavValue(Decimal(value)),
        basis=equity.FundNavBasis(
            currency_identity_id=_economic_id(701),
            unit_identity_id=_economic_id(702),
            basis=equity.FundNavBasisCode("per-unit"),
            evidence_ref=equity.EquityFundEvidenceRef(_uuid(703)),
        ),
    )


_NAV_CANONICAL: dict[str, str] = {
    "24.5": "24.5",
    "25": "25",
    "25.25": "25.25",
    "25.5": "25.5",
    "26": "26",
    "27": "27",
    "28": "28",
}


def _nav_material(value: str = "25.5") -> tuple[object, ...]:
    return (
        "fund-nav",
        (_NAV_CANONICAL[value],),
        (
            _uuid_material(701),
            _uuid_material(702),
            ("per-unit",),
            _uuid_material(703),
        ),
    )


def _pricing_terms() -> crypto.CryptoPerpetualPricingTerms:
    return crypto.CryptoPerpetualPricingTerms(
        index_relationship_id=identity.IdentityRelationshipId(_uuid(920)),
        roles=(
            crypto.CryptoPerpetualPriceRole.MARK_PRICE,
            crypto.CryptoPerpetualPriceRole.LAST_PRICE,
            crypto.CryptoPerpetualPriceRole.INDEX_PRICE,
        ),
        evidence_ref=crypto.CryptoEvidenceRef(_uuid(921)),
    )


_EXPECTED_PRICING_TERMS: tuple[object, ...] = (
    _uuid_material(920),
    ("index-price", "last-price", "mark-price"),
    _uuid_material(921),
)


def _cash_flow() -> fixed.FixedIncomeCashFlow:
    return fixed.FixedIncomeCashFlow(
        cash_flow_id=fixed.FixedIncomeCashFlowId(_uuid(931)),
        instrument_identity_id=_economic_id(932),
        kind=fixed.FixedIncomeCashFlowKind.PRINCIPAL,
        direction=fixed.FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=fixed.FixedIncomeCashAmount(Decimal("100")),
        currency_identity_id=_economic_id(930),
        payment_date=date(2030, 1, 1),
        evidence_ref=fixed.FixedIncomeEvidenceRef(_uuid(933)),
    )


_EXPECTED_CASH_FLOW: tuple[object, ...] = (
    _uuid_material(931),
    _uuid_material(932),
    "principal",
    "receivable",
    ("100",),
    _uuid_material(930),
    "2030-01-01",
    _uuid_material(933),
    None,
)


def _methodology() -> valuation.ValuationMethodologyIdentity:
    return valuation.ValuationMethodologyIdentity(
        family=valuation.ValuationMethodologyFamily("fund.nav.adjustment"),
        schema_version=valuation.ValuationMethodologySchemaVersion("v2.1"),
        software_revision=valuation.ValuationSoftwareRevision("fc10-r1"),
    )


_EXPECTED_METHODOLOGY: tuple[object, ...] = (
    ("fund.nav.adjustment",),
    ("v2.1",),
    ("fc10-r1",),
)


def _published(
    *,
    source_seed: int,
    binding_seed: int,
    economic_seed: int,
    source_observation_seed: int,
    evidence_seed: int,
    nav_value: str,
    as_of: valuation.ValuationAsOf,
) -> valuation.PublishedValuationSource:
    source = _source(source_seed, "valuation.external")
    binding = _provider_binding(
        source,
        seed=binding_seed,
        economic_seed=economic_seed,
        symbol=f"provider-asset-{binding_seed}",
    )
    return valuation.PublishedValuationSource(
        source_observation_id=valuation.ValuationSourceObservationId(
            _uuid(source_observation_seed)
        ),
        source=source,
        identity_binding=binding,
        as_of=as_of,
        measure=_nav_measure(nav_value),
        evidence_ref=valuation.ValuationSourceEvidenceRef(_uuid(evidence_seed)),
    )


def _published_material(
    *,
    source_seed: int,
    binding_seed: int,
    economic_seed: int,
    source_observation_seed: int,
    evidence_seed: int,
    nav_value: str,
    as_of_material: tuple[object, ...],
) -> tuple[object, ...]:
    return (
        "published",
        _uuid_material(source_observation_seed),
        _source_material(source_seed, "valuation.external"),
        _provider_binding_material(
            source_seed=source_seed,
            seed=binding_seed,
            economic_seed=economic_seed,
            symbol=f"provider-asset-{binding_seed}",
        ),
        as_of_material,
        _nav_material(nav_value),
        _uuid_material(evidence_seed),
    )


class _NonCanonicalUUID(UUID):
    def __str__(self) -> str:
        return "forged-noncanonical-uuid-material"


def test_full_closure_local_uuid_material_requires_exact_uuid_type() -> None:
    exact = UUID(int=8)
    forged = _NonCanonicalUUID(int=8)

    assert valuation.ValuationObservationId(exact).logical_values() == _uuid_material(8)
    assert valuation.ValuationEvidenceRef(exact).logical_values() == _uuid_material(8)
    assert valuation.ValuationSourceObservationId(exact).logical_values() == _uuid_material(8)
    assert valuation.ValuationSourceEvidenceRef(exact).logical_values() == _uuid_material(8)
    assert isinstance(forged, UUID)
    assert str(forged) == "forged-noncanonical-uuid-material"

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="UUID",
    ):
        valuation.ValuationObservationId(forged)
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="UUID",
    ):
        valuation.ValuationEvidenceRef(forged)
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="UUID",
    ):
        valuation.ValuationSourceObservationId(forged)
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="UUID",
    ):
        valuation.ValuationSourceEvidenceRef(forged)


def test_full_closure_temporal_projections_are_literal_and_offset_canonical() -> None:
    instant = valuation.ValuationAsOfInstant(
        datetime(2026, 1, 2, 7, tzinfo=timezone(timedelta(hours=-5)))
    )
    interval = valuation.ValuationAsOfInterval(
        datetime(2026, 1, 2, 7, tzinfo=timezone(timedelta(hours=-5))),
        datetime(2026, 1, 2, 8, tzinfo=timezone(timedelta(hours=-5))),
    )
    date_only = valuation.ValuationAsOfDate(date(2026, 1, 2))

    assert instant.logical_values() == (
        "instant",
        "2026-01-02T12:00:00.000000+00:00",
    )
    assert interval.logical_values() == (
        "interval",
        "2026-01-02T12:00:00.000000+00:00",
        "2026-01-02T13:00:00.000000+00:00",
    )
    assert date_only.logical_values() == ("date", "2026-01-02")
    assert valuation.ValuationAsOfInstant(
        datetime(2026, 1, 2, 12, tzinfo=UTC)
    ).logical_values() == instant.logical_values()


def test_full_closure_measure_family_projections_are_independent() -> None:
    price = valuation.FixedIncomePriceMeasure(
        fixed.FixedIncomePrice(
            Decimal("99.500"),
            fixed.FixedIncomePriceKind.CLEAN,
            fixed.FixedIncomePriceBasisCode("percent-of-par"),
        )
    )
    yield_measure = valuation.FixedIncomeYieldMeasure(
        fixed.FixedIncomeYield(Decimal("-0.002500")),
        _yield_convention(),
    )
    spread = valuation.FixedIncomeSpreadMeasure(
        fixed.FixedIncomeSpread(Decimal("-0.000500")),
        _economic_id(900),
    )
    zero = valuation.StandaloneRateMeasure(
        rates.ZeroRate(Decimal("-0.0100")),
        _rate_convention(),
        _tenor(2),
    )
    par = valuation.StandaloneRateMeasure(
        rates.ParRate(Decimal("0.0150")),
        _rate_convention(),
        _tenor(3),
    )
    forward_period = rates.ForwardRatePeriod(
        start_tenor=_tenor(1),
        period_tenor=_tenor(6, fixed.FinancialTenorUnit.MONTH),
    )
    forward = valuation.StandaloneRateMeasure(
        rates.ForwardRate(Decimal("0.0200")),
        _rate_convention(),
        forward_period,
    )
    discount = valuation.DiscountFactorMeasure(
        rates.DiscountFactor(Decimal("0.9700")),
        forward_period,
    )
    nav = _nav_measure()
    implied_vol = valuation.ImpliedVolatilityMeasure(
        valuation.ImpliedVolatility(Decimal("0.2000")),
        _economic_id(8001),
    )
    model = valuation.ModelValueMeasure(
        valuation.QuotedValuationValue(
            Decimal("-2.500"),
            _economic_id(910),
            valuation.ValuationQuoteBasisCode("currency-per-unit"),
        ),
        valuation.ValuationModelOutputCode("theoretical-value"),
    )
    crypto_measure = valuation.CryptoPerpetualPriceMeasure(
        valuation.CryptoPerpetualPriceValue(
            Decimal("100.00"),
            _economic_id(922),
            valuation.ValuationQuoteBasisCode("currency-per-unit"),
        ),
        crypto.CryptoPerpetualPriceRole.MARK_PRICE,
        _pricing_terms(),
    )
    cash_flow_value = valuation.FixedIncomeCashFlowValueMeasure(
        _cash_flow(),
        valuation.QuotedValuationValue(
            Decimal("95.00"),
            _economic_id(930),
            valuation.ValuationQuoteBasisCode("currency-amount"),
        ),
    )
    d05 = valuation.D05MarketPriceMeasure(
        market.MarketPrice(Decimal("1.1200")),
        market.MarketPriceSide.BID,
        valuation.D05OhlcPriceField.CLOSE,
    )

    assert d05.logical_values() == (
        "d05-market-price",
        ("1.12",),
        "bid",
        "close",
    )
    assert price.logical_values() == (
        "fixed-income-price",
        ("99.5", "clean", ("percent-of-par",)),
    )
    assert yield_measure.logical_values() == (
        "fixed-income-yield",
        ("-0.0025",),
        _EXPECTED_YIELD_CONVENTION,
    )
    assert spread.logical_values() == (
        "fixed-income-spread",
        ("-0.0005",),
        _uuid_material(900),
    )
    assert zero.logical_values() == (
        "zero-rate",
        ("-0.01",),
        _EXPECTED_RATE_CONVENTION,
        "tenor",
        (2, "year"),
    )
    assert par.logical_values() == (
        "par-rate",
        ("0.015",),
        _EXPECTED_RATE_CONVENTION,
        "tenor",
        (3, "year"),
    )
    assert forward.logical_values() == (
        "forward-rate",
        ("0.02",),
        _EXPECTED_RATE_CONVENTION,
        "forward-period",
        ("forward-period", (1, "year"), (6, "month")),
    )
    assert discount.logical_values() == (
        "discount-factor",
        ("0.97",),
        "forward-period",
        ("forward-period", (1, "year"), (6, "month")),
    )
    assert nav.logical_values() == _nav_material()
    assert implied_vol.logical_values() == (
        "implied-volatility",
        ("0.2",),
        _uuid_material(8001),
    )
    assert model.logical_values() == (
        "model-value",
        ("theoretical-value",),
        ("-2.5", _uuid_material(910), ("currency-per-unit",)),
    )
    assert crypto_measure.logical_values() == (
        "crypto-perpetual-price",
        ("100", _uuid_material(922), ("currency-per-unit",)),
        "mark-price",
        _EXPECTED_PRICING_TERMS,
    )
    assert cash_flow_value.logical_values() == (
        "fixed-income-cash-flow-value",
        _EXPECTED_CASH_FLOW,
        ("95", _uuid_material(930), ("currency-amount",)),
    )


def test_full_closure_identity_binding_projections_reconstruct_upstream_material() -> None:
    listing_binding = _listing_binding()
    provider_source = _source(20, "valuation.external")
    provider_binding = _provider_binding(
        provider_source,
        seed=20,
        economic_seed=30,
        symbol="provider-asset-20",
    )

    assert listing_binding.logical_values() == _EXPECTED_LISTING_BINDING
    assert provider_binding.logical_values() == _provider_binding_material(
        source_seed=20,
        seed=20,
        economic_seed=30,
        symbol="provider-asset-20",
    )


def test_full_closure_d05_quote_and_ohlc_sources_have_complete_independent_projection() -> None:
    quote_source = valuation.D05QuoteValuationSource(
        observation=_quote(),
        side=market.MarketPriceSide.BID,
        identity_binding=_legacy_binding(),
    )
    ohlc_source = valuation.D05OhlcValuationSource(
        observation=_ohlc(),
        field=valuation.D05OhlcPriceField.HIGH,
        identity_binding=_legacy_binding(),
    )

    assert quote_source.logical_values() == (
        "d05-quote",
        _EXPECTED_QUOTE,
        "bid",
        _EXPECTED_LEGACY_BINDING,
        ("d05-market-price", ("1.1",), "bid", None),
    )
    assert ohlc_source.logical_values() == (
        "d05-ohlc",
        _EXPECTED_OHLC,
        "high",
        _EXPECTED_LEGACY_BINDING,
        ("d05-market-price", ("1.14",), "bid", "high"),
    )


def test_full_closure_published_and_observed_projection_is_complete_and_offset_safe() -> None:
    as_of = valuation.ValuationAsOfInstant(
        datetime(2026, 1, 2, 7, tzinfo=timezone(timedelta(hours=-5)))
    )
    source = _published(
        source_seed=41,
        binding_seed=41,
        economic_seed=841,
        source_observation_seed=8041,
        evidence_seed=8141,
        nav_value="25.25",
        as_of=as_of,
    )
    observed = valuation.ObservedValuationObservation(
        observation_id=valuation.ValuationObservationId(_uuid(950)),
        source=source,
        recorded_at=datetime(
            2026,
            1,
            3,
            4,
            30,
            tzinfo=timezone(timedelta(hours=-5)),
        ),
        evidence_ref=valuation.ValuationEvidenceRef(_uuid(951)),
    )
    expected_source = _published_material(
        source_seed=41,
        binding_seed=41,
        economic_seed=841,
        source_observation_seed=8041,
        evidence_seed=8141,
        nav_value="25.25",
        as_of_material=(
            "instant",
            "2026-01-02T12:00:00.000000+00:00",
        ),
    )

    assert source.logical_values() == expected_source
    assert observed.logical_values() == (
        "observed",
        _uuid_material(950),
        expected_source,
        "2026-01-03T09:30:00.000000+00:00",
        _uuid_material(951),
    )


def test_full_closure_computed_provenance_uses_independent_sorted_material_and_fingerprint(
) -> None:
    source_a = _published(
        source_seed=51,
        binding_seed=51,
        economic_seed=851,
        source_observation_seed=8051,
        evidence_seed=8151,
        nav_value="25",
        as_of=valuation.ValuationAsOfDate(date(2026, 1, 2)),
    )
    source_b = _published(
        source_seed=52,
        binding_seed=52,
        economic_seed=852,
        source_observation_seed=8052,
        evidence_seed=8152,
        nav_value="26",
        as_of=valuation.ValuationAsOfDate(date(2026, 1, 2)),
    )
    alpha = valuation.ValuationComputedInput(
        valuation.ValuationInputRoleCode("alpha-input"),
        source_a,
    )
    zeta = valuation.ValuationComputedInput(
        valuation.ValuationInputRoleCode("zeta-input"),
        source_b,
    )
    provenance = valuation.ComputedValuationProvenance(
        methodology=_methodology(),
        inputs=(zeta, alpha),
        evidence_ref=valuation.ValuationEvidenceRef(_uuid(970)),
    )

    expected_source_a = _published_material(
        source_seed=51,
        binding_seed=51,
        economic_seed=851,
        source_observation_seed=8051,
        evidence_seed=8151,
        nav_value="25",
        as_of_material=("date", "2026-01-02"),
    )
    expected_source_b = _published_material(
        source_seed=52,
        binding_seed=52,
        economic_seed=852,
        source_observation_seed=8052,
        evidence_seed=8152,
        nav_value="26",
        as_of_material=("date", "2026-01-02"),
    )
    expected_inputs: tuple[tuple[object, ...], ...] = (
        (("alpha-input",), expected_source_a),
        (("zeta-input",), expected_source_b),
    )
    fingerprint_material = json.dumps(
        expected_inputs,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    expected_fingerprint = hashlib.sha256(
        fingerprint_material.encode("utf-8")
    ).hexdigest()

    assert provenance.logical_values() == (
        _EXPECTED_METHODOLOGY,
        expected_inputs,
        (expected_fingerprint,),
        _uuid_material(970),
    )
    assert tuple(item.role.value for item in provenance.inputs) == (
        "alpha-input",
        "zeta-input",
    )


def test_full_closure_computed_observation_projection_is_complete_and_offset_safe() -> None:
    source = _published(
        source_seed=61,
        binding_seed=61,
        economic_seed=861,
        source_observation_seed=8061,
        evidence_seed=8161,
        nav_value="27",
        as_of=valuation.ValuationAsOfDate(date(2026, 1, 2)),
    )
    one_input = valuation.ValuationComputedInput(
        valuation.ValuationInputRoleCode("source-nav"),
        source,
    )
    provenance = valuation.ComputedValuationProvenance(
        methodology=_methodology(),
        inputs=(one_input,),
        evidence_ref=valuation.ValuationEvidenceRef(_uuid(1010)),
    )
    observation = valuation.ComputedValuationObservation(
        observation_id=valuation.ValuationObservationId(_uuid(1011)),
        economic_identity_id=_economic_id(1012),
        as_of=valuation.ValuationAsOfInstant(
            datetime(
                2026,
                1,
                2,
                14,
                tzinfo=timezone(timedelta(hours=2)),
            )
        ),
        measure=_nav_measure("24.5"),
        provenance=provenance,
        recorded_at=datetime(
            2026,
            1,
            3,
            11,
            15,
            tzinfo=timezone(timedelta(hours=-3)),
        ),
        evidence_ref=valuation.ValuationEvidenceRef(_uuid(1013)),
    )

    expected_source = _published_material(
        source_seed=61,
        binding_seed=61,
        economic_seed=861,
        source_observation_seed=8061,
        evidence_seed=8161,
        nav_value="27",
        as_of_material=("date", "2026-01-02"),
    )
    expected_inputs: tuple[tuple[object, ...], ...] = (
        (("source-nav",), expected_source),
    )
    fingerprint_material = json.dumps(
        expected_inputs,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    expected_fingerprint = hashlib.sha256(
        fingerprint_material.encode("utf-8")
    ).hexdigest()
    expected_provenance: tuple[object, ...] = (
        _EXPECTED_METHODOLOGY,
        expected_inputs,
        (expected_fingerprint,),
        _uuid_material(1010),
    )

    assert observation.logical_values() == (
        "computed",
        _uuid_material(1011),
        _uuid_material(1012),
        ("instant", "2026-01-02T12:00:00.000000+00:00"),
        _nav_material("24.5"),
        expected_provenance,
        "2026-01-03T14:15:00.000000+00:00",
        _uuid_material(1013),
    )


def test_full_closure_date_only_semantics_remain_date_only() -> None:
    source = _published(
        source_seed=71,
        binding_seed=71,
        economic_seed=871,
        source_observation_seed=8071,
        evidence_seed=8171,
        nav_value="28",
        as_of=valuation.ValuationAsOfDate(date(2026, 1, 2)),
    )

    assert source.logical_values()[4] == ("date", "2026-01-02")
    assert "T00:00:00" not in repr(source.logical_values()[4])


def test_full_closure_three_residual_guards_are_structural_not_coverage_targets() -> None:
    # Lines 88 and 114 are after regexes that exclude every character required
    # by the configured secret markers ("=", or a space), so valid code/revision
    # material cannot reach the later marker-specific raises.
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="canonical lowercase code syntax",
    ):
        valuation.ValuationQuoteBasisCode("token=forbidden")
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="canonical revision syntax",
    ):
        valuation.ValuationSoftwareRevision("bearer forbidden")

    # Historical missed line 647 is downstream of the UMI-08 constructor
    # invariant requiring exactly MARK/INDEX/LAST. A valid pricing-terms object
    # therefore always contains every valid CryptoPerpetualPriceRole.
    terms = _pricing_terms()
    assert terms.roles == (
        crypto.CryptoPerpetualPriceRole.INDEX_PRICE,
        crypto.CryptoPerpetualPriceRole.LAST_PRICE,
        crypto.CryptoPerpetualPriceRole.MARK_PRICE,
    )
    with pytest.raises(
        crypto.CryptoPerpetualValidationError,
        match="mark, index, and last",
    ):
        crypto.CryptoPerpetualPricingTerms(
            index_relationship_id=identity.IdentityRelationshipId(_uuid(9220)),
            roles=(crypto.CryptoPerpetualPriceRole.MARK_PRICE,),
            evidence_ref=crypto.CryptoEvidenceRef(_uuid(9221)),
        )


def test_full_closure_reachable_measure_type_guards_fail_closed_directly() -> None:
    yield_convention = _yield_convention()
    rate_convention = _rate_convention()
    tenor = _tenor()
    pricing_terms = _pricing_terms()
    quote_basis = valuation.ValuationQuoteBasisCode("currency-per-unit")
    quoted = valuation.QuotedValuationValue(
        Decimal("1"),
        _economic_id(930),
        valuation.ValuationQuoteBasisCode("currency-amount"),
    )

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="FixedIncomePrice",
    ):
        valuation.FixedIncomePriceMeasure(cast(Any, Decimal("99")))

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="FixedIncomeYield",
    ):
        valuation.FixedIncomeYieldMeasure(
            cast(Any, Decimal("0.01")),
            yield_convention,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="YieldConvention",
    ):
        valuation.FixedIncomeYieldMeasure(
            fixed.FixedIncomeYield(Decimal("0.01")),
            cast(Any, object()),
        )

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="FixedIncomeSpread",
    ):
        valuation.FixedIncomeSpreadMeasure(
            cast(Any, Decimal("0.001")),
            _economic_id(900),
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="EconomicIdentityId",
    ):
        valuation.FixedIncomeSpreadMeasure(
            fixed.FixedIncomeSpread(Decimal("0.001")),
            cast(Any, "reference"),
        )

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="ZeroRate, ParRate, or ForwardRate",
    ):
        valuation.StandaloneRateMeasure(
            cast(Any, Decimal("0.01")),
            rate_convention,
            tenor,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="RateCurveConvention",
    ):
        valuation.StandaloneRateMeasure(
            rates.ZeroRate(Decimal("0.01")),
            cast(Any, object()),
            tenor,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="coordinate",
    ):
        valuation.StandaloneRateMeasure(
            rates.ZeroRate(Decimal("0.01")),
            rate_convention,
            cast(Any, "1y"),
        )

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="DiscountFactor",
    ):
        valuation.DiscountFactorMeasure(
            cast(Any, Decimal("0.97")),
            tenor,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="coordinate",
    ):
        valuation.DiscountFactorMeasure(
            rates.DiscountFactor(Decimal("0.97")),
            cast(Any, "1y"),
        )

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="quote identity",
    ):
        valuation.CryptoPerpetualPriceValue(
            Decimal("100"),
            cast(Any, "usd"),
            quote_basis,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="quote_basis",
    ):
        valuation.CryptoPerpetualPriceValue(
            Decimal("100"),
            _economic_id(922),
            cast(Any, "currency-per-unit"),
        )

    crypto_value = valuation.CryptoPerpetualPriceValue(
        Decimal("100"),
        _economic_id(922),
        quote_basis,
    )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="wrong value type",
    ):
        valuation.CryptoPerpetualPriceMeasure(
            cast(Any, Decimal("100")),
            crypto.CryptoPerpetualPriceRole.MARK_PRICE,
            pricing_terms,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="role has wrong type",
    ):
        valuation.CryptoPerpetualPriceMeasure(
            crypto_value,
            cast(Any, "mark-price"),
            pricing_terms,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="pricing_terms has wrong type",
    ):
        valuation.CryptoPerpetualPriceMeasure(
            crypto_value,
            crypto.CryptoPerpetualPriceRole.MARK_PRICE,
            cast(Any, object()),
        )

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="FixedIncomeCashFlow",
    ):
        valuation.FixedIncomeCashFlowValueMeasure(
            cast(Any, object()),
            quoted,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="QuotedValuationValue",
    ):
        valuation.FixedIncomeCashFlowValueMeasure(
            _cash_flow(),
            cast(Any, Decimal("95")),
        )


def test_full_closure_reachable_d05_ohlc_type_guards_fail_closed_directly() -> None:
    observation = _ohlc()
    binding = _legacy_binding()

    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="QualifiedOhlcBarObservation",
    ):
        valuation.D05OhlcValuationSource(
            cast(Any, object()),
            valuation.D05OhlcPriceField.CLOSE,
            binding,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="D05OhlcPriceField",
    ):
        valuation.D05OhlcValuationSource(
            observation,
            cast(Any, "close"),
            binding,
        )
    with pytest.raises(
        valuation.UniversalValuationObservationValidationError,
        match="ValuationIdentityBinding",
    ):
        valuation.D05OhlcValuationSource(
            observation,
            valuation.D05OhlcPriceField.CLOSE,
            cast(Any, object()),
        )
