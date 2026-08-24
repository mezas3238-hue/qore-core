from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    DerivativeTickValue,
    FuturesContractTerms,
)
from qore.infrastructure.futures_final_settlement_semantics import (
    FuturesFinalSettlementAlgorithmCode,
    FuturesFinalSettlementEvidenceRef,
    FuturesFinalSettlementInput,
    FuturesFinalSettlementInputRoleCode,
    FuturesFinalSettlementObservationWindow,
    FuturesFinalSettlementRoundingModeCode,
    FuturesFinalSettlementRoundingRule,
    FuturesFinalSettlementRule,
    FuturesFinalSettlementRuleId,
    FuturesFinalSettlementValidationError,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


class _CollidingUUID(UUID):
    def __str__(self) -> str:
        return "collision"


class _DecimalSubclass(Decimal):
    pass


class _StringSubclass(str):
    pass


class _DatetimeSubclass(datetime):
    pass


def _id(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=value))


def _futures(*, tick: bool = False) -> FuturesContractTerms:
    return FuturesContractTerms(
        terms_id=DerivativeTermsId(UUID(int=10)),
        instrument_identity_id=_id(11),
        reference_identity_id=_id(12),
        settlement_identity_id=_id(13),
        contract_month=DerivativeContractMonth(2027, 3),
        expiry_date=date(2027, 3, 22),
        multiplier=DerivativeContractMultiplier(Decimal("100000"), _id(14)),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=DerivativeEvidenceRef(UUID(int=15)),
        tick_value=(
            DerivativeTickValue(Decimal("12.5"), _id(16)) if tick else None
        ),
        last_trade_date=date(2027, 3, 19),
    )


def _window(
    *,
    hour: int = 15,
    minutes: int = 30,
    sampling: int | None = 60,
) -> FuturesFinalSettlementObservationWindow:
    return FuturesFinalSettlementObservationWindow(
        opened_at=datetime(2027, 3, 19, hour, 0, tzinfo=UTC),
        closed_at=datetime(2027, 3, 19, hour, minutes, tzinfo=UTC),
        sampling_interval_seconds=sampling,
    )


def _input(
    identity: int,
    role: str,
    *,
    window: FuturesFinalSettlementObservationWindow | None = None,
    weight: str | None = None,
) -> FuturesFinalSettlementInput:
    return FuturesFinalSettlementInput(
        reference_identity_id=_id(identity),
        role=FuturesFinalSettlementInputRoleCode(role),
        observation_window=window,
        fixed_weight=Decimal(weight) if weight is not None else None,
    )


def _rule(
    *,
    futures: FuturesContractTerms | None = None,
    inputs: tuple[FuturesFinalSettlementInput, ...] | None = None,
    rounding: FuturesFinalSettlementRoundingRule | None = None,
) -> FuturesFinalSettlementRule:
    return FuturesFinalSettlementRule(
        rule_id=FuturesFinalSettlementRuleId(UUID(int=20)),
        futures_terms=futures or _futures(),
        algorithm=FuturesFinalSettlementAlgorithmCode("volume-weighted-average"),
        final_settlement_date=date(2027, 3, 22),
        inputs=inputs
        or (
            _input(30, "primary-price", window=_window(), weight="0.75"),
            _input(31, "secondary-price", weight="0.25"),
        ),
        rounding=rounding,
        evidence_ref=FuturesFinalSettlementEvidenceRef(UUID(int=21)),
    )


def test_rule_is_canonical_across_input_order_and_optional_window_shapes() -> None:
    with_window = _input(30, "price", window=_window(), weight="0.75")
    without_window = _input(30, "price", weight="0.25")
    first = _rule(inputs=(with_window, without_window))
    second = _rule(inputs=(without_window, with_window))
    assert first.logical_values() == second.logical_values()
    assert first.inputs == second.inputs
    assert first.inputs[0] is without_window


def test_same_reference_and_role_with_different_window_remains_distinct_material() -> None:
    first = _input(30, "price", window=_window(hour=14), weight="1")
    second = _input(30, "price", window=_window(hour=15), weight="1")
    rule = _rule(inputs=(second, first))
    assert len(rule.inputs) == 2
    assert rule.inputs[0].logical_values() != rule.inputs[1].logical_values()


