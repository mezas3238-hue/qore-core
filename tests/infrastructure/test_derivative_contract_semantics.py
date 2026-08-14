from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.derivative_contract_semantics as dcs
import qore.infrastructure.fixed_income_economics as fie
import qore.infrastructure.rate_term_structure as rts
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId

_EFFECTIVE = date(2026, 1, 2)
_TERMINATION = date(2031, 1, 2)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _terms_id(value: int = 1) -> dcs.DerivativeTermsId:
    return dcs.DerivativeTermsId(_uuid(10_000 + value))


def _leg_id(value: int) -> dcs.DerivativeLegId:
    return dcs.DerivativeLegId(_uuid(20_000 + value))


def _evidence(value: int) -> dcs.DerivativeEvidenceRef:
    return dcs.DerivativeEvidenceRef(_uuid(30_000 + value))


def _tenor(
    value: int = 3,
    unit: fie.FinancialTenorUnit = fie.FinancialTenorUnit.MONTH,
) -> fie.FinancialTenor:
    return fie.FinancialTenor(value=value, unit=unit)


def _day_count() -> fie.DayCountConventionCode:
    return fie.DayCountConventionCode("actual-360")


def _settlement() -> fie.SettlementConvention:
    return fie.SettlementConvention(
        business_day_lag=2,
        calendar_ref=fie.BusinessCalendarRef("nyc"),
        business_day_convention=fie.BusinessDayConventionCode("modified-following"),
    )


def _rate_convention() -> rts.RateCurveConvention:
    return rts.RateCurveConvention(
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(6),
    )


def _yield_convention() -> fie.YieldConvention:
    return fie.YieldConvention(
        yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(6),
    )


def _floating_convention(
    calculation: str = "term-rate",
    *,
    fixing_lag: int = 2,
    lockout: int = 0,
    observation_shift: bool = False,
) -> dcs.DerivativeFloatingRateConvention:
    return dcs.DerivativeFloatingRateConvention(
        calculation=dcs.DerivativeFloatingRateCalculationCode(calculation),
        fixing_calendar_ref=fie.BusinessCalendarRef("nyc"),
        fixing_lag_business_days=fixing_lag,
        lockout_business_days=lockout,
        observation_shift=observation_shift,
    )


def _notional(
    value: str = "1000000",
    *,
    unit: EconomicIdentityId | None = None,
) -> dcs.DerivativeNotional:
    return dcs.DerivativeNotional(
        Decimal(value),
        unit or _identity(100),
    )


def _schedule(
    *,
    first_value: str = "1000000",
    second_value: str | None = None,
    first_date: date = _EFFECTIVE,
    second_date: date = date(2029, 1, 2),
    unit: EconomicIdentityId | None = None,
) -> dcs.DerivativeNotionalSchedule:
    notional_unit = unit or _identity(100)
    steps = [
        dcs.DerivativeNotionalStep(
            first_date,
            _notional(first_value, unit=notional_unit),
        )
    ]
    if second_value is not None:
        steps.append(
            dcs.DerivativeNotionalStep(
                second_date,
                _notional(second_value, unit=notional_unit),
            )
        )
    return dcs.DerivativeNotionalSchedule(tuple(steps))


def _benchmark(
    value: int = 200,
    role: str = "floating-index",
) -> dcs.DerivativeBenchmarkReference:
    return dcs.DerivativeBenchmarkReference(
        reference_identity_id=_identity(value),
        role=dcs.DerivativeReferenceRoleCode(role),
        tenor=_tenor(3),
    )


def _price_strike(value: str = "100") -> dcs.DerivativeStrike:
    return dcs.DerivativeStrike(
        Decimal(value),
        dcs.DerivativeStrikeBasis.PRICE,
        quote_identity_id=_identity(300),
    )


def _rate_strike(value: str = "0.05") -> dcs.DerivativeStrike:
    return dcs.DerivativeStrike(
        Decimal(value),
        dcs.DerivativeStrikeBasis.RATE,
        convention=_rate_convention(),
    )


def _yield_strike(value: str = "0.04") -> dcs.DerivativeStrike:
    return dcs.DerivativeStrike(
        Decimal(value),
        dcs.DerivativeStrikeBasis.YIELD,
        convention=_yield_convention(),
    )


def _fixed_leg(
    value: int,
    *,
    ordinal: int,
    direction: dcs.DerivativeLegDirection,
    schedule: dcs.DerivativeNotionalSchedule | None = None,
) -> dcs.FixedRateSwapLeg:
    return dcs.FixedRateSwapLeg(
        leg_id=_leg_id(value),
        ordinal=dcs.DerivativeLegOrdinal(ordinal),
        direction=direction,
        notional_schedule=schedule or _schedule(),
        rate=dcs.DerivativeContractRate(Decimal("0.03")),
        day_count=_day_count(),
        payment_tenor=_tenor(6),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(value),
    )


