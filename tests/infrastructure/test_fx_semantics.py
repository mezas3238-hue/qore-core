from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.fx_semantics as fx
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativePriceQuoteBasisCode,
    DerivativeSettlementStyle,
    DerivativeStrike,
    DerivativeStrikeBasis,
    DerivativeTermsId,
    OptionContractTerms,
    OptionExerciseStyle,
    OptionExerciseTerms,
    OptionRight,
)
from qore.infrastructure.fx_semantics import (
    FxCurrencyAmount,
    FxCurrencyFlow,
    FxEvidenceRef,
    FxExchangeRate,
    FxFixingTerms,
    FxFlowDirection,
    FxForwardDeliveryKind,
    FxForwardTerms,
    FxNonDeliverableSettlementTerms,
    FxOptionBinding,
    FxOptionPremiumTerms,
    FxQuoteBasis,
    FxQuotedCurrencyPair,
    FxSpotTerms,
    FxSwapLegId,
    FxSwapLegTerms,
    FxSwapTerms,
    FxTermsId,
    FxValidationError,
    FxValueDates,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def _eid(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uid(value))


def _ev(value: int) -> FxEvidenceRef:
    return FxEvidenceRef(_uid(value))


def _terms_id(value: int) -> FxTermsId:
    return FxTermsId(_uid(value))


def _swap_leg_id(value: int) -> FxSwapLegId:
    return FxSwapLegId(_uid(value))


def _pair() -> FxQuotedCurrencyPair:
    return FxQuotedCurrencyPair(
        pair_identity_id=_eid(3),
        currency1_identity_id=_eid(1),
        currency2_identity_id=_eid(2),
        quote_basis=FxQuoteBasis.CURRENCY1_PER_CURRENCY2,
        evidence_ref=_ev(1),
    )


def _rate(pair: FxQuotedCurrencyPair, value: str = "1.1") -> FxExchangeRate:
    return FxExchangeRate(
        value=Decimal(value),
        pair_identity_id=pair.pair_identity_id,
        quote_basis=pair.quote_basis,
    )


def _flows(
    pair: FxQuotedCurrencyPair,
    *,
    reverse_roles: bool = False,
) -> tuple[FxCurrencyFlow, ...]:
    if reverse_roles:
        return (
            FxCurrencyFlow(
                FxFlowDirection.RECEIVE,
                FxCurrencyAmount(Decimal("100"), pair.currency1_identity_id),
            ),
            FxCurrencyFlow(
                FxFlowDirection.PAY,
                FxCurrencyAmount(Decimal("110"), pair.currency2_identity_id),
            ),
        )
    return (
        FxCurrencyFlow(
            FxFlowDirection.PAY,
            FxCurrencyAmount(Decimal("100"), pair.currency1_identity_id),
        ),
        FxCurrencyFlow(
            FxFlowDirection.RECEIVE,
            FxCurrencyAmount(Decimal("110"), pair.currency2_identity_id),
        ),
    )


def _spot() -> FxSpotTerms:
    pair = _pair()
    return FxSpotTerms(
        terms_id=_terms_id(1),
        instrument_identity_id=_eid(4),
        quoted_pair=pair,
        flows=_flows(pair),
        value_dates=FxValueDates(date(2026, 8, 18), date(2026, 8, 20)),
        agreed_exchange_rate=_rate(pair),
        evidence_ref=_ev(2),
    )


def _option_terms(pair: FxQuotedCurrencyPair) -> OptionContractTerms:
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uid(100)),
        instrument_identity_id=_eid(101),
        underlying_identity_id=pair.pair_identity_id,
        settlement_identity_id=pair.currency2_identity_id,
        right=OptionRight.CALL,
        strike=DerivativeStrike(
            value=Decimal("1.1"),
            basis=DerivativeStrikeBasis.PRICE,
            quote_identity_id=pair.currency2_identity_id,
            price_quote_basis=DerivativePriceQuoteBasisCode(
                "currency2-per-currency1"
            ),
        ),
        expiry_date=date(2026, 9, 18),
        exercise=OptionExerciseTerms(OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=DerivativeEvidenceRef(_uid(102)),
        multiplier=DerivativeContractMultiplier(
            Decimal("100"),
            pair.currency1_identity_id,
        ),
    )


