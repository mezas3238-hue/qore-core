from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from typing import Any, cast
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
    BarrierOptionTerms,
    BarrierRebateTerms,
    BarrierRebateTriggerCondition,
    ChooserOptionTerms,
    CliquetOptionFeature,
    CliquetStrikeConventionCode,
    CompoundOptionRelationship,
    DigitalOptionPayout,
    DigitalPayoutAmount,
    DigitalPayoutKind,
    DigitalPayoutTiming,
    LookbackExtremumRole,
    LookbackKind,
    LookbackOptionTerms,
    OptionExoticValidationError,
    ShoutLockedInReferenceRuleCode,
    ShoutOptionFeature,
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


def _evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _structured_evidence(value: int) -> StructuredEvidenceRef:
    return StructuredEvidenceRef(_uuid(value))


def _decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _identity_expected(value: EconomicIdentityId) -> tuple[str, ...]:
    return (str(value.value),)


def _evidence_expected(value: DerivativeEvidenceRef) -> tuple[str, ...]:
    return (str(value.value),)


def _terms_id_expected(value: DerivativeTermsId) -> tuple[str, ...]:
    return (str(value.value),)


def _strike(
    value: str = "100",
    *,
    quote_identity: EconomicIdentityId | None = None,
) -> DerivativeStrike:
    return DerivativeStrike(
        value=Decimal(value),
        basis=DerivativeStrikeBasis.PRICE,
        quote_identity_id=quote_identity or _identity(900),
        price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
    )


def _strike_expected(value: DerivativeStrike) -> tuple[object, ...]:
    assert value.quote_identity_id is not None
    assert value.price_quote_basis is not None
    return (
        _decimal(value.value),
        value.basis.value,
        _identity_expected(value.quote_identity_id),
        (value.price_quote_basis.value,),
        None,
    )


def _exercise(
    style: OptionExerciseStyle = OptionExerciseStyle.EUROPEAN,
    *,
    american_start_date: date | None = None,
    bermudan_dates: tuple[date, ...] = (),
) -> OptionExerciseTerms:
    return OptionExerciseTerms(
        style=style,
        american_start_date=american_start_date,
        bermudan_dates=bermudan_dates,
    )


def _exercise_expected(value: OptionExerciseTerms) -> tuple[object, ...]:
    return (
        value.style.value,
        value.american_start_date.isoformat()
        if value.american_start_date is not None
        else None,
        tuple(item.isoformat() for item in value.bermudan_dates),
    )


def _notional(value: str = "1000", *, unit: int = 102) -> DerivativeNotional:
    return DerivativeNotional(Decimal(value), _identity(unit))


def _notional_expected(value: DerivativeNotional) -> tuple[object, ...]:
    return (_decimal(value.value), _identity_expected(value.unit_identity_id))


def _multiplier(value: str = "10", *, unit: int = 102) -> DerivativeContractMultiplier:
    return DerivativeContractMultiplier(Decimal(value), _identity(unit))


def _multiplier_expected(value: DerivativeContractMultiplier) -> tuple[object, ...]:
    return (_decimal(value.value), _identity_expected(value.unit_identity_id))


def _option(
    *,
    terms: int = 100,
    instrument: int = 101,
    underlying: int = 200,
    settlement: int = 102,
    right: OptionRight = OptionRight.CALL,
    expiry: date = date(2027, 12, 18),
    strike: DerivativeStrike | None = None,
    exercise: OptionExerciseTerms | None = None,
) -> OptionContractTerms:
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(terms)),
        instrument_identity_id=_identity(instrument),
        underlying_identity_id=_identity(underlying),
        settlement_identity_id=_identity(settlement),
        right=right,
        strike=strike or _strike(),
        expiry_date=expiry,
        exercise=exercise or _exercise(),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(terms + 1),
        notional=_notional(unit=settlement),
    )


def _option_expected(value: OptionContractTerms) -> tuple[object, ...]:
    return (
        "option",
        _terms_id_expected(value.terms_id),
        _identity_expected(value.instrument_identity_id),
        _identity_expected(value.underlying_identity_id),
        _identity_expected(value.settlement_identity_id),
        value.right.value,
        _strike_expected(value.strike),
        value.expiry_date.isoformat(),
        _exercise_expected(value.exercise),
        value.settlement_style.value,
        _evidence_expected(value.evidence_ref),
        _multiplier_expected(value.multiplier) if value.multiplier is not None else None,
        _notional_expected(value.notional) if value.notional is not None else None,
    )


