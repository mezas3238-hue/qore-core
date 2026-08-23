from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Decimal, localcontext
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
    terms = _correlation(reverse=True)
    assert tuple(
        constituent.reference_identity_id for constituent in terms.constituents
    ) == (_identity(31), _identity(32))
    assert terms.logical_values() == _EXPECTED_CORRELATION


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


def test_decimal_identity_is_independent_of_ambient_context() -> None:
    precise_strike = VarianceStrike(Decimal("0.123456789000"))
    precise_notional = DerivativeNotional(
        Decimal("123.456789000"),
        _identity(301),
    )
    with localcontext() as context:
        context.prec = 2
        assert precise_strike.logical_values() == ("0.123456789",)
        terms = VolatilitySwapTerms(
            terms_id=_terms_id(104),
            instrument_identity_id=_identity(40),
            reference_identity_id=_identity(41),
            observation_terms=_observation(),
            volatility_strike=VolatilityStrike(Decimal("0.23456789000")),
            vega_notional=precise_notional,
            settlement_terms=_settlement(),
            evidence_ref=_evidence(204),
        )
        assert terms.logical_values()[5] == ("0.23456789",)
        assert terms.logical_values()[6] == (
            "123.456789",
            (str(_uuid(301)),),
        )


def test_instrument_must_not_equal_settlement_identity() -> None:
    variance = _variance()
    self_settlement = VolatilitySettlementTerms(
        settlement_identity_id=variance.instrument_identity_id,
        settlement_date=variance.settlement_terms.settlement_date,
    )
    with pytest.raises(
        VolatilityVarianceValidationError,
        match="instrument and settlement identities must differ",
    ):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=DerivativeNotional(
                variance.variance_amount.value,
                variance.instrument_identity_id,
            ),
            settlement_terms=self_settlement,
            evidence_ref=variance.evidence_ref,
            vega_notional=None,
        )


def test_all_payout_notionals_must_match_settlement_identity() -> None:
    variance = _variance()
    wrong_unit = _notional("5000", 302)
    with pytest.raises(VolatilityVarianceValidationError, match="variance_amount unit"):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=wrong_unit,
            settlement_terms=variance.settlement_terms,
            evidence_ref=variance.evidence_ref,
            vega_notional=None,
        )
    with pytest.raises(VolatilityVarianceValidationError, match="vega_notional unit"):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=variance.variance_amount,
            settlement_terms=variance.settlement_terms,
            evidence_ref=variance.evidence_ref,
            vega_notional=_notional("250", 302),
        )

    volatility = _volatility()
    with pytest.raises(VolatilityVarianceValidationError, match="vega_notional unit"):
        VolatilitySwapTerms(
            terms_id=volatility.terms_id,
            instrument_identity_id=volatility.instrument_identity_id,
            reference_identity_id=volatility.reference_identity_id,
            observation_terms=volatility.observation_terms,
            volatility_strike=volatility.volatility_strike,
            vega_notional=_notional("100", 302),
            settlement_terms=volatility.settlement_terms,
            evidence_ref=volatility.evidence_ref,
        )

    correlation = _correlation()
    with pytest.raises(VolatilityVarianceValidationError, match="correlation_amount unit"):
        CorrelationSwapTerms(
            terms_id=correlation.terms_id,
            instrument_identity_id=correlation.instrument_identity_id,
            constituents=correlation.constituents,
            observation_terms=correlation.observation_terms,
            correlation_strike=correlation.correlation_strike,
            correlation_amount=_notional("10000", 302),
            settlement_terms=correlation.settlement_terms,
            evidence_ref=correlation.evidence_ref,
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


class _HostileUUID(UUID):
    def __str__(self) -> str:
        return "spoofed-uuid"


class _IdentitySubclass(EconomicIdentityId):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-identity",)


class _TermsIdSubclass(DerivativeTermsId):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-terms-id",)


class _EvidenceSubclass(DerivativeEvidenceRef):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-evidence",)


class _NotionalSubclass(DerivativeNotional):
    __slots__ = ()

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-notional",)


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


def test_imported_owner_subclasses_are_rejected_before_virtual_behavior() -> None:
    with pytest.raises(VolatilityVarianceValidationError, match="exact EconomicIdentityId"):
        VolatilitySettlementTerms(
            settlement_identity_id=_IdentitySubclass(_uuid(301)),
            settlement_date=date(2026, 7, 2),
        )

    variance = _variance()
    with pytest.raises(VolatilityVarianceValidationError, match="exact DerivativeTermsId"):
        VarianceSwapTerms(
            terms_id=_TermsIdSubclass(_uuid(101)),
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=variance.variance_amount,
            settlement_terms=variance.settlement_terms,
            evidence_ref=variance.evidence_ref,
            vega_notional=variance.vega_notional,
        )

    with pytest.raises(VolatilityVarianceValidationError, match="exact DerivativeEvidenceRef"):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=variance.variance_amount,
            settlement_terms=variance.settlement_terms,
            evidence_ref=_EvidenceSubclass(_uuid(201)),
            vega_notional=variance.vega_notional,
        )

    with pytest.raises(VolatilityVarianceValidationError, match="exact DerivativeNotional"):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=_NotionalSubclass(Decimal("5000"), _identity(301)),
            settlement_terms=variance.settlement_terms,
            evidence_ref=variance.evidence_ref,
            vega_notional=variance.vega_notional,
        )

    with pytest.raises(VolatilityVarianceValidationError, match="exact EconomicIdentityId"):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=_IdentitySubclass(
                variance.instrument_identity_id.value
            ),
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=variance.variance_amount,
            settlement_terms=variance.settlement_terms,
            evidence_ref=variance.evidence_ref,
            vega_notional=variance.vega_notional,
        )


