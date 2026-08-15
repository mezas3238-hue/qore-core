from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import qore.infrastructure.commodity_contract_delivery_semantics as commodity
import qore.infrastructure.crypto_perpetual_funding_semantics as crypto
import qore.infrastructure.derivative_contract_semantics as derivative
import qore.infrastructure.equity_fund_corporate_action_semantics as equity
import qore.infrastructure.fixed_income_economics as fixed_income
import qore.infrastructure.rate_term_structure as rates
import qore.infrastructure.structured_hybrid_synthetic_semantics as structured
import qore.infrastructure.universal_instrument_identity as identity
import qore.infrastructure.universal_market_topology as topology
import qore.infrastructure.universal_valuation_observation as valuation
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(_uuid(value))


def _tenor(
    value: int = 6,
    unit: fixed_income.FinancialTenorUnit = fixed_income.FinancialTenorUnit.MONTH,
) -> fixed_income.FinancialTenor:
    return fixed_income.FinancialTenor(value, unit)


def _day_count() -> fixed_income.DayCountConventionCode:
    return fixed_income.DayCountConventionCode("actual-365-fixed")


def _settlement() -> fixed_income.SettlementConvention:
    return fixed_income.SettlementConvention(
        business_day_lag=2,
        calendar_ref=fixed_income.BusinessCalendarRef("target2"),
        business_day_convention=fixed_income.BusinessDayConventionCode("following"),
    )


def _yield_convention() -> fixed_income.YieldConvention:
    return fixed_income.YieldConvention(
        yield_code=fixed_income.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=fixed_income.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(),
    )


def _rate_convention() -> rates.RateCurveConvention:
    return rates.RateCurveConvention(
        day_count=_day_count(),
        compounding=fixed_income.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(),
    )


def _fixed_income_profile() -> fixed_income.FixedIncomeEconomicProfile:
    instrument = _identity(1)
    currency = _identity(2)
    issue = date(2026, 1, 1)
    coupon_date = date(2026, 7, 1)
    maturity = date(2031, 1, 1)
    evidence = fixed_income.FixedIncomeEvidenceRef(_uuid(10_001))
    terms = fixed_income.FixedIncomeInstrumentTerms(
        terms_id=fixed_income.FixedIncomeTermsId(_uuid(10_002)),
        instrument_identity_id=instrument,
        denomination_currency_identity_id=currency,
        face_amount=fixed_income.FaceAmount(Decimal("1000")),
        issue_date=issue,
        maturity_date=maturity,
        coupon=fixed_income.FixedCouponTerms(
            rate=fixed_income.CouponRate(Decimal("0.05")),
            day_count=_day_count(),
            payment_tenor=_tenor(),
        ),
        settlement=_settlement(),
        yield_convention=_yield_convention(),
        evidence_ref=evidence,
        redemption_amount=fixed_income.FixedIncomeCashAmount(Decimal("1000")),
    )
    accrual = fixed_income.AccrualPeriod(
        start_date=issue,
        end_date=coupon_date,
        payment_date=coupon_date,
        day_count=_day_count(),
    )
    coupon = fixed_income.FixedIncomeCashFlow(
        cash_flow_id=fixed_income.FixedIncomeCashFlowId(_uuid(10_003)),
        instrument_identity_id=instrument,
        kind=fixed_income.FixedIncomeCashFlowKind.COUPON,
        direction=fixed_income.FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=fixed_income.FixedIncomeCashAmount(Decimal("25")),
        currency_identity_id=currency,
        payment_date=coupon_date,
        evidence_ref=fixed_income.FixedIncomeEvidenceRef(_uuid(10_004)),
        accrual_period=accrual,
    )
    principal = fixed_income.FixedIncomeCashFlow(
        cash_flow_id=fixed_income.FixedIncomeCashFlowId(_uuid(10_005)),
        instrument_identity_id=instrument,
        kind=fixed_income.FixedIncomeCashFlowKind.PRINCIPAL,
        direction=fixed_income.FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=fixed_income.FixedIncomeCashAmount(Decimal("1000")),
        currency_identity_id=currency,
        payment_date=maturity,
        evidence_ref=fixed_income.FixedIncomeEvidenceRef(_uuid(10_006)),
    )
    schedule = fixed_income.FixedIncomeCashFlowSchedule(
        instrument_identity_id=instrument,
        cash_flows=(principal, coupon),
    )
    return fixed_income.FixedIncomeEconomicProfile(
        terms=terms,
        cash_flow_schedule=schedule,
    )