def test_duplicate_logical_input_is_rejected() -> None:
    input_value = _input(30, "price", window=_window(), weight="1")
    with pytest.raises(
        FuturesFinalSettlementValidationError,
        match="duplicate logical declarations",
    ):
        _rule(inputs=(input_value, input_value))


def test_all_rule_fields_are_material_to_logical_identity() -> None:
    base = _rule(
        rounding=FuturesFinalSettlementRoundingRule(
            FuturesFinalSettlementRoundingModeCode("nearest"),
            Decimal("0.01"),
        )
    )
    baseline = base.logical_values()
    variants = (
        replace(base, rule_id=FuturesFinalSettlementRuleId(UUID(int=22))),
        replace(
            base,
            futures_terms=replace(
                base.futures_terms,
                expiry_date=date(2027, 3, 23),
            ),
        ),
        replace(
            base,
            algorithm=FuturesFinalSettlementAlgorithmCode(
                "settlement-window-average"
            ),
        ),
        replace(base, final_settlement_date=date(2027, 3, 23)),
        replace(base, inputs=(_input(32, "primary-price", weight="1"),)),
        replace(
            base,
            rounding=FuturesFinalSettlementRoundingRule(
                FuturesFinalSettlementRoundingModeCode("nearest"),
                Decimal("0.005"),
            ),
        ),
        replace(
            base,
            evidence_ref=FuturesFinalSettlementEvidenceRef(UUID(int=23)),
        ),
    )
    for variant in variants:
        assert variant.logical_values() != baseline


def test_final_settlement_date_is_not_forced_to_generic_last_trade_chronology() -> None:
    futures = replace(_futures(), last_trade_date=date(2027, 3, 21))
    rule = replace(_rule(futures=futures), final_settlement_date=date(2027, 3, 20))
    assert rule.final_settlement_date == date(2027, 3, 20)


def test_composed_futures_projection_preserves_umi05_field_semantics() -> None:
    futures = _futures(tick=True)
    composed = _rule(futures=futures).logical_values()[2]
    native = futures.logical_values()
    assert isinstance(composed, tuple)
    assert len(composed) == len(native) == 13
    for index in (0, 1, 2, 3, 4, 5, 6, 8, 9, 11, 12):
        assert composed[index] == native[index]

    composed_multiplier = composed[7]
    native_multiplier = native[7]
    assert isinstance(composed_multiplier, tuple)
    assert isinstance(native_multiplier, tuple)
    assert composed_multiplier[1] == native_multiplier[1]
    assert Decimal(str(composed_multiplier[0])) == futures.multiplier.value

    composed_tick = composed[10]
    native_tick = native[10]
    assert isinstance(composed_tick, tuple)
    assert isinstance(native_tick, tuple)
    assert futures.tick_value is not None
    assert composed_tick[1] == native_tick[1]
    assert Decimal(str(composed_tick[0])) == futures.tick_value.value


def test_optional_tick_none_path_preserves_native_none() -> None:
    futures = _futures(tick=False)
    composed = _rule(futures=futures).logical_values()[2]
    assert isinstance(composed, tuple)
    assert composed[10] is None
    assert futures.logical_values()[10] is None


def test_high_precision_weight_and_rounding_do_not_collapse() -> None:
    first_weight = _input(
        30,
        "price",
        weight="0.1234567890123456789012345678901",
    )
    second_weight = _input(
        30,
        "price",
        weight="0.1234567890123456789012345678909",
    )
    assert first_weight.fixed_weight != second_weight.fixed_weight
    assert first_weight.logical_values() != second_weight.logical_values()

    first_rounding = FuturesFinalSettlementRoundingRule(
        FuturesFinalSettlementRoundingModeCode("nearest"),
        Decimal("0.0000000000000000000000000000001"),
    )
    second_rounding = FuturesFinalSettlementRoundingRule(
        FuturesFinalSettlementRoundingModeCode("nearest"),
        Decimal("0.0000000000000000000000000000009"),
    )
    assert first_rounding.logical_values() != second_rounding.logical_values()