def _barrier(
    underlying: int = 200,
    *,
    feature: int = 300,
    kind: str = "knock-out",
) -> StructuredBarrierFeature:
    identity = _identity(underlying)
    return StructuredBarrierFeature(
        feature_id=StructuredFeatureId(_uuid(feature)),
        reference_identity_id=identity,
        barrier_kind=StructuredBarrierKindCode(kind),
        direction=StructuredBarrierDirection.AT_OR_ABOVE,
        level=StructuredContractLevel(
            value=Decimal("120"),
            kind=StructuredContractLevelKind.PRICE,
            reference_identity_id=identity,
            unit=StructuredLevelUnitCode("currency-per-unit"),
        ),
        observation=StructuredObservationTerms(mode=StructuredObservationMode.CONTINUOUS),
        evidence_ref=_structured_evidence(feature + 1),
    )


def _barrier_expected(value: StructuredBarrierFeature) -> tuple[object, ...]:
    return (
        "barrier",
        (str(value.feature_id.value),),
        _identity_expected(value.reference_identity_id),
        (value.barrier_kind.value,),
        value.direction.value,
        (
            _decimal(value.level.value),
            value.level.kind.value,
            _identity_expected(value.level.reference_identity_id),
            (value.level.unit.value,),
        ),
        (value.observation.mode.value, (), None),
        (str(value.evidence_ref.value),),
    )


def _barrier_option(*barriers: StructuredBarrierFeature) -> BarrierOptionTerms:
    return BarrierOptionTerms(
        option=_option(underlying=200),
        barriers=barriers or (_barrier(),),
        evidence_ref=_evidence(401),
    )


def _barrier_option_expected(value: BarrierOptionTerms) -> tuple[object, ...]:
    return (
        "barrier-option",
        _option_expected(value.option),
        tuple(_barrier_expected(item) for item in value.barriers),
        _evidence_expected(value.evidence_ref),
    )


def _payout(
    *,
    amount: str = "10",
    timing: DigitalPayoutTiming = DigitalPayoutTiming.DEFERRED,
) -> DigitalOptionPayout:
    return DigitalOptionPayout(
        kind=DigitalPayoutKind.CASH,
        amount=DigitalPayoutAmount(Decimal(amount), _identity(102)),
        timing=timing,
        evidence_ref=_evidence(402),
    )


def _payout_expected(value: DigitalOptionPayout) -> tuple[object, ...]:
    return (
        value.kind.value,
        (_decimal(value.amount.value), _identity_expected(value.amount.unit_identity_id)),
        value.timing.value,
        _evidence_expected(value.evidence_ref),
    )


def _lookback(
    *,
    kind: LookbackKind = LookbackKind.FIXED_STRIKE,
    right: OptionRight = OptionRight.PUT,
    extremum_role: LookbackExtremumRole | None = None,
    fixed_strike: DerivativeStrike | None = None,
    schedule: StructuredObservationScheduleCode | None = None,
    start: date = date(2027, 1, 2),
    end: date = date(2027, 11, 30),
    expiry: date = date(2027, 12, 18),
    exercise: OptionExerciseTerms | None = None,
    multiplier: DerivativeContractMultiplier | None = None,
    notional: DerivativeNotional | None = None,
) -> LookbackOptionTerms:
    if fixed_strike is None and kind is LookbackKind.FIXED_STRIKE:
        fixed_strike = _strike("95")
    if extremum_role is None:
        if kind is LookbackKind.FIXED_STRIKE:
            extremum_role = (
                LookbackExtremumRole.MAX
                if right is OptionRight.CALL
                else LookbackExtremumRole.MIN
            )
        else:
            extremum_role = (
                LookbackExtremumRole.MIN
                if right is OptionRight.CALL
                else LookbackExtremumRole.MAX
            )
    if notional is None and multiplier is None:
        notional = _notional()
    return LookbackOptionTerms(
        terms_id=DerivativeTermsId(_uuid(500)),
        instrument_identity_id=_identity(501),
        underlying_identity_id=_identity(502),
        settlement_identity_id=_identity(102),
        right=right,
        kind=kind,
        fixed_strike=fixed_strike,
        observation_window_start=start,
        observation_window_end=end,
        extremum_role=extremum_role,
        observation_schedule=schedule,
        expiry_date=expiry,
        exercise=exercise or _exercise(),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(503),
        multiplier=multiplier,
        notional=notional,
    )