def _rate_snapshot() -> rates.RateTermStructureSnapshot:
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(20_001)),
        source_id=SourceId(_uuid(20_002)),
        port_name=PortName("market-data.rates"),
    )
    evidence = rates.RateTermStructureEvidenceRef(_uuid(20_003))
    nodes = (
        rates.RateTermStructureNode(
            node_id=rates.RateTermStructureNodeId(_uuid(20_004)),
            ordinal=rates.RateTermStructureNodeOrdinal(2),
            coordinate=_tenor(2, fixed_income.FinancialTenorUnit.YEAR),
            value=rates.ZeroRate(Decimal("0.04")),
            evidence_ref=rates.RateTermStructureEvidenceRef(_uuid(20_005)),
        ),
        rates.RateTermStructureNode(
            node_id=rates.RateTermStructureNodeId(_uuid(20_006)),
            ordinal=rates.RateTermStructureNodeOrdinal(1),
            coordinate=_tenor(1, fixed_income.FinancialTenorUnit.YEAR),
            value=rates.ZeroRate(Decimal("0.03")),
            evidence_ref=rates.RateTermStructureEvidenceRef(_uuid(20_007)),
        ),
    )
    return rates.RateTermStructureSnapshot(
        snapshot_id=rates.RateTermStructureSnapshotId(_uuid(20_008)),
        curve_identity_id=_identity(10),
        currency_identity_id=_identity(2),
        curve_kind=rates.RateTermStructureKindCode("government"),
        measure=rates.RateTermStructureMeasure.ZERO_RATE,
        convention=_rate_convention(),
        as_of=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 8, 15, 12, 1, tzinfo=UTC),
        provenance=rates.RateTermStructureProvenance(
            kind=rates.RateTermStructureProvenanceKind.OBSERVED,
            methodology=rates.RateTermStructureMethodologyCode("official-published"),
            evidence_ref=evidence,
            source=source,
        ),
        nodes=nodes,
    )


def _futures() -> derivative.FuturesContractTerms:
    return derivative.FuturesContractTerms(
        terms_id=derivative.DerivativeTermsId(_uuid(30_001)),
        instrument_identity_id=_identity(20),
        reference_identity_id=_identity(21),
        settlement_identity_id=_identity(2),
        contract_month=derivative.DerivativeContractMonth(2026, 12),
        expiry_date=date(2026, 11, 20),
        multiplier=derivative.DerivativeContractMultiplier(
            Decimal("50"),
            _identity(21),
        ),
        settlement_style=derivative.DerivativeSettlementStyle.CASH,
        evidence_ref=derivative.DerivativeEvidenceRef(_uuid(30_002)),
        tick_value=derivative.DerivativeTickValue(Decimal("12.5"), _identity(2)),
        last_trade_date=date(2026, 11, 19),
    )


def _option() -> derivative.OptionContractTerms:
    return derivative.OptionContractTerms(
        terms_id=derivative.DerivativeTermsId(_uuid(31_001)),
        instrument_identity_id=_identity(22),
        underlying_identity_id=_identity(21),
        settlement_identity_id=_identity(2),
        right=derivative.OptionRight.CALL,
        strike=derivative.DerivativeStrike(
            value=Decimal("100"),
            basis=derivative.DerivativeStrikeBasis.PRICE,
            quote_identity_id=_identity(2),
            price_quote_basis=derivative.DerivativePriceQuoteBasisCode(
                "currency-per-unit"
            ),
        ),
        expiry_date=date(2026, 10, 16),
        exercise=derivative.OptionExerciseTerms(
            derivative.OptionExerciseStyle.EUROPEAN
        ),
        settlement_style=derivative.DerivativeSettlementStyle.CASH,
        evidence_ref=derivative.DerivativeEvidenceRef(_uuid(31_002)),
        multiplier=derivative.DerivativeContractMultiplier(
            Decimal("100"),
            _identity(21),
        ),
    )