def test_rule_decimal_material_ignores_ambient_context() -> None:
    futures = replace(
        _futures(tick=True),
        multiplier=DerivativeContractMultiplier(
            Decimal("123456789012345678901234567890"),
            _id(14),
        ),
        tick_value=DerivativeTickValue(
            Decimal("0.987654321098765432109876543210"),
            _id(16),
        ),
    )
    rule = _rule(
        futures=futures,
        inputs=(
            _input(
                30,
                "price",
                window=_window(),
                weight="0.123456789012345678901234567890",
            ),
        ),
        rounding=FuturesFinalSettlementRoundingRule(
            FuturesFinalSettlementRoundingModeCode("nearest"),
            Decimal("0.000000000000000000000000000001"),
        ),
    )
    baseline = rule.logical_values()
    with localcontext() as context:
        context.prec = 5
        assert rule.logical_values() == baseline


def test_extreme_decimal_material_stays_compact() -> None:
    futures = replace(
        _futures(tick=True),
        multiplier=DerivativeContractMultiplier(Decimal("1E+1000000"), _id(14)),
        tick_value=DerivativeTickValue(Decimal("1E-1000000"), _id(16)),
    )
    rule = _rule(
        futures=futures,
        inputs=(_input(30, "price", weight="1E+1000000"),),
        rounding=FuturesFinalSettlementRoundingRule(
            FuturesFinalSettlementRoundingModeCode("nearest"),
            Decimal("1E-1000000"),
        ),
    )
    values = rule.logical_values()
    futures_values = values[2]
    inputs_values = values[5]
    rounding_values = values[6]
    assert isinstance(futures_values, tuple)
    assert isinstance(inputs_values, tuple)
    assert isinstance(rounding_values, tuple)
    multiplier_values = futures_values[7]
    tick_values = futures_values[10]
    assert isinstance(multiplier_values, tuple)
    assert isinstance(tick_values, tuple)
    assert multiplier_values[0] == "1e+1000000"
    assert tick_values[0] == "1e-1000000"
    assert inputs_values[0][3] == "1e+1000000"
    assert rounding_values[1] == "1e-1000000"
    assert all(
        len(text) < 32
        for text in (
            str(multiplier_values[0]),
            str(tick_values[0]),
            str(inputs_values[0][3]),
            str(rounding_values[1]),
        )
    )


def test_observation_window_canonicalizes_equivalent_instants_to_utc() -> None:
    utc_window = FuturesFinalSettlementObservationWindow(
        datetime(2027, 3, 19, 15, tzinfo=UTC),
        datetime(2027, 3, 19, 15, 30, tzinfo=UTC),
        60,
    )
    offset = timezone(timedelta(hours=2))
    offset_window = FuturesFinalSettlementObservationWindow(
        datetime(2027, 3, 19, 17, tzinfo=offset),
        datetime(2027, 3, 19, 17, 30, tzinfo=offset),
        60,
    )
    assert utc_window.logical_values() == offset_window.logical_values()


def test_point_observation_without_sampling_interval_is_valid() -> None:
    instant = datetime(2027, 3, 19, 15, tzinfo=UTC)
    window = FuturesFinalSettlementObservationWindow(instant, instant)
    assert window.logical_values()[0] == window.logical_values()[1]


@pytest.mark.parametrize(
    ("opened_at", "closed_at", "sampling", "message"),
    (
        (
            datetime(2027, 3, 19, 16, tzinfo=UTC),
            datetime(2027, 3, 19, 15, tzinfo=UTC),
            None,
            "must not precede",
        ),
        (
            datetime(2027, 3, 19, 15),
            datetime(2027, 3, 19, 16, tzinfo=UTC),
            None,
            "timezone-aware",
        ),
        (
            datetime(2027, 3, 19, 15, tzinfo=UTC),
            datetime(2027, 3, 19, 15, tzinfo=UTC),
            60,
            "point observation",
        ),
        (
            datetime(2027, 3, 19, 15, tzinfo=UTC),
            datetime(2027, 3, 19, 16, tzinfo=UTC),
            True,
            "positive exact int",
        ),
    ),
)
def test_invalid_observation_windows_fail_closed(
    opened_at: datetime,
    closed_at: datetime,
    sampling: int | None,
    message: str,
) -> None:
    with pytest.raises(FuturesFinalSettlementValidationError, match=message):
        FuturesFinalSettlementObservationWindow(opened_at, closed_at, sampling)


