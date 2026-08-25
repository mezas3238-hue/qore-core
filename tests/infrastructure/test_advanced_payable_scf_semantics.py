from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.advanced_payable_scf_semantics as advanced_payable_module
from qore.infrastructure.advanced_payable_scf_semantics import (
    AdvancedPayableApprovedObligation,
    AdvancedPayableNetworkReferenceId,
    AdvancedPayableQualification,
    AdvancedPayableQualificationId,
    AdvancedPayableScfValidationError,
    AdvancedPayableTechniqueKind,
    AdvancedPayableTerms,
    AdvancedPayableUndertakingReferenceId,
    BankPaymentUndertakingTerms,
    CorporatePaymentUndertakingTerms,
    DynamicDiscountConvention,
    DynamicDiscountingTerms,
    DynamicDiscountRateSetter,
    DynamicDiscountTimingBasis,
)
from qore.infrastructure.supply_chain_finance_semantics import (
    ReceivablePaymentObligationTerms,
    ScfContractualAmount,
    ScfEvidenceRef,
    ScfObligationFormCode,
    ScfPartyReferenceId,
    ScfTradeObjectKindCode,
    ScfTradeObjectReferenceId,
    SupplyChainFinanceTechniqueKind,
    SupplyChainFinanceValidationError,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _party(value: int) -> ScfPartyReferenceId:
    return ScfPartyReferenceId(_uuid(value))


def _evidence(value: int) -> ScfEvidenceRef:
    return ScfEvidenceRef(_uuid(value))


def _currency(value: int = 900) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _obligation(
    *,
    reference: int = 10,
    kind: str = "payment-obligation",
    seller: int = 20,
    buyer: int = 30,
    amount: str = "100",
    due_date: date = date(2026, 10, 31),
) -> ReceivablePaymentObligationTerms:
    return ReceivablePaymentObligationTerms(
        obligation_reference_id=ScfTradeObjectReferenceId(_uuid(reference)),
        obligation_kind=ScfTradeObjectKindCode(kind),
        creditor_reference_id=_party(seller),
        debtor_reference_id=_party(buyer),
        face_amount=ScfContractualAmount(Decimal(amount), _currency()),
        due_date=due_date,
        obligation_form=ScfObligationFormCode("approved-invoice"),
        evidence_ref=_evidence(1000 + reference),
    )


def _approved(
    *,
    obligation: ReceivablePaymentObligationTerms | None = None,
) -> AdvancedPayableApprovedObligation:
    return AdvancedPayableApprovedObligation(
        obligation=_obligation() if obligation is None else obligation,
        approval_evidence_ref=_evidence(1100),
    )


def _cpu(
    *,
    approved: AdvancedPayableApprovedObligation | None = None,
    finance_provider: int = 40,
) -> CorporatePaymentUndertakingTerms:
    return CorporatePaymentUndertakingTerms(
        approved_obligation=_approved() if approved is None else approved,
        finance_provider_reference_id=_party(finance_provider),
        undertaking_reference_id=AdvancedPayableUndertakingReferenceId(_uuid(50)),
        undertaking_evidence_ref=_evidence(51),
    )


def _discount(
    *,
    setter: DynamicDiscountRateSetter = DynamicDiscountRateSetter.BUYER,
) -> DynamicDiscountConvention:
    return DynamicDiscountConvention(
        rate_setter=setter,
        timing_basis=DynamicDiscountTimingBasis.DAYS_BEFORE_ORIGINAL_DUE_DATE,
        evidence_ref=_evidence(60),
    )


def _dd(
    *,
    approved: AdvancedPayableApprovedObligation | None = None,
    convention: DynamicDiscountConvention | None = None,
) -> DynamicDiscountingTerms:
    return DynamicDiscountingTerms(
        approved_obligation=_approved() if approved is None else approved,
        discount_convention=_discount() if convention is None else convention,
        evidence_ref=_evidence(61),
    )


def _bpu(
    *,
    approved: AdvancedPayableApprovedObligation | None = None,
    issuing_bank: int = 70,
    beneficiary: int = 20,
) -> BankPaymentUndertakingTerms:
    return BankPaymentUndertakingTerms(
        approved_obligation=_approved() if approved is None else approved,
        issuing_bank_reference_id=_party(issuing_bank),
        beneficiary_reference_id=_party(beneficiary),
        undertaking_reference_id=AdvancedPayableUndertakingReferenceId(_uuid(71)),
        network_reference_id=AdvancedPayableNetworkReferenceId(_uuid(72)),
        undertaking_evidence_ref=_evidence(73),
    )


def _qualification(
    technique: AdvancedPayableTechniqueKind,
    terms: AdvancedPayableTerms,
    *,
    effective: date = date(2026, 8, 25),
    end: date | None = None,
) -> AdvancedPayableQualification:
    return AdvancedPayableQualification(
        qualification_id=AdvancedPayableQualificationId(_uuid(1)),
        technique=technique,
        terms=terms,
        effective_date=effective,
        evidence_ref=_evidence(2),
        end_date=end,
    )


def test_advanced_payable_technique_set_is_exactly_cpu_dd_bpu() -> None:
    assert tuple(item.value for item in AdvancedPayableTechniqueKind) == (
        "corporate-payment-undertaking",
        "dynamic-discounting",
        "bank-payment-undertaking",
    )


def test_retained_icc_2017_technique_set_remains_exactly_eight() -> None:
    assert tuple(item.value for item in SupplyChainFinanceTechniqueKind) == (
        "receivables-discounting",
        "factoring",
        "forfaiting",
        "payables-finance",
        "loan-or-advance-against-receivables",
        "distributor-finance",
        "loan-or-advance-against-inventory",
        "pre-shipment-finance",
    )


def test_cpu_qualification_binds_exact_cpu_terms() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING,
        _cpu(),
    )
    assert type(qualification.terms) is CorporatePaymentUndertakingTerms
    assert qualification.logical_values()[0] == "advanced-payable-scf.v1"
    assert qualification.logical_values()[2] == "corporate-payment-undertaking"


