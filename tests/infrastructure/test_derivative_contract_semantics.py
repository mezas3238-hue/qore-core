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


def _benchmark(value: int = 200) -> dcs.DerivativeBenchmarkReference:
    return dcs.DerivativeBenchmarkReference(
        reference_identity_id=_identity(value),
        role=dcs.DerivativeReferenceRoleCode("floating-index"),
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
        settlement_convention=_settlement(),
        evidence_ref=_evidence(value),
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


def test_contract_month_is_structural_and_strictly_typed() -> None:
    assert dcs.DerivativeContractMonth(2026, 12).logical_values() == (2026, 12)

    with pytest.raises(dcs.DerivativeContractValidationError, match="year"):
        dcs.DerivativeContractMonth(cast(int, True), 12)
    with pytest.raises(dcs.DerivativeContractValidationError, match="month"):
        dcs.DerivativeContractMonth(2026, 0)
    with pytest.raises(dcs.DerivativeContractValidationError, match="month"):
        dcs.DerivativeContractMonth(2026, 13)


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
    earlier = dcs.DerivativeNotionalStep(date(2026, 1, 2), _notional("100", unit=unit))
    later = dcs.DerivativeNotionalStep(date(2027, 1, 2), _notional("80", unit=unit))

    schedule = dcs.DerivativeNotionalSchedule((later, earlier))
    assert schedule.steps == (earlier, later)

    with pytest.raises(dcs.DerivativeContractValidationError, match="non-empty tuple"):
        dcs.DerivativeNotionalSchedule(cast(Any, [earlier]))
    with pytest.raises(dcs.DerivativeContractValidationError, match="unique"):
        dcs.DerivativeNotionalSchedule((earlier, replace(later, effective_date=earlier.effective_date)))
    with pytest.raises(dcs.DerivativeContractValidationError, match="one notional unit"):
        dcs.DerivativeNotionalSchedule(
            (earlier, replace(later, notional=_notional("80", unit=_identity(41))))
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
    assert price.logical_values() != rate.logical_values()


def test_strike_does_not_impose_false_global_positivity() -> None:
    negative_rate = _rate_strike("-0.01")
    negative_level = dcs.DerivativeStrike(
        Decimal("-20"),
        dcs.DerivativeStrikeBasis.LEVEL,
    )
    assert negative_rate.logical_values()[0] == "-0.01"
    assert negative_level.logical_values()[0] == "-20"


def test_price_strike_requires_quote_identity_only() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="price strike"):
        dcs.DerivativeStrike(Decimal("100"), dcs.DerivativeStrikeBasis.PRICE)
    with pytest.raises(dcs.DerivativeContractValidationError, match="price strike"):
        dcs.DerivativeStrike(
            Decimal("100"),
            dcs.DerivativeStrikeBasis.PRICE,
            quote_identity_id=_identity(1),
            convention=_rate_convention(),
        )


def test_rate_and_yield_strikes_require_matching_certified_convention() -> None:
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


def test_date_roles_reject_datetime_subclass_laundering() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="must be date"):
        dcs.DerivativeNotionalStep(
            cast(date, datetime(2026, 1, 2, 0, 0)),
            _notional(),
        )


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
    assert terms.multiplier.value == Decimal("50")
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


def test_physical_futures_may_retain_first_notice_without_forcing_ordering_to_last_trade() -> None:
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
    assert terms.first_notice_date == date(2027, 5, 20)
    assert terms.last_trade_date == date(2027, 5, 18)


def test_futures_identity_shape_is_typed_but_does_not_claim_identity_kind_proof() -> None:
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