def test_imported_owner_nested_primitives_are_rejected_before_behavior() -> None:
    hostile_uuid = cast(Any, _HostileUUID(int=301))
    with pytest.raises(VolatilityVarianceValidationError, match="exact UUID"):
        VolatilitySettlementTerms(
            settlement_identity_id=EconomicIdentityId(hostile_uuid),
            settlement_date=date(2026, 7, 2),
        )

    variance = _variance()
    with pytest.raises(VolatilityVarianceValidationError, match="exact UUID"):
        VarianceSwapTerms(
            terms_id=DerivativeTermsId(cast(Any, _HostileUUID(int=101))),
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=variance.variance_amount,
            settlement_terms=variance.settlement_terms,
            evidence_ref=variance.evidence_ref,
            vega_notional=variance.vega_notional,
        )

    with pytest.raises(VolatilityVarianceValidationError, match="exact UUID"):
        VarianceSwapTerms(
            terms_id=variance.terms_id,
            instrument_identity_id=variance.instrument_identity_id,
            reference_identity_id=variance.reference_identity_id,
            observation_terms=variance.observation_terms,
            variance_strike=variance.variance_strike,
            variance_amount=variance.variance_amount,
            settlement_terms=variance.settlement_terms,
            evidence_ref=DerivativeEvidenceRef(cast(Any, _HostileUUID(int=201))),
            vega_notional=variance.vega_notional,
        )

    hostile_decimal_notional = DerivativeNotional(
        cast(Any, _HostileDecimal("1")),
        _identity(301),
    )
    with pytest.raises(VolatilityVarianceValidationError, match="finite Decimal"):
        VolatilitySwapTerms(
            terms_id=_terms_id(102),
            instrument_identity_id=_identity(20),
            reference_identity_id=_identity(21),
            observation_terms=_observation(),
            volatility_strike=VolatilityStrike(Decimal("0.2")),
            vega_notional=hostile_decimal_notional,
            settlement_terms=_settlement(),
            evidence_ref=_evidence(202),
        )

    hostile_unit_identity = EconomicIdentityId(
        cast(Any, _HostileUUID(int=301))
    )
    hostile_unit_notional = DerivativeNotional(
        Decimal("100"),
        hostile_unit_identity,
    )
    with pytest.raises(VolatilityVarianceValidationError, match="exact UUID"):
        VolatilitySwapTerms(
            terms_id=_terms_id(102),
            instrument_identity_id=_identity(20),
            reference_identity_id=_identity(21),
            observation_terms=_observation(),
            volatility_strike=VolatilityStrike(Decimal("0.2")),
            vega_notional=hostile_unit_notional,
            settlement_terms=_settlement(),
            evidence_ref=_evidence(202),
        )


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