def _floating_leg(
    value: int,
    *,
    ordinal: int,
    direction: dcs.DerivativeLegDirection,
    schedule: dcs.DerivativeNotionalSchedule | None = None,
    fixing_convention: dcs.DerivativeFloatingRateConvention | None = None,
) -> dcs.FloatingRateSwapLeg:
    return dcs.FloatingRateSwapLeg(
        leg_id=_leg_id(value),
        ordinal=dcs.DerivativeLegOrdinal(ordinal),
        direction=direction,
        notional_schedule=schedule or _schedule(),
        benchmark=_benchmark(),
        spread=fie.FixedIncomeSpread(Decimal("0.001")),
        day_count=_day_count(),
        payment_tenor=_tenor(3),
        reset_tenor=_tenor(3),
        fixing_convention=fixing_convention or _floating_convention(),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(value),
    )


def _protection_leg(
    value: int,
    *,
    ordinal: int,
    direction: dcs.DerivativeLegDirection,
    style: dcs.DerivativeSettlementStyle = dcs.DerivativeSettlementStyle.CASH,
    method: str = "auction",
    settlement_identity: EconomicIdentityId | None = None,
    recovery: dcs.DerivativeRecoveryRate | None = None,
) -> dcs.ProtectionSwapLeg:
    return dcs.ProtectionSwapLeg(
        leg_id=_leg_id(value),
        ordinal=dcs.DerivativeLegOrdinal(ordinal),
        direction=direction,
        notional_schedule=_schedule(),
        reference=_benchmark(501, role="credit-reference"),
        contingency=dcs.DerivativeContingencyCode("credit-event"),
        settlement_style=style,
        settlement_method=dcs.DerivativeProtectionSettlementMethodCode(method),
        settlement_identity_id=settlement_identity or _identity(502),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(value),
        fixed_recovery_rate=recovery,
    )


def _swap(
    legs: tuple[dcs.DerivativeSwapLeg, ...] | None = None,
) -> dcs.SwapContractTerms:
    return dcs.SwapContractTerms(
        terms_id=_terms_id(50),
        instrument_identity_id=_identity(500),
        effective_date=_EFFECTIVE,
        termination_date=_TERMINATION,
        legs=legs
        or (
            _fixed_leg(1, ordinal=1, direction=dcs.DerivativeLegDirection.PAY),
            _floating_leg(
                2,
                ordinal=2,
                direction=dcs.DerivativeLegDirection.RECEIVE,
            ),
        ),
        evidence_ref=_evidence(50),
    )


def _composition_leg(
    value: int,
    ordinal: int,
    component: int,
    side: dcs.DerivativeCompositionSide,
    ratio: str = "1",
) -> dcs.DerivativeCompositionLeg:
    return dcs.DerivativeCompositionLeg(
        leg_id=_leg_id(value),
        ordinal=dcs.DerivativeLegOrdinal(ordinal),
        component_identity_id=_identity(component),
        side=side,
        ratio=Decimal(ratio),
        evidence_ref=_evidence(value),
    )


def test_local_ids_and_evidence_are_uuid_backed_not_economic_identity() -> None:
    assert dcs.DerivativeTermsId(_uuid(1)).logical_values() == (str(_uuid(1)),)
    assert dcs.DerivativeLegId(_uuid(2)).logical_values() == (str(_uuid(2)),)
    assert dcs.DerivativeEvidenceRef(_uuid(3)).logical_values() == (str(_uuid(3)),)

    for value_type in (
        dcs.DerivativeTermsId,
        dcs.DerivativeLegId,
        dcs.DerivativeEvidenceRef,
    ):
        with pytest.raises(dcs.DerivativeContractValidationError, match="UUID"):
            value_type(cast(Any, "token=secret"))


def test_contract_month_and_leg_ordinal_are_strictly_typed() -> None:
    assert dcs.DerivativeContractMonth(2026, 12).logical_values() == (2026, 12)
    assert dcs.DerivativeLegOrdinal(1).logical_values() == (1,)

    with pytest.raises(dcs.DerivativeContractValidationError, match="year"):
        dcs.DerivativeContractMonth(cast(int, True), 12)
    with pytest.raises(dcs.DerivativeContractValidationError, match="month"):
        dcs.DerivativeContractMonth(2026, 13)
    with pytest.raises(dcs.DerivativeContractValidationError, match="positive int"):
        dcs.DerivativeLegOrdinal(cast(int, True))


