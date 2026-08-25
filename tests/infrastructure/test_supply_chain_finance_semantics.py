from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.supply_chain_finance_semantics import (
    AdvanceBasedFinanceTerms,
    ReceivablePaymentObligationTerms,
    ReceivablesPurchaseTerms,
    ScfAssignmentQualificationCode,
    ScfContractualAmount,
    ScfEvidenceRef,
    ScfFundingRuleCode,
    ScfFundingTerms,
    ScfObligationFormCode,
    ScfPartyReferenceId,
    ScfRecourseQualificationCode,
    ScfTradeObjectBinding,
    ScfTradeObjectKindCode,
    ScfTradeObjectReferenceId,
    SupplyChainFinanceQualification,
    SupplyChainFinanceQualificationId,
    SupplyChainFinanceTechniqueKind,
    SupplyChainFinanceValidationError,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _currency(value: int = 900) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _amount(value: str = "100", *, currency: int = 900) -> ScfContractualAmount:
    return ScfContractualAmount(Decimal(value), _currency(currency))


def _party(value: int) -> ScfPartyReferenceId:
    return ScfPartyReferenceId(_uuid(value))


def _evidence(value: int) -> ScfEvidenceRef:
    return ScfEvidenceRef(_uuid(value))


def _trade_ref(value: int) -> ScfTradeObjectReferenceId:
    return ScfTradeObjectReferenceId(_uuid(value))


def _obligation(
    value: int = 10,
    *,
    kind: str = "receivable",
    creditor: int = 20,
    debtor: int = 30,
    amount: str = "100",
    due: date = date(2026, 9, 30),
    economic_identity: EconomicIdentityId | None = None,
) -> ReceivablePaymentObligationTerms:
    return ReceivablePaymentObligationTerms(
        obligation_reference_id=_trade_ref(value),
        obligation_kind=ScfTradeObjectKindCode(kind),
        creditor_reference_id=_party(creditor),
        debtor_reference_id=_party(debtor),
        face_amount=_amount(amount),
        due_date=due,
        obligation_form=ScfObligationFormCode("invoice"),
        evidence_ref=_evidence(1000 + value),
        economic_identity_id=economic_identity,
    )


def _funding(
    *,
    rule: str = "contractual-formula",
    fixed_amount: ScfContractualAmount | None = None,
) -> ScfFundingTerms:
    return ScfFundingTerms(ScfFundingRuleCode(rule), fixed_amount)


def _purchase_terms(
    *,
    obligations: tuple[ReceivablePaymentObligationTerms, ...] | None = None,
    recourse: str = "with-recourse",
    purchase_date: date = date(2026, 8, 25),
) -> ReceivablesPurchaseTerms:
    return ReceivablesPurchaseTerms(
        obligations=(_obligation(),) if obligations is None else obligations,
        transferor_reference_id=_party(40),
        financier_reference_id=_party(50),
        assignment_qualification=ScfAssignmentQualificationCode(
            "contractual-assignment"
        ),
        recourse_qualification=ScfRecourseQualificationCode(recourse),
        funding=_funding(),
        purchase_date=purchase_date,
        evidence_ref=_evidence(60),
    )


def _binding(
    value: int,
    kind: str,
    *,
    identity: EconomicIdentityId | None = None,
) -> ScfTradeObjectBinding:
    return ScfTradeObjectBinding(
        reference_id=_trade_ref(value),
        kind=ScfTradeObjectKindCode(kind),
        evidence_ref=_evidence(2000 + value),
        economic_identity_id=identity,
    )


def _advance_terms(
    *,
    trade_objects: tuple[ScfTradeObjectBinding, ...] | None = None,
    credit_leg_identity_id: EconomicIdentityId | None = None,
    start: date = date(2026, 8, 25),
    maturity: date | None = date(2027, 8, 25),
) -> AdvanceBasedFinanceTerms:
    return AdvanceBasedFinanceTerms(
        borrower_reference_id=_party(70),
        financier_reference_id=_party(80),
        trade_objects=(_binding(81, "receivable"),)
        if trade_objects is None
        else trade_objects,
        funding=_funding(fixed_amount=_amount("75")),
        start_date=start,
        evidence_ref=_evidence(90),
        maturity_date=maturity,
        credit_leg_identity_id=credit_leg_identity_id,
    )


def _qualification(
    technique: SupplyChainFinanceTechniqueKind,
    terms: ReceivablesPurchaseTerms | AdvanceBasedFinanceTerms,
    *,
    effective: date = date(2026, 8, 25),
    end: date | None = None,
) -> SupplyChainFinanceQualification:
    return SupplyChainFinanceQualification(
        qualification_id=SupplyChainFinanceQualificationId(_uuid(1)),
        technique=technique,
        terms=terms,
        effective_date=effective,
        evidence_ref=_evidence(2),
        end_date=end,
    )


def test_versioned_technique_set_is_exactly_the_retained_eight() -> None:
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
    "technique",
    (
        SupplyChainFinanceTechniqueKind.RECEIVABLES_DISCOUNTING,
        SupplyChainFinanceTechniqueKind.FACTORING,
        SupplyChainFinanceTechniqueKind.PAYABLES_FINANCE,
    ),
)
def test_purchase_techniques_accept_purchase_terms(
    technique: SupplyChainFinanceTechniqueKind,
) -> None:
    qualification = _qualification(technique, _purchase_terms())
    assert qualification.logical_values()[1] == technique.value


