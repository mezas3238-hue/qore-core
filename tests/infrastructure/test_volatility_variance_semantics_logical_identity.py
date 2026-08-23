from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeEvidenceRef,
    DerivativeNotional,
    DerivativeTermsId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.infrastructure.volatility_variance_semantics import (
    CorrelationConstituent,
    CorrelationStrike,
    CorrelationSwapTerms,
    VarianceStrike,
    VarianceSwapTerms,
    VolatilityCalculationConventionCode,
    VolatilityObservationScheduleCode,
    VolatilityObservationTerms,
    VolatilitySettlementTerms,
    VolatilityStrike,
    VolatilitySwapTerms,
    VolatilityVarianceValidationError,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _terms_id(value: int) -> DerivativeTermsId:
    return DerivativeTermsId(_uuid(value))


def _evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _notional(value: str, unit_identity: int) -> DerivativeNotional:
    return DerivativeNotional(Decimal(value), _identity(unit_identity))


def _observation() -> VolatilityObservationTerms:
    return VolatilityObservationTerms(
        observation_start_date=date(2026, 1, 2),
        observation_end_date=date(2026, 6, 30),
        schedule_code=VolatilityObservationScheduleCode("daily-close"),
        calculation_convention=VolatilityCalculationConventionCode(
            "log-return-standard"
        ),
        expected_observation_count=125,
    )


def _settlement() -> VolatilitySettlementTerms:
    return VolatilitySettlementTerms(
        settlement_identity_id=_identity(301),
        settlement_date=date(2026, 7, 2),
    )


def _variance() -> VarianceSwapTerms:
    return VarianceSwapTerms(
        terms_id=_terms_id(101),
        instrument_identity_id=_identity(10),
        reference_identity_id=_identity(11),
        observation_terms=_observation(),
        variance_strike=VarianceStrike(Decimal("0.0400")),
        variance_amount=_notional("5000.00", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(201),
        vega_notional=_notional("250.0", 301),
    )


def _volatility() -> VolatilitySwapTerms:
    return VolatilitySwapTerms(
        terms_id=_terms_id(102),
        instrument_identity_id=_identity(20),
        reference_identity_id=_identity(21),
        observation_terms=_observation(),
        volatility_strike=VolatilityStrike(Decimal("0.2000")),
        vega_notional=_notional("100.00", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(202),
    )


def _correlation(*, reverse: bool = True) -> CorrelationSwapTerms:
    constituents = (
        CorrelationConstituent(_identity(31), Decimal("0.6000")),
        CorrelationConstituent(_identity(32), Decimal("0.4000")),
    )
    return CorrelationSwapTerms(
        terms_id=_terms_id(103),
        instrument_identity_id=_identity(30),
        constituents=tuple(reversed(constituents)) if reverse else constituents,
        observation_terms=_observation(),
        correlation_strike=CorrelationStrike(Decimal("0.3500")),
        correlation_amount=_notional("10000.00", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(203),
    )


_EXPECTED_OBSERVATION: tuple[object, ...] = (
    "2026-01-02",
    "2026-06-30",
    ("daily-close",),
    ("log-return-standard",),
    125,
)

_EXPECTED_SETTLEMENT: tuple[object, ...] = (
    (str(_uuid(301)),),
    "2026-07-02",
)

_EXPECTED_VARIANCE: tuple[object, ...] = (
    "variance-swap",
    (str(_uuid(101)),),
    (str(_uuid(10)),),
    (str(_uuid(11)),),
    _EXPECTED_OBSERVATION,
    ("0.04",),
    ("5000", (str(_uuid(301)),)),
    ("250", (str(_uuid(301)),)),
    _EXPECTED_SETTLEMENT,
    (str(_uuid(201)),),
)

_EXPECTED_VOLATILITY: tuple[object, ...] = (
    "volatility-swap",
    (str(_uuid(102)),),
    (str(_uuid(20)),),
    (str(_uuid(21)),),
    _EXPECTED_OBSERVATION,
    ("0.2",),
    ("100", (str(_uuid(301)),)),
    _EXPECTED_SETTLEMENT,
    (str(_uuid(202)),),
)

_EXPECTED_CORRELATION: tuple[object, ...] = (
    "correlation-swap",
    (str(_uuid(103)),),
    (str(_uuid(30)),),
    (
        ((str(_uuid(31)),), "0.6"),
        ((str(_uuid(32)),), "0.4"),
    ),
    _EXPECTED_OBSERVATION,
    ("0.35",),
    ("10000", (str(_uuid(301)),)),
    _EXPECTED_SETTLEMENT,
    (str(_uuid(203)),),
)


def test_exact_dataclass_field_surfaces_are_frozen() -> None:
    assert tuple(field.name for field in fields(VolatilityObservationScheduleCode)) == (
        "value",
    )
    assert tuple(field.name for field in fields(VolatilityCalculationConventionCode)) == (
        "value",
    )
    assert tuple(field.name for field in fields(VarianceStrike)) == ("value",)
    assert tuple(field.name for field in fields(VolatilityStrike)) == ("value",)
    assert tuple(field.name for field in fields(CorrelationStrike)) == ("value",)
    assert tuple(field.name for field in fields(VolatilityObservationTerms)) == (
        "observation_start_date",
        "observation_end_date",
        "schedule_code",
        "calculation_convention",
        "expected_observation_count",
    )
    assert tuple(field.name for field in fields(VolatilitySettlementTerms)) == (
        "settlement_identity_id",
        "settlement_date",
    )
    assert tuple(field.name for field in fields(CorrelationConstituent)) == (
        "reference_identity_id",
        "weight",
    )
    assert tuple(field.name for field in fields(VarianceSwapTerms)) == (
        "terms_id",
        "instrument_identity_id",
        "reference_identity_id",
        "observation_terms",
        "variance_strike",
        "variance_amount",
        "settlement_terms",
        "evidence_ref",
        "vega_notional",
    )
    assert tuple(field.name for field in fields(VolatilitySwapTerms)) == (
        "terms_id",
        "instrument_identity_id",
        "reference_identity_id",
        "observation_terms",
        "volatility_strike",
        "vega_notional",
        "settlement_terms",
        "evidence_ref",
    )
    assert tuple(field.name for field in fields(CorrelationSwapTerms)) == (
        "terms_id",
        "instrument_identity_id",
        "constituents",
        "observation_terms",
        "correlation_strike",
        "correlation_amount",
        "settlement_terms",
        "evidence_ref",
    )


def test_wrapper_and_nested_projections_are_independently_reconstructed() -> None:
    assert VolatilityObservationScheduleCode("daily-close").logical_values() == (
        "daily-close",
    )
    assert VolatilityCalculationConventionCode(
        "log-return-standard"
    ).logical_values() == ("log-return-standard",)
    assert VarianceStrike(Decimal("0.0400")).logical_values() == ("0.04",)
    assert VolatilityStrike(Decimal("0.2000")).logical_values() == ("0.2",)
    assert CorrelationStrike(Decimal("0.3500")).logical_values() == ("0.35",)
    assert _observation().logical_values() == _EXPECTED_OBSERVATION
    assert _settlement().logical_values() == _EXPECTED_SETTLEMENT
    assert CorrelationConstituent(
        _identity(31), Decimal("0.6000")
    ).logical_values() == ((str(_uuid(31)),), "0.6")


def test_top_level_projections_are_complete_and_independent() -> None:
    assert _variance().logical_values() == _EXPECTED_VARIANCE
    assert _volatility().logical_values() == _EXPECTED_VOLATILITY
    assert _correlation(reverse=True).logical_values() == _EXPECTED_CORRELATION


def test_correlation_caller_order_does_not_change_logical_identity() -> None:
    assert _correlation(reverse=True).logical_values() == _correlation(
        reverse=False
    ).logical_values()


def test_product_discriminants_and_material_do_not_collapse() -> None:
    assert len({_EXPECTED_VARIANCE, _EXPECTED_VOLATILITY, _EXPECTED_CORRELATION}) == 3
    assert _variance().logical_values() != (
        "volatility-swap",
        *_EXPECTED_VARIANCE[1:],
    )
    assert _correlation().logical_values() != (
        *_EXPECTED_CORRELATION[:3],
        (
            ((str(_uuid(31)),), "0.5"),
            ((str(_uuid(32)),), "0.5"),
        ),
        *_EXPECTED_CORRELATION[4:],
    )


def test_composite_values_are_frozen_and_slotted() -> None:
    instances: tuple[object, ...] = (
        _observation(),
        _settlement(),
        CorrelationConstituent(_identity(31), Decimal("0.6")),
        _variance(),
        _volatility(),
        _correlation(),
    )
    for instance in instances:
        assert not hasattr(instance, "__dict__")
    with pytest.raises(FrozenInstanceError):
        cast(Any, instances[0]).expected_observation_count = 999
    with pytest.raises(FrozenInstanceError):
        cast(Any, instances[3]).variance_strike = VarianceStrike(Decimal("0.1"))


class _StringSubclass(str):
    pass


class _ScheduleSubclass(VolatilityObservationScheduleCode):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-schedule",)


class _ConventionSubclass(VolatilityCalculationConventionCode):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-convention",)


class _ObservationSubclass(VolatilityObservationTerms):
    __slots__ = ()

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-observation",)


class _SettlementSubclass(VolatilitySettlementTerms):
    __slots__ = ()

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-settlement",)


class _VarianceStrikeSubclass(VarianceStrike):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-variance",)


class _VolatilityStrikeSubclass(VolatilityStrike):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-volatility",)


class _CorrelationStrikeSubclass(CorrelationStrike):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-correlation",)


class _ConstituentSubclass(CorrelationConstituent):
    __slots__ = ()

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-constituent",)


class _HostileDecimal(Decimal):
    def is_finite(self) -> bool:
        return True

    def __lt__(self, other: object) -> bool:
        return False

    def __le__(self, other: object) -> bool:
        return False

    def __gt__(self, other: object) -> bool:
        return False

    def __ge__(self, other: object) -> bool:
        return False

    def normalize(self, *args: object, **kwargs: object) -> Decimal:
        return Decimal("999")


def test_code_wrappers_reject_string_subclass() -> None:
    with pytest.raises(VolatilityVarianceValidationError, match="canonical lowercase"):
        VolatilityObservationScheduleCode(cast(Any, _StringSubclass("daily")))


def test_decimal_boundaries_reject_hostile_subclasses_before_behavior() -> None:
    hostile = cast(Any, _HostileDecimal("NaN"))
    for factory in (VarianceStrike, VolatilityStrike, CorrelationStrike):
        with pytest.raises(VolatilityVarianceValidationError, match="finite Decimal"):
            factory(hostile)
    with pytest.raises(VolatilityVarianceValidationError, match="finite Decimal"):
        CorrelationConstituent(_identity(31), hostile)


def test_observation_rejects_local_code_subclasses_before_projection() -> None:
    with pytest.raises(VolatilityVarianceValidationError, match="schedule_code"):
        VolatilityObservationTerms(
            observation_start_date=date(2026, 1, 2),
            observation_end_date=date(2026, 6, 30),
            schedule_code=_ScheduleSubclass("daily-close"),
            calculation_convention=VolatilityCalculationConventionCode(
                "log-return-standard"
            ),
        )
    with pytest.raises(VolatilityVarianceValidationError, match="calculation_convention"):
        VolatilityObservationTerms(
            observation_start_date=date(2026, 1, 2),
            observation_end_date=date(2026, 6, 30),
            schedule_code=VolatilityObservationScheduleCode("daily-close"),
            calculation_convention=_ConventionSubclass("log-return-standard"),
        )


def test_variance_rejects_local_behavioral_subclasses() -> None:
    observation = _ObservationSubclass(
        observation_start_date=date(2026, 1, 2),
        observation_end_date=date(2026, 6, 30),
        schedule_code=VolatilityObservationScheduleCode("daily-close"),
        calculation_convention=VolatilityCalculationConventionCode(
            "log-return-standard"
        ),
        expected_observation_count=125,
    )
    with pytest.raises(VolatilityVarianceValidationError, match="observation_terms"):
        VarianceSwapTerms(
            terms_id=_terms_id(101),
            instrument_identity_id=_identity(10),
            reference_identity_id=_identity(11),
            observation_terms=observation,
            variance_strike=VarianceStrike(Decimal("0.04")),
            variance_amount=_notional("5000", 301),
            settlement_terms=_settlement(),
            evidence_ref=_evidence(201),
        )

    settlement = _SettlementSubclass(
        settlement_identity_id=_identity(301),
        settlement_date=date(2026, 7, 2),
    )
    with pytest.raises(VolatilityVarianceValidationError, match="settlement_terms"):
        VarianceSwapTerms(
            terms_id=_terms_id(101),
            instrument_identity_id=_identity(10),
            reference_identity_id=_identity(11),
            observation_terms=_observation(),
            variance_strike=VarianceStrike(Decimal("0.04")),
            variance_amount=_notional("5000", 301),
            settlement_terms=settlement,
            evidence_ref=_evidence(201),
        )

    with pytest.raises(VolatilityVarianceValidationError, match="variance_strike"):
        VarianceSwapTerms(
            terms_id=_terms_id(101),
            instrument_identity_id=_identity(10),
            reference_identity_id=_identity(11),
            observation_terms=_observation(),
            variance_strike=_VarianceStrikeSubclass(Decimal("0.04")),
            variance_amount=_notional("5000", 301),
            settlement_terms=_settlement(),
            evidence_ref=_evidence(201),
        )


def test_volatility_rejects_local_strike_subclass() -> None:
    with pytest.raises(VolatilityVarianceValidationError, match="volatility_strike"):
        VolatilitySwapTerms(
            terms_id=_terms_id(102),
            instrument_identity_id=_identity(20),
            reference_identity_id=_identity(21),
            observation_terms=_observation(),
            volatility_strike=_VolatilityStrikeSubclass(Decimal("0.2")),
            vega_notional=_notional("100", 301),
            settlement_terms=_settlement(),
            evidence_ref=_evidence(202),
        )


def test_correlation_rejects_local_constituent_and_strike_subclasses() -> None:
    with pytest.raises(VolatilityVarianceValidationError, match="CorrelationConstituent"):
        CorrelationSwapTerms(
            terms_id=_terms_id(103),
            instrument_identity_id=_identity(30),
            constituents=(
                _ConstituentSubclass(_identity(31), Decimal("0.6")),
                CorrelationConstituent(_identity(32), Decimal("0.4")),
            ),
            observation_terms=_observation(),
            correlation_strike=CorrelationStrike(Decimal("0.35")),
            correlation_amount=_notional("10000", 301),
            settlement_terms=_settlement(),
            evidence_ref=_evidence(203),
        )

    with pytest.raises(VolatilityVarianceValidationError, match="correlation_strike"):
        CorrelationSwapTerms(
            terms_id=_terms_id(103),
            instrument_identity_id=_identity(30),
            constituents=(
                CorrelationConstituent(_identity(31), Decimal("0.6")),
                CorrelationConstituent(_identity(32), Decimal("0.4")),
            ),
            observation_terms=_observation(),
            correlation_strike=_CorrelationStrikeSubclass(Decimal("0.35")),
            correlation_amount=_notional("10000", 301),
            settlement_terms=_settlement(),
            evidence_ref=_evidence(203),
        )