def test_notional_multiplier_and_tick_value_are_distinct_semantic_types() -> None:
    value = Decimal("100.00")
    unit = _identity(10)
    notional = dcs.DerivativeNotional(value, unit)
    multiplier = dcs.DerivativeContractMultiplier(value, unit)
    tick_value = dcs.DerivativeTickValue(value, unit)

    assert tuple(type(item) for item in (notional, multiplier, tick_value)) == (
        dcs.DerivativeNotional,
        dcs.DerivativeContractMultiplier,
        dcs.DerivativeTickValue,
    )
    assert notional.logical_values() == ("100", unit.logical_values())
    assert multiplier.logical_values() == ("100", unit.logical_values())
    assert tick_value.logical_values() == ("100", unit.logical_values())


@pytest.mark.parametrize(
    "value",
    [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")],
)
def test_notional_multiplier_and_tick_value_fail_closed(value: Decimal) -> None:
    unit = _identity(10)
    for value_type in (
        dcs.DerivativeNotional,
        dcs.DerivativeContractMultiplier,
        dcs.DerivativeTickValue,
    ):
        with pytest.raises(dcs.DerivativeContractValidationError):
            value_type(value, unit)


def test_contract_rate_is_distinct_and_allows_negative_rate_environment() -> None:
    rate = dcs.DerivativeContractRate(Decimal("-0.0050"))
    assert rate.logical_values() == ("-0.005",)
    assert not isinstance(rate, rts.ZeroRate)
    assert not isinstance(rate, fie.FixedIncomeYield)
    assert not isinstance(rate, fie.FixedIncomeSpread)


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_contract_rate_rejects_non_finite_values(value: Decimal) -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="finite Decimal"):
        dcs.DerivativeContractRate(value)


def test_notional_schedule_is_immutable_sorted_unique_and_unit_stable() -> None:
    unit = _identity(40)
    earlier = dcs.DerivativeNotionalStep(
        date(2026, 1, 2),
        _notional("100", unit=unit),
    )
    later = dcs.DerivativeNotionalStep(
        date(2027, 1, 2),
        _notional("80", unit=unit),
    )
    schedule = dcs.DerivativeNotionalSchedule((later, earlier))
    assert schedule.steps == (earlier, later)

    with pytest.raises(dcs.DerivativeContractValidationError, match="non-empty tuple"):
        dcs.DerivativeNotionalSchedule(cast(Any, [earlier]))
    with pytest.raises(dcs.DerivativeContractValidationError, match="unique"):
        dcs.DerivativeNotionalSchedule(
            (earlier, replace(later, effective_date=earlier.effective_date))
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="one notional unit"):
        dcs.DerivativeNotionalSchedule(
            (
                earlier,
                replace(later, notional=_notional("80", unit=_identity(41))),
            )
        )


def test_date_roles_reject_datetime_subclass_laundering() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="must be date"):
        dcs.DerivativeNotionalStep(
            cast(date, datetime(2026, 1, 2, 0, 0)),
            _notional(),
        )


def test_benchmark_reference_is_typed_and_grants_no_curve_engine() -> None:
    benchmark = _benchmark()
    assert benchmark.logical_values()[0] == _identity(200).logical_values()
    assert not hasattr(benchmark, "bootstrap")
    assert not hasattr(benchmark, "interpolate")

    with pytest.raises(dcs.DerivativeContractValidationError, match="EconomicIdentityId"):
        replace(benchmark, reference_identity_id=cast(Any, _uuid(200)))
    with pytest.raises(dcs.DerivativeContractValidationError, match="role"):
        replace(benchmark, role=cast(Any, "floating-index"))


def test_floating_rate_convention_retains_calculation_and_fixing_semantics() -> None:
    term = _floating_convention("term-rate", fixing_lag=2)
    compounded = _floating_convention(
        "compounded-in-arrears",
        fixing_lag=5,
        lockout=2,
        observation_shift=True,
    )

    assert term.logical_values() == (("term-rate",), ("nyc",), 2, 0, False)
    assert compounded.logical_values() != term.logical_values()


def test_floating_rate_convention_rejects_type_laundering() -> None:
    base = _floating_convention()
    with pytest.raises(dcs.DerivativeContractValidationError, match="calculation"):
        replace(base, calculation=cast(Any, "term-rate"))
    with pytest.raises(dcs.DerivativeContractValidationError, match="fixing_calendar"):
        replace(base, fixing_calendar_ref=cast(Any, "nyc"))
    with pytest.raises(dcs.DerivativeContractValidationError, match="non-negative int"):
        replace(base, fixing_lag_business_days=cast(int, True))
    with pytest.raises(dcs.DerivativeContractValidationError, match="non-negative int"):
        replace(base, lockout_business_days=-1)
    with pytest.raises(dcs.DerivativeContractValidationError, match="must be bool"):
        replace(base, observation_shift=cast(Any, 1))


def test_floating_swap_leg_requires_explicit_fixing_convention() -> None:
    leg = _floating_leg(
        1,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )
    assert isinstance(leg.fixing_convention, dcs.DerivativeFloatingRateConvention)
    with pytest.raises(dcs.DerivativeContractValidationError, match="fixing_convention"):
        replace(leg, fixing_convention=cast(Any, "term-rate"))