def test_dd_qualification_binds_exact_dd_terms() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
        _dd(),
    )
    assert type(qualification.terms) is DynamicDiscountingTerms
    assert qualification.logical_values()[2] == "dynamic-discounting"


def test_bpu_qualification_binds_exact_bpu_terms() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING,
        _bpu(),
    )
    assert type(qualification.terms) is BankPaymentUndertakingTerms
    assert qualification.logical_values()[2] == "bank-payment-undertaking"


@pytest.mark.parametrize(
    ("technique", "wrong_terms", "message"),
    (
        (
            AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING,
            _dd(),
            "CPU technique requires exact",
        ),
        (
            AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
            _bpu(),
            "DD technique requires exact",
        ),
        (
            AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING,
            _cpu(),
            "BPU technique requires exact",
        ),
    ),
)
def test_technique_and_terms_cannot_be_cross_laundered(
    technique: AdvancedPayableTechniqueKind,
    wrong_terms: AdvancedPayableTerms,
    message: str,
) -> None:
    with pytest.raises(AdvancedPayableScfValidationError, match=message):
        _qualification(technique, wrong_terms)


def test_advanced_payable_requires_approved_payment_obligation_not_receivable() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="requires payment-obligation kind",
    ):
        _approved(obligation=_obligation(kind="receivable"))


def test_approved_obligation_reuses_unr021_amount_due_date_and_parties() -> None:
    approved = _approved(
        obligation=_obligation(
            amount="123.4500",
            due_date=date(2027, 1, 15),
            seller=22,
            buyer=33,
        )
    )
    obligation = approved.obligation
    values = obligation.logical_values()
    assert values[4] == ("123.45", (str(_uuid(900)),))
    assert values[5] == "2027-01-15"
    assert obligation.creditor_reference_id == _party(22)
    assert obligation.debtor_reference_id == _party(33)
    assert obligation.obligation_kind.value == "payment-obligation"


