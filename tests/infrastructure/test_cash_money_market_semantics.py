from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.cash_money_market_semantics as cmm
from qore.infrastructure.derivative_contract_semantics import (
    DerivativePriceQuoteBasisCode,
    DerivativeStrike,
    DerivativeStrikeBasis,
)
from qore.infrastructure.fixed_income_economics import (
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def eid(seed: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=seed))


def tid(seed: int = 1) -> cmm.CashMoneyMarketTermsId:
    return cmm.CashMoneyMarketTermsId(UUID(int=10_000 + seed))


def ev(seed: int = 1) -> cmm.CashMoneyMarketEvidenceRef:
    return cmm.CashMoneyMarketEvidenceRef(UUID(int=20_000 + seed))


def dc() -> DayCountConventionCode:
    return DayCountConventionCode("actual-360")


def pay(*values: date) -> cmm.CommercialPaperPaymentDateSchedule:
    return cmm.CommercialPaperPaymentDateSchedule(
        tuple(values or (date(2026, 4, 1), date(2026, 7, 1)))
    )


def reset(*values: date) -> cmm.CommercialPaperResetDateSchedule:
    return cmm.CommercialPaperResetDateSchedule(
        tuple(values or (date(2026, 2, 1), date(2026, 5, 1)))
    )


def cdreset(*values: date) -> cmm.CertificateOfDepositResetDateSchedule:
    return cmm.CertificateOfDepositResetDateSchedule(
        tuple(values or (date(2026, 3, 1), date(2026, 6, 1)))
    )


def replace_any(value: Any, **changes: Any) -> Any:
    return replace(value, **changes)


def dcd(
    orientation: cmm.DualCurrencyFxQuoteOrientation = (
        cmm.DualCurrencyFxQuoteOrientation.ALTERNATE_PER_PRINCIPAL
    ),
    *,
    base: int = 3,
    alternate: int = 4,
    fixing: int = 5,
    fixing_date: date = date(2026, 6, 15),
    quote_basis: str = "currency-per-unit",
    quote_seed: int | None = None,
    strike_value: str = "1.25",
    true_seed: int | None = None,
    false_seed: int | None = None,
) -> cmm.TermDepositDualCurrencyFeature:
    expected_quote = alternate if (
        orientation is cmm.DualCurrencyFxQuoteOrientation.ALTERNATE_PER_PRINCIPAL
    ) else base
    return cmm.TermDepositDualCurrencyFeature(
        base_currency_identity_id=eid(base),
        alternate_currency_identity_id=eid(alternate),
        fx_fixing_identity_id=eid(fixing),
        fixing_date=fixing_date,
        strike=DerivativeStrike(
            Decimal(strike_value),
            DerivativeStrikeBasis.PRICE,
            quote_identity_id=eid(expected_quote if quote_seed is None else quote_seed),
            price_quote_basis=DerivativePriceQuoteBasisCode(quote_basis),
        ),
        orientation=orientation,
        comparator=cmm.DualCurrencyTriggerComparator.GREATER_THAN_OR_EQUAL,
        true_payout_identity_id=eid(alternate if true_seed is None else true_seed),
        false_payout_identity_id=eid(base if false_seed is None else false_seed),
        evidence_ref=ev(2),
    )


def term(
    rate: str = "0.02",
    *,
    feature: cmm.TermDepositDualCurrencyFeature | None = None,
) -> cmm.TermDepositTerms:
    return cmm.TermDepositTerms(
        terms_id=tid(),
        instrument_identity_id=eid(1),
        deposit_obligor_identity_id=eid(2),
        principal=cmm.CashMoneyMarketDepositPrincipal(Decimal("100000")),
        denomination_currency_identity_id=eid(3),
        start_date=date(2026, 1, 1),
        maturity_date=date(2026, 12, 31),
        contractual_rate=cmm.CashMoneyMarketContractualRate(Decimal(rate)),
        day_count=dc(),
        evidence_ref=ev(),
        dual_currency_feature=feature,
    )


