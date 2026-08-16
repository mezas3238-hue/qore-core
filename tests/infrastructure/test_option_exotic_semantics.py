from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeNotional,
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
from qore.infrastructure.option_exotic_semantics import (
    AsianAveragingMethodCode,
    AsianAveragingObservation,
    AsianAveragingPeriod,
    AsianAveragingRole,
    AsianAveragingScheduleCode,
    AsianOptionTerms,
    BarrierOptionTerms,
    DigitalOptionPayout,
    DigitalOptionTerms,
    DigitalOptionTrigger,
    DigitalPayoutAmount,
    DigitalPayoutKind,
    DigitalPayoutTiming,
    DigitalTouchCondition,
    DigitalTriggerStyle,
    OptionExoticValidationError,
)
from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredBarrierDirection,
    StructuredBarrierFeature,
    StructuredBarrierKindCode,
    StructuredContractLevel,
    StructuredContractLevelKind,
    StructuredEvidenceRef,
    StructuredFeatureId,
    StructuredLevelUnitCode,
    StructuredObservationMode,
    StructuredObservationScheduleCode,
    StructuredObservationTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _derivative_evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _structured_evidence(value: int) -> StructuredEvidenceRef:
    return StructuredEvidenceRef(_uuid(value))


def _strike(underlying: EconomicIdentityId) -> DerivativeStrike:
    return DerivativeStrike(
        value=Decimal("100"),
        basis=DerivativeStrikeBasis.PRICE,
        quote_identity_id=_identity(900),
        price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
    )


def _option(
    underlying: EconomicIdentityId,
    *,
    expiry: date = date(2026, 12, 18),
) -> OptionContractTerms:
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(100)),
        instrument_identity_id=_identity(101),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(102),
        right=OptionRight.CALL,
        strike=_strike(underlying),
        expiry_date=expiry,
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(103),
        notional=DerivativeNotional(Decimal("1000"), _identity(102)),
    )


def _barrier(
    underlying: EconomicIdentityId,
    *,
    feature_id: int = 200,
    kind: str = "knock-out",
    direction: StructuredBarrierDirection = StructuredBarrierDirection.AT_OR_ABOVE,
    observation: StructuredObservationTerms | None = None,
) -> StructuredBarrierFeature:
    return StructuredBarrierFeature(
        feature_id=StructuredFeatureId(_uuid(feature_id)),
        reference_identity_id=underlying,
        barrier_kind=StructuredBarrierKindCode(kind),
        direction=direction,
        level=StructuredContractLevel(
            value=Decimal("120"),
            kind=StructuredContractLevelKind.PRICE,
            reference_identity_id=underlying,
            unit=StructuredLevelUnitCode("currency-per-unit"),
        ),
        observation=observation
        or StructuredObservationTerms(mode=StructuredObservationMode.CONTINUOUS),
        evidence_ref=_structured_evidence(feature_id + 1),
    )


def _digital_payout(
    *,
    kind: DigitalPayoutKind = DigitalPayoutKind.CASH,
    timing: DigitalPayoutTiming = DigitalPayoutTiming.DEFERRED,
) -> DigitalOptionPayout:
    return DigitalOptionPayout(
        kind=kind,
        amount=DigitalPayoutAmount(Decimal("10"), _identity(102)),
        timing=timing,
        evidence_ref=_derivative_evidence(300),
    )


def _digital_trigger(
    underlying: EconomicIdentityId,
    *,
    style: DigitalTriggerStyle = DigitalTriggerStyle.TOUCH,
    touch_condition: DigitalTouchCondition | None = DigitalTouchCondition.TOUCH,
    observation: StructuredObservationTerms | None = None,
) -> DigitalOptionTrigger:
    return DigitalOptionTrigger(
        barrier=_barrier(underlying, observation=observation),
        style=style,
        touch_condition=touch_condition,
        evidence_ref=_derivative_evidence(301),
    )