def test_strike_basis_preserves_price_rate_yield_spread_and_level_semantics() -> None:
    price = _price_strike("100.00")
    rate = _rate_strike("0.0500")
    bond_yield = _yield_strike("0.0400")
    spread = dcs.DerivativeStrike(
        Decimal("0.0010"),
        dcs.DerivativeStrikeBasis.SPREAD,
    )
    level = dcs.DerivativeStrike(
        Decimal("5000"),
        dcs.DerivativeStrikeBasis.LEVEL,
    )

    assert price.logical_values()[0:2] == ("100", "price")
    assert rate.logical_values()[0:2] == ("0.05", "rate")
    assert bond_yield.logical_values()[0:2] == ("0.04", "yield")
    assert spread.logical_values()[0:2] == ("0.001", "spread")
    assert level.logical_values()[0:2] == ("5000", "level")


def test_strike_does_not_impose_false_global_positivity() -> None:
    assert _rate_strike("-0.01").logical_values()[0] == "-0.01"
    level = dcs.DerivativeStrike(Decimal("-20"), dcs.DerivativeStrikeBasis.LEVEL)
    assert level.logical_values()[0] == "-20"


def test_price_rate_and_yield_strikes_require_matching_semantic_material() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="price strike"):
        dcs.DerivativeStrike(Decimal("100"), dcs.DerivativeStrikeBasis.PRICE)
    with pytest.raises(dcs.DerivativeContractValidationError, match="rate strike"):
        dcs.DerivativeStrike(
            Decimal("0.05"),
            dcs.DerivativeStrikeBasis.RATE,
            convention=_yield_convention(),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="yield strike"):
        dcs.DerivativeStrike(
            Decimal("0.04"),
            dcs.DerivativeStrikeBasis.YIELD,
            convention=_rate_convention(),
        )


def test_spread_and_level_strikes_reject_rate_yield_or_quote_laundering() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="spread/level"):
        dcs.DerivativeStrike(
            Decimal("0.001"),
            dcs.DerivativeStrikeBasis.SPREAD,
            convention=_rate_convention(),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="spread/level"):
        dcs.DerivativeStrike(
            Decimal("5000"),
            dcs.DerivativeStrikeBasis.LEVEL,
            quote_identity_id=_identity(2),
        )


def test_strike_rejects_raw_basis_and_non_finite_decimal() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="basis"):
        dcs.DerivativeStrike(Decimal("1"), cast(Any, "price"))
    with pytest.raises(dcs.DerivativeContractValidationError, match="finite Decimal"):
        dcs.DerivativeStrike(Decimal("NaN"), dcs.DerivativeStrikeBasis.LEVEL)


def test_bermudan_exercise_requires_explicit_unique_dates_and_is_sorted() -> None:
    first = date(2026, 3, 1)
    second = date(2026, 6, 1)
    terms = dcs.OptionExerciseTerms(
        dcs.OptionExerciseStyle.BERMUDAN,
        (second, first),
    )
    assert terms.bermudan_dates == (first, second)

    with pytest.raises(dcs.DerivativeContractValidationError, match="requires explicit"):
        dcs.OptionExerciseTerms(dcs.OptionExerciseStyle.BERMUDAN)
    with pytest.raises(dcs.DerivativeContractValidationError, match="unique"):
        dcs.OptionExerciseTerms(
            dcs.OptionExerciseStyle.BERMUDAN,
            (first, first),
        )


def test_non_bermudan_exercise_rejects_explicit_date_list() -> None:
    for style in (dcs.OptionExerciseStyle.EUROPEAN, dcs.OptionExerciseStyle.AMERICAN):
        with pytest.raises(dcs.DerivativeContractValidationError, match="only Bermudan"):
            dcs.OptionExerciseTerms(style, (date(2026, 3, 1),))


def test_futures_contract_retains_month_expiry_multiplier_settlement_and_tick_value() -> None:
    terms = dcs.FuturesContractTerms(
        terms_id=_terms_id(1),
        instrument_identity_id=_identity(1),
        reference_identity_id=_identity(2),
        settlement_identity_id=_identity(3),
        contract_month=dcs.DerivativeContractMonth(2026, 12),
        expiry_date=date(2026, 12, 18),
        multiplier=dcs.DerivativeContractMultiplier(Decimal("50"), _identity(3)),
        settlement_style=dcs.DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(1),
        tick_value=dcs.DerivativeTickValue(Decimal("12.5"), _identity(3)),
        last_trade_date=date(2026, 12, 18),
    )
    assert terms.logical_values()[0] == "futures"
    assert terms.tick_value is not None
    assert not hasattr(terms, "execute")