def _swap() -> derivative.SwapContractTerms:
    notional = derivative.DerivativeNotionalSchedule(
        (
            derivative.DerivativeNotionalStep(
                date(2026, 1, 2),
                derivative.DerivativeNotional(Decimal("1000000"), _identity(2)),
            ),
        )
    )
    schedule = derivative.DerivativeScheduleConvention(
        stub=derivative.DerivativeScheduleStubCode("none"),
        roll=derivative.DerivativeScheduleRollCode("end-of-month"),
        calendar_ref=fixed_income.BusinessCalendarRef("nyc"),
        business_day_convention=fixed_income.BusinessDayConventionCode(
            "modified-following"
        ),
    )
    fixed_leg = derivative.FixedRateSwapLeg(
        leg_id=derivative.DerivativeLegId(_uuid(32_001)),
        ordinal=derivative.DerivativeLegOrdinal(1),
        direction=derivative.DerivativeLegDirection.PAY,
        notional_schedule=notional,
        rate=derivative.DerivativeContractRate(Decimal("0.03")),
        day_count=fixed_income.DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(),
        schedule_convention=schedule,
        settlement_convention=_settlement(),
        evidence_ref=derivative.DerivativeEvidenceRef(_uuid(32_002)),
    )
    floating_leg = derivative.FloatingRateSwapLeg(
        leg_id=derivative.DerivativeLegId(_uuid(32_003)),
        ordinal=derivative.DerivativeLegOrdinal(2),
        direction=derivative.DerivativeLegDirection.RECEIVE,
        notional_schedule=notional,
        benchmark=derivative.DerivativeBenchmarkReference(
            reference_identity_id=_identity(23),
            role=derivative.DerivativeReferenceRoleCode("floating-index"),
            tenor=_tenor(3),
        ),
        spread=fixed_income.FixedIncomeSpread(Decimal("0.001")),
        day_count=fixed_income.DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(3),
        reset_tenor=_tenor(3),
        fixing_convention=derivative.DerivativeFloatingRateConvention(
            calculation=derivative.DerivativeFloatingRateCalculationCode("term-rate"),
            fixing_calendar_ref=fixed_income.BusinessCalendarRef("nyc"),
            fixing_lag_business_days=2,
        ),
        schedule_convention=schedule,
        settlement_convention=_settlement(),
        evidence_ref=derivative.DerivativeEvidenceRef(_uuid(32_004)),
    )
    return derivative.SwapContractTerms(
        terms_id=derivative.DerivativeTermsId(_uuid(32_005)),
        instrument_identity_id=_identity(24),
        effective_date=date(2026, 1, 2),
        termination_date=date(2031, 1, 2),
        legs=(floating_leg, fixed_leg),
        evidence_ref=derivative.DerivativeEvidenceRef(_uuid(32_006)),
    )


def _fund() -> equity.FundVehicleTerms:
    nav_basis = equity.FundNavBasis(
        currency_identity_id=_identity(2),
        unit_identity_id=_identity(30),
        basis=equity.FundNavBasisCode("per-share"),
        evidence_ref=equity.EquityFundEvidenceRef(_uuid(40_001)),
    )
    return equity.FundVehicleTerms(
        terms_id=equity.EquityFundTermsId(_uuid(40_002)),
        instrument_identity_id=_identity(30),
        vehicle_kind=equity.FundVehicleKind.ETF,
        share_class=equity.EquityShareClassCode("class-a"),
        nav_basis=nav_basis,
        evidence_ref=equity.EquityFundEvidenceRef(_uuid(40_003)),
    )


