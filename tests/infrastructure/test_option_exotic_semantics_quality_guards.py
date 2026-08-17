from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
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
    AsianAveragingLiteralDate,
    AsianAveragingLiteralDateTime,
    AsianAveragingMethodCode,
    AsianAveragingObservation,
    AsianAveragingObservationKind,
    AsianAveragingPeriod,
    AsianAveragingRole,
    AsianAveragingScheduleCode,
    AsianAveragingScheduleObservation,
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


def _strike() -> DerivativeStrike:
    return DerivativeStrike(
        value=Decimal("100"),
        basis=DerivativeStrikeBasis.PRICE,
        quote_identity_id=_identity(900),
        price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
    )


def _option(underlying: EconomicIdentityId) -> OptionContractTerms:
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(100)),
        instrument_identity_id=_identity(101),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(102),
        right=OptionRight.CALL,
        strike=_strike(),
        expiry_date=date(2026, 12, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(103),
        notional=DerivativeNotional(Decimal("1000"), _identity(102)),
    )


def _barrier(underlying: EconomicIdentityId) -> StructuredBarrierFeature:
    return StructuredBarrierFeature(
        feature_id=StructuredFeatureId(_uuid(200)),
        reference_identity_id=underlying,
        barrier_kind=StructuredBarrierKindCode("knock-out"),
        direction=StructuredBarrierDirection.AT_OR_ABOVE,
        level=StructuredContractLevel(
            value=Decimal("120"),
            kind=StructuredContractLevelKind.PRICE,
            reference_identity_id=underlying,
            unit=StructuredLevelUnitCode("currency-per-unit"),
        ),
        observation=StructuredObservationTerms(mode=StructuredObservationMode.CONTINUOUS),
        evidence_ref=_structured_evidence(201),
    )


def _payout() -> DigitalOptionPayout:
    return DigitalOptionPayout(
        kind=DigitalPayoutKind.CASH,
        amount=DigitalPayoutAmount(Decimal("10"), _identity(102)),
        timing=DigitalPayoutTiming.DEFERRED,
        evidence_ref=_derivative_evidence(300),
    )


def _trigger(underlying: EconomicIdentityId) -> DigitalOptionTrigger:
    return DigitalOptionTrigger(
        barrier=_barrier(underlying),
        style=DigitalTriggerStyle.TOUCH,
        touch_condition=DigitalTouchCondition.TOUCH,
        evidence_ref=_derivative_evidence(301),
    )


def _digital_terms() -> DigitalOptionTerms:
    underlying = _identity(1)
    return DigitalOptionTerms(
        terms_id=DerivativeTermsId(_uuid(302)),
        instrument_identity_id=_identity(303),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(102),
        expiry_date=date(2026, 12, 18),
        triggers=(_trigger(underlying),),
        payout=_payout(),
        evidence_ref=_derivative_evidence(304),
    )


def _literal_date(value: int) -> AsianAveragingLiteralDate:
    return AsianAveragingLiteralDate(date(2026, 10, value))


def _literal_datetime(
    value: int,
    hour: int,
    tz: timezone = timezone.utc,
) -> AsianAveragingLiteralDateTime:
    return AsianAveragingLiteralDateTime(
        datetime(2026, 10, value, hour, 0, tzinfo=tz)
    )


def _schedule_observation(
    code: str,
    number: int,
) -> AsianAveragingScheduleObservation:
    return AsianAveragingScheduleObservation(
        schedule_code=AsianAveragingScheduleCode(code),
        observation_number=number,
    )


def _period(
    *days: int,
    kind: AsianAveragingObservationKind = AsianAveragingObservationKind.UNWEIGHTED,
) -> AsianAveragingPeriod:
    return AsianAveragingPeriod(
        explicit_observations=tuple(
            AsianAveragingObservation(_literal_date(day)) for day in days
        ),
        observation_kind=kind,
    )