def _chooser(
    *,
    allowed_rights: tuple[OptionRight, ...] = (OptionRight.PUT, OptionRight.CALL),
    decision: date = date(2027, 6, 1),
    expiry: date = date(2027, 12, 18),
    exercise: OptionExerciseTerms | None = None,
    multiplier: DerivativeContractMultiplier | None = None,
    notional: DerivativeNotional | None = None,
) -> ChooserOptionTerms:
    if notional is None and multiplier is None:
        notional = _notional()
    return ChooserOptionTerms(
        terms_id=DerivativeTermsId(_uuid(600)),
        instrument_identity_id=_identity(601),
        underlying_identity_id=_identity(602),
        settlement_identity_id=_identity(102),
        allowed_rights=allowed_rights,
        common_strike=_strike("105"),
        decision_date=decision,
        expiry_date=expiry,
        exercise=exercise or _exercise(),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(603),
        multiplier=multiplier,
        notional=notional,
    )


def _compound(
    *,
    outer_right: OptionRight = OptionRight.CALL,
    inner_right: OptionRight = OptionRight.PUT,
    outer_expiry: date = date(2027, 6, 1),
    inner_expiry: date = date(2027, 12, 18),
) -> CompoundOptionRelationship:
    inner = _option(
        terms=700,
        instrument=701,
        underlying=702,
        right=inner_right,
        expiry=inner_expiry,
    )
    outer = _option(
        terms=710,
        instrument=711,
        underlying=701,
        right=outer_right,
        expiry=outer_expiry,
    )
    return CompoundOptionRelationship(
        outer_option=outer,
        underlying_option=inner,
        evidence_ref=_evidence(720),
    )


def _cliquet(
    *,
    reset_dates: tuple[date, ...] = (date(2027, 9, 1), date(2027, 3, 1)),
    cap: Decimal | None = Decimal("0.10"),
    floor: Decimal | None = Decimal("-0.05"),
    window: tuple[date, date] | None = (date(2027, 1, 1), date(2027, 11, 1)),
) -> CliquetOptionFeature:
    return CliquetOptionFeature(
        option=_option(expiry=date(2027, 12, 18)),
        reset_dates=reset_dates,
        local_strike_convention=CliquetStrikeConventionCode("previous-reset"),
        local_cap=cap,
        local_floor=floor,
        local_reset_observation_window=window,
        evidence_ref=_evidence(801),
    )


def _shout(
    *,
    count: int = 2,
    start: date = date(2027, 1, 1),
    end: date = date(2027, 12, 18),
) -> ShoutOptionFeature:
    return ShoutOptionFeature(
        option=_option(expiry=date(2027, 12, 18)),
        shout_right_count=count,
        shout_window_start=start,
        shout_window_end=end,
        locked_in_reference_rule=ShoutLockedInReferenceRuleCode("intrinsic-at-shout"),
        evidence_ref=_evidence(901),
    )


def _rebate(
    *,
    feature: int = 300,
    trigger_condition: BarrierRebateTriggerCondition = (
        BarrierRebateTriggerCondition.ON_BARRIER_EVENT
    ),
) -> BarrierRebateTerms:
    first = _barrier(feature=300)
    second = _barrier(feature=301, kind="knock-in")
    return BarrierRebateTerms(
        barrier_option=_barrier_option(first, second),
        barrier_feature_id=StructuredFeatureId(_uuid(feature)),
        trigger_condition=trigger_condition,
        payout=_payout(),
        evidence_ref=_evidence(999),
    )


def test_lookback_fixed_projection_is_complete_and_independent() -> None:
    value = _lookback(schedule=StructuredObservationScheduleCode("month-end"))
    assert value.logical_values() == (
        "lookback-option",
        (str(_uuid(500)),),
        (str(_uuid(501)),),
        (str(_uuid(502)),),
        (str(_uuid(102)),),
        "put",
        "fixed-strike",
        ("95", "price", (str(_uuid(900)),), ("currency-per-unit",), None),
        "2027-01-02",
        "2027-11-30",
        "min",
        ("month-end",),
        "2027-12-18",
        ("european", None, ()),
        "cash",
        (str(_uuid(503)),),
        None,
        ("1000", (str(_uuid(102)),)),
    )