def _digital_terms(
    underlying: EconomicIdentityId,
    trigger: DigitalOptionTrigger,
    *,
    expiry: date = date(2026, 12, 18),
    payout: DigitalOptionPayout | None = None,
) -> DigitalOptionTerms:
    return DigitalOptionTerms(
        terms_id=DerivativeTermsId(_uuid(302)),
        instrument_identity_id=_identity(303),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(102),
        expiry_date=expiry,
        triggers=(trigger,),
        payout=payout or _digital_payout(),
        evidence_ref=_derivative_evidence(304),
    )


def _period(
    *dates: date,
    schedule: str | None = None,
    weight: Decimal | None = None,
) -> AsianAveragingPeriod:
    return AsianAveragingPeriod(
        explicit_observations=tuple(
            AsianAveragingObservation(value, weight=weight) for value in dates
        ),
        schedule_code=AsianAveragingScheduleCode(schedule) if schedule is not None else None,
    )


def _asian(
    role: AsianAveragingRole,
    *,
    period_in: AsianAveragingPeriod | None = None,
    period_out: AsianAveragingPeriod | None = None,
    fixed_strike: DerivativeStrike | None = None,
    expiry: date = date(2026, 12, 18),
) -> AsianOptionTerms:
    underlying = _identity(400)
    return AsianOptionTerms(
        terms_id=DerivativeTermsId(_uuid(401)),
        instrument_identity_id=_identity(402),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(403),
        right=OptionRight.CALL,
        expiry_date=expiry,
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(404),
        averaging_role=role,
        averaging_method=AsianAveragingMethodCode("arithmetic"),
        averaging_period_in=period_in,
        averaging_period_out=period_out,
        fixed_strike=fixed_strike,
        notional=DerivativeNotional(Decimal("1000"), _identity(403)),
    )


def test_barrier_option_reuses_existing_structured_barrier() -> None:
    underlying = _identity(1)
    terms = BarrierOptionTerms(
        option=_option(underlying),
        barriers=(_barrier(underlying),),
        evidence_ref=_derivative_evidence(500),
    )
    assert terms.logical_values()[0] == "barrier-option"


def test_barrier_option_rejects_reference_mismatch() -> None:
    with pytest.raises(OptionExoticValidationError, match="reference"):
        BarrierOptionTerms(
            option=_option(_identity(1)),
            barriers=(_barrier(_identity(2)),),
            evidence_ref=_derivative_evidence(500),
        )


def test_barrier_option_rejects_duplicate_feature_ids_directly() -> None:
    underlying = _identity(1)
    left = _barrier(underlying, feature_id=200, kind="knock-out")
    right = _barrier(
        underlying,
        feature_id=200,
        kind="knock-in",
        direction=StructuredBarrierDirection.AT_OR_BELOW,
    )
    with pytest.raises(OptionExoticValidationError, match="feature ids"):
        BarrierOptionTerms(
            option=_option(underlying),
            barriers=(left, right),
            evidence_ref=_derivative_evidence(500),
        )


def test_barrier_option_canonicalizes_non_semantic_tuple_order() -> None:
    underlying = _identity(1)
    left = _barrier(underlying, feature_id=201)
    right = _barrier(underlying, feature_id=202)
    first = BarrierOptionTerms(
        _option(underlying),
        (left, right),
        _derivative_evidence(500),
    )
    second = BarrierOptionTerms(
        _option(underlying),
        (right, left),
        _derivative_evidence(500),
    )
    assert first.logical_values() == second.logical_values()


def test_barrier_kind_and_direction_remain_existing_umi09_logical_material() -> None:
    underlying = _identity(1)
    up_out = _barrier(underlying, kind="knock-out")
    down_out = _barrier(
        underlying,
        kind="knock-out",
        direction=StructuredBarrierDirection.AT_OR_BELOW,
    )
    up_in = _barrier(underlying, kind="knock-in")
    assert up_out.logical_values() != down_out.logical_values()
    assert up_out.logical_values() != up_in.logical_values()


def test_barrier_continuous_and_discrete_remain_distinct() -> None:
    underlying = _identity(1)
    continuous = _barrier(underlying)
    discrete = _barrier(
        underlying,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2026, 11, 18),),
        ),
    )
    assert continuous.logical_values() != discrete.logical_values()


