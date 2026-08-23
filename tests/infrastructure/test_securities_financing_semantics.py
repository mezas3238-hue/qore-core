from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.securities_financing_semantics as s
from qore.infrastructure.fixed_income_economics import (
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
)
from qore.infrastructure.securities_financing_semantics import (
    MarginLendingTerms,
    RepoFarLegTerms,
    RepoTerms,
    SecuritiesFinancingValidationError,
    SecuritiesLendingCompensationLegTerms,
    SecuritiesLendingCompensationTerms,
    SecuritiesLendingTerms,
    SftArrangementMode,
    SftArrangementTerms,
    SftCashAmount,
    SftCollateralEligibilityCode,
    SftCollateralizationMode,
    SftCompensationAccrualBasisCode,
    SftCompensationPaymentMode,
    SftCompensationResetMode,
    SftDurationMode,
    SftDurationTerms,
    SftEvidenceRef,
    SftFinancingCalculationCode,
    SftFinancingFixingTiming,
    SftFinancingObservationMode,
    SftFinancingPaymentMode,
    SftFinancingResetMode,
    SftMarginTerms,
    SftPartyReferenceId,
    SftRateKind,
    SftRateTerms,
    SftScheduleReferenceId,
    SftSecurityQuantity,
    SftSecurityQuantityBasisCode,
    SftTermsId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(n: int) -> UUID:
    return UUID(int=n)


def _id(n: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(n))


def _terms(n: int = 100) -> SftTermsId:
    return SftTermsId(_uuid(n))


def _evidence(n: int = 200) -> SftEvidenceRef:
    return SftEvidenceRef(_uuid(n))


def _party(n: int) -> SftPartyReferenceId:
    return SftPartyReferenceId(_uuid(n))


def _schedule(n: int = 700) -> SftScheduleReferenceId:
    return SftScheduleReferenceId(_uuid(n))


def _cash(amount: str = "1000000", currency: int = 300) -> SftCashAmount:
    return SftCashAmount(Decimal(amount), _id(currency))


def _security(n: int = 400, q: str = "100", basis: str = "units") -> SftSecurityQuantity:
    return SftSecurityQuantity(_id(n), Decimal(q), SftSecurityQuantityBasisCode(basis))


def _fixed(v: str = "0.03", dc: str = "act-360") -> SftRateTerms:
    return SftRateTerms(SftRateKind.FIXED, Decimal(v), DayCountConventionCode(dc))


def _floating(v: str = "0.001", dc: str = "act-360", ref: int = 500) -> SftRateTerms:
    return SftRateTerms(SftRateKind.FLOATING, Decimal(v), DayCountConventionCode(dc), _id(ref))


def _tenor(v: int = 1, unit: FinancialTenorUnit = FinancialTenorUnit.MONTH) -> FinancialTenor:
    return FinancialTenor(v, unit)


def _fixed_leg(
    *,
    rate: str = "0.0025",
    currency: int = 303,
    basis: str = "principal-market-value",
    payment_mode: SftCompensationPaymentMode = SftCompensationPaymentMode.PERIODIC,
    payment_tenor: FinancialTenor | None = None,
    payment_ref: SftScheduleReferenceId | None = None,
) -> SecuritiesLendingCompensationLegTerms:
    if payment_mode is SftCompensationPaymentMode.PERIODIC and payment_tenor is None:
        payment_tenor = _tenor()
    return SecuritiesLendingCompensationLegTerms(
        rate=_fixed(rate),
        currency_identity_id=_id(currency),
        accrual_basis=SftCompensationAccrualBasisCode(basis),
        payment_mode=payment_mode,
        payment_tenor=payment_tenor,
        payment_schedule_reference=payment_ref,
    )


def _floating_leg(
    *,
    rate: str = "-0.001",
    currency: int = 301,
    basis: str = "cash-collateral",
    payment_mode: SftCompensationPaymentMode = SftCompensationPaymentMode.PERIODIC,
    payment_tenor: FinancialTenor | None = None,
    payment_ref: SftScheduleReferenceId | None = None,
    reset_mode: SftCompensationResetMode = SftCompensationResetMode.PERIODIC,
    reset_tenor: FinancialTenor | None = None,
    reset_ref: SftScheduleReferenceId | None = None,
) -> SecuritiesLendingCompensationLegTerms:
    if payment_mode is SftCompensationPaymentMode.PERIODIC and payment_tenor is None:
        payment_tenor = _tenor()
    if reset_mode is SftCompensationResetMode.PERIODIC and reset_tenor is None:
        reset_tenor = _tenor(1, FinancialTenorUnit.DAY)
    return SecuritiesLendingCompensationLegTerms(
        rate=_floating(rate),
        currency_identity_id=_id(currency),
        accrual_basis=SftCompensationAccrualBasisCode(basis),
        payment_mode=payment_mode,
        payment_tenor=payment_tenor,
        payment_schedule_reference=payment_ref,
        reset_mode=reset_mode,
        reset_tenor=reset_tenor,
        reset_schedule_reference=reset_ref,
    )


def _term() -> SftDurationTerms:
    return SftDurationTerms(SftDurationMode.TERM, date(2026, 1, 2), date(2026, 2, 2))


def _open() -> SftDurationTerms:
    return SftDurationTerms(SftDurationMode.OPEN, date(2026, 1, 2), notice_days=1)


def _callable(end: bool = True) -> SftDurationTerms:
    return SftDurationTerms(
        SftDurationMode.CALLABLE,
        date(2026, 1, 2),
        date(2026, 6, 2) if end else None,
        2,
    )


def _bilateral() -> SftArrangementTerms:
    return SftArrangementTerms(SftArrangementMode.BILATERAL)


def _tri() -> SftArrangementTerms:
    return SftArrangementTerms(SftArrangementMode.TRI_PARTY, _party(50))


def _repo() -> RepoTerms:
    return RepoTerms(
        terms_id=_terms(101),
        instrument_identity_id=_id(10),
        seller_reference_id=_party(1),
        buyer_reference_id=_party(2),
        duration=_term(),
        near_cash=_cash(),
        transferred_securities=(_security(402, "50"), _security(401)),
        financing_rate=_fixed(),
        arrangement=_bilateral(),
        evidence_ref=_evidence(201),
        far_leg=RepoFarLegTerms(date(2026, 2, 2), _cash("1002500")),
        margin_terms=SftMarginTerms(haircut_ratio=Decimal("0.02")),
    )


def _loan() -> SecuritiesLendingTerms:
    return SecuritiesLendingTerms(
        terms_id=_terms(102),
        instrument_identity_id=_id(20),
        lender_reference_id=_party(3),
        borrower_reference_id=_party(4),
        duration=_open(),
        principal_security=_security(410, "250"),
        compensation=SecuritiesLendingCompensationTerms(
            lending_fee=_fixed_leg(),
            cash_collateral_rebate=_floating_leg(),
        ),
        collateral=(_security(411, "75"), _cash("500000", 301)),
        arrangement=_tri(),
        evidence_ref=_evidence(202),
        collateralization_mode=SftCollateralizationMode.EXPLICIT,
        margin_terms=SftMarginTerms(initial_margin_ratio=Decimal("1.05")),
    )


def _margin_loan() -> MarginLendingTerms:
    return MarginLendingTerms(
        terms_id=_terms(103),
        instrument_identity_id=_id(30),
        lender_reference_id=_party(5),
        borrower_reference_id=_party(6),
        duration=_callable(),
        credit_limit=_cash("2500000", 302),
        financing_rate=_floating("0.015"),
        financing_payment_mode=SftFinancingPaymentMode.PERIODIC,
        collateral_eligibility=SftCollateralEligibilityCode("prime-broker-approved"),
        eligible_collateral_identity_ids=(_id(421), _id(420)),
        arrangement=_bilateral(),
        evidence_ref=_evidence(203),
        financing_payment_tenor=_tenor(),
        financing_reset_mode=SftFinancingResetMode.PERIODIC,
        financing_reset_tenor=_tenor(),
        financing_fixing_timing=SftFinancingFixingTiming.IN_ADVANCE,
        financing_calculation=SftFinancingCalculationCode("daily-simple"),
        financing_observation_mode=SftFinancingObservationMode.NONE,
        margin_terms=SftMarginTerms(haircut_ratio=Decimal("0.25")),
    )


class _BadDecimal(Decimal):
    pass


class _BadUUID(UUID):
    pass


class _IdentitySubclass(EconomicIdentityId):
    __slots__ = ()


class _DayCountSubclass(DayCountConventionCode):
    __slots__ = ()


class _TenorSubclass(FinancialTenor):
    __slots__ = ()


class _CashSubclass(SftCashAmount):
    __slots__ = ()


class _DurationSubclass(SftDurationTerms):
    __slots__ = ()


def _bad_identity() -> EconomicIdentityId:
    return EconomicIdentityId(cast(Any, _BadUUID(int=99)))


def _malformed(cls: type[Any], **attrs: object) -> Any:
    value = object.__new__(cls)
    for name, attr in attrs.items():
        object.__setattr__(value, name, attr)
    return value


def test_id_and_code_values() -> None:
    ids = (_terms(1), _evidence(2), _party(3), _schedule(4))
    assert [x.logical_values() for x in ids] == [
        (str(_uuid(1)),), (str(_uuid(2)),), (str(_uuid(3)),), (str(_uuid(4)),)
    ]
    for id_cls in (
        SftTermsId,
        SftEvidenceRef,
        SftPartyReferenceId,
        SftScheduleReferenceId,
    ):
        with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
            id_cls(cast(Any, "bad"))
    for code_cls in (
        SftCollateralEligibilityCode,
        SftSecurityQuantityBasisCode,
        SftCompensationAccrualBasisCode,
        SftFinancingCalculationCode,
    ):
        assert code_cls("valid-code").logical_values() == ("valid-code",)
        for bad in ("", "UPPER", "bad code", "a" * 65, 1, True):
            with pytest.raises(SecuritiesFinancingValidationError):
                code_cls(cast(Any, bad))


def test_cash_and_security_validation_and_decimal_canonicalization() -> None:
    assert _cash("1000.00").logical_values()[0] == "1000"
    assert _security(400, "12.500").logical_values()[-2:] == ("12.5", ("units",))
    assert _security(400, "100", "units").logical_values() != _security(
        400, "100", "nominal-amount"
    ).logical_values()
    for bad in ("0", "-1", "NaN", "Infinity"):
        with pytest.raises(SecuritiesFinancingValidationError):
            SftCashAmount(Decimal(bad), _id(300))
        with pytest.raises(SecuritiesFinancingValidationError):
            SftSecurityQuantity(_id(400), Decimal(bad), SftSecurityQuantityBasisCode("units"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact Decimal"):
        SftCashAmount(cast(Any, _BadDecimal("1")), _id(300))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact EconomicIdentityId"):
        SftCashAmount(Decimal("1"), cast(Any, _IdentitySubclass(_uuid(300))))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        SftCashAmount(Decimal("1"), _bad_identity())
    with pytest.raises(
        SecuritiesFinancingValidationError,
        match="exact SftSecurityQuantityBasisCode",
    ):
        SftSecurityQuantity(_id(400), Decimal("1"), cast(Any, "units"))
    bad_basis = _malformed(SftSecurityQuantityBasisCode, value="INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        SftSecurityQuantity(_id(400), Decimal("1"), bad_basis)
    with localcontext() as ctx:
        ctx.prec = 2
        assert _cash("1.2300").logical_values()[0] == "1.23"
        assert _cash("0.00100").logical_values()[0] == "0.001"
        assert _cash("1E+20").logical_values()[0] == "1e+20"
        assert _cash("1E-20").logical_values()[0] == "1e-20"
        assert _cash("1E+1000000").logical_values()[0] == "1e+1000000"
        assert _cash("1E-1000000").logical_values()[0] == "1e-1000000"
    assert SftMarginTerms(haircut_ratio=Decimal("-0")).logical_values()[1] == "0"


def test_rate_contracts() -> None:
    assert _fixed("-0.001").logical_values() == ("fixed", "-0.001", ("act-360",), None)
    assert _floating().logical_values()[-1] == (str(_uuid(500)),)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftRateKind"):
        SftRateTerms(cast(Any, "fixed"), Decimal("0.1"), DayCountConventionCode("act-360"))
    with pytest.raises(SecuritiesFinancingValidationError, match="finite exact Decimal"):
        SftRateTerms(SftRateKind.FIXED, cast(Any, 1.0), DayCountConventionCode("act-360"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact DayCountConventionCode"):
        SftRateTerms(SftRateKind.FIXED, Decimal("0.1"), _DayCountSubclass("act-360"))
    bad_dc = _malformed(DayCountConventionCode, value="INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        SftRateTerms(SftRateKind.FIXED, Decimal("0.1"), bad_dc)
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        SftRateTerms(SftRateKind.FIXED, Decimal("0.1"), DayCountConventionCode("act-360"), _id(500))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires reference"):
        SftRateTerms(SftRateKind.FLOATING, Decimal("0.1"), DayCountConventionCode("act-360"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact EconomicIdentityId"):
        SftRateTerms(
            SftRateKind.FLOATING,
            Decimal("0.1"),
            DayCountConventionCode("act-360"),
            cast(Any, _IdentitySubclass(_uuid(500))),
        )


def test_duration_arrangement_margin_and_far_leg() -> None:
    assert _term().logical_values() == ("term", "2026-01-02", "2026-02-02", None)
    assert _open().logical_values() == ("open", "2026-01-02", None, 1)
    assert _callable().logical_values() == ("callable", "2026-01-02", "2026-06-02", 2)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftDurationMode"):
        SftDurationTerms(cast(Any, "open"), date(2026, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact date"):
        SftDurationTerms(SftDurationMode.OPEN, cast(Any, "bad"))
    with pytest.raises(SecuritiesFinancingValidationError, match="after start"):
        SftDurationTerms(SftDurationMode.TERM, date(2026, 2, 1), date(2026, 1, 1))
    for notice in (0, -1, True, 1.2, "2"):
        with pytest.raises(SecuritiesFinancingValidationError, match="notice_days"):
            SftDurationTerms(SftDurationMode.OPEN, date(2026, 1, 1), notice_days=cast(Any, notice))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires termination"):
        SftDurationTerms(SftDurationMode.TERM, date(2026, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires termination"):
        SftDurationTerms(SftDurationMode.TERM, date(2026, 1, 1), date(2026, 2, 1), 1)
    with pytest.raises(SecuritiesFinancingValidationError, match="must not invent"):
        SftDurationTerms(SftDurationMode.OPEN, date(2026, 1, 1), date(2026, 2, 1))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires positive"):
        SftDurationTerms(SftDurationMode.CALLABLE, date(2026, 1, 1))

    assert _bilateral().logical_values() == ("bilateral", None)
    assert _tri().logical_values()[0] == "tri-party"
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftArrangementMode"):
        SftArrangementTerms(cast(Any, "bilateral"))
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        SftArrangementTerms(SftArrangementMode.BILATERAL, _party(1))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires agent"):
        SftArrangementTerms(SftArrangementMode.TRI_PARTY)
    bad_party = _malformed(SftPartyReferenceId, value=cast(Any, _BadUUID(int=1)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        SftArrangementTerms(SftArrangementMode.TRI_PARTY, bad_party)

    value = SftMarginTerms(
        initial_margin_ratio=Decimal("1.05"),
        haircut_ratio=Decimal("0.02"),
    )
    assert value.logical_values() == ("1.05", "0.02")
    with pytest.raises(SecuritiesFinancingValidationError):
        SftMarginTerms()
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        SftMarginTerms(initial_margin_ratio=Decimal("-0.1"))
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        SftMarginTerms(haircut_ratio=Decimal("-0.1"))

    assert RepoFarLegTerms(date(2026, 2, 1)).logical_values() == ("2026-02-01", None)
    assert RepoFarLegTerms(date(2026, 2, 1), _cash("1010")).logical_values()[1] is not None
    with pytest.raises(SecuritiesFinancingValidationError, match="exact date"):
        RepoFarLegTerms(cast(Any, "bad"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftCashAmount"):
        RepoFarLegTerms(date(2026, 2, 1), cast(Any, Decimal("1")))


def test_compensation_payment_modes_and_references() -> None:
    periodic = _fixed_leg()
    at_end = _fixed_leg(payment_mode=SftCompensationPaymentMode.AT_TERMINATION)
    external = _fixed_leg(
        payment_mode=SftCompensationPaymentMode.EXTERNAL_SCHEDULE,
        payment_ref=_schedule(701),
    )
    assert periodic.logical_values()[3] == ("periodic", (1, "month"), None)
    assert at_end.logical_values()[3] == ("at-termination", None, None)
    assert external.logical_values()[3] == ("external-schedule", None, (str(_uuid(701)),))
    assert len({periodic.logical_values(), at_end.logical_values(), external.logical_values()}) == 3

    with pytest.raises(SecuritiesFinancingValidationError, match="exact payment mode"):
        SecuritiesLendingCompensationLegTerms(
            _fixed(), _id(303), SftCompensationAccrualBasisCode("principal-market-value")
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires tenor"):
        SecuritiesLendingCompensationLegTerms(
            rate=_fixed(),
            currency_identity_id=_id(303),
            accrual_basis=SftCompensationAccrualBasisCode("principal-market-value"),
            payment_mode=SftCompensationPaymentMode.PERIODIC,
            payment_tenor=None,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="no schedule ref"):
        _fixed_leg(payment_ref=_schedule(1))
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        _fixed_leg(
            payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
            payment_tenor=_tenor(),
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule ref"):
        _fixed_leg(payment_mode=SftCompensationPaymentMode.EXTERNAL_SCHEDULE)
    with pytest.raises(SecuritiesFinancingValidationError, match="no tenor"):
        _fixed_leg(
            payment_mode=SftCompensationPaymentMode.EXTERNAL_SCHEDULE,
            payment_tenor=_tenor(),
            payment_ref=_schedule(2),
        )
    bad_ref = _malformed(SftScheduleReferenceId, value=cast(Any, _BadUUID(int=2)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        _fixed_leg(
            payment_mode=SftCompensationPaymentMode.EXTERNAL_SCHEDULE,
            payment_ref=bad_ref,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenor"):
        _fixed_leg(payment_tenor=cast(Any, "monthly"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenor"):
        _fixed_leg(payment_tenor=_TenorSubclass(1, FinancialTenorUnit.MONTH))
    bad_tenor = _malformed(FinancialTenor, value=0, unit=FinancialTenorUnit.MONTH)
    with pytest.raises(SecuritiesFinancingValidationError, match="positive int"):
        _fixed_leg(payment_tenor=bad_tenor)
    bad_unit = _malformed(FinancialTenor, value=1, unit=cast(Any, "month"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenorUnit"):
        _fixed_leg(payment_tenor=bad_unit)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftScheduleReferenceId"):
        SecuritiesLendingCompensationLegTerms(
            rate=_fixed(),
            currency_identity_id=_id(303),
            accrual_basis=SftCompensationAccrualBasisCode("principal-market-value"),
            payment_mode=SftCompensationPaymentMode.EXTERNAL_SCHEDULE,
            payment_schedule_reference=cast(Any, _uuid(1)),
        )


def test_compensation_reset_modes_and_fixed_boundary() -> None:
    periodic = _floating_leg()
    at_payment = _floating_leg(reset_mode=SftCompensationResetMode.AT_PAYMENT, reset_tenor=None)
    external = _floating_leg(
        reset_mode=SftCompensationResetMode.EXTERNAL_SCHEDULE,
        reset_tenor=None,
        reset_ref=_schedule(702),
    )
    reference = _floating_leg(
        reset_mode=SftCompensationResetMode.REFERENCE_CONVENTION,
        reset_tenor=None,
    )
    assert periodic.logical_values()[4] == ("periodic", (1, "day"), None)
    assert at_payment.logical_values()[4] == ("at-payment", None, None)
    assert external.logical_values()[4] == ("external-schedule", None, (str(_uuid(702)),))
    assert reference.logical_values()[4] == ("reference-convention", None, None)
    assert len({x.logical_values() for x in (periodic, at_payment, external, reference)}) == 4

    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry reset timing"):
        _fixed_leg().__class__(
            rate=_fixed(),
            currency_identity_id=_id(303),
            accrual_basis=SftCompensationAccrualBasisCode("principal-market-value"),
            payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
            reset_mode=SftCompensationResetMode.AT_PAYMENT,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires exact reset mode"):
        SecuritiesLendingCompensationLegTerms(
            rate=_floating(),
            currency_identity_id=_id(301),
            accrual_basis=SftCompensationAccrualBasisCode("cash-collateral"),
            payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires tenor"):
        SecuritiesLendingCompensationLegTerms(
            rate=_floating(),
            currency_identity_id=_id(301),
            accrual_basis=SftCompensationAccrualBasisCode("cash-collateral"),
            payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
            reset_mode=SftCompensationResetMode.PERIODIC,
            reset_tenor=None,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="no schedule ref"):
        _floating_leg(reset_ref=_schedule(2))
    for mode in (
        SftCompensationResetMode.AT_PAYMENT,
        SftCompensationResetMode.REFERENCE_CONVENTION,
    ):
        with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
            _floating_leg(reset_mode=mode, reset_tenor=_tenor())
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule ref"):
        _floating_leg(reset_mode=SftCompensationResetMode.EXTERNAL_SCHEDULE, reset_tenor=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="no tenor"):
        _floating_leg(
            reset_mode=SftCompensationResetMode.EXTERNAL_SCHEDULE,
            reset_tenor=_tenor(),
            reset_ref=_schedule(2),
        )
    bad_ref = _malformed(SftScheduleReferenceId, value=cast(Any, _BadUUID(int=2)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        _floating_leg(
            reset_mode=SftCompensationResetMode.EXTERNAL_SCHEDULE,
            reset_tenor=None,
            reset_ref=bad_ref,
        )


def test_compensation_container_and_material_noncollapse() -> None:
    fee = _fixed_leg(rate="0.01")
    rebate = _fixed_leg(rate="-0.002", currency=301, basis="cash-collateral")
    c = SecuritiesLendingCompensationTerms(fee, rebate)
    assert c.logical_values() == (fee.logical_values(), rebate.logical_values())
    assert SecuritiesLendingCompensationTerms(lending_fee=fee).logical_values() == (
        fee.logical_values(),
        None,
    )
    assert SecuritiesLendingCompensationTerms(
        cash_collateral_rebate=rebate
    ).logical_values() == (None, rebate.logical_values())
    with pytest.raises(SecuritiesFinancingValidationError, match="requires fee or rebate"):
        SecuritiesLendingCompensationTerms()
    with pytest.raises(
        SecuritiesFinancingValidationError,
        match="exact SecuritiesLendingCompensationLegTerms",
    ):
        SecuritiesLendingCompensationTerms(lending_fee=cast(Any, Decimal("0.1")))
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        SecuritiesLendingCompensationTerms(lending_fee=_fixed_leg(rate="-0.01"))

    base = _fixed_leg(rate="0.002")
    variants = (
        replace(base, rate=_fixed("0.002", "30-360")),
        replace(base, accrual_basis=SftCompensationAccrualBasisCode("original-principal")),
        replace(base, currency_identity_id=_id(304)),
        replace(base, payment_tenor=_tenor(3)),
        _fixed_leg(rate="0.002", payment_mode=SftCompensationPaymentMode.AT_TERMINATION),
        _fixed_leg(
            rate="0.002",
            payment_mode=SftCompensationPaymentMode.EXTERNAL_SCHEDULE,
            payment_ref=_schedule(703),
        ),
    )
    assert len({base.logical_values(), *(x.logical_values() for x in variants)}) == 7
    assert _floating_leg().logical_values() != replace(
        _floating_leg(), rate=_floating("-0.001", ref=501)
    ).logical_values()

    with pytest.raises(
        SecuritiesFinancingValidationError,
        match="exact SftCompensationAccrualBasisCode",
    ):
        SecuritiesLendingCompensationLegTerms(
            _fixed(), _id(303), cast(Any, "principal-market-value"),
            payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
        )
    bad_basis = _malformed(SftCompensationAccrualBasisCode, value="INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        SecuritiesLendingCompensationLegTerms(
            _fixed(), _id(303), bad_basis,
            payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
        )


def test_repo_semantics_and_fail_closed_matrix() -> None:
    repo = _repo()
    assert repo.transferred_securities[0].security_identity_id.value == _uuid(401)
    reversed_repo = replace(
        repo,
        transferred_securities=tuple(reversed(repo.transferred_securities)),
    )
    assert reversed_repo.logical_values() == repo.logical_values()
    with pytest.raises(SecuritiesFinancingValidationError, match="non-empty"):
        replace(repo, transferred_securities=())
    with pytest.raises(SecuritiesFinancingValidationError, match="duplicate"):
        replace(repo, transferred_securities=(_security(401, "1"), _security(401, "2")))
    with pytest.raises(SecuritiesFinancingValidationError, match="must not equal"):
        replace(repo, instrument_identity_id=_id(401))
    with pytest.raises(SecuritiesFinancingValidationError, match="term repo requires"):
        replace(repo, far_leg=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="far date"):
        replace(repo, far_leg=RepoFarLegTerms(date(2026, 2, 3)))
    opened = replace(repo, duration=_open(), far_leg=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="must not invent"):
        replace(opened, far_leg=RepoFarLegTerms(date(2026, 2, 2)))
    callable_no_end = replace(repo, duration=_callable(False), far_leg=None)
    with pytest.raises(
        SecuritiesFinancingValidationError,
        match="requires contractual termination",
    ):
        replace(callable_no_end, far_leg=RepoFarLegTerms(date(2026, 2, 2)))
    callable_end = replace(repo, duration=_callable(True), far_leg=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="far date"):
        replace(callable_end, far_leg=RepoFarLegTerms(date(2026, 6, 3)))
    assert replace(callable_end, far_leg=RepoFarLegTerms(date(2026, 6, 2))).far_leg is not None
    with pytest.raises(SecuritiesFinancingValidationError, match="currencies must match"):
        replace(repo, far_leg=RepoFarLegTerms(date(2026, 2, 2), _cash("1", 999)))
    with pytest.raises(SecuritiesFinancingValidationError, match="must differ"):
        replace(repo, buyer_reference_id=repo.seller_reference_id)

    bad_cash = _malformed(SftCashAmount, amount=Decimal("0"), currency_identity_id=_id(300))
    with pytest.raises(SecuritiesFinancingValidationError, match="positive"):
        replace(repo, near_cash=bad_cash)
    bad_duration = _malformed(
        SftDurationTerms,
        mode=SftDurationMode.TERM,
        start_date=date(2026, 2, 2),
        termination_date=date(2026, 1, 2),
        notice_days=None,
    )
    with pytest.raises(SecuritiesFinancingValidationError, match="after start"):
        replace(repo, duration=bad_duration)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftCashAmount"):
        replace(repo, near_cash=_CashSubclass(Decimal("1"), _id(300)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftDurationTerms"):
        replace(
            repo,
            duration=_DurationSubclass(
                SftDurationMode.TERM,
                date(2026, 1, 2),
                date(2026, 2, 2),
            ),
        )

    invalid: tuple[dict[str, object], ...] = (
        {"terms_id": _uuid(1)}, {"seller_reference_id": _uuid(1)}, {"buyer_reference_id": _uuid(2)},
        {"transferred_securities": (cast(Any, "bad"),)}, {"financing_rate": Decimal("0.1")},
        {"arrangement": "bilateral"}, {"evidence_ref": _uuid(1)}, {"margin_terms": Decimal("0.1")},
        {"far_leg": date(2026, 2, 2)},
    )
    for changes in invalid:
        with pytest.raises(SecuritiesFinancingValidationError):
            replace(repo, **cast(Any, changes))


def test_securities_lending_collateralization_modes_close_empty_collision() -> None:
    loan = _loan()
    assert loan.collateralization_mode is SftCollateralizationMode.EXPLICIT
    assert loan.collateral[0] == _cash("500000", 301)
    reversed_loan = replace(loan, collateral=tuple(reversed(loan.collateral)))
    assert reversed_loan.logical_values() == loan.logical_values()

    with pytest.raises(SecuritiesFinancingValidationError, match="non-empty"):
        replace(loan, collateral=())
    unsecured = replace(
        loan,
        collateral=(),
        collateralization_mode=SftCollateralizationMode.UNCOLLATERALIZED,
    )
    external = replace(
        loan,
        collateral=(),
        collateralization_mode=SftCollateralizationMode.EXTERNAL_SCHEDULE,
        collateral_schedule_reference=_schedule(710),
    )
    assert unsecured.logical_values() != external.logical_values()
    assert unsecured.logical_values()[8] == ("uncollateralized", None)
    assert external.logical_values()[8] == ("external-schedule", (str(_uuid(710)),))

    with pytest.raises(SecuritiesFinancingValidationError, match="exact mode"):
        replace(loan, collateralization_mode=cast(Any, "explicit"))
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        replace(
            loan,
            collateralization_mode=SftCollateralizationMode.UNCOLLATERALIZED,
            collateral_schedule_reference=_schedule(1),
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        replace(loan, collateralization_mode=SftCollateralizationMode.UNCOLLATERALIZED)
    with pytest.raises(SecuritiesFinancingValidationError, match="non-empty"):
        replace(
            loan,
            collateral=(),
            collateralization_mode=SftCollateralizationMode.EXPLICIT,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="non-empty"):
        replace(
            loan,
            collateralization_mode=SftCollateralizationMode.EXPLICIT,
            collateral_schedule_reference=_schedule(1),
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule reference"):
        replace(
            loan,
            collateral=(),
            collateralization_mode=SftCollateralizationMode.EXTERNAL_SCHEDULE,
            collateral_schedule_reference=None,
        )
    bad_ref = _malformed(SftScheduleReferenceId, value=cast(Any, _BadUUID(int=10)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        replace(
            loan,
            collateralization_mode=SftCollateralizationMode.EXTERNAL_SCHEDULE,
            collateral_schedule_reference=bad_ref,
        )
    assert replace(
        loan,
        collateralization_mode=SftCollateralizationMode.EXTERNAL_SCHEDULE,
        collateral_schedule_reference=_schedule(711),
    ).collateral


def test_securities_lending_collateral_container_and_parent_guards() -> None:
    loan = _loan()
    with pytest.raises(SecuritiesFinancingValidationError, match="duplicate"):
        replace(loan, collateral=(_cash("1", 301), _cash("2", 301)))
    with pytest.raises(SecuritiesFinancingValidationError, match="duplicate"):
        replace(loan, collateral=(_security(411, "1"), _security(411, "2")))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact tuple"):
        replace(loan, collateral=cast(Any, [_cash("1", 301)]))
    with pytest.raises(SecuritiesFinancingValidationError, match="unsupported"):
        replace(loan, collateral=cast(Any, ("bad",)))
    with pytest.raises(SecuritiesFinancingValidationError, match="unsupported"):
        s._collateral_key(cast(Any, object()))
    with pytest.raises(SecuritiesFinancingValidationError, match="must differ"):
        replace(loan, instrument_identity_id=loan.principal_security.security_identity_id)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact"):
        replace(loan, compensation=cast(Any, Decimal("0.1")))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftSecurityQuantity"):
        replace(loan, principal_security=cast(Any, _id(410)))

    bad_leg = _malformed(
        SecuritiesLendingCompensationLegTerms,
        rate=_fixed("-1"), currency_identity_id=_id(303),
        accrual_basis=SftCompensationAccrualBasisCode("principal-market-value"),
        payment_mode=SftCompensationPaymentMode.AT_TERMINATION,
        payment_tenor=None, payment_schedule_reference=None,
        reset_mode=None, reset_tenor=None, reset_schedule_reference=None,
    )
    bad_comp = _malformed(
        SecuritiesLendingCompensationTerms,
        lending_fee=bad_leg,
        cash_collateral_rebate=None,
    )
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        replace(loan, compensation=bad_comp)


def test_margin_lending_financing_payment_modes_close_r3_collision() -> None:
    periodic = _margin_loan()
    at_end = replace(
        periodic,
        financing_payment_mode=SftFinancingPaymentMode.AT_TERMINATION,
        financing_payment_tenor=None,
    )
    external = replace(
        periodic,
        financing_payment_mode=SftFinancingPaymentMode.EXTERNAL_SCHEDULE,
        financing_payment_tenor=None,
        financing_payment_schedule_reference=_schedule(720),
    )

    assert periodic.logical_values()[8] == ("periodic", (1, "month"), None)
    assert at_end.logical_values()[8] == ("at-termination", None, None)
    assert external.logical_values()[8] == (
        "external-schedule",
        None,
        (str(_uuid(720)),),
    )
    assert len(
        {periodic.logical_values(), at_end.logical_values(), external.logical_values()}
    ) == 3

    with pytest.raises(SecuritiesFinancingValidationError, match="requires exact mode"):
        replace(periodic, financing_payment_mode=cast(Any, "periodic"))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires tenor only"):
        replace(periodic, financing_payment_tenor=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="requires tenor only"):
        replace(periodic, financing_payment_schedule_reference=_schedule(721))
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        replace(at_end, financing_payment_tenor=_tenor())
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
        replace(at_end, financing_payment_schedule_reference=_schedule(722))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule ref only"):
        replace(
            periodic,
            financing_payment_mode=SftFinancingPaymentMode.EXTERNAL_SCHEDULE,
            financing_payment_tenor=None,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule ref only"):
        replace(external, financing_payment_tenor=_tenor())
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftScheduleReferenceId"):
        replace(
            periodic,
            financing_payment_mode=SftFinancingPaymentMode.EXTERNAL_SCHEDULE,
            financing_payment_tenor=None,
            financing_payment_schedule_reference=cast(Any, _uuid(723)),
        )
    bad_ref = _malformed(SftScheduleReferenceId, value=cast(Any, _BadUUID(int=724)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        replace(
            periodic,
            financing_payment_mode=SftFinancingPaymentMode.EXTERNAL_SCHEDULE,
            financing_payment_tenor=None,
            financing_payment_schedule_reference=bad_ref,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenor"):
        replace(periodic, financing_payment_tenor=cast(Any, "monthly"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenor"):
        replace(periodic, financing_payment_tenor=_TenorSubclass(1, FinancialTenorUnit.MONTH))
    bad_tenor = _malformed(FinancialTenor, value=0, unit=FinancialTenorUnit.MONTH)
    with pytest.raises(SecuritiesFinancingValidationError, match="positive int"):
        replace(periodic, financing_payment_tenor=bad_tenor)
    bad_unit = _malformed(FinancialTenor, value=1, unit=cast(Any, "month"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenorUnit"):
        replace(periodic, financing_payment_tenor=bad_unit)


def test_margin_lending_financing_reset_fixing_and_calculation_noncollapse() -> None:
    periodic_advance = _margin_loan()
    periodic_arrears = replace(
        periodic_advance,
        financing_fixing_timing=SftFinancingFixingTiming.IN_ARREARS,
    )
    periodic_reference = replace(
        periodic_advance,
        financing_fixing_timing=SftFinancingFixingTiming.REFERENCE_CONVENTION,
    )
    compounded = replace(
        periodic_advance,
        financing_calculation=SftFinancingCalculationCode("daily-compounded"),
    )
    observation_reference = replace(
        periodic_advance,
        financing_observation_mode=SftFinancingObservationMode.REFERENCE_CONVENTION,
    )
    observation_external = replace(
        periodic_advance,
        financing_observation_mode=SftFinancingObservationMode.EXTERNAL_TERMS,
        financing_observation_reference=_schedule(740),
    )
    at_payment = replace(
        periodic_advance,
        financing_reset_mode=SftFinancingResetMode.AT_PAYMENT,
        financing_reset_tenor=None,
        financing_fixing_timing=None,
    )
    external = replace(
        periodic_advance,
        financing_reset_mode=SftFinancingResetMode.EXTERNAL_SCHEDULE,
        financing_reset_tenor=None,
        financing_reset_schedule_reference=_schedule(730),
        financing_fixing_timing=None,
    )
    reference = replace(
        periodic_advance,
        financing_reset_mode=SftFinancingResetMode.REFERENCE_CONVENTION,
        financing_reset_tenor=None,
        financing_fixing_timing=None,
    )

    assert periodic_advance.logical_values()[9] == (
        "periodic", (1, "month"), None, "in-advance", ("daily-simple",), ("none", None)
    )
    assert periodic_arrears.logical_values()[9][3] == "in-arrears"
    assert periodic_reference.logical_values()[9][3] == "reference-convention"
    assert compounded.logical_values()[9][4] == ("daily-compounded",)
    assert observation_reference.logical_values()[9][5] == ("reference-convention", None)
    assert observation_external.logical_values()[9][5] == (
        "external-terms", (str(_uuid(740)),)
    )
    assert at_payment.logical_values()[9][0:4] == ("at-payment", None, None, None)
    assert external.logical_values()[9][0:4] == (
        "external-schedule", None, (str(_uuid(730)),), None
    )
    assert reference.logical_values()[9][0:4] == (
        "reference-convention", None, None, None
    )
    variants = (
        periodic_advance,
        periodic_arrears,
        periodic_reference,
        compounded,
        observation_reference,
        observation_external,
        at_payment,
        external,
        reference,
    )
    assert len({item.logical_values() for item in variants}) == len(variants)


def test_margin_lending_financing_floating_convention_guards() -> None:
    periodic = _margin_loan()
    fixed = replace(
        periodic,
        financing_rate=_fixed("0.05"),
        financing_reset_mode=None,
        financing_reset_tenor=None,
        financing_fixing_timing=None,
        financing_calculation=None,
        financing_observation_mode=None,
    )
    assert fixed.logical_values()[9] is None

    with pytest.raises(SecuritiesFinancingValidationError, match="reset/fixing timing"):
        replace(fixed, financing_reset_mode=SftFinancingResetMode.AT_PAYMENT)
    with pytest.raises(SecuritiesFinancingValidationError, match="floating convention"):
        replace(fixed, financing_calculation=SftFinancingCalculationCode("daily-simple"))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires exact reset mode"):
        replace(
            periodic,
            financing_reset_mode=None,
            financing_reset_tenor=None,
            financing_fixing_timing=None,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires exact reset mode"):
        replace(periodic, financing_reset_mode=cast(Any, "periodic"))
    with pytest.raises(SecuritiesFinancingValidationError, match="requires tenor only"):
        replace(periodic, financing_reset_tenor=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="requires tenor only"):
        replace(periodic, financing_reset_schedule_reference=_schedule(731))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact fixing timing"):
        replace(periodic, financing_fixing_timing=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact fixing timing"):
        replace(periodic, financing_fixing_timing=cast(Any, "in-advance"))

    for mode in (
        SftFinancingResetMode.AT_PAYMENT,
        SftFinancingResetMode.REFERENCE_CONVENTION,
    ):
        with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
            replace(periodic, financing_reset_mode=mode, financing_reset_tenor=_tenor())
        with pytest.raises(SecuritiesFinancingValidationError, match="must not carry"):
            replace(
                periodic,
                financing_reset_mode=mode,
                financing_reset_tenor=None,
                financing_fixing_timing=SftFinancingFixingTiming.IN_ARREARS,
            )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule ref only"):
        replace(
            periodic,
            financing_reset_mode=SftFinancingResetMode.EXTERNAL_SCHEDULE,
            financing_reset_tenor=None,
            financing_fixing_timing=None,
        )
    external = replace(
        periodic,
        financing_reset_mode=SftFinancingResetMode.EXTERNAL_SCHEDULE,
        financing_reset_tenor=None,
        financing_reset_schedule_reference=_schedule(730),
        financing_fixing_timing=None,
    )
    with pytest.raises(SecuritiesFinancingValidationError, match="requires schedule ref only"):
        replace(external, financing_reset_tenor=_tenor())
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftScheduleReferenceId"):
        replace(
            periodic,
            financing_reset_mode=SftFinancingResetMode.EXTERNAL_SCHEDULE,
            financing_reset_tenor=None,
            financing_reset_schedule_reference=cast(Any, _uuid(733)),
            financing_fixing_timing=None,
        )
    bad_ref = _malformed(SftScheduleReferenceId, value=cast(Any, _BadUUID(int=734)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        replace(
            periodic,
            financing_reset_mode=SftFinancingResetMode.EXTERNAL_SCHEDULE,
            financing_reset_tenor=None,
            financing_reset_schedule_reference=bad_ref,
            financing_fixing_timing=None,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenor"):
        replace(periodic, financing_reset_tenor=cast(Any, "monthly"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenor"):
        replace(periodic, financing_reset_tenor=_TenorSubclass(1, FinancialTenorUnit.MONTH))
    bad_tenor = _malformed(FinancialTenor, value=0, unit=FinancialTenorUnit.MONTH)
    with pytest.raises(SecuritiesFinancingValidationError, match="positive int"):
        replace(periodic, financing_reset_tenor=bad_tenor)
    bad_unit = _malformed(FinancialTenor, value=1, unit=cast(Any, "month"))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact FinancialTenorUnit"):
        replace(periodic, financing_reset_tenor=bad_unit)

    with pytest.raises(SecuritiesFinancingValidationError, match="requires calculation code"):
        replace(periodic, financing_calculation=None)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact calculation code"):
        replace(periodic, financing_calculation=cast(Any, "daily-simple"))
    bad_calculation = _malformed(SftFinancingCalculationCode, value="INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        replace(periodic, financing_calculation=bad_calculation)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact observation mode"):
        replace(periodic, financing_observation_mode=cast(Any, "none"))
    with pytest.raises(SecuritiesFinancingValidationError, match="require reference"):
        replace(
            periodic,
            financing_observation_mode=SftFinancingObservationMode.EXTERNAL_TERMS,
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="must not carry reference"):
        replace(periodic, financing_observation_reference=_schedule(741))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftScheduleReferenceId"):
        replace(
            periodic,
            financing_observation_mode=SftFinancingObservationMode.EXTERNAL_TERMS,
            financing_observation_reference=cast(Any, _uuid(742)),
        )
    bad_observation_ref = _malformed(
        SftScheduleReferenceId,
        value=cast(Any, _BadUUID(int=743)),
    )
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        replace(
            periodic,
            financing_observation_mode=SftFinancingObservationMode.EXTERNAL_TERMS,
            financing_observation_reference=bad_observation_ref,
        )


def test_margin_lending_constraints() -> None:
    m = _margin_loan()
    assert tuple(x.value for x in m.eligible_collateral_identity_ids) == (_uuid(420), _uuid(421))
    assert replace(m, eligible_collateral_identity_ids=()).logical_values()[11] == ()
    with pytest.raises(SecuritiesFinancingValidationError, match="unique"):
        replace(m, eligible_collateral_identity_ids=(_id(420), _id(420)))
    with pytest.raises(SecuritiesFinancingValidationError, match="must not be eligible"):
        replace(m, eligible_collateral_identity_ids=(m.instrument_identity_id,))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact EconomicIdentityId"):
        replace(m, eligible_collateral_identity_ids=(cast(Any, _IdentitySubclass(_uuid(420))),))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact tuple"):
        replace(m, eligible_collateral_identity_ids=cast(Any, [_id(420)]))
    bad_code = _malformed(SftCollateralEligibilityCode, value="INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        replace(m, collateral_eligibility=bad_code)
    bad_margin = _malformed(
        SftMarginTerms,
        initial_margin_ratio=None,
        haircut_ratio=Decimal("-0.1"),
    )
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        replace(m, margin_terms=bad_margin)
    for changes in (
        {"collateral_eligibility": "approved"}, {"arrangement": "bilateral"},
        {"financing_rate": Decimal("0.1")}, {"margin_terms": Decimal("0.1")},
        {"evidence_ref": _uuid(203)},
    ):
        with pytest.raises(SecuritiesFinancingValidationError):
            replace(m, **cast(Any, changes))


def test_complete_logical_identity_oracles() -> None:
    repo = _repo()
    assert repo.logical_values()[0] == "repo"
    loan = _loan()
    lv = loan.logical_values()
    assert lv[0] == "securities-lending"
    compensation_values = loan.compensation.logical_values()
    fee_values = cast(tuple[object, ...], compensation_values[0])
    rebate_values = cast(tuple[object, ...], compensation_values[1])
    assert fee_values[3] == ("periodic", (1, "month"), None)
    assert rebate_values[4] == ("periodic", (1, "day"), None)
    assert lv[8] == ("explicit", None)
    assert lv[9] == (
        ("5e+5", (str(_uuid(301)),)),
        ((str(_uuid(411)),), "75", ("units",)),
    )
    margin = _margin_loan()
    assert margin.logical_values()[0] == "margin-lending"
    assert margin.logical_values()[8] == ("periodic", (1, "month"), None)
    assert margin.logical_values()[9] == (
        "periodic",
        (1, "month"),
        None,
        "in-advance",
        ("daily-simple",),
        ("none", None),
    )
    assert {repo.logical_values()[0], lv[0], margin.logical_values()[0]} == {
        "repo", "securities-lending", "margin-lending"
    }


def test_reflective_revalidation_and_frozen_slotted_values() -> None:
    cash = _cash("1")
    object.__setattr__(cash, "amount", Decimal("0"))
    with pytest.raises(SecuritiesFinancingValidationError, match="positive"):
        cash.logical_values()
    leg = _fixed_leg()
    object.__setattr__(leg.accrual_basis, "value", "INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        leg.logical_values()
    margin = _margin_loan()
    assert margin.financing_calculation is not None
    object.__setattr__(margin.financing_calculation, "value", "INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        margin.logical_values()
    repo = _repo()
    object.__setattr__(repo.duration, "termination_date", date(2025, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError, match="after start"):
        repo.logical_values()

    values: tuple[object, ...] = (
        _terms(), _evidence(), _party(1), _schedule(1),
        SftCollateralEligibilityCode("approved"), SftSecurityQuantityBasisCode("units"),
        SftCompensationAccrualBasisCode("principal-market-value"),
        SftFinancingCalculationCode("daily-simple"), _cash(), _security(),
        _fixed(), _term(), _bilateral(), SftMarginTerms(haircut_ratio=Decimal("0.1")),
        RepoFarLegTerms(date(2026, 2, 2)), _fixed_leg(), _floating_leg(),
        SecuritiesLendingCompensationTerms(lending_fee=_fixed_leg()),
        _repo(), _loan(), _margin_loan(),
    )
    assert all(not hasattr(v, "__dict__") for v in values)
    with pytest.raises(FrozenInstanceError):
        cast(Any, values[8]).amount = Decimal("2")


def test_top_level_negative_space_and_source_guards() -> None:
    forbidden_fields = {
        "current_margin", "current_collateral", "current_utilization", "available_credit",
        "margin_call", "position", "valuation", "provider_symbol", "settled",
    }
    for cls in (RepoTerms, SecuritiesLendingTerms, MarginLendingTerms):
        assert not {f.name for f in fields(cls)}.intersection(forbidden_fields)
    source_path = Path(s.__file__)
    source = source_path.read_text()
    assert "isinstance(" not in source
    assert ".normalize(" not in source
    assert "datetime.now(" not in source
    assert "date.today(" not in source
    assert "uuid4(" not in source
    assert "random." not in source
    assert "secrets." not in source
    tree = ast.parse(source)
    forbidden_imports = {
        "asyncio",
        "httpx",
        "numpy",
        "pandas",
        "requests",
        "socket",
        "subprocess",
        "threading",
    }
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported.intersection(forbidden_imports)
    forbidden_calls = {
        "calculate",
        "connect",
        "execute",
        "fetch",
        "liquidate",
        "recall",
        "settle",
        "submit",
        "transfer",
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not calls.intersection(forbidden_calls)