def test_lookback_floating_has_no_fake_strike_and_is_logically_distinct() -> None:
    floating = _lookback(kind=LookbackKind.FLOATING_STRIKE, fixed_strike=None)
    fixed = _lookback()
    assert floating.fixed_strike is None
    assert floating.logical_values()[6] == "floating-strike"
    assert floating.logical_values()[7] is None
    assert floating.logical_values() != fixed.logical_values()


@pytest.mark.parametrize(
    ("kind", "right", "extremum"),
    [
        (LookbackKind.FIXED_STRIKE, OptionRight.CALL, LookbackExtremumRole.MAX),
        (LookbackKind.FIXED_STRIKE, OptionRight.PUT, LookbackExtremumRole.MIN),
        (LookbackKind.FLOATING_STRIKE, OptionRight.CALL, LookbackExtremumRole.MIN),
        (LookbackKind.FLOATING_STRIKE, OptionRight.PUT, LookbackExtremumRole.MAX),
    ],
)
def test_lookback_kind_right_extremum_mapping_accepts_canonical_forms(
    kind: LookbackKind,
    right: OptionRight,
    extremum: LookbackExtremumRole,
) -> None:
    value = _lookback(kind=kind, right=right, extremum_role=extremum)
    assert value.right is right
    assert value.kind is kind
    assert value.extremum_role is extremum


@pytest.mark.parametrize(
    ("kind", "right", "extremum"),
    [
        (LookbackKind.FIXED_STRIKE, OptionRight.CALL, LookbackExtremumRole.MIN),
        (LookbackKind.FIXED_STRIKE, OptionRight.PUT, LookbackExtremumRole.MAX),
        (LookbackKind.FLOATING_STRIKE, OptionRight.CALL, LookbackExtremumRole.MAX),
        (LookbackKind.FLOATING_STRIKE, OptionRight.PUT, LookbackExtremumRole.MIN),
    ],
)
def test_lookback_kind_right_extremum_mapping_rejects_inverse_forms(
    kind: LookbackKind,
    right: OptionRight,
    extremum: LookbackExtremumRole,
) -> None:
    with pytest.raises(OptionExoticValidationError):
        _lookback(kind=kind, right=right, extremum_role=extremum)


def test_lookback_strike_presence_is_fail_closed() -> None:
    fixed = _lookback()
    with pytest.raises(OptionExoticValidationError):
        replace(fixed, fixed_strike=None)
    floating = _lookback(kind=LookbackKind.FLOATING_STRIKE, fixed_strike=None)
    with pytest.raises(OptionExoticValidationError):
        replace(floating, fixed_strike=_strike())


@pytest.mark.parametrize(
    ("start", "end", "expiry"),
    [
        (date(2027, 2, 1), date(2027, 2, 1), date(2027, 12, 18)),
        (date(2027, 2, 2), date(2027, 2, 1), date(2027, 12, 18)),
        (date(2027, 2, 1), date(2028, 1, 1), date(2027, 12, 18)),
    ],
)
def test_lookback_window_chronology_is_fail_closed(
    start: date,
    end: date,
    expiry: date,
) -> None:
    with pytest.raises(OptionExoticValidationError):
        _lookback(start=start, end=end, expiry=expiry)


def test_lookback_exercise_chronology_is_fail_closed() -> None:
    with pytest.raises(OptionExoticValidationError):
        _lookback(
            exercise=_exercise(
                OptionExerciseStyle.AMERICAN,
                american_start_date=date(2028, 1, 1),
            )
        )
    with pytest.raises(OptionExoticValidationError):
        _lookback(
            exercise=_exercise(
                OptionExerciseStyle.BERMUDAN,
                bermudan_dates=(date(2028, 1, 1),),
            )
        )


def test_lookback_multiplier_only_is_valid_and_material() -> None:
    value = _lookback(notional=None, multiplier=_multiplier("5"))
    assert value.logical_values()[-2] == ("5", (str(_uuid(102)),))
    assert value.logical_values()[-1] is None