def test_barrier_option_rejects_observation_after_expiry() -> None:
    underlying = _identity(1)
    barrier = _barrier(
        underlying,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2027, 1, 18),),
        ),
    )
    with pytest.raises(OptionExoticValidationError, match="must not follow expiry"):
        BarrierOptionTerms(
            _option(underlying),
            (barrier,),
            _derivative_evidence(500),
        )


def test_digital_expiry_trigger_forbids_touch_condition() -> None:
    with pytest.raises(OptionExoticValidationError, match="must not carry"):
        _digital_trigger(
            _identity(1),
            style=DigitalTriggerStyle.EXPIRY,
            touch_condition=DigitalTouchCondition.TOUCH,
        )


def test_digital_touch_trigger_requires_touch_condition() -> None:
    with pytest.raises(OptionExoticValidationError, match="requires"):
        _digital_trigger(
            _identity(1),
            style=DigitalTriggerStyle.TOUCH,
            touch_condition=None,
        )


def test_touch_and_no_touch_are_distinct_from_trigger_direction() -> None:
    underlying = _identity(1)
    touch = _digital_trigger(
        underlying,
        touch_condition=DigitalTouchCondition.TOUCH,
    )
    no_touch = _digital_trigger(
        underlying,
        touch_condition=DigitalTouchCondition.NO_TOUCH,
    )
    down_touch = DigitalOptionTrigger(
        barrier=_barrier(
            underlying,
            direction=StructuredBarrierDirection.AT_OR_BELOW,
        ),
        style=DigitalTriggerStyle.TOUCH,
        touch_condition=DigitalTouchCondition.TOUCH,
        evidence_ref=_derivative_evidence(301),
    )
    assert touch.logical_values() != no_touch.logical_values()
    assert touch.logical_values() != down_touch.logical_values()


def test_digital_payout_amount_requires_positive_finite_decimal() -> None:
    for value in (
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        1,
        1.0,
        True,
    ):
        with pytest.raises(OptionExoticValidationError):
            DigitalPayoutAmount(cast(Decimal, value), _identity(1))


def test_cash_and_asset_payouts_are_distinct() -> None:
    assert _digital_payout(kind=DigitalPayoutKind.CASH).logical_values() != _digital_payout(
        kind=DigitalPayoutKind.ASSET
    ).logical_values()


def test_immediate_and_deferred_payouts_are_distinct() -> None:
    assert _digital_payout(
        timing=DigitalPayoutTiming.IMMEDIATE
    ).logical_values() != _digital_payout(
        timing=DigitalPayoutTiming.DEFERRED
    ).logical_values()


def test_digital_terms_require_exactly_one_trigger_in_bounded_owner() -> None:
    underlying = _identity(1)
    with pytest.raises(OptionExoticValidationError, match="exactly one"):
        DigitalOptionTerms(
            DerivativeTermsId(_uuid(302)),
            _identity(303),
            underlying,
            _identity(102),
            date(2026, 12, 18),
            (),
            _digital_payout(),
            _derivative_evidence(304),
        )


def test_digital_terms_reject_trigger_reference_mismatch() -> None:
    trigger = _digital_trigger(_identity(2))
    with pytest.raises(OptionExoticValidationError, match="reference"):
        _digital_terms(_identity(1), trigger)


def test_digital_expiry_continuous_observation_rejected() -> None:
    underlying = _identity(1)
    trigger = _digital_trigger(
        underlying,
        style=DigitalTriggerStyle.EXPIRY,
        touch_condition=None,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.CONTINUOUS,
        ),
    )
    with pytest.raises(OptionExoticValidationError, match="continuous observation"):
        _digital_terms(underlying, trigger)


def test_digital_expiry_explicit_observation_must_equal_option_expiry() -> None:
    underlying = _identity(1)
    trigger = _digital_trigger(
        underlying,
        style=DigitalTriggerStyle.EXPIRY,
        touch_condition=None,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2026, 12, 17),),
        ),
    )
    with pytest.raises(OptionExoticValidationError, match="option expiry"):
        _digital_terms(underlying, trigger)