def _commodity() -> commodity.CommodityFuturesContractTerms:
    reference = commodity.CommodityReferenceTerms(
        terms_id=commodity.CommodityTermsId(_uuid(50_001)),
        reference_identity_id=_identity(40),
        commodity_class=commodity.CommodityClassCode("energy"),
        measurement_unit_identity_id=_identity(41),
        evidence_ref=commodity.CommodityEvidenceRef(_uuid(50_002)),
    )
    futures = derivative.FuturesContractTerms(
        terms_id=derivative.DerivativeTermsId(_uuid(50_003)),
        instrument_identity_id=_identity(42),
        reference_identity_id=_identity(40),
        settlement_identity_id=_identity(2),
        contract_month=derivative.DerivativeContractMonth(2026, 9),
        expiry_date=date(2026, 8, 20),
        multiplier=derivative.DerivativeContractMultiplier(
            Decimal("1000"),
            _identity(41),
        ),
        settlement_style=derivative.DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=derivative.DerivativeEvidenceRef(_uuid(50_004)),
        first_notice_date=date(2026, 8, 17),
        last_trade_date=date(2026, 8, 19),
    )
    physical = commodity.CommodityPhysicalDeliveryTerms(
        (
            commodity.CommodityDeliveryAlternative(
                grade=commodity.CommodityGradeCode("grade-a"),
                location_identity_id=_identity(43),
                method=commodity.CommodityDeliveryMethodCode("pipeline-transfer"),
                window=commodity.CommodityDeliveryWindow(
                    date(2026, 8, 21),
                    date(2026, 8, 31),
                ),
            ),
        )
    )
    return commodity.CommodityFuturesContractTerms(
        terms_id=commodity.CommodityTermsId(_uuid(50_005)),
        futures=futures,
        commodity_reference=reference,
        evidence_ref=commodity.CommodityEvidenceRef(_uuid(50_006)),
        physical_delivery=physical,
    )


def _perpetual() -> crypto.CryptoPerpetualContractTerms:
    pricing = crypto.CryptoPerpetualPricingTerms(
        index_relationship_id=identity.IdentityRelationshipId(_uuid(60_001)),
        roles=(
            crypto.CryptoPerpetualPriceRole.LAST_PRICE,
            crypto.CryptoPerpetualPriceRole.MARK_PRICE,
            crypto.CryptoPerpetualPriceRole.INDEX_PRICE,
        ),
        evidence_ref=crypto.CryptoEvidenceRef(_uuid(60_002)),
    )
    funding = crypto.CryptoFundingTerms(
        interval=crypto.CryptoFundingInterval(fixed_seconds=28_800),
        sign_convention=crypto.CryptoFundingSignConvention.POSITIVE_LONG_PAYS,
        payment_identity_id=_identity(2),
        evidence_ref=crypto.CryptoEvidenceRef(_uuid(60_003)),
    )
    return crypto.CryptoPerpetualContractTerms(
        terms_id=crypto.CryptoTermsId(_uuid(60_004)),
        instrument_identity_id=_identity(50),
        reference_identity_id=_identity(51),
        settlement_identity_id=_identity(2),
        collateral_identity_id=_identity(52),
        multiplier=derivative.DerivativeContractMultiplier(
            Decimal("1"),
            _identity(51),
        ),
        tick_value=derivative.DerivativeTickValue(Decimal("0.01"), _identity(2)),
        funding=funding,
        pricing=pricing,
        evidence_ref=crypto.CryptoEvidenceRef(_uuid(60_005)),
    )


def _structured() -> structured.StructuredHybridSyntheticTerms:
    root = _identity(60)
    target = _identity(61)
    relationship = identity.IdentityRelationship(
        relationship_id=identity.IdentityRelationshipId(_uuid(70_001)),
        source_identity_id=root,
        target_identity_id=target,
        relationship=identity.IdentityRelationshipCode("structured-component"),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=identity.IdentityEvidenceRef(_uuid(70_002)),
        ordinal=1,
    )
    component = structured.StructuredComponentBinding(
        root_identity_id=root,
        relationship=relationship,
        role=structured.StructuredComponentRoleCode("principal-component"),
        evidence_ref=structured.StructuredEvidenceRef(_uuid(70_003)),
    )
    feature = structured.StructuredCapitalProtectionFeature(
        feature_id=structured.StructuredFeatureId(_uuid(70_004)),
        protected_identity_id=target,
        protected_principal_ratio=structured.StructuredPositiveRatio(Decimal("1")),
        evidence_ref=structured.StructuredEvidenceRef(_uuid(70_005)),
    )
    return structured.StructuredHybridSyntheticTerms(
        terms_id=structured.StructuredTermsId(_uuid(70_006)),
        instrument_identity_id=root,
        components=(component,),
        features=(feature,),
        evidence_ref=structured.StructuredEvidenceRef(_uuid(70_007)),
    )