def test_cash_futures_reject_first_notice_and_dates_after_expiry() -> None:
    base = dcs.FuturesContractTerms(
        terms_id=_terms_id(2),
        instrument_identity_id=_identity(4),
        reference_identity_id=_identity(5),
        settlement_identity_id=_identity(6),
        contract_month=dcs.DerivativeContractMonth(2027, 3),
        expiry_date=date(2027, 3, 31),
        multiplier=dcs.DerivativeContractMultiplier(Decimal("1000"), _identity(6)),
        settlement_style=dcs.DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(2),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="cash-settled"):
        replace(base, first_notice_date=date(2027, 3, 1))
    with pytest.raises(dcs.DerivativeContractValidationError, match="last_trade"):
        replace(base, last_trade_date=date(2027, 4, 1))


def test_physical_futures_can_retain_notice_and_independent_last_trade_order() -> None:
    terms = dcs.FuturesContractTerms(
        terms_id=_terms_id(3),
        instrument_identity_id=_identity(7),
        reference_identity_id=_identity(8),
        settlement_identity_id=_identity(8),
        contract_month=dcs.DerivativeContractMonth(2027, 5),
        expiry_date=date(2027, 5, 31),
        multiplier=dcs.DerivativeContractMultiplier(Decimal("5000"), _identity(8)),
        settlement_style=dcs.DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=_evidence(3),
        first_notice_date=date(2027, 5, 20),
        last_trade_date=date(2027, 5, 18),
    )
    assert terms.first_notice_date is not None
    assert terms.last_trade_date is not None
    assert terms.first_notice_date > terms.last_trade_date


def test_futures_identity_shape_is_typed_but_does_not_claim_kind_proof() -> None:
    terms = dcs.FuturesContractTerms(
        terms_id=_terms_id(4),
        instrument_identity_id=_identity(9),
        reference_identity_id=_identity(10),
        settlement_identity_id=_identity(11),
        contract_month=dcs.DerivativeContractMonth(2027, 6),
        expiry_date=date(2027, 6, 30),
        multiplier=dcs.DerivativeContractMultiplier(Decimal("1"), _identity(11)),
        settlement_style=dcs.DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(4),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="EconomicIdentityId"):
        replace(terms, instrument_identity_id=cast(Any, _uuid(9)))


def _option() -> dcs.OptionContractTerms:
    return dcs.OptionContractTerms(
        terms_id=_terms_id(10),
        instrument_identity_id=_identity(20),
        underlying_identity_id=_identity(21),
        settlement_identity_id=_identity(22),
        right=dcs.OptionRight.CALL,
        strike=_price_strike("150"),
        expiry_date=date(2027, 1, 15),
        exercise=dcs.OptionExerciseTerms(dcs.OptionExerciseStyle.AMERICAN),
        settlement_style=dcs.DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=_evidence(10),
        multiplier=dcs.DerivativeContractMultiplier(Decimal("100"), _identity(21)),
    )


def test_option_preserves_right_strike_exercise_settlement_and_size() -> None:
    terms = _option()
    assert terms.logical_values()[0] == "option"
    assert terms.right is dcs.OptionRight.CALL
    assert not hasattr(terms, "delta")
    assert not hasattr(terms, "implied_volatility")


def test_option_requires_multiplier_or_notional_and_allows_otc_notional() -> None:
    base = _option()
    with pytest.raises(dcs.DerivativeContractValidationError, match="multiplier and/or"):
        replace(base, multiplier=None, notional=None)

    otc = replace(
        base,
        multiplier=None,
        notional=_notional("10000000", unit=_identity(22)),
    )
    assert otc.multiplier is None
    assert otc.notional is not None


def test_option_rejects_bermudan_date_after_expiry_and_raw_right() -> None:
    base = _option()
    with pytest.raises(dcs.DerivativeContractValidationError, match="after option expiry"):
        replace(
            base,
            exercise=dcs.OptionExerciseTerms(
                dcs.OptionExerciseStyle.BERMUDAN,
                (date(2027, 1, 16),),
            ),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="option right"):
        replace(base, right=cast(Any, "call"))


def _cash_forward() -> dcs.ForwardContractTerms:
    fixing = dcs.DerivativeFixingTerms(
        reference=_benchmark(400),
        fixing_date=date(2027, 6, 29),
        evidence_ref=_evidence(20),
    )
    return dcs.ForwardContractTerms(
        terms_id=_terms_id(20),
        instrument_identity_id=_identity(40),
        reference_identity_id=_identity(41),
        settlement_identity_id=_identity(42),
        notional=_notional(unit=_identity(41)),
        agreed_strike=_price_strike("1.10"),
        maturity_date=date(2027, 6, 30),
        settlement_style=dcs.DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(21),
        fixing=fixing,
        settlement_convention=_settlement(),
    )