def test_digital_expiry_exact_explicit_observation_is_valid() -> None:
    underlying = _identity(1)
    expiry = date(2026, 12, 18)
    trigger = _digital_trigger(
        underlying,
        style=DigitalTriggerStyle.EXPIRY,
        touch_condition=None,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(expiry,),
        ),
    )
    assert _digital_terms(underlying, trigger, expiry=expiry).logical_values()[0] == (
        "digital-option"
    )


def test_digital_observation_after_expiry_rejected_independently() -> None:
    underlying = _identity(1)
    trigger = _digital_trigger(
        underlying,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2027, 1, 1),),
        ),
    )
    with pytest.raises(OptionExoticValidationError, match="must not follow expiry"):
        _digital_terms(underlying, trigger)


def test_digital_schedule_code_remains_static_and_not_resolved() -> None:
    underlying = _identity(1)
    trigger = _digital_trigger(
        underlying,
        observation=StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            schedule_code=StructuredObservationScheduleCode("monthly-close"),
        ),
    )
    assert _digital_terms(underlying, trigger).triggers[0].barrier.observation.schedule_code


def test_asian_schedule_only_period_is_valid() -> None:
    period = _period(schedule="monthly-business-day")
    assert period.logical_values()[1] == ("monthly-business-day",)


def test_asian_explicit_only_period_is_valid() -> None:
    period = _period(date(2026, 10, 1), date(2026, 11, 1))
    assert len(period.explicit_observations) == 2


def test_asian_period_allows_schedule_plus_explicit_additions() -> None:
    period = _period(date(2026, 10, 15), schedule="monthly-business-day")
    assert period.explicit_observations
    assert period.schedule_code is not None


def test_asian_period_requires_at_least_one_representation() -> None:
    with pytest.raises(OptionExoticValidationError, match="requires"):
        AsianAveragingPeriod()


def test_asian_period_rejects_duplicate_explicit_dates() -> None:
    with pytest.raises(OptionExoticValidationError, match="must be unique"):
        _period(date(2026, 10, 1), date(2026, 10, 1))


def test_asian_period_canonicalizes_observation_order() -> None:
    first = _period(date(2026, 11, 1), date(2026, 10, 1))
    second = _period(date(2026, 10, 1), date(2026, 11, 1))
    assert first.logical_values() == second.logical_values()


def test_asian_weight_requires_positive_finite_decimal() -> None:
    for value in (
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        1,
        1.0,
        True,
    ):
        with pytest.raises(OptionExoticValidationError):
            AsianAveragingObservation(
                date(2026, 10, 1),
                cast(Decimal, value),
            )


def test_asian_weights_are_retained_without_normalization() -> None:
    period = _period(
        date(2026, 10, 1),
        date(2026, 11, 1),
        weight=Decimal("2"),
    )
    assert period.explicit_observations[0].logical_values()[1] == "2"
    assert period.explicit_observations[1].logical_values()[1] == "2"


def test_asian_averaging_in_is_valid_without_fixed_strike() -> None:
    terms = _asian(
        AsianAveragingRole.IN,
        period_in=_period(date(2026, 10, 1), date(2026, 11, 1)),
    )
    assert terms.fixed_strike is None


def test_asian_averaging_in_rejects_fixed_strike() -> None:
    with pytest.raises(OptionExoticValidationError, match="must not carry"):
        _asian(
            AsianAveragingRole.IN,
            period_in=_period(date(2026, 10, 1)),
            fixed_strike=_strike(_identity(400)),
        )


def test_asian_averaging_in_requires_in_period_only() -> None:
    with pytest.raises(OptionExoticValidationError, match="only in period"):
        _asian(AsianAveragingRole.IN)


def test_asian_averaging_out_requires_fixed_strike() -> None:
    with pytest.raises(OptionExoticValidationError, match="requires fixed strike"):
        _asian(
            AsianAveragingRole.OUT,
            period_out=_period(date(2026, 10, 1)),
        )


def test_asian_averaging_out_is_valid_with_fixed_strike() -> None:
    terms = _asian(
        AsianAveragingRole.OUT,
        period_out=_period(date(2026, 10, 1)),
        fixed_strike=_strike(_identity(400)),
    )
    assert terms.fixed_strike is not None