@pytest.mark.parametrize(
    "bad_value",
    (
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        1.0,
        True,
    ),
)
def test_reused_contractual_amount_remains_positive_finite_exact_decimal(
    bad_value: object,
) -> None:
    with pytest.raises(SupplyChainFinanceValidationError):
        ScfContractualAmount(cast(Any, bad_value), _currency())


def test_cpu_finance_provider_must_differ_from_buyer_and_seller() -> None:
    for party in (20, 30):
        with pytest.raises(
            AdvancedPayableScfValidationError,
            match="finance provider must differ",
        ):
            _cpu(finance_provider=party)


def test_cpu_retains_undertaking_without_receivables_purchase_shape() -> None:
    terms = _cpu()
    assert terms.finance_provider_reference_id == _party(40)
    assert terms.undertaking_reference_id.logical_values() == (str(_uuid(50)),)
    names = {field.name for field in fields(CorporatePaymentUndertakingTerms)}
    assert "obligations" not in names
    assert "assignment_qualification" not in names
    assert "recourse_qualification" not in names
    source = Path(advanced_payable_module.__file__).read_text()
    assert "ReceivablesPurchaseTerms" not in source
    assert "AdvanceBasedFinanceTerms" not in source
    assert "ScfFundingTerms" not in source


def test_dynamic_discount_is_structurally_buyer_funded_without_financier_field() -> None:
    terms = _dd()
    values = terms.logical_values()
    assert values[1] == "buyer-own-funds"
    names = tuple(field.name for field in fields(DynamicDiscountingTerms))
    assert names == (
        "approved_obligation",
        "discount_convention",
        "evidence_ref",
    )
    assert "finance_provider_reference_id" not in names


def test_dynamic_discount_preserves_timing_and_rate_setter_without_calculation() -> None:
    buyer_convention = _discount()
    seller_convention = _discount(setter=DynamicDiscountRateSetter.SELLER)
    assert buyer_convention.logical_values()[:2] == (
        "buyer",
        "days-before-original-due-date",
    )
    assert seller_convention.logical_values()[:2] == (
        "seller",
        "days-before-original-due-date",
    )
    terms = _dd(convention=seller_convention)
    assert terms.logical_values()[1] == "buyer-own-funds"
    assert terms.discount_convention.rate_setter is DynamicDiscountRateSetter.SELLER


@pytest.mark.parametrize(
    ("setter", "timing"),
    (
        ("buyer", DynamicDiscountTimingBasis.DAYS_BEFORE_ORIGINAL_DUE_DATE),
        (DynamicDiscountRateSetter.BUYER, "days-before-original-due-date"),
    ),
)
def test_dynamic_discount_enum_fields_require_exact_runtime_types(
    setter: object,
    timing: object,
) -> None:
    with pytest.raises(AdvancedPayableScfValidationError):
        DynamicDiscountConvention(
            rate_setter=cast(Any, setter),
            timing_basis=cast(Any, timing),
            evidence_ref=_evidence(64),
        )


def test_bpu_issuing_bank_must_differ_from_buyer_seller_and_beneficiary() -> None:
    for bad_bank in (20, 30, 80):
        with pytest.raises(
            AdvancedPayableScfValidationError,
            match="issuing bank must differ",
        ):
            _bpu(issuing_bank=bad_bank, beneficiary=80)


def test_bpu_beneficiary_must_differ_from_buyer() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="beneficiary must differ from buyer",
    ):
        _bpu(beneficiary=30)


def test_bpu_allows_seller_or_other_bank_beneficiary_and_keeps_bank_primary_obligor() -> None:
    seller_beneficiary = _bpu(beneficiary=20)
    other_bank_beneficiary = _bpu(beneficiary=80)
    assert seller_beneficiary.beneficiary_reference_id == _party(20)
    assert other_bank_beneficiary.beneficiary_reference_id == _party(80)
    values = seller_beneficiary.logical_values()
    assert values[3] == "issuing-bank-primary-obligor"
    assert seller_beneficiary.network_reference_id.logical_values() == (str(_uuid(72)),)