def test_lookback_requires_sizing_material() -> None:
    value = _lookback()
    with pytest.raises(OptionExoticValidationError):
        replace(value, multiplier=None, notional=None)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("terms_id", object()),
        ("instrument_identity_id", object()),
        ("underlying_identity_id", object()),
        ("settlement_identity_id", object()),
        ("right", "call"),
        ("kind", "fixed-strike"),
        ("fixed_strike", object()),
        ("observation_window_start", cast(Any, "2027-01-01")),
        ("observation_window_end", cast(Any, "2027-11-01")),
        ("extremum_role", "min"),
        ("observation_schedule", object()),
        ("expiry_date", cast(Any, "2027-12-18")),
        ("exercise", object()),
        ("settlement_style", "cash"),
        ("evidence_ref", object()),
        ("multiplier", object()),
        ("notional", object()),
    ],
)
def test_lookback_rejects_wrong_public_types(field: str, bad: object) -> None:
    value = _lookback()
    with pytest.raises(OptionExoticValidationError):
        replace(cast(Any, value), **{field: bad})


def test_lookback_identity_self_bindings_are_rejected() -> None:
    value = _lookback()
    with pytest.raises(OptionExoticValidationError):
        replace(value, underlying_identity_id=value.instrument_identity_id)
    with pytest.raises(OptionExoticValidationError):
        replace(value, settlement_identity_id=value.instrument_identity_id)


def test_chooser_projection_canonicalizes_rights_and_keeps_common_strike() -> None:
    value = _chooser(allowed_rights=(OptionRight.PUT, OptionRight.CALL))
    assert value.allowed_rights == (OptionRight.CALL, OptionRight.PUT)
    assert value.logical_values() == (
        "chooser-option",
        (str(_uuid(600)),),
        (str(_uuid(601)),),
        (str(_uuid(602)),),
        (str(_uuid(102)),),
        ("call", "put"),
        ("105", "price", (str(_uuid(900)),), ("currency-per-unit",), None),
        "2027-06-01",
        "2027-12-18",
        ("european", None, ()),
        "cash",
        (str(_uuid(603)),),
        None,
        ("1000", (str(_uuid(102)),)),
    )


@pytest.mark.parametrize(
    "allowed_rights",
    [
        (),
        (OptionRight.CALL,),
        (OptionRight.PUT,),
        (OptionRight.CALL, OptionRight.CALL),
        cast(tuple[OptionRight, ...], (OptionRight.CALL, "put")),
    ],
)
def test_chooser_requires_exact_call_put_choice_set(
    allowed_rights: tuple[OptionRight, ...],
) -> None:
    with pytest.raises(OptionExoticValidationError):
        _chooser(allowed_rights=allowed_rights)


def test_chooser_rejects_non_tuple_choice_set() -> None:
    value = _chooser()
    with pytest.raises(OptionExoticValidationError):
        replace(value, allowed_rights=cast(Any, [OptionRight.CALL, OptionRight.PUT]))


@pytest.mark.parametrize(
    ("decision", "expiry"),
    [
        (date(2027, 12, 18), date(2027, 12, 18)),
        (date(2028, 1, 1), date(2027, 12, 18)),
    ],
)
def test_chooser_decision_must_precede_expiry(decision: date, expiry: date) -> None:
    with pytest.raises(OptionExoticValidationError):
        _chooser(decision=decision, expiry=expiry)


def test_chooser_exercise_chronology_is_fail_closed() -> None:
    with pytest.raises(OptionExoticValidationError):
        _chooser(
            exercise=_exercise(
                OptionExerciseStyle.AMERICAN,
                american_start_date=date(2028, 1, 1),
            )
        )
    with pytest.raises(OptionExoticValidationError):
        _chooser(
            exercise=_exercise(
                OptionExerciseStyle.BERMUDAN,
                bermudan_dates=(date(2028, 1, 1),),
            )
        )


def test_chooser_requires_sizing_material() -> None:
    value = _chooser()
    with pytest.raises(OptionExoticValidationError):
        replace(value, multiplier=None, notional=None)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("terms_id", object()),
        ("instrument_identity_id", object()),
        ("underlying_identity_id", object()),
        ("settlement_identity_id", object()),
        ("common_strike", object()),
        ("decision_date", cast(Any, "2027-06-01")),
        ("expiry_date", cast(Any, "2027-12-18")),
        ("exercise", object()),
        ("settlement_style", "cash"),
        ("evidence_ref", object()),
        ("multiplier", object()),
        ("notional", object()),
    ],
)
def test_chooser_rejects_wrong_public_types(field: str, bad: object) -> None:
    value = _chooser()
    with pytest.raises(OptionExoticValidationError):
        replace(cast(Any, value), **{field: bad})