def test_forfaiting_requires_without_recourse_qualification() -> None:
    qualification = _qualification(
        SupplyChainFinanceTechniqueKind.FORFAITING,
        _purchase_terms(recourse="without-recourse"),
    )
    assert qualification.logical_values()[1] == "forfaiting"

    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="forfaiting requires without-recourse",
    ):
        _qualification(
            SupplyChainFinanceTechniqueKind.FORFAITING,
            _purchase_terms(recourse="with-recourse"),
        )


@pytest.mark.parametrize(
    ("technique", "kind"),
    (
        (
            SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_RECEIVABLES,
            "payment-obligation",
        ),
        (SupplyChainFinanceTechniqueKind.DISTRIBUTOR_FINANCE, "goods"),
        (
            SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_INVENTORY,
            "inventory",
        ),
        (SupplyChainFinanceTechniqueKind.PRE_SHIPMENT_FINANCE, "purchase-order"),
    ),
)
def test_advance_techniques_accept_appropriate_trade_objects(
    technique: SupplyChainFinanceTechniqueKind,
    kind: str,
) -> None:
    terms = _advance_terms(trade_objects=(_binding(100, kind),))
    qualification = _qualification(technique, terms)
    assert qualification.logical_values()[1] == technique.value


def test_purchase_and_advance_terms_cannot_be_mixed() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="purchase technique requires exact ReceivablesPurchaseTerms",
    ):
        _qualification(
            SupplyChainFinanceTechniqueKind.FACTORING,
            _advance_terms(),
        )

    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="advance technique requires exact AdvanceBasedFinanceTerms",
    ):
        _qualification(
            SupplyChainFinanceTechniqueKind.DISTRIBUTOR_FINANCE,
            _purchase_terms(),
        )


def test_receivables_advance_rejects_non_receivable_trade_object() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="receivables advance requires",
    ):
        _qualification(
            SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_RECEIVABLES,
            _advance_terms(trade_objects=(_binding(101, "inventory"),)),
        )


def test_inventory_advance_requires_inventory_trade_objects() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="inventory advance requires inventory",
    ):
        _qualification(
            SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_INVENTORY,
            _advance_terms(trade_objects=(_binding(102, "goods"),)),
        )


def test_purchase_obligation_rejects_non_receivable_kind() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="purchased obligation kind must be",
    ):
        _obligation(kind="inventory")


def test_distributor_and_pre_shipment_are_not_forced_into_receivable_shape() -> None:
    distributor = _qualification(
        SupplyChainFinanceTechniqueKind.DISTRIBUTOR_FINANCE,
        _advance_terms(trade_objects=(_binding(103, "inventory"),)),
    )
    pre_shipment = _qualification(
        SupplyChainFinanceTechniqueKind.PRE_SHIPMENT_FINANCE,
        _advance_terms(
            trade_objects=(
                _binding(104, "purchase-order"),
                _binding(105, "goods"),
            )
        ),
    )
    assert distributor.technique is SupplyChainFinanceTechniqueKind.DISTRIBUTOR_FINANCE
    assert pre_shipment.technique is SupplyChainFinanceTechniqueKind.PRE_SHIPMENT_FINANCE


def test_formula_funding_does_not_require_synthetic_fixed_amount() -> None:
    funding = _funding(rule="eligibility-formula", fixed_amount=None)
    assert funding.logical_values() == (("eligibility-formula",), None)


def test_fixed_contractual_amount_is_retained_when_explicit() -> None:
    funding = _funding(rule="fixed-contractual-amount", fixed_amount=_amount("123.4500"))
    assert funding.logical_values()[1] == ("123.45", (str(_uuid(900)),))