def _topology_profile(
    economic_identity_id: identity.EconomicIdentityId,
    *,
    venue: str,
    mechanism: topology.MarketInteractionMechanism,
    seed: int,
) -> topology.MarketTopologyProfile:
    return topology.MarketTopologyProfile(
        profile_id=topology.MarketTopologyProfileId(_uuid(80_000 + seed)),
        subject=topology.EconomicVenueMarketTopologyScope(
            economic_identity_id,
            identity.MarketVenueCode(venue),
        ),
        mechanisms=(mechanism,),
        effective_interval=topology.MarketTopologyEffectiveInterval(
            datetime(2026, 1, 1, tzinfo=UTC),
            None,
        ),
        evidence_ref=topology.MarketTopologyEvidenceRef(_uuid(81_000 + seed)),
        stages=(topology.MarketStage.SECONDARY,),
    )


def test_materially_different_assets_share_identity_fabric_without_flattening() -> None:
    bond = _fixed_income_profile()
    curve = _rate_snapshot()
    futures = _futures()
    option = _option()
    swap = _swap()
    fund = _fund()
    commodity_future = _commodity()
    perpetual = _perpetual()
    structured_terms = _structured()

    economic_ids = (
        bond.terms.instrument_identity_id,
        curve.curve_identity_id,
        futures.instrument_identity_id,
        option.instrument_identity_id,
        swap.instrument_identity_id,
        fund.instrument_identity_id,
        commodity_future.futures.instrument_identity_id,
        perpetual.instrument_identity_id,
        structured_terms.instrument_identity_id,
    )
    assert all(isinstance(value, identity.EconomicIdentityId) for value in economic_ids)
    assert len(set(economic_ids)) == len(economic_ids)

    assert bond.cash_flow_schedule is not None
    assert len(bond.cash_flow_schedule.cash_flows) == 2
    assert len(curve.nodes) == 2
    assert futures.logical_values()[0] == "futures"
    assert option.logical_values()[0] == "option"
    assert swap.logical_values()[0] == "swap"
    assert fund.vehicle_kind is equity.FundVehicleKind.ETF
    assert commodity_future.physical_delivery is not None
    assert not hasattr(perpetual, "expiry_date")
    assert structured_terms.logical_values()[0] == "structured-hybrid-synthetic"


def test_same_numeric_magnitude_keeps_cross_asset_value_semantics() -> None:
    magnitude = Decimal("0.0500")
    bond_price = valuation.FixedIncomePriceMeasure(
        fixed_income.FixedIncomePrice(
            magnitude,
            fixed_income.FixedIncomePriceKind.CLEAN,
            fixed_income.FixedIncomePriceBasisCode("percent-of-par"),
        )
    )
    bond_yield = valuation.FixedIncomeYieldMeasure(
        fixed_income.FixedIncomeYield(magnitude),
        _yield_convention(),
    )
    standalone_rate = valuation.StandaloneRateMeasure(
        rates.ZeroRate(magnitude),
        _rate_convention(),
        _tenor(1, fixed_income.FinancialTenorUnit.YEAR),
    )
    fund = _fund()
    assert fund.nav_basis is not None
    nav = valuation.FundNavMeasure(
        valuation.FundNavValue(magnitude),
        fund.nav_basis,
    )
    implied_volatility = valuation.ImpliedVolatilityMeasure(
        valuation.ImpliedVolatility(magnitude),
        _option().underlying_identity_id,
    )

    measures: tuple[valuation.ValuationMeasure, ...] = (
        bond_price,
        bond_yield,
        standalone_rate,
        nav,
        implied_volatility,
    )
    assert tuple(value.logical_values()[0] for value in measures) == (
        "fixed-income-price",
        "fixed-income-yield",
        "zero-rate",
        "fund-nav",
        "implied-volatility",
    )
    assert len({type(value) for value in measures}) == len(measures)