def test_cash_settled_forward_requires_fixing_before_or_at_maturity() -> None:
    terms = _cash_forward()
    with pytest.raises(dcs.DerivativeContractValidationError, match="requires explicit fixing"):
        replace(terms, fixing=None)
    assert terms.fixing is not None
    with pytest.raises(dcs.DerivativeContractValidationError, match="fixing_date"):
        replace(
            terms,
            fixing=replace(terms.fixing, fixing_date=date(2027, 7, 1)),
        )


def test_physical_forward_without_fixing_is_valid_and_does_not_settle_itself() -> None:
    terms = dcs.ForwardContractTerms(
        terms_id=_terms_id(24),
        instrument_identity_id=_identity(46),
        reference_identity_id=_identity(47),
        settlement_identity_id=_identity(47),
        notional=_notional(unit=_identity(47)),
        agreed_strike=_price_strike("75"),
        maturity_date=date(2028, 1, 1),
        settlement_style=dcs.DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=_evidence(24),
        settlement_convention=_settlement(),
    )
    assert terms.fixing is None
    assert not hasattr(terms, "settle")


def test_physical_forward_may_retain_valid_fixing_precheck_umi05_01() -> None:
    fixing = dcs.DerivativeFixingTerms(
        reference=_benchmark(405),
        fixing_date=date(2027, 12, 30),
        evidence_ref=_evidence(25),
    )
    terms = dcs.ForwardContractTerms(
        terms_id=_terms_id(25),
        instrument_identity_id=_identity(48),
        reference_identity_id=_identity(49),
        settlement_identity_id=_identity(49),
        notional=_notional(unit=_identity(49)),
        agreed_strike=_price_strike("80"),
        maturity_date=date(2028, 1, 1),
        settlement_style=dcs.DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=_evidence(26),
        fixing=fixing,
    )
    assert terms.fixing == fixing
    with pytest.raises(dcs.DerivativeContractValidationError, match="fixing_date"):
        replace(terms, fixing=replace(fixing, fixing_date=date(2028, 1, 2)))


def test_fixed_and_floating_swap_legs_retain_separate_semantics() -> None:
    fixed = _fixed_leg(1, ordinal=1, direction=dcs.DerivativeLegDirection.PAY)
    floating = _floating_leg(
        2,
        ordinal=2,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )
    assert fixed.logical_values()[0] == "fixed-rate"
    assert floating.logical_values()[0] == "floating-rate"
    assert floating.logical_values()[10] == _floating_convention().logical_values()


def test_ois_and_term_float_legs_do_not_collapse_to_same_logical_material() -> None:
    term = _floating_leg(
        1,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
        fixing_convention=_floating_convention("term-rate", fixing_lag=2),
    )
    ois = replace(
        term,
        fixing_convention=_floating_convention(
            "compounded-in-arrears",
            fixing_lag=5,
            lockout=2,
            observation_shift=True,
        ),
    )
    assert term.logical_values() != ois.logical_values()


def test_reference_return_exchange_and_protection_legs_are_explicit_types() -> None:
    reference_return = dcs.ReferenceReturnSwapLeg(
        leg_id=_leg_id(3),
        ordinal=dcs.DerivativeLegOrdinal(1),
        direction=dcs.DerivativeLegDirection.RECEIVE,
        notional_schedule=_schedule(),
        reference=_benchmark(500),
        payment_tenor=_tenor(3),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(30),
    )
    exchange = dcs.ExchangeSwapLeg(
        leg_id=_leg_id(4),
        ordinal=dcs.DerivativeLegOrdinal(2),
        direction=dcs.DerivativeLegDirection.PAY,
        amount=_notional("1000000"),
        payment_date=_EFFECTIVE,
        evidence_ref=_evidence(31),
    )
    protection = _protection_leg(
        5,
        ordinal=3,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )

    assert reference_return.logical_values()[0] == "reference-return"
    assert exchange.logical_values()[0] == "exchange"
    assert protection.logical_values()[0] == "protection"


def test_protection_leg_retains_cash_vs_physical_settlement_semantics() -> None:
    cash = _protection_leg(
        10,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
        style=dcs.DerivativeSettlementStyle.CASH,
        method="auction",
        settlement_identity=_identity(700),
    )
    physical = _protection_leg(
        11,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
        style=dcs.DerivativeSettlementStyle.PHYSICAL,
        method="physical-delivery",
        settlement_identity=_identity(701),
    )
    assert cash.logical_values() != physical.logical_values()

    with pytest.raises(dcs.DerivativeContractValidationError, match="settlement_style"):
        replace(cash, settlement_style=cast(Any, "cash"))
    with pytest.raises(dcs.DerivativeContractValidationError, match="EconomicIdentityId"):
        replace(cash, settlement_identity_id=cast(Any, _uuid(700)))