@pytest.mark.parametrize(
    "wrapper",
    (
        AdvancedPayableQualificationId,
        AdvancedPayableUndertakingReferenceId,
        AdvancedPayableNetworkReferenceId,
    ),
)
def test_advanced_payable_id_wrappers_require_exact_uuid(
    wrapper: type[
        AdvancedPayableQualificationId
        | AdvancedPayableUndertakingReferenceId
        | AdvancedPayableNetworkReferenceId
    ],
) -> None:
    with pytest.raises(AdvancedPayableScfValidationError, match="exact UUID"):
        wrapper(cast(Any, "not-a-uuid"))
    with pytest.raises(AdvancedPayableScfValidationError, match="exact UUID"):
        wrapper(cast(Any, True))


def test_qualification_requires_exact_enum_and_exact_date() -> None:
    with pytest.raises(AdvancedPayableScfValidationError, match="technique must be exact"):
        AdvancedPayableQualification(
            qualification_id=AdvancedPayableQualificationId(_uuid(1)),
            technique=cast(Any, "dynamic-discounting"),
            terms=_dd(),
            effective_date=date(2026, 8, 25),
            evidence_ref=_evidence(2),
        )
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="effective date must be exact date",
    ):
        _qualification(
            AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
            _dd(),
            effective=cast(Any, datetime(2026, 8, 25, 0, 0)),
        )


def test_qualification_end_date_must_be_exact_and_not_precede_effective_date() -> None:
    with pytest.raises(AdvancedPayableScfValidationError, match="end date must be exact"):
        _qualification(
            AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
            _dd(),
            end=cast(Any, datetime(2027, 1, 1, 0, 0)),
        )
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="end date must not precede",
    ):
        _qualification(
            AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING,
            _cpu(),
            effective=date(2026, 8, 25),
            end=date(2026, 8, 24),
        )
    qualification = _qualification(
        AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING,
        _bpu(),
        end=date(2027, 8, 25),
    )
    assert qualification.logical_values()[-1] == "2027-08-25"


def test_logical_values_are_deterministic_and_distinguish_techniques() -> None:
    first = _qualification(AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING, _dd())
    second = _qualification(AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING, _dd())
    cpu = _qualification(AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING, _cpu())
    bpu = _qualification(AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING, _bpu())
    assert first.logical_values() == second.logical_values()
    assert len({first.logical_values(), cpu.logical_values(), bpu.logical_values()}) == 3


def test_recursive_logical_values_revalidates_corrupted_nested_obligation() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING,
        _cpu(),
    )
    obligation = cast(CorporatePaymentUndertakingTerms, qualification.terms).approved_obligation.obligation
    object.__setattr__(obligation.obligation_kind, "value", "receivable")
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="requires payment-obligation kind",
    ):
        qualification.logical_values()


def test_recursive_logical_values_revalidates_corrupted_nested_evidence() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
        _dd(),
    )
    terms = cast(DynamicDiscountingTerms, qualification.terms)
    object.__setattr__(terms.evidence_ref, "value", cast(Any, "corrupt"))
    with pytest.raises(SupplyChainFinanceValidationError, match="exact UUID"):
        qualification.logical_values()


def test_values_are_frozen() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING,
        _bpu(),
    )
    with pytest.raises(FrozenInstanceError):
        qualification.effective_date = date(2027, 1, 1)  # type: ignore[misc]


def test_source_has_no_implicit_runtime_network_or_payment_side_effects() -> None:
    source = Path(advanced_payable_module.__file__).read_text().lower()
    forbidden = (
        "datetime.now",
        "datetime.utcnow",
        "uuid4",
        "requests.",
        "httpx",
        "socket.",
        "urllib",
        "sleep(",
        "threading",
        "subprocess",
        "submit_order",
        "place_order",
        "execute_payment",
        "settle_payment",
    )
    for token in forbidden:
        assert token not in source


def test_source_has_no_provider_credentials_or_production_authority() -> None:
    source = Path(advanced_payable_module.__file__).read_text().lower()
    forbidden = (
        "broker_token",
        "api_key",
        "access_token",
        "client_secret",
        "production_account",
        "real_capital",
    )
    for token in forbidden:
        assert token not in source