def fixed_cp() -> cmm.CommercialPaperFixedInterestTerms:
    return cmm.CommercialPaperFixedInterestTerms(
        cmm.CashMoneyMarketContractualRate(Decimal("0.03")),
        dc(),
        pay(),
    )


def floating_cp(**kwargs: Any) -> cmm.CommercialPaperFloatingInterestTerms:
    values: dict[str, object] = {
        "reference_identity_id": eid(14),
        "reset_dates": reset(),
        "payment_dates": pay(),
        "day_count": dc(),
    }
    values.update(kwargs)
    return cmm.CommercialPaperFloatingInterestTerms(**cast(Any, values))


def cp(
    pricing: cmm.CommercialPaperPricingTerms,
    interest: cmm.CommercialPaperInterestTerms,
) -> cmm.CommercialPaperTerms:
    return cmm.CommercialPaperTerms(
        terms_id=tid(11),
        instrument_identity_id=eid(11),
        issuer_obligor_identity_id=eid(12),
        denomination_currency_identity_id=eid(13),
        face_redemption_amount=cmm.CashMoneyMarketCommercialPaperFaceAmount(
            Decimal("1000")
        ),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2026, 12, 31),
        pricing=pricing,
        interest=interest,
        evidence_ref=ev(11),
    )


def fixed_cd() -> cmm.CertificateOfDepositFixedRateTerms:
    return cmm.CertificateOfDepositFixedRateTerms(
        cmm.CashMoneyMarketContractualRate(Decimal("-0.001")),
        dc(),
    )


def cd(
    return_terms: cmm.CertificateOfDepositReturnTerms,
    negotiability: cmm.CertificateOfDepositNegotiability = (
        cmm.CertificateOfDepositNegotiability.NEGOTIABLE
    ),
) -> cmm.CertificateOfDepositTerms:
    return cmm.CertificateOfDepositTerms(
        terms_id=tid(21),
        instrument_identity_id=eid(21),
        issuing_institution_identity_id=eid(22),
        denomination_currency_identity_id=eid(23),
        deposit_principal=cmm.CashMoneyMarketDepositPrincipal(Decimal("50000")),
        issue_start_date=date(2026, 1, 1),
        maturity_date=date(2026, 12, 31),
        negotiability=negotiability,
        return_terms=return_terms,
        evidence_ref=ev(21),
    )


def test_ids_numeric_values_and_enum_wire_values() -> None:
    assert tid().logical_values() == (str(UUID(int=10_001)),)
    assert ev().logical_values() == (str(UUID(int=20_001)),)
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cmm.CashMoneyMarketTermsId(cast(Any, "bad"))
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cmm.CashMoneyMarketEvidenceRef(cast(Any, "bad"))

    for text in ("1", "1.0", "1.00"):
        assert cmm.CashMoneyMarketContractualRate(Decimal(text)).logical_values() == (
            "1",
        )
    for text in ("0.00", "-0"):
        assert cmm.CashMoneyMarketContractualRate(Decimal(text)).logical_values() == (
            "0",
        )
    assert cmm.CashMoneyMarketContractualRate(Decimal("-0.01")).logical_values() == (
        "-0.01",
    )

    assert tuple(item.value for item in cmm.DualCurrencyFxQuoteOrientation) == (
        "alternate-per-principal",
        "principal-per-alternate",
    )
    assert tuple(item.value for item in cmm.DualCurrencyTriggerComparator) == (
        "less-than",
        "less-than-or-equal",
        "greater-than",
        "greater-than-or-equal",
    )
    assert tuple(item.value for item in cmm.CertificateOfDepositNegotiability) == (
        "negotiable",
        "non-negotiable",
    )