def test_option_preserves_right_strike_exercise_settlement_and_size() -> None:
    terms = dcs.OptionContractTerms(
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

    assert terms.logical_values()[0] == "option"
    assert terms.right is dcs.OptionRight.CALL
    assert not hasattr(terms, "delta")
    assert not hasattr(terms, "implied_volatility")


def test_option_requires_multiplier_or_notional_but_allows_otc_notional() -> None:
    kwargs: dict[str, object] = {
        "terms_id": _terms_id(11),
        "instrument_identity_id": _identity(23),
        "underlying_identity_id": _identity(24),
        "settlement_identity_id": _identity(25),
        "right": dcs.OptionRight.PUT,
        "strike": _rate_strike("0.02"),
        "expiry_date": date(2028, 1, 1),
        "exercise": dcs.OptionExerciseTerms(dcs.OptionExerciseStyle.EUROPEAN),
        "settlement_style": dcs.DerivativeSettlementStyle.CASH,
        "evidence_ref": _evidence(11),
    }
    with pytest.raises(dcs.DerivativeContractValidationError, match="multiplier and/or"):
        dcs.OptionContractTerms(**cast(Any, kwargs))

    otc = dcs.OptionContractTerms(
        **cast(Any, kwargs),
        notional=_notional("10000000", unit=_identity(25)),
    )
    assert otc.multiplier is None
    assert otc.notional is not None


def test_option_rejects_bermudan_exercise_date_after_expiry() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="after option expiry"):
        dcs.OptionContractTerms(
            terms_id=_terms_id(12),
            instrument_identity_id=_identity(26),
            underlying_identity_id=_identity(27),
            settlement_identity_id=_identity(28),
            right=dcs.OptionRight.CALL,
            strike=_price_strike(),
            expiry_date=date(2027, 1, 1),
            exercise=dcs.OptionExerciseTerms(
                dcs.OptionExerciseStyle.BERMUDAN,
                (date(2027, 1, 2),),
            ),
            settlement_style=dcs.DerivativeSettlementStyle.CASH,
            evidence_ref=_evidence(12),
            notional=_notional(unit=_identity(28)),
        )


def test_option_rejects_raw_right_and_self_underlying() -> None:
    terms = dcs.OptionContractTerms(
        terms_id=_terms_id(13),
        instrument_identity_id=_identity(29),
        underlying_identity_id=_identity(30),
        settlement_identity_id=_identity(31),
        right=dcs.OptionRight.CALL,
        strike=_price_strike(),
        expiry_date=date(2027, 1, 1),
        exercise=dcs.OptionExerciseTerms(dcs.OptionExerciseStyle.EUROPEAN),
        settlement_style=dcs.DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(13),
        multiplier=dcs.DerivativeContractMultiplier(Decimal("1"), _identity(31)),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="option right"):
        replace(terms, right=cast(Any, "call"))
    with pytest.raises(dcs.DerivativeContractValidationError, match="underlying identity"):
        replace(terms, underlying_identity_id=terms.instrument_identity_id)