def _swap_leg(
    *,
    pair: FxQuotedCurrencyPair,
    leg_id: int,
    reverse_roles: bool,
    currency1_date: date,
    currency2_date: date,
) -> FxSwapLegTerms:
    return FxSwapLegTerms(
        leg_id=_swap_leg_id(leg_id),
        quoted_pair=pair,
        flows=_flows(pair, reverse_roles=reverse_roles),
        value_dates=FxValueDates(currency1_date, currency2_date),
        agreed_exchange_rate=_rate(pair),
        evidence_ref=_ev(10 + leg_id),
    )


def _valid_swap() -> FxSwapTerms:
    pair = _pair()
    return FxSwapTerms(
        terms_id=_terms_id(3),
        instrument_identity_id=_eid(4),
        quoted_pair=pair,
        near_leg=_swap_leg(
            pair=pair,
            leg_id=1,
            reverse_roles=False,
            currency1_date=date(2026, 8, 18),
            currency2_date=date(2026, 8, 20),
        ),
        far_leg=_swap_leg(
            pair=pair,
            leg_id=2,
            reverse_roles=True,
            currency1_date=date(2026, 8, 25),
            currency2_date=date(2026, 8, 27),
        ),
        evidence_ref=_ev(20),
    )


def test_local_ids_are_frozen_and_slotted() -> None:
    terms_id = _terms_id(1)
    value_attribute = "value"
    extra_attribute = "extra"
    with pytest.raises(FrozenInstanceError):
        setattr(terms_id, value_attribute, _uid(2))
    with pytest.raises((AttributeError, TypeError)):
        setattr(terms_id, extra_attribute, "forbidden")


def test_pair_same_currency_rejected() -> None:
    with pytest.raises(FxValidationError):
        FxQuotedCurrencyPair(
            pair_identity_id=_eid(3),
            currency1_identity_id=_eid(1),
            currency2_identity_id=_eid(1),
            quote_basis=FxQuoteBasis.CURRENCY1_PER_CURRENCY2,
            evidence_ref=_ev(1),
        )


def test_pair_identity_cannot_equal_currency_identity() -> None:
    with pytest.raises(FxValidationError):
        FxQuotedCurrencyPair(
            pair_identity_id=_eid(1),
            currency1_identity_id=_eid(1),
            currency2_identity_id=_eid(2),
            quote_basis=FxQuoteBasis.CURRENCY1_PER_CURRENCY2,
            evidence_ref=_ev(1),
        )


def test_opposite_quote_basis_changes_logical_values() -> None:
    pair = _pair()
    opposite = replace(
        pair,
        quote_basis=FxQuoteBasis.CURRENCY2_PER_CURRENCY1,
    )
    assert pair.logical_values() != opposite.logical_values()


