from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeContractValidationError,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    DerivativeTickValue,
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


class _CollidingUUID(UUID):
    def __str__(self) -> str:
        return "collision"


class _DecimalSubclass(Decimal):
    pass


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


def _basket_with_futures(futures: FuturesContractTerms) -> FuturesDeliverableBasketTerms:
    return FuturesDeliverableBasketTerms(
        terms_id=FuturesDeliverableBasketTermsId(UUID(int=20)),
        futures_terms=futures,
        entries=(_entry(30, "0.875"),),
        evidence_ref=FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
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
    assert _entry(30, "0.875").logical_values() != _entry(
        30, "0.900"
    ).logical_values()


def test_high_precision_conversion_factors_do_not_collapse() -> None:
    first = FuturesConversionFactor(Decimal("0.1234567890123456789012345678901"))
    second = FuturesConversionFactor(Decimal("0.1234567890123456789012345678909"))
    assert first.value != second.value
    assert first.logical_values() != second.logical_values()


def test_conversion_factor_logical_values_ignore_ambient_decimal_context() -> None:
    factor = FuturesConversionFactor(Decimal("0.123456789012345678901234567890"))
    baseline = factor.logical_values()
    with localcontext() as context:
        context.prec = 5
        assert factor.logical_values() == baseline


def test_extreme_exponent_conversion_factor_uses_compact_logical_material() -> None:
    logical_values = FuturesConversionFactor(Decimal("1E+1000000")).logical_values()
    assert logical_values == ("1e+1000000",)
    assert len(logical_values[0]) < 32


def test_composed_futures_projection_matches_umi05_for_normal_decimal_values() -> None:
    futures = replace(
        _futures(),
        tick_value=DerivativeTickValue(Decimal("12.5"), _id(16)),
    )
    basket = _basket_with_futures(futures)
    assert basket.logical_values()[2] == futures.logical_values()


def test_composed_futures_high_precision_multiplier_does_not_collapse() -> None:
    first_futures = replace(
        _futures(),
        multiplier=DerivativeContractMultiplier(
            Decimal("1234567890123456789012345678901"),
            _id(14),
        ),
    )
    second_futures = replace(
        _futures(),
        multiplier=DerivativeContractMultiplier(
            Decimal("1234567890123456789012345678909"),
            _id(14),
        ),
    )
    assert first_futures.multiplier.value != second_futures.multiplier.value
    assert _basket_with_futures(first_futures).logical_values() != _basket_with_futures(
        second_futures
    ).logical_values()


def test_composed_futures_decimal_leaves_ignore_ambient_context() -> None:
    futures = replace(
        _futures(),
        multiplier=DerivativeContractMultiplier(
            Decimal("123456789012345678901234567890"),
            _id(14),
        ),
        tick_value=DerivativeTickValue(
            Decimal("0.987654321098765432109876543210"),
            _id(16),
        ),
    )
    basket = _basket_with_futures(futures)
    baseline = basket.logical_values()
    with localcontext() as context:
        context.prec = 5
        assert basket.logical_values() == baseline


def test_composed_futures_extreme_decimal_leaves_stay_compact() -> None:
    futures = replace(
        _futures(),
        multiplier=DerivativeContractMultiplier(Decimal("1E+1000000"), _id(14)),
        tick_value=DerivativeTickValue(Decimal("1E-1000000"), _id(16)),
    )
    futures_values = _basket_with_futures(futures).logical_values()[2]
    multiplier_text = futures_values[7][0]
    tick_text = futures_values[10][0]
    assert multiplier_text == "1e+1000000"
    assert tick_text == "1e-1000000"
    assert len(multiplier_text) < 32
    assert len(tick_text) < 32


def test_duplicate_deliverable_identity_is_rejected_even_if_factor_differs() -> None:
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="identities must be unique",
    ):
        _basket((_entry(30, "0.875"), _entry(30, "0.900")))


def test_self_deliverable_is_rejected() -> None:
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="cannot be its own deliverable",
    ):
        _basket((_entry(11, "1"),))


def test_cash_settled_future_cannot_carry_deliverable_basket() -> None:
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="physically settled",
    ):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            _futures(settlement=DerivativeSettlementStyle.CASH),
            (_entry(30, "0.875"),),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
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
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures,
            (_entry(30, "0.875"),),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