def test_derivative_notional_multiplier_and_contract_identity_do_not_collapse() -> None:
    swap = _swap()
    futures = _futures()

    first_leg = swap.legs[0]
    assert isinstance(first_leg, derivative.FixedRateSwapLeg | derivative.FloatingRateSwapLeg)
    assert isinstance(first_leg.notional_schedule, derivative.DerivativeNotionalSchedule)
    assert isinstance(futures.multiplier, derivative.DerivativeContractMultiplier)
    assert type(first_leg.notional_schedule.steps[0].notional) is derivative.DerivativeNotional
    assert type(futures.multiplier) is derivative.DerivativeContractMultiplier
    assert swap.instrument_identity_id != first_leg.notional_schedule.steps[0].notional.unit_identity_id


def test_commodity_reuses_futures_terms_without_becoming_settlement_engine() -> None:
    commodity_future = _commodity()

    assert isinstance(commodity_future.futures, derivative.FuturesContractTerms)
    assert commodity_future.futures.reference_identity_id == (
        commodity_future.commodity_reference.reference_identity_id
    )
    assert commodity_future.futures.multiplier.unit_identity_id == (
        commodity_future.commodity_reference.measurement_unit_identity_id
    )
    assert commodity_future.physical_delivery is not None
    assert not hasattr(commodity_future, "settle")
    assert not hasattr(commodity_future, "transfer_title")
    assert not hasattr(commodity_future, "execute")


def test_perpetual_reuses_derivative_primitives_without_dated_futures_lifecycle() -> None:
    perpetual = _perpetual()

    assert isinstance(perpetual.multiplier, derivative.DerivativeContractMultiplier)
    assert isinstance(perpetual.tick_value, derivative.DerivativeTickValue)
    assert perpetual.pricing.roles == tuple(sorted(crypto.CryptoPerpetualPriceRole, key=lambda item: item.value))
    for forbidden in (
        "contract_month",
        "expiry_date",
        "first_notice_date",
        "last_trade_date",
        "mark_price",
        "index_price",
        "last_price",
        "funding_rate",
    ):
        assert not hasattr(perpetual, forbidden)


def test_structured_product_retains_exact_umi02_relationship_not_fake_primitive() -> None:
    terms = _structured()
    component = terms.components[0]

    assert component.root_identity_id == terms.instrument_identity_id
    assert component.relationship.source_identity_id == terms.instrument_identity_id
    assert component.component_identity_id == _identity(61)
    assert isinstance(component.relationship, identity.IdentityRelationship)
    assert not hasattr(terms, "symbol")
    assert not hasattr(terms, "provider")
    assert not hasattr(terms, "execute")


def test_market_topology_is_orthogonal_to_asset_family_and_provider_support() -> None:
    bond_profile = _topology_profile(
        _fixed_income_profile().terms.instrument_identity_id,
        venue="venue-bond",
        mechanism=topology.MarketInteractionMechanism.DEALER_RFQ,
        seed=1,
    )
    crypto_profile = _topology_profile(
        _perpetual().instrument_identity_id,
        venue="venue-crypto",
        mechanism=topology.MarketInteractionMechanism.AUTOMATED_MARKET_MAKER,
        seed=2,
    )

    assert bond_profile.economic_identity_id == _identity(1)
    assert crypto_profile.economic_identity_id == _identity(50)
    assert bond_profile.mechanisms == (topology.MarketInteractionMechanism.DEALER_RFQ,)
    assert crypto_profile.mechanisms == (
        topology.MarketInteractionMechanism.AUTOMATED_MARKET_MAKER,
    )
    for profile in (bond_profile, crypto_profile):
        assert not hasattr(profile, "provider_capability")
        assert not hasattr(profile, "best_venue")
        assert not hasattr(profile, "execute")


def test_certified_owner_logical_material_is_repeatable_in_cross_asset_collection() -> None:
    specimens = (
        _fixed_income_profile(),
        _rate_snapshot(),
        _futures(),
        _option(),
        _swap(),
        _fund(),
        _commodity(),
        _perpetual(),
        _structured(),
        _topology_profile(
            _identity(90),
            venue="venue-z",
            mechanism=topology.MarketInteractionMechanism.QUOTE_DRIVEN,
            seed=9,
        ),
    )

    first = tuple(value.logical_values() for value in specimens)
    second = tuple(value.logical_values() for value in specimens)
    assert first == second
    assert len({repr(value) for value in first}) == len(first)
