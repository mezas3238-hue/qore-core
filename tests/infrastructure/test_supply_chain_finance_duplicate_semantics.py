from __future__ import annotations

from datetime import date
from decimal import Decimal
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
    SupplyChainFinanceValidationError,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _party(value: int) -> ScfPartyReferenceId:
    return ScfPartyReferenceId(_uuid(value))


def _evidence(value: int) -> ScfEvidenceRef:
    return ScfEvidenceRef(_uuid(value))


def _trade_ref(value: int) -> ScfTradeObjectReferenceId:
    return ScfTradeObjectReferenceId(_uuid(value))


def _amount() -> ScfContractualAmount:
    return ScfContractualAmount(
        Decimal("100"),
        EconomicIdentityId(_uuid(900)),
    )


def _funding() -> ScfFundingTerms:
    return ScfFundingTerms(ScfFundingRuleCode("contractual-formula"))


def _obligation(
    reference: int,
    *,
    creditor: int = 20,
    debtor: int = 30,
    economic_identity_id: EconomicIdentityId | None = None,
) -> ReceivablePaymentObligationTerms:
    return ReceivablePaymentObligationTerms(
        obligation_reference_id=_trade_ref(reference),
        obligation_kind=ScfTradeObjectKindCode("receivable"),
        creditor_reference_id=_party(creditor),
        debtor_reference_id=_party(debtor),
        face_amount=_amount(),
        due_date=date(2026, 9, 30),
        obligation_form=ScfObligationFormCode("invoice"),
        evidence_ref=_evidence(1000 + reference),
        economic_identity_id=economic_identity_id,
    )


def _purchase(
    obligations: tuple[ReceivablePaymentObligationTerms, ...],
    *,
    transferor: int = 40,
    financier: int = 50,
) -> ReceivablesPurchaseTerms:
    return ReceivablesPurchaseTerms(
        obligations=obligations,
        transferor_reference_id=_party(transferor),
        financier_reference_id=_party(financier),
        assignment_qualification=ScfAssignmentQualificationCode(
            "contractual-assignment"
        ),
        recourse_qualification=ScfRecourseQualificationCode("with-recourse"),
        funding=_funding(),
        purchase_date=date(2026, 8, 25),
        evidence_ref=_evidence(60),
    )


def test_obligation_rejects_same_creditor_and_debtor_reference() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="creditor and debtor references must differ",
    ):
        _obligation(10, creditor=20, debtor=20)


def test_purchase_rejects_duplicate_canonical_economic_obligation_identity() -> None:
    canonical_identity = EconomicIdentityId(_uuid(700))
    obligations = (
        _obligation(10, economic_identity_id=canonical_identity),
        _obligation(11, economic_identity_id=canonical_identity),
    )
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="must not duplicate economic identity",
    ):
        _purchase(obligations)


def test_purchase_rejects_same_transferor_and_financier_reference() -> None:
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="transferor and financier references must differ",
    ):
        _purchase((_obligation(10),), transferor=40, financier=40)


def test_advance_rejects_same_borrower_and_financier_reference() -> None:
    binding = ScfTradeObjectBinding(
        reference_id=_trade_ref(80),
        kind=ScfTradeObjectKindCode("inventory"),
        evidence_ref=_evidence(2080),
    )
    with pytest.raises(
        SupplyChainFinanceValidationError,
        match="borrower and financier references must differ",
    ):
        AdvanceBasedFinanceTerms(
            borrower_reference_id=_party(70),
            financier_reference_id=_party(70),
            trade_objects=(binding,),
            funding=_funding(),
            start_date=date(2026, 8, 25),
            evidence_ref=_evidence(90),
        )