@pytest.mark.parametrize(
    "bad_value",
    (
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        1.0,
        True,
    ),
)
def test_contractual_amount_requires_positive_finite_exact_decimal(
    bad_value: object,
) -> None:
    with pytest.raises(SupplyChainFinanceValidationError):
        ScfContractualAmount(Any if False else bad_value, _currency())  # type: ignore[arg-type]


def test_extreme_decimal_exponents_use_compact_bounded_output() -> None:
    positive = _amount("1E+100000000")
    negative = _amount("1E-100000000")
    assert positive.logical_values()[0] == "1e+100000000"
    assert negative.logical_values()[0] == "1e-100000000"


def test_currency_identity_requires_exact_wrapper_and_inner_uuid() -> None:
    class EconomicIdentityIdSubclass(EconomicIdentityId):
        pass

    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="exact EconomicIdentityId",
    ):
        ScfContractualAmount(Decimal("1"), EconomicIdentityIdSubclass(_uuid(900)))

    currency = _currency()
    amount = ScfContractualAmount(Decimal("1"), currency)
    object.__setattr__(currency, "value", "not-a-uuid")
    with pytest.raises(SupplyChainFinanceValidationError, match="must be exact UUID"):
        amount.logical_values()


def test_optional_credit_leg_identity_is_canonical_and_revalidated() -> None:
    identity = EconomicIdentityId(_uuid(333))
    terms = _advance_terms(credit_leg_identity_id=identity)
    assert terms.logical_values()[-1] == (str(_uuid(333)),)

    object.__setattr__(identity, "value", "corrupted")
    with pytest.raises(SupplyChainFinanceValidationError, match="must be exact UUID"):
        terms.logical_values()


def test_optional_trade_object_and_obligation_identities_are_revalidated() -> None:
    obligation_identity = EconomicIdentityId(_uuid(334))
    obligation = _obligation(economic_identity=obligation_identity)
    assert obligation.logical_values()[-1] == (str(_uuid(334)),)
    object.__setattr__(obligation_identity, "value", "corrupted")
    with pytest.raises(SupplyChainFinanceValidationError, match="must be exact UUID"):
        obligation.logical_values()

    binding_identity = EconomicIdentityId(_uuid(335))
    binding = _binding(110, "goods", identity=binding_identity)
    assert binding.logical_values()[-1] == (str(_uuid(335)),)
    object.__setattr__(binding_identity, "value", "corrupted")
    with pytest.raises(SupplyChainFinanceValidationError, match="must be exact UUID"):
        binding.logical_values()


def test_uuid_subclass_and_str_subclass_laundering_are_rejected() -> None:
    class UUIDSubclass(UUID):
        pass

    class StrSubclass(str):
        pass

    with pytest.raises(SupplyChainFinanceValidationError, match="exact UUID"):
        ScfPartyReferenceId(UUIDSubclass(int=1))

    with pytest.raises(SupplyChainFinanceValidationError, match="canonical lowercase"):
        ScfTradeObjectKindCode(StrSubclass("receivable"))


def test_datetime_is_rejected_where_exact_date_is_required() -> None:
    bad_date = datetime(2026, 8, 25, 12, 0)
    with pytest.raises(SupplyChainFinanceValidationError, match="exact date"):
        _purchase_terms(purchase_date=Any if False else bad_date)  # type: ignore[arg-type]

    with pytest.raises(SupplyChainFinanceValidationError, match="exact date"):
        _advance_terms(start=Any if False else bad_date)  # type: ignore[arg-type]

    with pytest.raises(SupplyChainFinanceValidationError, match="exact date"):
        _qualification(
            SupplyChainFinanceTechniqueKind.FACTORING,
            _purchase_terms(),
            effective=Any if False else bad_date,  # type: ignore[arg-type]
        )


def test_non_tuple_collections_are_rejected() -> None:
    with pytest.raises(SupplyChainFinanceValidationError, match="non-empty exact tuple"):
        ReceivablesPurchaseTerms(
            obligations=Any if False else [_obligation()],  # type: ignore[arg-type]
            transferor_reference_id=_party(40),
            financier_reference_id=_party(50),
            assignment_qualification=ScfAssignmentQualificationCode(
                "contractual-assignment"
            ),
            recourse_qualification=ScfRecourseQualificationCode("with-recourse"),
            funding=_funding(),
            purchase_date=date(2026, 8, 25),
            evidence_ref=_evidence(60),
        )

    with pytest.raises(SupplyChainFinanceValidationError, match="non-empty exact tuple"):
        AdvanceBasedFinanceTerms(
            borrower_reference_id=_party(70),
            financier_reference_id=_party(80),
            trade_objects=Any if False else [_binding(81, "receivable")],  # type: ignore[arg-type]
            funding=_funding(),
            start_date=date(2026, 8, 25),
            evidence_ref=_evidence(90),
        )