@pytest.mark.parametrize(
    "factory",
    [
        cmm.CashMoneyMarketDepositPrincipal,
        cmm.CashMoneyMarketCommercialPaperFaceAmount,
        cmm.CashMoneyMarketCommercialPaperIssuePrice,
        cmm.CashMoneyMarketContractualRate,
        cmm.CashMoneyMarketFloatingSpread,
        cmm.CashMoneyMarketFloatingMultiplier,
    ],
)
def test_numeric_objects_reject_bad_runtime_values(factory: type[Any]) -> None:
    for bad in (cast(Any, True), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            factory(bad)


@pytest.mark.parametrize(
    "factory",
    [
        cmm.CashMoneyMarketDepositPrincipal,
        cmm.CashMoneyMarketCommercialPaperFaceAmount,
        cmm.CashMoneyMarketCommercialPaperIssuePrice,
        cmm.CashMoneyMarketFloatingMultiplier,
    ],
)
def test_positive_numeric_objects_reject_non_positive(factory: type[Any]) -> None:
    for bad in (Decimal("0"), Decimal("-1")):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            factory(bad)


@pytest.mark.parametrize(
    "factory",
    [
        cmm.CommercialPaperPaymentDateSchedule,
        cmm.CommercialPaperResetDateSchedule,
        cmm.CertificateOfDepositResetDateSchedule,
    ],
)
def test_date_schedules_are_exact_unique_and_canonical(factory: type[Any]) -> None:
    early, late = date(2026, 4, 1), date(2026, 7, 1)
    schedule = factory((late, early))
    assert schedule.dates == (early, late)
    assert schedule.logical_values() == (("2026-04-01", "2026-07-01"),)
    for bad in (
        cast(Any, [early]),
        (),
        (early, early),
        (cast(Any, datetime(2026, 4, 1)),),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            factory(bad)


@pytest.mark.parametrize("orientation", list(cmm.DualCurrencyFxQuoteOrientation))
def test_dcd_orientation_binding_and_logical_material(
    orientation: cmm.DualCurrencyFxQuoteOrientation,
) -> None:
    feature = dcd(orientation)
    assert feature.strike.basis is DerivativeStrikeBasis.PRICE
    assert feature.strike.price_quote_basis == DerivativePriceQuoteBasisCode(
        "currency-per-unit"
    )
    assert feature.logical_values()[7] == feature.strike.logical_values()
    assert feature.logical_values()[-1] == feature.evidence_ref.logical_values()


@pytest.mark.parametrize("comparator", list(cmm.DualCurrencyTriggerComparator))
def test_all_dcd_comparators_are_representable(
    comparator: cmm.DualCurrencyTriggerComparator,
) -> None:
    base = dcd()
    feature = cmm.TermDepositDualCurrencyFeature(
        base.base_currency_identity_id,
        base.alternate_currency_identity_id,
        base.fx_fixing_identity_id,
        base.fixing_date,
        base.strike,
        base.orientation,
        comparator,
        base.true_payout_identity_id,
        base.false_payout_identity_id,
        base.evidence_ref,
    )
    assert feature.comparator is comparator


def test_dcd_and_parent_term_fail_closed() -> None:
    for kwargs in (
        {"alternate": 3},
        {"fixing": 3},
        {"quote_basis": "percent-of-par"},
        {"quote_seed": 3},
        {"strike_value": "0"},
        {"true_seed": 3, "false_seed": 3},
        {"true_seed": 4, "false_seed": 99},
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            dcd(**cast(Any, kwargs))

    assert term("-0.01").contractual_rate.logical_values() == ("-0.01",)
    assert term("0").contractual_rate.logical_values() == ("0",)
    assert term("0.01", feature=dcd()).dual_currency_feature is not None

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        term(feature=dcd(base=6))
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        term(feature=dcd(fixing_date=date(2025, 12, 31)))


def test_cp_cross_product_discount_and_neutral_floating_defaults() -> None:
    at_par = cmm.CommercialPaperAtParPricing()
    discounted = cmm.CommercialPaperDiscountedPricing(
        cmm.CashMoneyMarketCommercialPaperIssuePrice(Decimal("990"))
    )
    no_interest = cmm.CommercialPaperNoInterestTerms()
    fixed = fixed_cp()
    floating = floating_cp()

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cp(at_par, no_interest)
    for pricing, interest in (
        (discounted, no_interest),
        (at_par, fixed),
        (discounted, fixed),
        (at_par, floating),
        (discounted, floating),
    ):
        assert cp(pricing, interest).logical_values()[0] == "commercial-paper"

    explicit = floating_cp(
        spread=cmm.CashMoneyMarketFloatingSpread(Decimal("0.00")),
        multiplier=cmm.CashMoneyMarketFloatingMultiplier(Decimal("1.0")),
    )
    assert floating.spread == cmm.CashMoneyMarketFloatingSpread(Decimal("0"))
    assert floating.multiplier == cmm.CashMoneyMarketFloatingMultiplier(Decimal("1"))
    assert floating == explicit
    assert floating.logical_values() == explicit.logical_values()

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cp(
            cmm.CommercialPaperDiscountedPricing(
                cmm.CashMoneyMarketCommercialPaperIssuePrice(Decimal("1000"))
            ),
            no_interest,
        )


def test_cp_index_maturity_and_contract_interval_validation() -> None:
    tenor = FinancialTenor(3, FinancialTenorUnit.MONTH)
    assert floating_cp(index_maturity=None).logical_values()[2] is None
    assert floating_cp(index_maturity=tenor).logical_values()[2] == tenor.logical_values()
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        floating_cp(index_maturity=cast(Any, "3m"))

    for interest in (
        cmm.CommercialPaperFixedInterestTerms(
            cmm.CashMoneyMarketContractualRate(Decimal("0.01")),
            dc(),
            pay(date(2025, 12, 31)),
        ),
        floating_cp(reset_dates=reset(date(2027, 1, 1))),
        floating_cp(payment_dates=pay(date(2027, 1, 1))),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            cp(cmm.CommercialPaperAtParPricing(), interest)

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cp(
            cmm.CommercialPaperAtParPricing(),
            floating_cp(reference_identity_id=eid(11)),
        )


def test_cd_fixed_reference_and_preset_variants() -> None:
    assert cd(fixed_cd()).return_terms.logical_values()[0] == "fixed-rate"
    assert cd(
        fixed_cd(), cmm.CertificateOfDepositNegotiability.NON_NEGOTIABLE
    ).negotiability is cmm.CertificateOfDepositNegotiability.NON_NEGOTIABLE

    reference = cmm.CertificateOfDepositReferenceLinkedRateTerms(
        eid(24),
        cmm.CashMoneyMarketFloatingSpread(Decimal("0")),
        cdreset(),
        dc(),
    )
    assert cd(reference).return_terms.logical_values()[0] == "reference-linked"

    early = cmm.CertificateOfDepositPresetRateStep(
        date(2026, 2, 1), cmm.CashMoneyMarketContractualRate(Decimal("0.01"))
    )
    late = cmm.CertificateOfDepositPresetRateStep(
        date(2026, 8, 1), cmm.CashMoneyMarketContractualRate(Decimal("0.02"))
    )
    schedule = cmm.CertificateOfDepositPresetStepSchedule((late, early))
    assert schedule.steps == (early, late)
    assert isinstance(schedule.logical_values()[0], tuple)
    preset = cmm.CertificateOfDepositPresetStepsRateTerms(schedule, dc())
    assert cd(preset).return_terms.logical_values()[0] == "preset-steps"

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cmm.CertificateOfDepositPresetStepSchedule((early, early))
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cmm.CertificateOfDepositPresetStepSchedule(cast(Any, (date(2026, 2, 1),)))


def test_cd_cross_object_validation_and_fail_closed_negotiability() -> None:
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cd(
            cmm.CertificateOfDepositReferenceLinkedRateTerms(
                eid(21),
                cmm.CashMoneyMarketFloatingSpread(Decimal("0")),
                cdreset(),
                dc(),
            )
        )
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cd(
            cmm.CertificateOfDepositReferenceLinkedRateTerms(
                eid(24),
                cmm.CashMoneyMarketFloatingSpread(Decimal("0")),
                cdreset(date(2027, 1, 1)),
                dc(),
            )
        )
    outside = cmm.CertificateOfDepositPresetStepSchedule(
        (
            cmm.CertificateOfDepositPresetRateStep(
                date(2027, 1, 1),
                cmm.CashMoneyMarketContractualRate(Decimal("0.02")),
            ),
        )
    )
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cd(cmm.CertificateOfDepositPresetStepsRateTerms(outside, dc()))
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cd(fixed_cd(), cast(Any, "unknown"))


def test_determinism_immutability_and_no_operational_api() -> None:
    first = cp(cmm.CommercialPaperAtParPricing(), fixed_cp())
    second = cp(cmm.CommercialPaperAtParPricing(), fixed_cp())
    different = cp(
        cmm.CommercialPaperDiscountedPricing(
            cmm.CashMoneyMarketCommercialPaperIssuePrice(Decimal("990"))
        ),
        fixed_cp(),
    )
    assert first.logical_values() == second.logical_values()
    assert first.logical_values() != different.logical_values()

    for value in (term(), first, cd(fixed_cd())):
        with pytest.raises(FrozenInstanceError):
            cast(Any, value).evidence_ref = ev(99)
        assert not hasattr(value, "__dict__")
        for forbidden in ("execute", "settle", "fetch", "refresh", "provider"):
            assert not hasattr(value, forbidden)


def test_dcd_defensive_runtime_type_guards() -> None:
    base = dcd()
    for field_name, bad_value in (
        ("base_currency_identity_id", UUID(int=1)),
        ("alternate_currency_identity_id", UUID(int=2)),
        ("fx_fixing_identity_id", UUID(int=3)),
        ("true_payout_identity_id", UUID(int=4)),
        ("false_payout_identity_id", UUID(int=5)),
        ("fixing_date", datetime(2026, 6, 15)),
        ("strike", object()),
        ("orientation", "alternate-per-principal"),
        ("comparator", "greater-than"),
        ("evidence_ref", UUID(int=6)),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(base, **{field_name: bad_value})

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(
            base,
            strike=DerivativeStrike(Decimal("1"), DerivativeStrikeBasis.LEVEL),
        )

    forged = object.__new__(DerivativeStrike)
    object.__setattr__(forged, "value", Decimal("1"))
    object.__setattr__(forged, "basis", DerivativeStrikeBasis.PRICE)
    object.__setattr__(forged, "quote_identity_id", base.alternate_currency_identity_id)
    object.__setattr__(
        forged,
        "price_quote_basis",
        DerivativePriceQuoteBasisCode("currency-per-unit"),
    )
    object.__setattr__(forged, "convention", object())
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, strike=forged)


def test_term_deposit_defensive_runtime_type_guards() -> None:
    base = term()
    for field_name, bad_value in (
        ("terms_id", UUID(int=1)),
        ("instrument_identity_id", UUID(int=2)),
        ("deposit_obligor_identity_id", UUID(int=3)),
        ("denomination_currency_identity_id", UUID(int=4)),
        ("principal", Decimal("1")),
        ("start_date", datetime(2026, 1, 1)),
        ("maturity_date", datetime(2026, 12, 31)),
        ("contractual_rate", Decimal("0.01")),
        ("day_count", "actual-360"),
        ("evidence_ref", UUID(int=5)),
        ("dual_currency_feature", object()),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(base, **{field_name: bad_value})

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, deposit_obligor_identity_id=base.instrument_identity_id)
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, maturity_date=base.start_date)


def test_cp_variant_defensive_runtime_type_guards() -> None:
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        cmm.CommercialPaperDiscountedPricing(cast(Any, Decimal("990")))

    fixed = fixed_cp()
    for field_name, bad_value in (
        ("contractual_rate", Decimal("0.01")),
        ("day_count", "actual-360"),
        ("payment_dates", (date(2026, 4, 1),)),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(fixed, **{field_name: bad_value})

    floating = floating_cp()
    for field_name, bad_value in (
        ("reference_identity_id", UUID(int=1)),
        ("reset_dates", (date(2026, 2, 1),)),
        ("payment_dates", (date(2026, 4, 1),)),
        ("day_count", "actual-360"),
        ("spread", Decimal("0")),
        ("multiplier", Decimal("1")),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(floating, **{field_name: bad_value})


def test_commercial_paper_outer_defensive_runtime_guards() -> None:
    base = cp(cmm.CommercialPaperAtParPricing(), fixed_cp())
    for field_name, bad_value in (
        ("terms_id", UUID(int=1)),
        ("instrument_identity_id", UUID(int=2)),
        ("issuer_obligor_identity_id", UUID(int=3)),
        ("denomination_currency_identity_id", UUID(int=4)),
        ("face_redemption_amount", Decimal("1000")),
        ("issue_date", datetime(2026, 1, 1)),
        ("maturity_date", datetime(2026, 12, 31)),
        ("pricing", object()),
        ("interest", object()),
        ("evidence_ref", UUID(int=5)),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(base, **{field_name: bad_value})

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, issuer_obligor_identity_id=base.instrument_identity_id)
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, maturity_date=base.issue_date)


def test_cd_variant_defensive_runtime_type_guards() -> None:
    fixed = fixed_cd()
    for field_name, bad_value in (
        ("contractual_rate", Decimal("0.01")),
        ("day_count", "actual-360"),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(fixed, **{field_name: bad_value})

    reference = cmm.CertificateOfDepositReferenceLinkedRateTerms(
        eid(24),
        cmm.CashMoneyMarketFloatingSpread(Decimal("0")),
        cdreset(),
        dc(),
    )
    for field_name, bad_value in (
        ("reference_identity_id", UUID(int=1)),
        ("spread", Decimal("0")),
        ("reset_schedule", (date(2026, 3, 1),)),
        ("day_count", "actual-360"),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(reference, **{field_name: bad_value})

    step = cmm.CertificateOfDepositPresetRateStep(
        date(2026, 2, 1), cmm.CashMoneyMarketContractualRate(Decimal("0.01"))
    )
    for field_name, bad_value in (
        ("effective_date", datetime(2026, 2, 1)),
        ("contractual_rate", Decimal("0.01")),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(step, **{field_name: bad_value})

    for bad_steps in (cast(Any, [step]), (), cast(Any, (date(2026, 2, 1),))):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            cmm.CertificateOfDepositPresetStepSchedule(bad_steps)

    schedule = cmm.CertificateOfDepositPresetStepSchedule((step,))
    preset = cmm.CertificateOfDepositPresetStepsRateTerms(schedule, dc())
    for field_name, bad_value in (
        ("steps", (step,)),
        ("day_count", "actual-360"),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(preset, **{field_name: bad_value})


def test_certificate_of_deposit_outer_defensive_runtime_guards() -> None:
    base = cd(fixed_cd())
    for field_name, bad_value in (
        ("terms_id", UUID(int=1)),
        ("instrument_identity_id", UUID(int=2)),
        ("issuing_institution_identity_id", UUID(int=3)),
        ("denomination_currency_identity_id", UUID(int=4)),
        ("deposit_principal", Decimal("1")),
        ("issue_start_date", datetime(2026, 1, 1)),
        ("maturity_date", datetime(2026, 12, 31)),
        ("negotiability", "negotiable"),
        ("return_terms", object()),
        ("evidence_ref", UUID(int=5)),
    ):
        with pytest.raises(cmm.CashMoneyMarketValidationError):
            replace_any(base, **{field_name: bad_value})

    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, issuing_institution_identity_id=base.instrument_identity_id)
    with pytest.raises(cmm.CashMoneyMarketValidationError):
        replace_any(base, maturity_date=base.issue_start_date)