def test_chooser_identity_self_bindings_are_rejected() -> None:
    value = _chooser()
    with pytest.raises(OptionExoticValidationError):
        replace(value, underlying_identity_id=value.instrument_identity_id)
    with pytest.raises(OptionExoticValidationError):
        replace(value, settlement_identity_id=value.instrument_identity_id)


@pytest.mark.parametrize(
    ("outer_right", "inner_right"),
    [
        (OptionRight.CALL, OptionRight.CALL),
        (OptionRight.CALL, OptionRight.PUT),
        (OptionRight.PUT, OptionRight.CALL),
        (OptionRight.PUT, OptionRight.PUT),
    ],
)
def test_compound_right_combinations_remain_distinct(
    outer_right: OptionRight,
    inner_right: OptionRight,
) -> None:
    value = _compound(outer_right=outer_right, inner_right=inner_right)
    projection = value.logical_values()
    assert projection[0] == "compound-option"
    assert cast(tuple[object, ...], projection[1])[5] == outer_right.value
    assert cast(tuple[object, ...], projection[2])[5] == inner_right.value


def test_compound_projection_is_complete_and_independent() -> None:
    value = _compound()
    assert value.logical_values() == (
        "compound-option",
        _option_expected(value.outer_option),
        _option_expected(value.underlying_option),
        (str(_uuid(720)),),
    )


def test_compound_requires_exact_identity_binding() -> None:
    value = _compound()
    wrong_outer = _option(
        terms=710,
        instrument=711,
        underlying=999,
        expiry=date(2027, 6, 1),
    )
    with pytest.raises(OptionExoticValidationError):
        replace(value, outer_option=wrong_outer)


def test_compound_requires_outer_expiry_before_underlying_expiry() -> None:
    with pytest.raises(OptionExoticValidationError):
        _compound(outer_expiry=date(2027, 12, 18), inner_expiry=date(2027, 12, 18))
    with pytest.raises(OptionExoticValidationError):
        _compound(outer_expiry=date(2028, 1, 1), inner_expiry=date(2027, 12, 18))


def test_compound_requires_distinct_terms_ids() -> None:
    value = _compound()
    inner = value.underlying_option
    outer = replace(value.outer_option, terms_id=inner.terms_id)
    with pytest.raises(OptionExoticValidationError):
        replace(value, outer_option=outer)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("outer_option", object()),
        ("underlying_option", object()),
        ("evidence_ref", object()),
    ],
)
def test_compound_rejects_wrong_public_types(field: str, bad: object) -> None:
    value = _compound()
    with pytest.raises(OptionExoticValidationError):
        replace(cast(Any, value), **{field: bad})


def test_cliquet_projection_canonicalizes_resets_and_retains_static_limits() -> None:
    value = _cliquet()
    assert value.reset_dates == (date(2027, 3, 1), date(2027, 9, 1))
    assert value.logical_values() == (
        "cliquet-option",
        _option_expected(value.option),
        ("2027-03-01", "2027-09-01"),
        ("previous-reset",),
        "0.1",
        "-0.05",
        ("2027-01-01", "2027-11-01"),
        (str(_uuid(801)),),
    )


@pytest.mark.parametrize(
    "reset_dates",
    [
        (),
        (date(2027, 3, 1), date(2027, 3, 1)),
        (date(2028, 1, 1),),
        cast(tuple[date, ...], ("2027-03-01",)),
    ],
)
def test_cliquet_reset_dates_are_fail_closed(reset_dates: tuple[date, ...]) -> None:
    with pytest.raises(OptionExoticValidationError):
        _cliquet(reset_dates=reset_dates)


def test_cliquet_reset_at_expiry_is_valid_without_observation_window() -> None:
    value = _cliquet(reset_dates=(date(2027, 12, 18),), window=None)
    assert value.reset_dates == (date(2027, 12, 18),)


def test_cliquet_reset_after_expiry_is_rejected() -> None:
    with pytest.raises(OptionExoticValidationError):
        _cliquet(reset_dates=(date(2027, 12, 19),), window=None)