def test_asian_averaging_both_requires_both_periods() -> None:
    with pytest.raises(OptionExoticValidationError, match="requires both"):
        _asian(
            AsianAveragingRole.BOTH,
            period_in=_period(date(2026, 10, 1)),
        )


def test_asian_averaging_both_rejects_fixed_strike() -> None:
    with pytest.raises(OptionExoticValidationError, match="must not carry"):
        _asian(
            AsianAveragingRole.BOTH,
            period_in=_period(date(2026, 10, 1)),
            period_out=_period(date(2026, 11, 1)),
            fixed_strike=_strike(_identity(400)),
        )


def test_asian_in_out_and_both_are_distinct_logical_material() -> None:
    in_terms = _asian(
        AsianAveragingRole.IN,
        period_in=_period(date(2026, 10, 1)),
    )
    out_terms = _asian(
        AsianAveragingRole.OUT,
        period_out=_period(date(2026, 10, 1)),
        fixed_strike=_strike(_identity(400)),
    )
    both_terms = _asian(
        AsianAveragingRole.BOTH,
        period_in=_period(date(2026, 10, 1)),
        period_out=_period(date(2026, 11, 1)),
    )
    logical_variants = {
        in_terms.logical_values(),
        out_terms.logical_values(),
        both_terms.logical_values(),
    }
    assert len(logical_variants) == 3


def test_asian_observation_after_expiry_rejected() -> None:
    with pytest.raises(OptionExoticValidationError, match="must not follow expiry"):
        _asian(
            AsianAveragingRole.IN,
            period_in=_period(date(2027, 1, 1)),
        )


def test_asian_method_code_is_extensible_but_canonical() -> None:
    assert AsianAveragingMethodCode("weighted-arithmetic").logical_values() == (
        "weighted-arithmetic",
    )
    with pytest.raises(OptionExoticValidationError):
        AsianAveragingMethodCode("Weighted Arithmetic")


def test_asian_requires_multiplier_or_notional() -> None:
    underlying = _identity(400)
    with pytest.raises(OptionExoticValidationError, match="multiplier"):
        AsianOptionTerms(
            terms_id=DerivativeTermsId(_uuid(401)),
            instrument_identity_id=_identity(402),
            underlying_identity_id=underlying,
            settlement_identity_id=_identity(403),
            right=OptionRight.CALL,
            expiry_date=date(2026, 12, 18),
            exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
            settlement_style=DerivativeSettlementStyle.CASH,
            evidence_ref=_derivative_evidence(404),
            averaging_role=AsianAveragingRole.IN,
            averaging_method=AsianAveragingMethodCode("arithmetic"),
            averaging_period_in=_period(date(2026, 10, 1)),
        )


def test_asian_allows_multiplier_sizing() -> None:
    underlying = _identity(400)
    terms = AsianOptionTerms(
        terms_id=DerivativeTermsId(_uuid(401)),
        instrument_identity_id=_identity(402),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(403),
        right=OptionRight.CALL,
        expiry_date=date(2026, 12, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(404),
        averaging_role=AsianAveragingRole.IN,
        averaging_method=AsianAveragingMethodCode("arithmetic"),
        averaging_period_in=_period(date(2026, 10, 1)),
        multiplier=DerivativeContractMultiplier(Decimal("100"), _identity(403)),
    )
    assert terms.multiplier is not None


def test_strict_date_rejects_datetime_for_asian_observation() -> None:
    with pytest.raises(OptionExoticValidationError):
        AsianAveragingObservation(datetime(2026, 10, 1))


def test_exotic_values_are_frozen_and_slotted() -> None:
    value = DigitalPayoutAmount(Decimal("1"), _identity(1))
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", Decimal("2"))
    assert not hasattr(value, "__dict__")


def test_static_terms_expose_no_operational_methods() -> None:
    prohibited = {
        "execute",
        "submit",
        "settle",
        "price",
        "calculate",
        "fetch",
        "refresh",
        "observe",
        "trigger_now",
    }
    for contract_type in (
        BarrierOptionTerms,
        DigitalOptionTerms,
        AsianOptionTerms,
    ):
        assert prohibited.isdisjoint(set(contract_type.__dict__))