@pytest.mark.parametrize(
    "bad_value",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_currency_amount_rejects_invalid_decimals(bad_value: Decimal) -> None:
    with pytest.raises(FxValidationError):
        FxCurrencyAmount(bad_value, _eid(1))


def test_currency_amount_rejects_non_decimal() -> None:
    with pytest.raises(FxValidationError):
        FxCurrencyAmount(cast(Decimal, 1), _eid(1))


def test_exchange_rate_rejects_non_decimal() -> None:
    pair = _pair()
    with pytest.raises(FxValidationError):
        FxExchangeRate(
            cast(Decimal, 1.1),
            pair.pair_identity_id,
            pair.quote_basis,
        )


def test_flows_require_immutable_tuple() -> None:
    pair = _pair()
    with pytest.raises(FxValidationError):
        FxSpotTerms(
            terms_id=_terms_id(1),
            instrument_identity_id=_eid(4),
            quoted_pair=pair,
            flows=cast(tuple[FxCurrencyFlow, ...], list(_flows(pair))),
            value_dates=FxValueDates(date(2026, 8, 18), date(2026, 8, 20)),
            agreed_exchange_rate=_rate(pair),
            evidence_ref=_ev(2),
        )


def test_flows_require_one_pay_one_receive() -> None:
    pair = _pair()
    with pytest.raises(FxValidationError):
        FxSpotTerms(
            terms_id=_terms_id(1),
            instrument_identity_id=_eid(4),
            quoted_pair=pair,
            flows=(
                FxCurrencyFlow(
                    FxFlowDirection.PAY,
                    FxCurrencyAmount(Decimal("100"), pair.currency1_identity_id),
                ),
                FxCurrencyFlow(
                    FxFlowDirection.PAY,
                    FxCurrencyAmount(Decimal("110"), pair.currency2_identity_id),
                ),
            ),
            value_dates=FxValueDates(date(2026, 8, 18), date(2026, 8, 20)),
            agreed_exchange_rate=_rate(pair),
            evidence_ref=_ev(2),
        )


def test_flows_reject_third_currency() -> None:
    pair = _pair()
    with pytest.raises(FxValidationError):
        FxSpotTerms(
            terms_id=_terms_id(1),
            instrument_identity_id=_eid(4),
            quoted_pair=pair,
            flows=(
                FxCurrencyFlow(
                    FxFlowDirection.PAY,
                    FxCurrencyAmount(Decimal("100"), pair.currency1_identity_id),
                ),
                FxCurrencyFlow(
                    FxFlowDirection.RECEIVE,
                    FxCurrencyAmount(Decimal("110"), _eid(999)),
                ),
            ),
            value_dates=FxValueDates(date(2026, 8, 18), date(2026, 8, 20)),
            agreed_exchange_rate=_rate(pair),
            evidence_ref=_ev(2),
        )


def test_flow_caller_order_is_canonicalized() -> None:
    pair = _pair()
    direct = _spot()
    reversed_caller_order = replace(
        direct,
        flows=tuple(reversed(_flows(pair))),
    )
    assert direct.logical_values() == reversed_caller_order.logical_values()


def test_pay_receive_currency_roles_remain_distinct() -> None:
    direct = _spot()
    reversed_roles = replace(
        direct,
        flows=_flows(direct.quoted_pair, reverse_roles=True),
    )
    assert direct.logical_values() != reversed_roles.logical_values()


def test_value_dates_reject_datetime() -> None:
    with pytest.raises(FxValidationError):
        FxValueDates(
            cast(date, datetime(2026, 8, 18)),
            date(2026, 8, 20),
        )


def test_common_and_split_value_dates_are_representable() -> None:
    common = FxValueDates(date(2026, 8, 20), date(2026, 8, 20))
    split = FxValueDates(date(2026, 8, 18), date(2026, 8, 20))
    assert common.logical_values() != split.logical_values()


def test_valid_spot() -> None:
    assert _spot().logical_values()[0] == "fx-spot-terms"


def test_spot_rejects_rate_pair_mismatch() -> None:
    spot = _spot()
    with pytest.raises(FxValidationError):
        replace(
            spot,
            agreed_exchange_rate=FxExchangeRate(
                Decimal("1.1"),
                _eid(888),
                spot.quoted_pair.quote_basis,
            ),
        )


def test_spot_rejects_rate_quote_basis_mismatch() -> None:
    spot = _spot()
    with pytest.raises(FxValidationError):
        replace(
            spot,
            agreed_exchange_rate=FxExchangeRate(
                Decimal("1.1"),
                spot.quoted_pair.pair_identity_id,
                FxQuoteBasis.CURRENCY2_PER_CURRENCY1,
            ),
        )


def test_spot_rejects_instrument_pair_identity_collision() -> None:
    spot = _spot()
    with pytest.raises(FxValidationError):
        replace(
            spot,
            instrument_identity_id=spot.quoted_pair.pair_identity_id,
        )


def _valid_ndf() -> FxForwardTerms:
    pair = _pair()
    fixing = FxFixingTerms(date(2026, 8, 19), _eid(5), _ev(3))
    settlement = FxNonDeliverableSettlementTerms(
        settlement_currency_identity_id=pair.currency2_identity_id,
        fixing=fixing,
        settlement_date=date(2026, 8, 20),
        evidence_ref=_ev(4),
    )
    return FxForwardTerms(
        terms_id=_terms_id(2),
        instrument_identity_id=_eid(4),
        quoted_pair=pair,
        flows=_flows(pair),
        value_dates=FxValueDates(date(2026, 8, 18), date(2026, 8, 20)),
        agreed_exchange_rate=_rate(pair),
        delivery_kind=FxForwardDeliveryKind.NON_DELIVERABLE,
        non_deliverable_settlement=settlement,
        evidence_ref=_ev(5),
    )


def test_spot_and_forward_do_not_collapse() -> None:
    spot = _spot()
    pair = spot.quoted_pair
    forward = FxForwardTerms(
        terms_id=_terms_id(2),
        instrument_identity_id=spot.instrument_identity_id,
        quoted_pair=pair,
        flows=spot.flows,
        value_dates=spot.value_dates,
        agreed_exchange_rate=spot.agreed_exchange_rate,
        delivery_kind=FxForwardDeliveryKind.DELIVERABLE,
        evidence_ref=_ev(5),
    )
    assert spot.logical_values()[0] != forward.logical_values()[0]


def test_deliverable_and_ndf_do_not_collapse() -> None:
    ndf = _valid_ndf()
    deliverable = replace(
        ndf,
        delivery_kind=FxForwardDeliveryKind.DELIVERABLE,
        non_deliverable_settlement=None,
    )
    assert ndf.logical_values() != deliverable.logical_values()


def test_deliverable_rejects_ndf_settlement() -> None:
    ndf = _valid_ndf()
    with pytest.raises(FxValidationError):
        replace(ndf, delivery_kind=FxForwardDeliveryKind.DELIVERABLE)


def test_ndf_requires_settlement_terms() -> None:
    ndf = _valid_ndf()
    with pytest.raises(FxValidationError):
        replace(ndf, non_deliverable_settlement=None)


def test_ndf_rejects_fixing_after_settlement_date() -> None:
    with pytest.raises(FxValidationError):
        FxNonDeliverableSettlementTerms(
            settlement_currency_identity_id=_eid(2),
            fixing=FxFixingTerms(date(2026, 8, 21), _eid(5), _ev(3)),
            settlement_date=date(2026, 8, 20),
            evidence_ref=_ev(4),
        )


def test_fixing_terms_have_no_current_observed_value_slot() -> None:
    assert {field.name for field in fields(FxFixingTerms)} == {
        "fixing_date",
        "fixing_reference_identity_id",
        "evidence_ref",
    }


def test_valid_fx_swap() -> None:
    assert _valid_swap().logical_values()[0] == "fx-swap-terms"


def test_fx_swap_rejects_non_reversing_roles() -> None:
    swap = _valid_swap()
    with pytest.raises(FxValidationError):
        replace(
            swap,
            far_leg=replace(
                swap.far_leg,
                flows=_flows(swap.quoted_pair, reverse_roles=False),
            ),
        )


def test_fx_swap_rejects_duplicate_leg_ids() -> None:
    swap = _valid_swap()
    with pytest.raises(FxValidationError):
        replace(
            swap,
            far_leg=replace(swap.far_leg, leg_id=swap.near_leg.leg_id),
        )


def test_fx_swap_rejects_non_later_currency1_far_date() -> None:
    swap = _valid_swap()
    with pytest.raises(FxValidationError):
        replace(
            swap,
            far_leg=replace(
                swap.far_leg,
                value_dates=replace(
                    swap.far_leg.value_dates,
                    currency1_value_date=swap.near_leg.value_dates.currency1_value_date,
                ),
            ),
        )


def test_fx_swap_rejects_non_later_currency2_far_date() -> None:
    swap = _valid_swap()
    with pytest.raises(FxValidationError):
        replace(
            swap,
            far_leg=replace(
                swap.far_leg,
                value_dates=replace(
                    swap.far_leg.value_dates,
                    currency2_value_date=swap.near_leg.value_dates.currency2_value_date,
                ),
            ),
        )


def test_fx_swap_rejects_pair_mismatch() -> None:
    swap = _valid_swap()
    other_pair = replace(swap.quoted_pair, pair_identity_id=_eid(300))
    with pytest.raises(FxValidationError):
        replace(swap, far_leg=replace(swap.far_leg, quoted_pair=other_pair))


def _valid_option_binding() -> FxOptionBinding:
    pair = _pair()
    return FxOptionBinding(
        option_terms=_option_terms(pair),
        quoted_pair=pair,
        put_currency_amount=FxCurrencyAmount(
            Decimal("100"),
            pair.currency1_identity_id,
        ),
        call_currency_amount=FxCurrencyAmount(
            Decimal("110"),
            pair.currency2_identity_id,
        ),
        evidence_ref=_ev(8),
    )


def test_valid_fx_option_binding_uses_real_generic_option() -> None:
    binding = _valid_option_binding()
    assert binding.logical_values()[0] == "fx-option-binding"
    assert binding.option_terms.logical_values()[0] == "option"


def test_fx_option_rejects_underlying_pair_mismatch() -> None:
    binding = _valid_option_binding()
    invalid_option = replace(binding.option_terms, underlying_identity_id=_eid(999))
    with pytest.raises(FxValidationError):
        replace(binding, option_terms=invalid_option)


def test_fx_option_same_currency_rejected() -> None:
    binding = _valid_option_binding()
    with pytest.raises(FxValidationError):
        replace(
            binding,
            call_currency_amount=FxCurrencyAmount(
                Decimal("110"),
                binding.quoted_pair.currency1_identity_id,
            ),
        )


def test_fx_option_rejects_third_currency_amount() -> None:
    binding = _valid_option_binding()
    with pytest.raises(FxValidationError):
        replace(
            binding,
            call_currency_amount=FxCurrencyAmount(Decimal("110"), _eid(999)),
        )


def test_fx_option_reverse_put_call_changes_logical_values() -> None:
    binding = _valid_option_binding()
    reversed_binding = replace(
        binding,
        put_currency_amount=FxCurrencyAmount(
            Decimal("100"),
            binding.quoted_pair.currency2_identity_id,
        ),
        call_currency_amount=FxCurrencyAmount(
            Decimal("110"),
            binding.quoted_pair.currency1_identity_id,
        ),
    )
    assert binding.logical_values() != reversed_binding.logical_values()


def test_fx_option_premium_terms_are_static() -> None:
    premium = FxOptionPremiumTerms(
        amount=FxCurrencyAmount(Decimal("1"), _eid(2)),
        payment_date=date(2026, 8, 20),
        evidence_ref=_ev(9),
    )
    binding = replace(_valid_option_binding(), premium=premium)
    assert binding.premium == premium
    assert {field.name for field in fields(FxOptionPremiumTerms)} == {
        "amount",
        "payment_date",
        "evidence_ref",
    }


def test_module_has_no_runtime_side_effect_authority() -> None:
    source = inspect.getsource(fx)
    forbidden = (
        "uuid4(",
        "datetime.now(",
        "time.time(",
        "random.",
        "requests.",
        "httpx.",
        "subprocess.",
        "threading.",
        ".execute(",
        ".submit(",
        ".settle(",
    )
    for marker in forbidden:
        assert marker not in source