@pytest.mark.parametrize(
    ("reset", "window", "valid"),
    [
        (date(2026, 12, 31), (date(2027, 1, 1), date(2027, 11, 1)), False),
        (date(2027, 1, 1), (date(2027, 1, 1), date(2027, 11, 1)), True),
        (date(2027, 6, 1), (date(2027, 1, 1), date(2027, 11, 1)), True),
        (date(2027, 11, 1), (date(2027, 1, 1), date(2027, 11, 1)), True),
        (date(2027, 11, 2), (date(2027, 1, 1), date(2027, 11, 1)), False),
    ],
)
def test_cliquet_reset_observation_window_contains_every_reset(
    reset: date,
    window: tuple[date, date],
    valid: bool,
) -> None:
    if valid:
        value = _cliquet(reset_dates=(reset,), window=window)
        assert value.reset_dates == (reset,)
    else:
        with pytest.raises(OptionExoticValidationError):
            _cliquet(reset_dates=(reset,), window=window)


def test_cliquet_maturity_reset_requires_window_end_at_maturity_when_window_present() -> None:
    expiry = date(2027, 12, 18)
    value = _cliquet(
        reset_dates=(expiry,),
        window=(date(2027, 1, 1), expiry),
    )
    assert value.reset_dates == (expiry,)
    with pytest.raises(OptionExoticValidationError):
        _cliquet(
            reset_dates=(expiry,),
            window=(date(2027, 1, 1), date(2027, 12, 17)),
        )


def test_cliquet_requires_tuple_reset_dates() -> None:
    value = _cliquet()
    with pytest.raises(OptionExoticValidationError):
        replace(value, reset_dates=cast(Any, [date(2027, 3, 1)]))


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
def test_cliquet_rejects_nonfinite_caps_and_floors(bad: Decimal) -> None:
    with pytest.raises(OptionExoticValidationError):
        _cliquet(cap=bad)
    with pytest.raises(OptionExoticValidationError):
        _cliquet(floor=bad)


def test_cliquet_floor_must_not_exceed_cap() -> None:
    with pytest.raises(OptionExoticValidationError):
        _cliquet(cap=Decimal("0.01"), floor=Decimal("0.02"))


@pytest.mark.parametrize(
    "window",
    [
        (date(2027, 4, 1), date(2027, 4, 1)),
        (date(2027, 5, 1), date(2027, 4, 1)),
        (date(2027, 1, 1), date(2028, 1, 1)),
        cast(tuple[date, date], (date(2027, 1, 1), cast(Any, "2027-02-01"))),
    ],
)
def test_cliquet_reset_window_is_fail_closed(window: tuple[date, date]) -> None:
    with pytest.raises(OptionExoticValidationError):
        _cliquet(window=window)


def test_cliquet_reset_window_requires_exact_two_date_tuple() -> None:
    value = _cliquet()
    with pytest.raises(OptionExoticValidationError):
        replace(value, local_reset_observation_window=cast(Any, (date(2027, 1, 1),)))
    with pytest.raises(OptionExoticValidationError):
        replace(
            value,
            local_reset_observation_window=cast(
                Any, [date(2027, 1, 1), date(2027, 2, 1)]
            ),
        )


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("option", object()),
        ("local_strike_convention", object()),
        ("local_cap", cast(Any, 1)),
        ("local_floor", cast(Any, 0.1)),
        ("evidence_ref", object()),
    ],
)
def test_cliquet_rejects_wrong_public_types(field: str, bad: object) -> None:
    value = _cliquet()
    with pytest.raises(OptionExoticValidationError):
        replace(cast(Any, value), **{field: bad})


@pytest.mark.parametrize("bad", ["Previous Reset", "UPPER", "", "a" * 65])
def test_cliquet_code_is_canonical(bad: str) -> None:
    with pytest.raises(OptionExoticValidationError):
        CliquetStrikeConventionCode(bad)


def test_shout_projection_retains_rights_not_events() -> None:
    value = _shout()
    assert value.logical_values() == (
        "shout-option",
        _option_expected(value.option),
        "2",
        "2027-01-01",
        "2027-12-18",
        ("intrinsic-at-shout",),
        (str(_uuid(901)),),
    )
    assert not hasattr(value, "shout_dates")


@pytest.mark.parametrize("count", [0, -1, True, cast(Any, 1.5)])
def test_shout_right_count_is_strict_positive_int(count: int) -> None:
    with pytest.raises(OptionExoticValidationError):
        _shout(count=count)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2027, 1, 1), date(2027, 1, 1)),
        (date(2027, 2, 1), date(2027, 1, 1)),
        (date(2027, 1, 1), date(2028, 1, 1)),
    ],
)
def test_shout_window_is_fail_closed(start: date, end: date) -> None:
    with pytest.raises(OptionExoticValidationError):
        _shout(start=start, end=end)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("option", object()),
        ("shout_window_start", cast(Any, "2027-01-01")),
        ("shout_window_end", cast(Any, "2027-12-18")),
        ("locked_in_reference_rule", object()),
        ("evidence_ref", object()),
    ],
)
def test_shout_rejects_wrong_public_types(field: str, bad: object) -> None:
    value = _shout()
    with pytest.raises(OptionExoticValidationError):
        replace(cast(Any, value), **{field: bad})