def test_corrupted_nested_futures_identity_is_revalidated_fail_closed() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(
        basket.futures_terms.instrument_identity_id,
        "value",
        "not-a-uuid",
    )
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures instrument identity value must be exact UUID",
    ):
        basket.logical_values()


def test_corrupted_nested_futures_terms_id_is_revalidated_fail_closed() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.futures_terms.terms_id, "value", "not-a-uuid")
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures terms_id value must be exact UUID",
    ):
        basket.logical_values()


def test_corrupted_nested_futures_evidence_is_revalidated_fail_closed() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.futures_terms.evidence_ref, "value", "not-a-uuid")
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures evidence_ref value must be exact UUID",
    ):
        basket.logical_values()


def test_corrupted_nested_futures_multiplier_is_revalidated_fail_closed() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.futures_terms.multiplier, "value", "not-a-decimal")
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures multiplier value must be exact Decimal",
    ):
        basket.logical_values()


def test_uuid_subclass_cannot_collapse_deliverable_identity() -> None:
    first = EconomicIdentityId(_CollidingUUID(int=30))
    second = EconomicIdentityId(_CollidingUUID(int=31))
    assert first != second
    assert first.logical_values() == second.logical_values()
    for identity in (first, second):
        with pytest.raises(
            FuturesDeliverableBasketValidationError,
            match="deliverable identity value must be exact UUID",
        ):
            FuturesDeliverableBasketEntry(
                identity,
                FuturesConversionFactor(Decimal("0.875")),
            )


def test_uuid_subclass_in_reused_futures_leaf_is_rejected() -> None:
    futures = _futures()
    object.__setattr__(futures.terms_id, "value", _CollidingUUID(int=10))
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures terms_id value must be exact UUID",
    ):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures,
            (_entry(30, "0.875"),),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


def test_decimal_subclass_in_multiplier_is_rejected() -> None:
    futures = _futures()
    object.__setattr__(futures.multiplier, "value", _DecimalSubclass("100000"))
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures multiplier value must be exact Decimal",
    ):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures,
            (_entry(30, "0.875"),),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


def test_decimal_subclass_in_tick_value_is_rejected() -> None:
    futures = replace(
        _futures(),
        tick_value=DerivativeTickValue(Decimal("12.5"), _id(16)),
    )
    assert futures.tick_value is not None
    object.__setattr__(futures.tick_value, "value", _DecimalSubclass("12.5"))
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="futures tick_value value must be exact Decimal",
    ):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            futures,
            (_entry(30, "0.875"),),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
        )


def test_corrupted_conversion_factor_is_revalidated_fail_closed() -> None:
    entry = _entry(30, "0.875")
    object.__setattr__(entry.conversion_factor, "value", Decimal("NaN"))
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="finite Decimal",
    ):
        _basket((entry,))


def test_corrupted_deliverable_identity_is_revalidated_fail_closed() -> None:
    entry = _entry(30, "0.875")
    object.__setattr__(entry.deliverable_identity_id, "value", "not-a-uuid")
    with pytest.raises(FuturesDeliverableBasketValidationError):
        _basket((entry,))


def test_corrupted_terms_id_is_revalidated_by_logical_values() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.terms_id, "value", "not-a-uuid")
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="terms id must be UUID",
    ):
        basket.logical_values()


def test_corrupted_evidence_ref_is_revalidated_by_logical_values() -> None:
    basket = _basket((_entry(30, "0.875"),))
    object.__setattr__(basket.evidence_ref, "value", "not-a-uuid")
    with pytest.raises(
        FuturesDeliverableBasketValidationError,
        match="evidence ref must be UUID",
    ):
        basket.logical_values()


def test_exact_types_and_non_empty_entries_fail_closed() -> None:
    with pytest.raises(FuturesDeliverableBasketValidationError):
        FuturesDeliverableBasketTerms(
            FuturesDeliverableBasketTermsId(UUID(int=20)),
            _futures(),
            (),
            FuturesDeliverableBasketEvidenceRef(UUID(int=21)),
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