def test_duplicate_purchase_obligation_references_are_rejected() -> None:
    first = _obligation(120, amount="100")
    second = _obligation(120, amount="200")
    with pytest.raises(SupplyChainFinanceValidationError, match="references must be unique"):
        _purchase_terms(obligations=(first, second))


def test_duplicate_advance_trade_object_references_are_rejected() -> None:
    first = _binding(121, "goods")
    second = _binding(121, "inventory")
    with pytest.raises(SupplyChainFinanceValidationError, match="references must be unique"):
        _advance_terms(trade_objects=(first, second))


def test_purchase_obligation_order_is_canonical_and_caller_independent() -> None:
    first = _obligation(130, amount="50")
    second = _obligation(131, amount="75")
    forward = _purchase_terms(obligations=(first, second))
    reverse = _purchase_terms(obligations=(second, first))
    assert forward.logical_values() == reverse.logical_values()


def test_advance_trade_object_order_is_canonical_and_caller_independent() -> None:
    first = _binding(140, "purchase-order")
    second = _binding(141, "goods")
    forward = _advance_terms(trade_objects=(first, second))
    reverse = _advance_terms(trade_objects=(second, first))
    assert forward.logical_values() == reverse.logical_values()


def test_overdue_receivable_is_not_rejected_by_purchase_date_alone() -> None:
    overdue = _obligation(due=date(2026, 7, 1))
    terms = _purchase_terms(
        obligations=(overdue,),
        purchase_date=date(2026, 8, 25),
    )
    assert terms.obligations[0].due_date == date(2026, 7, 1)


def test_advance_and_qualification_chronology_fail_closed() -> None:
    with pytest.raises(SupplyChainFinanceValidationError, match="maturity date"):
        _advance_terms(
            start=date(2026, 8, 25),
            maturity=date(2026, 8, 24),
        )

    with pytest.raises(SupplyChainFinanceValidationError, match="end date"):
        _qualification(
            SupplyChainFinanceTechniqueKind.FACTORING,
            _purchase_terms(),
            effective=date(2026, 8, 25),
            end=date(2026, 8, 24),
        )


def test_nested_state_corruption_is_rejected_on_logical_values() -> None:
    rule = ScfFundingRuleCode("contractual-formula")
    funding = ScfFundingTerms(rule)
    terms = _advance_terms()
    object.__setattr__(terms, "funding", funding)
    object.__setattr__(rule, "value", "INVALID CODE")
    with pytest.raises(SupplyChainFinanceValidationError, match="canonical lowercase"):
        terms.logical_values()

    party = _party(500)
    purchase = _purchase_terms()
    object.__setattr__(purchase, "transferor_reference_id", party)
    object.__setattr__(party, "value", "corrupted")
    with pytest.raises(SupplyChainFinanceValidationError, match="exact UUID"):
        purchase.logical_values()


def test_top_level_rejects_raw_technique_string() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="exact SupplyChainFinanceTechniqueKind",
    ):
        SupplyChainFinanceQualification(
            qualification_id=SupplyChainFinanceQualificationId(_uuid(1)),
            technique=Any if False else "factoring",  # type: ignore[arg-type]
            terms=_purchase_terms(),
            effective_date=date(2026, 8, 25),
            evidence_ref=_evidence(2),
        )


def test_logical_values_are_deterministic_and_revalidate_recursively() -> None:
    qualification = _qualification(
        SupplyChainFinanceTechniqueKind.PRE_SHIPMENT_FINANCE,
        _advance_terms(
            trade_objects=(
                _binding(601, "goods"),
                _binding(600, "purchase-order"),
            ),
            credit_leg_identity_id=EconomicIdentityId(_uuid(602)),
        ),
        end=date(2027, 8, 25),
    )
    first = qualification.logical_values()
    second = qualification.logical_values()
    assert first == second
    assert first[1] == "pre-shipment-finance"


def test_contract_carries_no_implicit_clock_or_generated_identity() -> None:
    import inspect

    import qore.infrastructure.supply_chain_finance_semantics as module

    source = inspect.getsource(module)
    assert "datetime.now" not in source
    assert "date.today" not in source
    assert "uuid4" not in source
    assert "requests." not in source
    assert "httpx." not in source
    assert "submit_order" not in source
    assert "settle_order" not in source