@pytest.mark.parametrize("bad", ["Intrinsic At Shout", "UPPER", "", "a" * 65])
def test_shout_rule_code_is_canonical(bad: str) -> None:
    with pytest.raises(OptionExoticValidationError):
        ShoutLockedInReferenceRuleCode(bad)


def test_barrier_rebate_projection_binds_exact_parent_feature_and_payout() -> None:
    value = _rebate(feature=301)
    assert value.logical_values() == (
        "barrier-rebate",
        _barrier_option_expected(value.barrier_option),
        (str(_uuid(301)),),
        "on-barrier-event",
        _payout_expected(value.payout),
        (str(_uuid(999)),),
    )


def test_barrier_rebate_trigger_condition_is_independent_material() -> None:
    on_event = _rebate(trigger_condition=BarrierRebateTriggerCondition.ON_BARRIER_EVENT)
    no_event = _rebate(
        trigger_condition=BarrierRebateTriggerCondition.ON_NO_BARRIER_EVENT_BY_EXPIRY
    )
    assert on_event.barrier_option == no_event.barrier_option
    assert on_event.barrier_feature_id == no_event.barrier_feature_id
    assert on_event.payout == no_event.payout
    assert on_event.evidence_ref == no_event.evidence_ref
    assert on_event.logical_values()[3] == "on-barrier-event"
    assert no_event.logical_values()[3] == "on-no-barrier-event-by-expiry"
    assert on_event.logical_values() != no_event.logical_values()


def test_barrier_rebate_rejects_feature_not_in_parent_option() -> None:
    with pytest.raises(OptionExoticValidationError):
        _rebate(feature=999)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("barrier_option", object()),
        ("barrier_feature_id", object()),
        ("trigger_condition", "on-barrier-event"),
        ("trigger_condition", LookbackKind.FIXED_STRIKE),
        ("payout", object()),
        ("evidence_ref", object()),
    ],
)
def test_barrier_rebate_rejects_wrong_public_types(field: str, bad: object) -> None:
    value = _rebate()
    with pytest.raises(OptionExoticValidationError):
        replace(cast(Any, value), **{field: bad})


def test_new_values_are_frozen_and_slotted() -> None:
    values_and_fields: tuple[tuple[object, str, object], ...] = (
        (_lookback(), "right", OptionRight.CALL),
        (_chooser(), "decision_date", date(2027, 5, 1)),
        (_compound(), "evidence_ref", _evidence(1)),
        (CliquetStrikeConventionCode("previous-reset"), "value", "other"),
        (_cliquet(), "reset_dates", (date(2027, 4, 1),)),
        (ShoutLockedInReferenceRuleCode("intrinsic-at-shout"), "value", "other"),
        (_shout(), "shout_right_count", 1),
        (_rebate(), "evidence_ref", _evidence(1)),
    )
    for value, field, replacement_value in values_and_fields:
        assert not hasattr(value, "__dict__")
        with pytest.raises(FrozenInstanceError):
            cast(Any, value).__setattr__(field, replacement_value)


def test_equal_decimals_do_not_flatten_unrelated_semantic_fields() -> None:
    cliquet = _cliquet(cap=Decimal("0.10"), floor=Decimal("0.10"))
    lookback = _lookback(fixed_strike=_strike("0.10"))
    assert lookback.fixed_strike is not None
    assert cliquet.local_cap == lookback.fixed_strike.value
    assert cliquet.logical_values()[4] == "0.1"
    assert cast(tuple[object, ...], lookback.logical_values()[7])[0] == "0.1"
    assert cliquet.logical_values() != lookback.logical_values()


def test_full_closure_values_expose_no_operational_methods() -> None:
    for value in (_lookback(), _chooser(), _compound(), _cliquet(), _shout(), _rebate()):
        for name in (
            "execute",
            "submit",
            "send",
            "settle",
            "price",
            "value",
            "observe",
            "connect",
            "retry",
        ):
            assert not callable(getattr(value, name, None))