def test_cash_settled_forward_requires_typed_fixing_before_or_at_maturity() -> None:
    fixing = dcs.DerivativeFixingTerms(
        reference=_benchmark(400),
        fixing_date=date(2027, 6, 29),
        evidence_ref=_evidence(20),
    )
    terms = dcs.ForwardContractTerms(
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
    assert terms.fixing == fixing

    with pytest.raises(dcs.DerivativeContractValidationError, match="fixing_date"):
        replace(terms, fixing=replace(fixing, fixing_date=date(2027, 7, 1)))


def test_cash_forward_without_fixing_and_physical_forward_with_fixing_fail_closed() -> None:
    cash = dcs.ForwardContractTerms(
        terms_id=_terms_id(22),
        instrument_identity_id=_identity(43),
        reference_identity_id=_identity(44),
        settlement_identity_id=_identity(45),
        notional=_notional(unit=_identity(44)),
        agreed_strike=_price_strike("50"),
        maturity_date=date(2027, 12, 1),
        settlement_style=dcs.DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(22),
        fixing=dcs.DerivativeFixingTerms(
            _benchmark(401),
            date(2027, 11, 30),
            _evidence(23),
        ),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="requires explicit fixing"):
        replace(cash, fixing=None)
    with pytest.raises(dcs.DerivativeContractValidationError, match="physical forward"):
        replace(cash, settlement_style=dcs.DerivativeSettlementStyle.PHYSICAL)


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


def test_swap_fixed_and_floating_legs_retain_separate_semantics() -> None:
    fixed = _fixed_leg(1, ordinal=1, direction=dcs.DerivativeLegDirection.PAY)
    floating = _floating_leg(
        2,
        ordinal=2,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )

    assert fixed.logical_values()[0] == "fixed-rate"
    assert floating.logical_values()[0] == "floating-rate"
    assert fixed.rate.value == Decimal("0.03")
    assert floating.spread.value == Decimal("0.001")


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
    protection = dcs.ProtectionSwapLeg(
        leg_id=_leg_id(5),
        ordinal=dcs.DerivativeLegOrdinal(3),
        direction=dcs.DerivativeLegDirection.RECEIVE,
        notional_schedule=_schedule(),
        reference=_benchmark(501),
        contingency=dcs.DerivativeContingencyCode("credit-event"),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(32),
    )

    assert reference_return.logical_values()[0] == "reference-return"
    assert exchange.logical_values()[0] == "exchange"
    assert protection.logical_values()[0] == "protection"


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


def test_swap_order_is_deterministic_and_requires_contiguous_unique_ordinals() -> None:
    first = _fixed_leg(1, ordinal=1, direction=dcs.DerivativeLegDirection.PAY)
    second = _floating_leg(
        2,
        ordinal=2,
        direction=dcs.DerivativeLegDirection.RECEIVE,
    )

    left = _swap((first, second))
    right = _swap((second, first))
    assert left.legs == right.legs == (first, second)
    assert left.logical_values() == right.logical_values()

    with pytest.raises(dcs.DerivativeContractValidationError, match="ordinals must be unique"):
        _swap((first, replace(second, ordinal=first.ordinal)))
    with pytest.raises(dcs.DerivativeContractValidationError, match="contiguous from 1"):
        _swap((first, replace(second, ordinal=dcs.DerivativeLegOrdinal(3))))
    with pytest.raises(dcs.DerivativeContractValidationError, match="ids must be unique"):
        _swap((first, replace(second, leg_id=first.leg_id)))


def test_swap_notional_schedule_must_cover_effective_start_and_stop_before_termination() -> None:
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

    too_late = _schedule(
        second_value="500000",
        second_date=_TERMINATION,
    )
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


def test_swap_exchange_dates_must_fall_within_contract_term() -> None:
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


def test_swap_termination_must_follow_effective_date_and_dates_are_pure_dates() -> None:
    swap = _swap()
    with pytest.raises(dcs.DerivativeContractValidationError, match="after effective_date"):
        replace(swap, termination_date=swap.effective_date)
    with pytest.raises(dcs.DerivativeContractValidationError, match="must be date"):
        replace(swap, effective_date=cast(date, datetime(2026, 1, 2, 0, 0)))


def test_swap_leg_type_laundering_fails_closed() -> None:
    swap = _swap()
    with pytest.raises(dcs.DerivativeContractValidationError, match="certified derivative"):
        replace(swap, legs=cast(Any, (swap.legs[0], "floating")))


def test_composition_references_existing_derivative_identities_with_explicit_ratio() -> None:
    first = dcs.DerivativeCompositionLeg(
        leg_id=_leg_id(101),
        ordinal=dcs.DerivativeLegOrdinal(1),
        component_identity_id=_identity(601),
        side=dcs.DerivativeCompositionSide.LONG,
        ratio=Decimal("1.0"),
        evidence_ref=_evidence(101),
    )
    second = dcs.DerivativeCompositionLeg(
        leg_id=_leg_id(102),
        ordinal=dcs.DerivativeLegOrdinal(2),
        component_identity_id=_identity(602),
        side=dcs.DerivativeCompositionSide.SHORT,
        ratio=Decimal("2.00"),
        evidence_ref=_evidence(102),
    )
    terms = dcs.DerivativeCompositionTerms(
        terms_id=_terms_id(100),
        instrument_identity_id=_identity(600),
        legs=(second, first),
        evidence_ref=_evidence(100),
    )

    assert terms.legs == (first, second)
    assert terms.logical_values()[0] == "derivative-composition"
    assert terms.legs[1].logical_values()[4] == "2"


def test_composition_rejects_self_duplicate_component_and_invalid_ratio() -> None:
    first = dcs.DerivativeCompositionLeg(
        leg_id=_leg_id(111),
        ordinal=dcs.DerivativeLegOrdinal(1),
        component_identity_id=_identity(611),
        side=dcs.DerivativeCompositionSide.LONG,
        ratio=Decimal("1"),
        evidence_ref=_evidence(111),
    )
    second = dcs.DerivativeCompositionLeg(
        leg_id=_leg_id(112),
        ordinal=dcs.DerivativeLegOrdinal(2),
        component_identity_id=_identity(612),
        side=dcs.DerivativeCompositionSide.SHORT,
        ratio=Decimal("1"),
        evidence_ref=_evidence(112),
    )
    base = dcs.DerivativeCompositionTerms(
        terms_id=_terms_id(110),
        instrument_identity_id=_identity(610),
        legs=(first, second),
        evidence_ref=_evidence(110),
    )

    with pytest.raises(dcs.DerivativeContractValidationError, match="must not reference itself"):
        replace(
            base,
            legs=(replace(first, component_identity_id=base.instrument_identity_id), second),
        )
    with pytest.raises(dcs.DerivativeContractValidationError, match="component identities"):
        replace(base, legs=(first, replace(second, component_identity_id=first.component_identity_id)))
    with pytest.raises(dcs.DerivativeContractValidationError, match="positive"):
        replace(first, ratio=Decimal("0"))


def test_composition_requires_two_immutable_typed_legs_and_contiguous_ordinals() -> None:
    first = dcs.DerivativeCompositionLeg(
        _leg_id(121),
        dcs.DerivativeLegOrdinal(1),
        _identity(621),
        dcs.DerivativeCompositionSide.LONG,
        Decimal("1"),
        _evidence(121),
    )
    second = dcs.DerivativeCompositionLeg(
        _leg_id(122),
        dcs.DerivativeLegOrdinal(2),
        _identity(622),
        dcs.DerivativeCompositionSide.SHORT,
        Decimal("1"),
        _evidence(122),
    )
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


def test_leg_ordinal_and_composition_side_reject_bool_or_raw_string_laundering() -> None:
    with pytest.raises(dcs.DerivativeContractValidationError, match="positive int"):
        dcs.DerivativeLegOrdinal(cast(int, True))

    leg = dcs.DerivativeCompositionLeg(
        _leg_id(130),
        dcs.DerivativeLegOrdinal(1),
        _identity(630),
        dcs.DerivativeCompositionSide.LONG,
        Decimal("1"),
        _evidence(130),
    )
    with pytest.raises(dcs.DerivativeContractValidationError, match="composition side"):
        replace(leg, side=cast(Any, "long"))


def test_terms_are_structural_and_expose_no_pricing_risk_or_execution_engines() -> None:
    objects: tuple[object, ...] = (
        _swap(),
        dcs.FuturesContractTerms(
            _terms_id(140),
            _identity(640),
            _identity(641),
            _identity(642),
            dcs.DerivativeContractMonth(2028, 6),
            date(2028, 6, 30),
            dcs.DerivativeContractMultiplier(Decimal("1"), _identity(642)),
            dcs.DerivativeSettlementStyle.CASH,
            _evidence(140),
        ),
    )
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
