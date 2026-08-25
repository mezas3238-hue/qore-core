from __future__ import annotations

from dataclasses import fields
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


def _discount() -> DynamicDiscountConvention:
    return DynamicDiscountConvention(
        rate_setter=DynamicDiscountRateSetter.BUYER,
        timing_basis=DynamicDiscountTimingBasis.DAYS_BEFORE_ORIGINAL_DUE_DATE,
        evidence_ref=_evidence(60),
    )


def _dd(
    *,
    approved: AdvancedPayableApprovedObligation | None = None,
) -> DynamicDiscountingTerms:
    return DynamicDiscountingTerms(
        approved_obligation=_approved() if approved is None else approved,
        discount_convention=_discount(),
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
    terms: CorporatePaymentUndertakingTerms
    | DynamicDiscountingTerms
    | BankPaymentUndertakingTerms,
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


@pytest.mark.parametrize(
    ("technique", "terms_type"),
    (
        (
            AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING,
            CorporatePaymentUndertakingTerms,
        ),
        (
            AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
            DynamicDiscountingTerms,
        ),
        (
            AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING,
            BankPaymentUndertakingTerms,
        ),
    ),
)
def test_each_technique_accepts_only_its_bounded_terms(
    technique: AdvancedPayableTechniqueKind,
    terms_type: type[object],
) -> None:
    terms = {
        AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING: _cpu(),
        AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING: _dd(),
        AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING: _bpu(),
    }[technique]
    qualification = _qualification(technique, terms)
    assert type(qualification.terms) is terms_type
    assert qualification.logical_values()[0] == "advanced-payable-scf.v1"
    assert qualification.logical_values()[2] == technique.value


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
    wrong_terms: object,
    message: str,
) -> None:
    with pytest.raises(AdvancedPayableScfValidationError, match=message):
        _qualification(technique, cast(Any, wrong_terms))


def test_advanced_payable_requires_approved_payment_obligation_not_receivable() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="requires payment-obligation kind",
    ):
        _approved(obligation=_obligation(kind="receivable"))


def test_approved_obligation_reuses_exact_unr021_amount_and_due_date_semantics() -> None:
    approved = _approved(
        obligation=_obligation(amount="123.4500", due_date=date(2027, 1, 15))
    )
    values = approved.logical_values()[0]
    assert values[4] == ("123.45", (str(_uuid(900)),))
    assert values[5] == "2027-01-15"
    assert values[1] == ("payment-obligation",)


def test_cpu_finance_provider_must_differ_from_buyer_and_seller() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="finance provider must differ",
    ):
        _cpu(finance_provider=20)
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="finance provider must differ",
    ):
        _cpu(finance_provider=30)


def test_cpu_retains_undertaking_without_receivables_purchase_shape() -> None:
    terms = _cpu()
    values = terms.logical_values()
    assert values[1] == (str(_uuid(40)),)
    assert values[2] == (str(_uuid(50)),)
    assert "ReceivablesPurchaseTerms" not in {
        field.type if isinstance(field.type, str) else str(field.type)
        for field in fields(CorporatePaymentUndertakingTerms)
    }


def test_dynamic_discount_is_structurally_buyer_funded() -> None:
    terms = _dd()
    assert terms.logical_values()[1] == "buyer-own-funds"
    assert tuple(field.name for field in fields(DynamicDiscountingTerms)) == (
        "approved_obligation",
        "discount_convention",
        "evidence_ref",
    )
    assert "finance_provider_reference_id" not in {
        field.name for field in fields(DynamicDiscountingTerms)
    }


def test_dynamic_discount_timing_is_days_before_original_due_date() -> None:
    convention = _discount()
    assert convention.logical_values()[:2] == (
        "buyer",
        "days-before-original-due-date",
    )


def test_dynamic_discount_allows_seller_rate_setter_without_changing_funding_source() -> None:
    convention = DynamicDiscountConvention(
        rate_setter=DynamicDiscountRateSetter.SELLER,
        timing_basis=DynamicDiscountTimingBasis.DAYS_BEFORE_ORIGINAL_DUE_DATE,
        evidence_ref=_evidence(62),
    )
    terms = DynamicDiscountingTerms(
        approved_obligation=_approved(),
        discount_convention=convention,
        evidence_ref=_evidence(63),
    )
    assert terms.logical_values()[1] == "buyer-own-funds"
    assert terms.logical_values()[2][0] == "seller"


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("rate_setter", "buyer"),
        ("timing_basis", "days-before-original-due-date"),
    ),
)
def test_dynamic_discount_enum_fields_require_exact_runtime_types(
    field_name: str,
    bad_value: object,
) -> None:
    values: dict[str, object] = {
        "rate_setter": DynamicDiscountRateSetter.BUYER,
        "timing_basis": DynamicDiscountTimingBasis.DAYS_BEFORE_ORIGINAL_DUE_DATE,
        "evidence_ref": _evidence(64),
    }
    values[field_name] = bad_value
    with pytest.raises(AdvancedPayableScfValidationError):
        DynamicDiscountConvention(**cast(Any, values))


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


