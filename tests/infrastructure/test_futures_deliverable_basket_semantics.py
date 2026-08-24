from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeContractValidationError,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    FuturesContractTerms,
)
from qore.infrastructure.futures_deliverable_basket_semantics import (
    FuturesConversionFactor,
    FuturesDeliverableBasketEntry,
    FuturesDeliverableBasketEvidenceRef,
    FuturesDeliverableBasketTerms,
    FuturesDeliverableBasketTermsId,
    FuturesDeliverableBasketValidationError,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    UniversalInstrumentIdentityValidationError,
)


def _id(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=value))


def _futures(
    *,
    settlement: DerivativeSettlementStyle = DerivativeSettlementStyle.PHYSICAL,
) -> FuturesContractTerms:
    first_notice_date = (
        date(2027, 2, 26)
        if settlement is DerivativeSettlementStyle.PHYSICAL
        else None
    )
    return FuturesContractTerms(
        terms_id=DerivativeTermsId(UUID(int=10)),
        instrument_identity_id=_id(11),
        reference_identity_id=_id(12),
        settlement_identity_id=_id(13),
        contract_month=DerivativeContractMonth(2027, 3),
        expiry_date=date(2027, 3, 22),
        multiplier=DerivativeContractMultiplier(Decimal("100000"), _id(14)),
        settlement_style=settlement,
        evidence_ref=DerivativeEvidenceRef(UUID(int=15)),
        first_notice_date=first_notice_date,
        last_trade_date=date(2027, 3, 19),
    )


def _entry(identity: int, factor: str) -> FuturesDeliverableBasketEntry:
    return FuturesDeliverableBasketEntry(
        _id(identity),
        FuturesConversionFactor(Decimal(factor)),
    )


def _basket(
    entries: tuple[FuturesDeliverableBasketEntry, ...],
) -> FuturesDeliverableBasketTerms:
    return FuturesDeliverableBasketTerms(
        terms_id=FuturesDeliverableBasketTermsId(UUID(int=20)),
        futures_terms=_futures(),
        entries=entries,
        evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
    )


def test_basket_is_canonical_and_retains_conversion_factor_material() -> None:
    first = _entry(31, "0.9123")
    second = _entry(30, "0.875")
    left = _basket((first, second))
    right = _basket((second, first))
    assert left.logical_values() == right.logical_values()
    assert left.entries == (second, first)


def test_same_deliverable_with_different_factor_does_not_collapse_identity() -> None:
    assert _entry(30, "0.875").logical_values() != _entry(30, "0.900").logical_values()


def test_duplicate_deliverable_identity_is_rejected_even_if_factor_differs() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError, match="identities must be unique"):
        _basket((_entry(30, "0.875"), _entry(30, "0.900")))


def test_self_deliverable_is_rejected() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError, match="cannot be its own deliverable"):
        _basket((_entry(11, "1"),))


def test_cash_settled_future_cannot_carry_deliverable_basket() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError, match="physically settled"):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            _futures(settlement=DerivativeSettlementStyle.CASH),
            (_entry(30, "0.875"),),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")])
def test_conversion_factor_must_be_positive_and_finite(value: Decimal) -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesConversionFactor(value)


def test_nested_futures_state_is_revalidated_fail_closed() -> None:
    futures = _futures()
    object.__setattr__(futures, "expiry_date", "2027-03-22")
    with pytest.raises(DerivativeContractValidationError):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)), futures, (_entry(30, "0.875"),), FuturesDeliverableBasketEvidenceRef(UUID(int=21))
        )


def test_corrupted_conversion_factor_is_revalidated_fail_closed() -> None:
    entry = _entry(30, "0.875")
    object.__setattr__(entry.conversion_factor, "value", Decimal("NaN"))
    with pytest.raises(FuturesDeliverableBasketValidationError, match="finite Decimal"):
        _basket((entry,))


def test_corrupted_deliverable_identity_is_revalidated_fail_closed() -> None:
    entry = _entry(30, "0.875")
    object.__setattr__(entry.deliverable_identity_id, "value", "not-a-uuid")
    with pytest.raises(UniversalInstrumentIdentityValidationError):
        _basket((entry,))


def test_corrupted_terms_id_is_revalidated_by_logical_values() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.terms_id, "value", "not-a-uuid")
    with pytest.raises(FuturesDeliverableBasketValidationError, match="terms id must be UUID"):
        basket.logical_values()


def test_corrupted_evidence_ref_is_revalidated_by_logical_values() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.evidence_ref, "value", "not-a-uuid")
    with pytest.raises(FuturesDeliverableBasketValidationError, match="evidence ref must be UUID"):
        basket.logical_values()


def test_exact_types_and_non_empty_entries_fail_closed() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)), _futures(), (), FuturesDeliverableBasketEvidenceRef(UUID(int=21))
        )
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesDeliverableBasketEntry("bond", FuturesConversionFactor(Decimal("1")))  # type: ignore[arg-type]


def test_all_parent_fields_are_material_to_logical_values() -> None:
    basket = _basket((_entry(30, "0.875"),))
    changed = replace(basket, evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=99)))
    assert basket.logical_values() != changed.logical_values()