def test_protection_auction_and_fixed_recovery_do_not_collapse_precheck_umi05_04() -> None:
    auction = _protection_leg(
        20,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
        style=dcs.DerivativeSettlementStyle.CASH,
        method="auction",
        settlement_identity=_identity(710),
    )
    fixed = _protection_leg(
        21,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
        style=dcs.DerivativeSettlementStyle.CASH,
        method="fixed-recovery",
        settlement_identity=_identity(710),
        recovery=dcs.DerivativeRecoveryRate(Decimal("0.40")),
    )
    assert auction.logical_values() != fixed.logical_values()
    assert fixed.fixed_recovery_rate is not None
    assert fixed.fixed_recovery_rate.logical_values() == ("0.4",)


def test_fixed_recovery_requires_cash_style_and_explicit_bounded_rate() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="requires recovery rate"):
        _protection_leg(
            30,
            ordinal=1,
            direction=dcs.DerivativeLegDirection.RECEIVE,
            method="fixed-recovery",
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="must be CASH"):
        _protection_leg(
            31,
            ordinal=1,
            direction=dcs.DerivativeLegDirection.RECEIVE,
            style=dcs.DerivativeSettlementStyle.PHYSICAL,
            method="fixed-recovery",
            recovery=dcs.DerivativeRecoveryRate(Decimal("0.4")),
        )
    for value in (Decimal("-0.01"), Decimal("1.01"), Decimal("NaN")):
        with pytest.raises(dcs.DerivativeContractValidationError):
            dcs.DerivativeRecoveryRate(value)


def test_non_fixed_recovery_rejects_recovery_rate_and_method_style_mismatch() -> None:
    auction = _protection_leg(
        40,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="only fixed-recovery"):
        replace(
            auction,
            fixed_recovery_rate=dcs.DerivativeRecoveryRate(Decimal("0.4")),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="auction.*CASH"):
        replace(auction, settlement_style=dcs.DerivativeSettlementStyle.PHYSICAL)

    physical = _protection_leg(
        41,
        ordinal=1,
        direction=dcs.DerivativeLegDirection.RECEIVE,
        style=dcs.DerivativeSettlementStyle.PHYSICAL,
        method="physical-delivery",
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="physical-delivery.*PHYSICAL"):
        replace(physical, settlement_style=dcs.DerivativeSettlementStyle.CASH)
    with pytest.raises(dcs.DerivativeContractValidationError, match="settlement_method"):
        replace(auction, settlement_method=cast(Any, "auction"))


def test_swap_requires_two_typed_legs_pay_and_receive() -> None:
    pay = _fixed_leg(1, ordinal=1, direction=dcs.DerivativeLegDirection.PAY)
    receive = _floating_leg(
        2,
        ordinal=2,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )
    assert _swap((pay, receive)).legs == (pay, receive)

    with pytest.raises(dcs.DerivativeContractValidationError, match="at least two"):
        _swap((pay,))
    with pytest.raises(dcs.DerivativeContractValidationError, match="PAY and one RECEIVE"):
        _swap((pay, replace(receive, direction=dcs.DerivativeLegDirection.PAY)))


def test_swap_order_is_deterministic_and_requires_unique_contiguous_ordinals() -> None:
    first = _fixed_leg(1, ordinal=1, direction=dcs.DerivativeLegDirection.PAY)
    second = _floating_leg(
        2,
        ordinal=2,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )
    left = _swap((first, second))
    right = _swap((second, first))
    assert left.logical_values() == right.logical_values()

    with pytest.raises(dcs.DerivativeContractValidationError, match="ordinals must be unique"):
        _swap((first, replace(second, ordinal=first.ordinal)))
    with pytest.raises(dcs.DerivativeContractValidationError, match="contiguous from 1"):
        _swap((first, replace(second, ordinal=dcs.DerivativeLegOrdinal(3))))
    with pytest.raises(dcs.DerivativeContractValidationError, match="ids must be unique"):
        _swap((first, replace(second, leg_id=first.leg_id)))


def test_swap_notional_schedule_must_start_at_effective_and_change_before_termination() -> None:
    wrong_start = _schedule(first_date=date(2026, 1, 3))
    with pytest.raises(dcs.DerivativeContractValidationError, match="start at effective_date"):
        _swap(
            (
                _fixed_leg(
                    1,
                    ordinal=1,
                    direction=dcs.DerivativeLegDirection.PAY,
                    schedule=wrong_start,
                ),
                _floating_leg(
                    2,
                    ordinal=2,
                    direction=dcs.DerivativeLegDirection.RECEIVE,
                ),
            )
        )

    too_late = _schedule(second_value="500000", second_date=_TERMINATION)
    with pytest.raises(dcs.DerivativeContractValidationError, match="precede termination"):
        _swap(
            (
                _fixed_leg(
                    1,
                    ordinal=1,
                    direction=dcs.DerivativeLegDirection.PAY,
                    schedule=too_late,
                ),
                _floating_leg(
                    2,
                    ordinal=2,
                    direction=dcs.DerivativeLegDirection.RECEIVE,
                ),
            )
        )