def test_bpu_may_name_seller_or_other_bank_as_beneficiary() -> None:
    seller_beneficiary = _bpu(beneficiary=20)
    bank_beneficiary = _bpu(beneficiary=80)
    assert seller_beneficiary.logical_values()[2] == (str(_uuid(20)),)
    assert bank_beneficiary.logical_values()[2] == (str(_uuid(80)),)


def test_bpu_retains_primary_obligor_and_opaque_network_reference() -> None:
    values = _bpu().logical_values()
    assert values[3] == "issuing-bank-primary-obligor"
    assert values[5] == (str(_uuid(72)),)


def test_network_reference_requires_exact_uuid() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="network reference ID must be exact UUID",
    ):
        AdvancedPayableNetworkReferenceId(cast(Any, 72))


def test_undertaking_reference_requires_exact_uuid() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="undertaking reference ID must be exact UUID",
    ):
        AdvancedPayableUndertakingReferenceId(cast(Any, "not-a-uuid"))


def test_qualification_id_rejects_uuid_subclass_or_non_uuid() -> None:
    class UUIDSubclass(UUID):
        pass

    with pytest.raises(AdvancedPayableScfValidationError, match="exact UUID"):
        AdvancedPayableQualificationId(cast(Any, UUIDSubclass(int=1)))
    with pytest.raises(AdvancedPayableScfValidationError, match="exact UUID"):
        AdvancedPayableQualificationId(cast(Any, True))


def test_qualification_requires_exact_date_not_datetime() -> None:
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="effective date must be exact date",
    ):
        _qualification(
            AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
            _dd(),
            effective=cast(Any, datetime(2026, 8, 25, 0, 0)),
        )


def test_qualification_end_date_cannot_precede_effective_date() -> None:
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


def test_qualification_end_date_is_retained_when_present() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING,
        _bpu(),
        end=date(2027, 8, 25),
    )
    assert qualification.logical_values()[-1] == "2027-08-25"


def test_logical_values_are_deterministic_for_equal_material() -> None:
    first = _qualification(AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING, _dd())
    second = _qualification(AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING, _dd())
    assert first.logical_values() == second.logical_values()


def test_logical_values_distinguish_cpu_dd_and_bpu() -> None:
    cpu = _qualification(AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING, _cpu())
    dd = _qualification(AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING, _dd())
    bpu = _qualification(AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING, _bpu())
    assert len({cpu.logical_values(), dd.logical_values(), bpu.logical_values()}) == 3


def test_recursive_revalidation_catches_corrupted_payment_obligation_kind() -> None:
    qualification = _qualification(
        AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING,
        _cpu(),
    )
    object.__setattr__(
        qualification.terms.approved_obligation.obligation.obligation_kind,
        "value",
        "receivable",
    )
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="requires payment-obligation kind",
    ):
        qualification.logical_values()


def test_recursive_revalidation_catches_corrupted_nested_party_uuid() -> None:
    terms = _cpu()
    object.__setattr__(terms.finance_provider_reference_id, "value", cast(Any, "bad"))
    with pytest.raises(SupplyChainFinanceValidationError, match="exact UUID"):
        terms.logical_values()


def test_recursive_revalidation_catches_corrupted_network_uuid() -> None:
    terms = _bpu()
    object.__setattr__(terms.network_reference_id, "value", cast(Any, "bad"))
    with pytest.raises(AdvancedPayableScfValidationError, match="exact UUID"):
        terms.logical_values()


def test_recursive_revalidation_catches_corrupted_discount_enum() -> None:
    terms = _dd()
    object.__setattr__(terms.discount_convention, "rate_setter", cast(Any, "buyer"))
    with pytest.raises(AdvancedPayableScfValidationError, match="rate setter"):
        terms.logical_values()


def test_exact_terms_wrapper_rejects_subclass_laundering() -> None:
    class DynamicDiscountingTermsSubclass(DynamicDiscountingTerms):
        pass

    subclassed = DynamicDiscountingTermsSubclass(
        approved_obligation=_approved(),
        discount_convention=_discount(),
        evidence_ref=_evidence(90),
    )
    with pytest.raises(
        AdvancedPayableScfValidationError,
        match="DD technique requires exact",
    ):
        _qualification(
            AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING,
            cast(Any, subclassed),
        )


def test_advanced_payable_source_does_not_import_purchase_or_advance_terms() -> None:
    source = Path(cast(str, advanced_payable_module.__file__)).read_text()
    assert "ReceivablesPurchaseTerms" not in source
    assert "AdvanceBasedFinanceTerms" not in source
    assert "ScfFundingTerms" not in source


def test_advanced_payable_source_has_no_implicit_runtime_or_network_side_effects() -> None:
    source = Path(cast(str, advanced_payable_module.__file__)).read_text()
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
    )
    for token in forbidden:
        assert token not in source


def test_advanced_payable_source_does_not_claim_operational_authority() -> None:
    source = Path(cast(str, advanced_payable_module.__file__)).read_text().lower()
    forbidden = (
        "submit_order",
        "place_order",
        "execute_payment",
        "settle_payment",
        "broker_token",
        "api_key",
        "production_account",
    )
    for token in forbidden:
        assert token not in source