def test_datetime_subclass_is_rejected() -> None:
    subclass_value = _DatetimeSubclass(2027, 3, 19, 15, tzinfo=UTC)
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact datetime"):
        FuturesFinalSettlementObservationWindow(
            subclass_value,
            datetime(2027, 3, 19, 16, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    "value",
    (
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ),
)
def test_fixed_weight_must_be_positive_finite_exact_decimal(value: Decimal) -> None:
    with pytest.raises(FuturesFinalSettlementValidationError):
        FuturesFinalSettlementInput(
            _id(30),
            FuturesFinalSettlementInputRoleCode("price"),
            fixed_weight=value,
        )


@pytest.mark.parametrize(
    "value",
    (
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ),
)
def test_rounding_increment_must_be_positive_finite_exact_decimal(
    value: Decimal,
) -> None:
    with pytest.raises(FuturesFinalSettlementValidationError):
        FuturesFinalSettlementRoundingRule(
            FuturesFinalSettlementRoundingModeCode("nearest"),
            value,
        )


def test_decimal_subclasses_are_rejected() -> None:
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact Decimal"):
        FuturesFinalSettlementInput(
            _id(30),
            FuturesFinalSettlementInputRoleCode("price"),
            fixed_weight=_DecimalSubclass("1"),
        )
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact Decimal"):
        FuturesFinalSettlementRoundingRule(
            FuturesFinalSettlementRoundingModeCode("nearest"),
            _DecimalSubclass("0.01"),
        )


def test_colliding_uuid_subclasses_are_rejected_before_logical_material() -> None:
    left = EconomicIdentityId(_CollidingUUID(int=30))
    right = EconomicIdentityId(_CollidingUUID(int=31))
    assert left.value != right.value
    assert left.logical_values() == right.logical_values() == ("collision",)
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact UUID"):
        FuturesFinalSettlementInput(
            left,
            FuturesFinalSettlementInputRoleCode("price"),
        )


def test_rule_and_evidence_uuid_subclasses_are_rejected() -> None:
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact UUID"):
        FuturesFinalSettlementRuleId(_CollidingUUID(int=20))
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact UUID"):
        FuturesFinalSettlementEvidenceRef(_CollidingUUID(int=21))


def test_code_subclasses_and_noncanonical_codes_are_rejected() -> None:
    with pytest.raises(FuturesFinalSettlementValidationError):
        FuturesFinalSettlementAlgorithmCode(_StringSubclass("average"))
    with pytest.raises(FuturesFinalSettlementValidationError):
        FuturesFinalSettlementInputRoleCode("Primary Price")
    with pytest.raises(FuturesFinalSettlementValidationError):
        FuturesFinalSettlementRoundingModeCode("token=secret")


def test_nested_futures_reflective_corruption_fails_closed() -> None:
    rule = _rule()
    object.__setattr__(rule.futures_terms.terms_id, "value", "not-a-uuid")
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact UUID"):
        rule.logical_values()


def test_nested_input_reflective_corruption_fails_closed() -> None:
    rule = _rule()
    object.__setattr__(rule.inputs[0].reference_identity_id, "value", "not-a-uuid")
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact UUID"):
        rule.logical_values()


def test_non_empty_exact_tuple_and_exact_input_types_are_required() -> None:
    with pytest.raises(FuturesFinalSettlementValidationError, match="non-empty"):
        replace(_rule(), inputs=())
    invalid_list = cast(
        tuple[FuturesFinalSettlementInput, ...],
        [_input(30, "price")],
    )
    with pytest.raises(
        FuturesFinalSettlementValidationError,
        match="immutable tuple",
    ):
        replace(_rule(), inputs=invalid_list)

    wrong_item = cast(tuple[FuturesFinalSettlementInput, ...], ("wrong",))
    with pytest.raises(
        FuturesFinalSettlementValidationError,
        match="exact FuturesFinalSettlementInput",
    ):
        replace(_rule(), inputs=wrong_item)


def test_final_settlement_date_requires_exact_date_not_datetime() -> None:
    invalid_date = cast(date, datetime(2027, 3, 22, tzinfo=UTC))
    with pytest.raises(FuturesFinalSettlementValidationError, match="exact date"):
        replace(_rule(), final_settlement_date=invalid_date)


def test_source_has_no_engine_provider_or_implicit_clock_authority() -> None:
    source = Path(
        "src/qore/infrastructure/futures_final_settlement_semantics.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "def calculate(",
        "def compute(",
        "market_observation",
        "market_data",
        "provider",
        "requests",
        "httpx",
        "datetime.now(",
        "uuid4(",
        "execution",
        "risk",
        "account",
    )
    for marker in forbidden:
        assert marker not in source.lower()