def test_swap_exchange_dates_and_contract_chronology_fail_closed() -> None:
    exchange = dcs.ExchangeSwapLeg(
        leg_id=_leg_id(1),
        ordinal=dcs.DerivativeLegOrdinal(1),
        direction=dcs.DerivativeLegDirection.PAY,
        amount=_notional(),
        payment_date=date(2032, 1, 1),
        evidence_ref=_evidence(40),
    )
    floating = _floating_leg(
        2,
        ordinal=2,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="within swap term"):
        _swap((exchange, floating))

    swap = _swap()
    with pytest.raises(dcs.DerivativeContractValidationError, match="after effective_date"):
        replace(swap, termination_date=swap.effective_date)
    with pytest.raises(dcs.DerivativeContractValidationError, match="must be date"):
        replace(swap, effective_date=cast(date, datetime(2026, 1, 2, 0, 0)))


def test_swap_leg_type_laundering_fails_closed() -> None:
    swap = _swap()
    with pytest.raises(dcs.DerivativeContractValidationError, match="certified derivative"):
        replace(swap, legs=cast(Any, (swap.legs[0], "floating")))


def test_composition_references_existing_identities_with_explicit_ratio() -> None:
    first = _composition_leg(101, 1, 601, dcs.DerivativeCompositionSide.LONG)
    second = _composition_leg(
        102,
        2,
        602,
        dcs.DerivativeCompositionSide.SHORT,
        "2.00",
    )
    terms = dcs.DerivativeCompositionTerms(
        terms_id=_terms_id(100),
        instrument_identity_id=_identity(600),
        legs=(second, first),
        evidence_ref=_evidence(100),
    )
    assert terms.legs == (first, second)
    assert terms.legs[1].logical_values()[4] == "2"


def test_composition_rejects_self_duplicate_component_and_invalid_ratio() -> None:
    first = _composition_leg(111, 1, 611, dcs.DerivativeCompositionSide.LONG)
    second = _composition_leg(112, 2, 612, dcs.DerivativeCompositionSide.SHORT)
    base = dcs.DerivativeCompositionTerms(
        terms_id=_terms_id(110),
        instrument_identity_id=_identity(610),
        legs=(first, second),
        evidence_ref=_evidence(110),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="must not reference itself"):
        replace(
            base,
            legs=(
                replace(first, component_identity_id=base.instrument_identity_id),
                second,
            ),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="component identities"):
        replace(
            base,
            legs=(
                first,
                replace(second, component_identity_id=first.component_identity_id),
            ),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="positive"):
        replace(first, ratio=Decimal("0"))


def test_composition_requires_two_immutable_legs_and_contiguous_ordinals() -> None:
    first = _composition_leg(121, 1, 621, dcs.DerivativeCompositionSide.LONG)
    second = _composition_leg(122, 2, 622, dcs.DerivativeCompositionSide.SHORT)
    base = dcs.DerivativeCompositionTerms(
        _terms_id(120),
        _identity(620),
        (first, second),
        _evidence(120),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="at least two"):
        replace(base, legs=(first,))
    with pytest.raises(dcs.DerivativeContractValidationError, match="contiguous from 1"):
        replace(base, legs=(first, replace(second, ordinal=dcs.DerivativeLegOrdinal(3))))
    with pytest.raises(dcs.DerivativeContractValidationError, match="immutable tuple"):
        replace(base, legs=cast(Any, [first, second]))


def test_composition_side_rejects_raw_string_laundering() -> None:
    leg = _composition_leg(130, 1, 630, dcs.DerivativeCompositionSide.LONG)
    with pytest.raises(dcs.DerivativeContractValidationError, match="composition side"):
        replace(leg, side=cast(Any, "long"))


def test_terms_expose_no_pricing_risk_execution_or_settlement_engines() -> None:
    objects: tuple[object, ...] = (_swap(), _option(), _cash_forward())
    forbidden = (
        "price",
        "present_value",
        "delta",
        "gamma",
        "vega",
        "implied_volatility",
        "margin",
        "execute",
        "settle",
        "bootstrap",
    )
    for value in objects:
        for attribute in forbidden:
            assert not hasattr(value, attribute)


def test_logical_values_are_deterministic_and_do_not_contain_secret_markers() -> None:
    left = _swap()
    right = _swap(tuple(reversed(left.legs)))
    assert left.logical_values() == right.logical_values()

    material = repr(left.logical_values()).lower()
    for marker in ("token=", "password=", "secret=", "bearer "):
        assert marker not in material