def _asian_in() -> AsianOptionTerms:
    return AsianOptionTerms(
        terms_id=DerivativeTermsId(_uuid(401)),
        instrument_identity_id=_identity(402),
        underlying_identity_id=_identity(400),
        settlement_identity_id=_identity(403),
        right=OptionRight.CALL,
        expiry_date=date(2026, 12, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(404),
        averaging_role=AsianAveragingRole.IN,
        averaging_method=AsianAveragingMethodCode("arithmetic"),
        averaging_period_in=_period(1),
        notional=DerivativeNotional(Decimal("1000"), _identity(403)),
    )


def _asian_out() -> AsianOptionTerms:
    return AsianOptionTerms(
        terms_id=DerivativeTermsId(_uuid(411)),
        instrument_identity_id=_identity(412),
        underlying_identity_id=_identity(410),
        settlement_identity_id=_identity(413),
        right=OptionRight.PUT,
        expiry_date=date(2026, 12, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(414),
        averaging_role=AsianAveragingRole.OUT,
        averaging_method=AsianAveragingMethodCode("arithmetic"),
        averaging_period_out=_period(2),
        fixed_strike=_strike(),
        multiplier=DerivativeContractMultiplier(Decimal("100"), _identity(413)),
    )


def test_schedule_code_rejects_wrong_type_length_and_noncanonical_syntax() -> None:
    for value in (cast(str, 1), "a" * 65, "Monthly Close"):
        with pytest.raises(OptionExoticValidationError, match="canonical lowercase"):
            AsianAveragingScheduleCode(value)


def test_digital_payout_amount_rejects_invalid_unit_identity_directly() -> None:
    with pytest.raises(OptionExoticValidationError, match="payout unit identity"):
        DigitalPayoutAmount(
            Decimal("1"),
            cast(EconomicIdentityId, object()),
        )


def test_digital_option_payout_rejects_each_invalid_component_type_directly() -> None:
    valid = _payout()
    with pytest.raises(OptionExoticValidationError, match="payout kind"):
        replace(valid, kind=cast(DigitalPayoutKind, "cash"))
    with pytest.raises(OptionExoticValidationError, match="payout amount"):
        replace(valid, amount=cast(DigitalPayoutAmount, object()))
    with pytest.raises(OptionExoticValidationError, match="payout timing"):
        replace(valid, timing=cast(DigitalPayoutTiming, "deferred"))
    with pytest.raises(OptionExoticValidationError, match="payout evidence"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_digital_trigger_rejects_each_invalid_component_type_directly() -> None:
    valid = _trigger(_identity(1))
    with pytest.raises(OptionExoticValidationError, match="reuse StructuredBarrierFeature"):
        replace(valid, barrier=cast(StructuredBarrierFeature, object()))
    with pytest.raises(OptionExoticValidationError, match="trigger style"):
        replace(valid, style=cast(DigitalTriggerStyle, "touch"))
    with pytest.raises(OptionExoticValidationError, match="touch condition"):
        replace(valid, touch_condition=cast(DigitalTouchCondition, "touch"))
    with pytest.raises(OptionExoticValidationError, match="trigger evidence"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_barrier_option_rejects_structural_type_guards_directly() -> None:
    underlying = _identity(1)
    valid = BarrierOptionTerms(
        option=_option(underlying),
        barriers=(_barrier(underlying),),
        evidence_ref=_derivative_evidence(500),
    )
    with pytest.raises(OptionExoticValidationError, match="compose OptionContractTerms"):
        replace(valid, option=cast(OptionContractTerms, object()))
    with pytest.raises(OptionExoticValidationError, match="immutable non-empty barriers"):
        replace(
            valid,
            barriers=cast(tuple[StructuredBarrierFeature, ...], [valid.barriers[0]]),
        )
    with pytest.raises(OptionExoticValidationError, match="immutable non-empty barriers"):
        replace(valid, barriers=())
    with pytest.raises(OptionExoticValidationError, match="reuse StructuredBarrierFeature"):
        replace(
            valid,
            barriers=(cast(StructuredBarrierFeature, object()),),
        )
    with pytest.raises(OptionExoticValidationError, match="barrier option evidence"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_digital_terms_reject_identifier_and_identity_type_guards_directly() -> None:
    valid = _digital_terms()
    with pytest.raises(OptionExoticValidationError, match="terms_id"):
        replace(valid, terms_id=cast(DerivativeTermsId, object()))
    with pytest.raises(OptionExoticValidationError, match="instrument identity"):
        replace(valid, instrument_identity_id=cast(EconomicIdentityId, object()))
    with pytest.raises(OptionExoticValidationError, match="underlying identity"):
        replace(valid, underlying_identity_id=cast(EconomicIdentityId, object()))
    with pytest.raises(OptionExoticValidationError, match="settlement identity"):
        replace(valid, settlement_identity_id=cast(EconomicIdentityId, object()))


def test_digital_terms_reject_identity_collisions_directly() -> None:
    valid = _digital_terms()
    with pytest.raises(OptionExoticValidationError, match="instrument and underlying"):
        replace(valid, instrument_identity_id=valid.underlying_identity_id)
    with pytest.raises(OptionExoticValidationError, match="instrument and settlement"):
        replace(valid, instrument_identity_id=valid.settlement_identity_id)


def test_digital_terms_reject_strict_expiry_and_trigger_shape_types_directly() -> None:
    valid = _digital_terms()
    with pytest.raises(OptionExoticValidationError, match="digital expiry"):
        replace(valid, expiry_date=datetime(2026, 12, 18))
    with pytest.raises(OptionExoticValidationError, match="exactly one trigger"):
        replace(
            valid,
            triggers=cast(tuple[DigitalOptionTrigger, ...], [valid.triggers[0]]),
        )
    with pytest.raises(OptionExoticValidationError, match="trigger has invalid type"):
        replace(valid, triggers=(cast(DigitalOptionTrigger, object()),))


def test_digital_terms_reject_invalid_payout_and_evidence_types_directly() -> None:
    valid = _digital_terms()
    with pytest.raises(OptionExoticValidationError, match="payout has invalid type"):
        replace(valid, payout=cast(DigitalOptionPayout, object()))
    with pytest.raises(OptionExoticValidationError, match="option evidence"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_asian_period_rejects_container_item_schedule_and_kind_types_directly() -> None:
    valid = _period(1)
    with pytest.raises(OptionExoticValidationError, match="immutable tuple"):
        replace(
            valid,
            explicit_observations=cast(
                tuple[AsianAveragingObservation, ...],
                [valid.explicit_observations[0]],
            ),
        )
    with pytest.raises(OptionExoticValidationError, match="observation has invalid type"):
        replace(
            valid,
            explicit_observations=(cast(AsianAveragingObservation, object()),),
        )
    with pytest.raises(OptionExoticValidationError, match="schedule code has invalid type"):
        replace(
            valid,
            schedule_codes=(
                cast(AsianAveragingScheduleCode, object()),
            ),
        )
    with pytest.raises(OptionExoticValidationError, match="observation kind has invalid type"):
        replace(
            valid,
            observation_kind=cast(AsianAveragingObservationKind, "unweighted"),
        )


def test_asian_period_rejects_schedule_codes_list_container_directly() -> None:
    valid = _period(1)
    with pytest.raises(OptionExoticValidationError, match="immutable tuple"):
        replace(
            valid,
            schedule_codes=cast(
                tuple[AsianAveragingScheduleCode, ...],
                [AsianAveragingScheduleCode("monthly")],
            ),
        )


def test_asian_terms_reject_identifier_and_identity_type_guards_directly() -> None:
    valid = _asian_in()
    with pytest.raises(OptionExoticValidationError, match="terms_id"):
        replace(valid, terms_id=cast(DerivativeTermsId, object()))
    with pytest.raises(OptionExoticValidationError, match="instrument identity"):
        replace(valid, instrument_identity_id=cast(EconomicIdentityId, object()))
    with pytest.raises(OptionExoticValidationError, match="underlying identity"):
        replace(valid, underlying_identity_id=cast(EconomicIdentityId, object()))
    with pytest.raises(OptionExoticValidationError, match="settlement identity"):
        replace(valid, settlement_identity_id=cast(EconomicIdentityId, object()))


def test_asian_terms_reject_identity_collisions_directly() -> None:
    valid = _asian_in()
    with pytest.raises(OptionExoticValidationError, match="instrument and underlying"):
        replace(valid, instrument_identity_id=valid.underlying_identity_id)
    with pytest.raises(OptionExoticValidationError, match="instrument and settlement"):
        replace(valid, instrument_identity_id=valid.settlement_identity_id)


def test_asian_terms_reject_core_contract_type_guards_directly() -> None:
    valid = _asian_in()
    with pytest.raises(OptionExoticValidationError, match="right has invalid type"):
        replace(valid, right=cast(OptionRight, "call"))
    with pytest.raises(OptionExoticValidationError, match="asian expiry"):
        replace(valid, expiry_date=datetime(2026, 12, 18))
    with pytest.raises(OptionExoticValidationError, match="exercise has invalid type"):
        replace(valid, exercise=cast(OptionExerciseTerms, object()))
    with pytest.raises(OptionExoticValidationError, match="settlement style"):
        replace(valid, settlement_style=cast(DerivativeSettlementStyle, "cash"))
    with pytest.raises(OptionExoticValidationError, match="asian evidence"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_asian_terms_reject_exercise_chronology_directly() -> None:
    valid = _asian_in()
    with pytest.raises(OptionExoticValidationError, match="American start"):
        replace(
            valid,
            exercise=OptionExerciseTerms(
                style=OptionExerciseStyle.AMERICAN,
                american_start_date=date(2027, 1, 1),
            ),
        )
    with pytest.raises(OptionExoticValidationError, match="Bermudan date"):
        replace(
            valid,
            exercise=OptionExerciseTerms(
                style=OptionExerciseStyle.BERMUDAN,
                bermudan_dates=(date(2027, 1, 1),),
            ),
        )


def test_asian_terms_reject_averaging_component_type_guards_directly() -> None:
    valid = _asian_in()
    with pytest.raises(OptionExoticValidationError, match="averaging role"):
        replace(valid, averaging_role=cast(AsianAveragingRole, "in"))
    with pytest.raises(OptionExoticValidationError, match="averaging method"):
        replace(valid, averaging_method=cast(AsianAveragingMethodCode, object()))
    with pytest.raises(OptionExoticValidationError, match="averaging-in period"):
        replace(valid, averaging_period_in=cast(AsianAveragingPeriod, object()))
    with pytest.raises(OptionExoticValidationError, match="averaging-out period"):
        replace(valid, averaging_period_out=cast(AsianAveragingPeriod, object()))
    with pytest.raises(OptionExoticValidationError, match="fixed strike"):
        replace(valid, fixed_strike=cast(DerivativeStrike, object()))
    with pytest.raises(OptionExoticValidationError, match="strike factor must be finite Decimal"):
        replace(valid, strike_factor=cast(Decimal, "1"))
    with pytest.raises(OptionExoticValidationError, match="multiplier has invalid type"):
        replace(valid, multiplier=cast(DerivativeContractMultiplier, object()))
    with pytest.raises(OptionExoticValidationError, match="notional has invalid type"):
        replace(valid, notional=cast(DerivativeNotional, object()))


def test_asian_in_and_out_reject_opposite_periods_directly() -> None:
    asian_in = _asian_in()
    with pytest.raises(OptionExoticValidationError, match="only in period"):
        replace(asian_in, averaging_period_out=_period(2))

    asian_out = _asian_out()
    with pytest.raises(OptionExoticValidationError, match="only out period"):
        replace(asian_out, averaging_period_in=_period(1))


def test_asian_literal_date_and_datetime_are_strict_locators() -> None:
    with pytest.raises(OptionExoticValidationError, match="must be date"):
        AsianAveragingLiteralDate(cast(date, datetime(2026, 10, 1)))
    with pytest.raises(OptionExoticValidationError, match="aware datetime"):
        AsianAveragingLiteralDateTime(datetime(2026, 10, 1, 10, 0))


def test_asian_schedule_observation_number_rejects_bool_and_wrong_types() -> None:
    for value in (0, -1, 1.0, True):
        with pytest.raises(OptionExoticValidationError):
            _schedule_observation("monthly", cast(int, value))
