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
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


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
    assert left.logical_values()[3] == (
        (_id(30).logical_values(), ("0.875",)),
        (_id(31).logical_values(), ("0.9123",)),
    )


def test_same_deliverable_with_different_factor_does_not_collapse_identity() -> None:
    low = _entry(30, "0.875")
    high = _entry(30, "0.900")
    assert low.logical_values() != high.logical_values()


def test_duplicate_deliverable_identity_is_rejected_even_if_factor_differs() -> None:
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="identities must be unique",
    ):
        _basket((_entry(30, "0.875"), _entry(30, "0.900")))


def test_cash_settled_future_cannot_carry_deliverable_basket() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError, match="physically settled"):
        FuturesDeliverableBasketTerms(
            terms_id=FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures_terms=_futures(settlement=DerivativeSettlementStyle.CASH),
            entries=(_entry(30, "0.875"),),
            evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


@pytest.mark.parametrize(
    "value",
    [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")],
)
def test_conversion_factor_must_be_positive_and_finite(value: Decimal) -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesConversionFactor(value)


def test_nested_futures_state_is_revalidated_fail_closed() -> None:
    futures = _futures()
    object.__setattr__(futures, "expiry_date", "2027-03-22")
    with pytest.raises(DerivativeContractValidationError):
        FuturesDeliverableBasketTerms(
            terms_id=FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures_terms=futures,
            entries=(_entry(30, "0.875"),),
            evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


def test_exact_types_and_non_empty_entries_fail_closed() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesDeliverableBasketTerms(
            terms_id=FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures_terms=_futures(),
            entries=(),
            evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesDeliverableBasketEntry(
            "bond",  # type: ignore[arg-type]
            FuturesConversionFactor(Decimal("1")),
        )


def test_all_parent_fields_are_material_to_logical_values() -> None:
    basket = _basket((_entry(30, "0.875"),))
    changed = replace(
        basket,
        evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=99)),
    )
    assert basket.logical_values() != changed.logical_values()
