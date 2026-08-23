from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from pathlib import Path
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


def _terms_id(value: int = 100) -> DerivativeTermsId:
    return DerivativeTermsId(_uuid(value))


def _evidence(value: int = 200) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _notional(value: str = "1000", identity: int = 300) -> DerivativeNotional:
    return DerivativeNotional(Decimal(value), _identity(identity))


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
        variance_strike=VarianceStrike(Decimal("0.04")),
        variance_amount=_notional("5000", 301),
        vega_notional=_notional("250", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(201),
    )


def _volatility() -> VolatilitySwapTerms:
    return VolatilitySwapTerms(
        terms_id=_terms_id(102),
        instrument_identity_id=_identity(20),
        reference_identity_id=_identity(21),
        observation_terms=_observation(),
        volatility_strike=VolatilityStrike(Decimal("0.20")),
        vega_notional=_notional("100", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(202),
    )


def _correlation() -> CorrelationSwapTerms:
    return CorrelationSwapTerms(
        terms_id=_terms_id(103),
        instrument_identity_id=_identity(30),
        constituents=(
            CorrelationConstituent(_identity(31), Decimal("0.6")),
            CorrelationConstituent(_identity(32), Decimal("0.4")),
        ),
        observation_terms=_observation(),
        correlation_strike=CorrelationStrike(Decimal("0.35")),
        correlation_amount=_notional("10000", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(203),
    )


def test_code_wrappers_are_typed_and_deterministic() -> None:
    schedule = VolatilityObservationScheduleCode("business-day-close")
    convention = VolatilityCalculationConventionCode("log-return-252")
    assert schedule.logical_values() == ("business-day-close",)
    assert convention.logical_values() == ("log-return-252",)


@pytest.mark.parametrize(
    "factory",
    [VolatilityObservationScheduleCode, VolatilityCalculationConventionCode],
)
@pytest.mark.parametrize("value", ["", "UPPER", "bad code", "a" * 65, 1])
def test_code_wrappers_fail_closed(factory: Any, value: object) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        factory(cast(Any, value))


@pytest.mark.parametrize(
    ("factory", "value", "expected"),
    [
        (VarianceStrike, "0", ("0",)),
        (VarianceStrike, "0.0400", ("0.04",)),
        (VolatilityStrike, "0", ("0",)),
        (VolatilityStrike, "0.2000", ("0.2",)),
        (CorrelationStrike, "-1", ("-1",)),
        (CorrelationStrike, "0.3500", ("0.35",)),
        (CorrelationStrike, "1", ("1",)),
    ],
)
def test_strike_wrappers_preserve_distinct_contract_units(
    factory: Any,
    value: str,
    expected: tuple[str, ...],
) -> None:
    assert factory(Decimal(value)).logical_values() == expected


@pytest.mark.parametrize(
    "factory",
    [VarianceStrike, VolatilityStrike],
)
@pytest.mark.parametrize("value", ["-0.01", "NaN", "Infinity"])
def test_non_negative_strikes_fail_closed(factory: Any, value: str) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        factory(Decimal(value))


@pytest.mark.parametrize("value", ["-1.0001", "1.0001", "NaN", "Infinity"])
def test_correlation_strike_is_bounded(value: str) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationStrike(Decimal(value))


@pytest.mark.parametrize(
    "factory",
    [VarianceStrike, VolatilityStrike, CorrelationStrike],
)
def test_strikes_reject_non_decimal(factory: Any) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        factory(cast(Any, 0.2))


def test_observation_terms_are_static_and_deterministic() -> None:
    terms = _observation()
    assert terms.logical_values() == (
        "2026-01-02",
        "2026-06-30",
        ("daily-close",),
        ("log-return-standard",),
        125,
    )


def test_observation_terms_allow_unspecified_expected_count() -> None:
    terms = VolatilityObservationTerms(
        observation_start_date=date(2026, 1, 1),
        observation_end_date=date(2026, 2, 1),
        schedule_code=VolatilityObservationScheduleCode("contract-schedule"),
        calculation_convention=VolatilityCalculationConventionCode(
            "contract-defined"
        ),
    )
    assert terms.logical_values()[-1] is None


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2026, 1, 1), date(2026, 1, 1)),
        (date(2026, 2, 1), date(2026, 1, 1)),
    ],
)
def test_observation_window_must_be_forward(start: date, end: date) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilityObservationTerms(
            observation_start_date=start,
            observation_end_date=end,
            schedule_code=VolatilityObservationScheduleCode("daily"),
            calculation_convention=VolatilityCalculationConventionCode("standard"),
        )


@pytest.mark.parametrize("count", [0, -1, True, 1.5, "10"])
def test_expected_observation_count_is_strict_positive_int(count: object) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilityObservationTerms(
            observation_start_date=date(2026, 1, 1),
            observation_end_date=date(2026, 2, 1),
            schedule_code=VolatilityObservationScheduleCode("daily"),
            calculation_convention=VolatilityCalculationConventionCode("standard"),
            expected_observation_count=cast(Any, count),
        )


def test_observation_terms_reject_raw_dates_and_codes() -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilityObservationTerms(
            observation_start_date=cast(Any, "2026-01-01"),
            observation_end_date=date(2026, 2, 1),
            schedule_code=VolatilityObservationScheduleCode("daily"),
            calculation_convention=VolatilityCalculationConventionCode("standard"),
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilityObservationTerms(
            observation_start_date=date(2026, 1, 1),
            observation_end_date=cast(Any, "2026-02-01"),
            schedule_code=VolatilityObservationScheduleCode("daily"),
            calculation_convention=VolatilityCalculationConventionCode("standard"),
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilityObservationTerms(
            observation_start_date=date(2026, 1, 1),
            observation_end_date=date(2026, 2, 1),
            schedule_code=cast(Any, "daily"),
            calculation_convention=VolatilityCalculationConventionCode("standard"),
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilityObservationTerms(
            observation_start_date=date(2026, 1, 1),
            observation_end_date=date(2026, 2, 1),
            schedule_code=VolatilityObservationScheduleCode("daily"),
            calculation_convention=cast(Any, "standard"),
        )


def test_settlement_terms_are_static() -> None:
    terms = _settlement()
    assert terms.logical_values() == (
        _identity(301).logical_values(),
        "2026-07-02",
    )


def test_settlement_terms_reject_raw_values() -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySettlementTerms(
            settlement_identity_id=cast(Any, _uuid(1)),
            settlement_date=date(2026, 1, 1),
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySettlementTerms(
            settlement_identity_id=_identity(1),
            settlement_date=cast(Any, "2026-01-01"),
        )


def test_correlation_constituent_preserves_weight() -> None:
    constituent = CorrelationConstituent(_identity(1), Decimal("1.2500"))
    assert constituent.logical_values() == (
        _identity(1).logical_values(),
        "1.25",
    )


@pytest.mark.parametrize("weight", ["0", "-1", "NaN", "Infinity"])
def test_correlation_constituent_requires_positive_finite_weight(
    weight: str,
) -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationConstituent(_identity(1), Decimal(weight))


def test_correlation_constituent_rejects_raw_identity_and_weight() -> None:
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationConstituent(cast(Any, _uuid(1)), Decimal("1"))
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationConstituent(_identity(1), cast(Any, 1.0))


def test_variance_swap_retains_variance_and_vega_notional_distinctly() -> None:
    terms = _variance()
    logical = terms.logical_values()
    assert logical[0] == "variance-swap"
    assert logical[5] == ("0.04",)
    assert logical[6] == _notional("5000", 301).logical_values()
    assert logical[7] == _notional("250", 301).logical_values()


def test_variance_swap_allows_absent_vega_notional() -> None:
    terms = VarianceSwapTerms(
        terms_id=_terms_id(111),
        instrument_identity_id=_identity(12),
        reference_identity_id=_identity(13),
        observation_terms=_observation(),
        variance_strike=VarianceStrike(Decimal("0.03")),
        variance_amount=_notional("500", 301),
        settlement_terms=_settlement(),
        evidence_ref=_evidence(211),
    )
    assert terms.logical_values()[7] is None


def test_variance_and_volatility_same_decimal_do_not_collapse() -> None:
    variance = VarianceStrike(Decimal("0.20"))
    volatility = VolatilityStrike(Decimal("0.20"))
    assert variance.__class__.__name__ != volatility.__class__.__name__
    assert variance.logical_values() == volatility.logical_values()


def test_volatility_swap_retains_volatility_strike_and_vega_notional() -> None:
    terms = _volatility()
    logical = terms.logical_values()
    assert logical[0] == "volatility-swap"
    assert logical[5] == ("0.2",)
    assert logical[6] == _notional("100", 301).logical_values()


def test_variance_and_volatility_contracts_have_distinct_discriminants() -> None:
    assert _variance().logical_values()[0] == "variance-swap"
    assert _volatility().logical_values()[0] == "volatility-swap"


@pytest.mark.parametrize("factory", [_variance, _volatility, _correlation])
def test_settlement_must_not_precede_observation_end(factory: Any) -> None:
    terms = factory()
    early = VolatilitySettlementTerms(
        settlement_identity_id=_identity(301),
        settlement_date=date(2026, 6, 29),
    )
    with pytest.raises(VolatilityVarianceValidationError):
        if isinstance(terms, VarianceSwapTerms):
            VarianceSwapTerms(
                terms_id=terms.terms_id,
                instrument_identity_id=terms.instrument_identity_id,
                reference_identity_id=terms.reference_identity_id,
                observation_terms=terms.observation_terms,
                variance_strike=terms.variance_strike,
                variance_amount=terms.variance_amount,
                vega_notional=terms.vega_notional,
                settlement_terms=early,
                evidence_ref=terms.evidence_ref,
            )
        elif isinstance(terms, VolatilitySwapTerms):
            VolatilitySwapTerms(
                terms_id=terms.terms_id,
                instrument_identity_id=terms.instrument_identity_id,
                reference_identity_id=terms.reference_identity_id,
                observation_terms=terms.observation_terms,
                volatility_strike=terms.volatility_strike,
                vega_notional=terms.vega_notional,
                settlement_terms=early,
                evidence_ref=terms.evidence_ref,
            )
        else:
            CorrelationSwapTerms(
                terms_id=terms.terms_id,
                instrument_identity_id=terms.instrument_identity_id,
                constituents=terms.constituents,
                observation_terms=terms.observation_terms,
                correlation_strike=terms.correlation_strike,
                correlation_amount=terms.correlation_amount,
                settlement_terms=early,
                evidence_ref=terms.evidence_ref,
            )


@pytest.mark.parametrize(
    "kind",
    ["terms", "instrument", "observation", "settlement", "evidence"],
)
def test_variance_common_wrappers_fail_closed(kind: str) -> None:
    base = _variance()
    values: dict[str, Any] = {
        "terms_id": base.terms_id,
        "instrument_identity_id": base.instrument_identity_id,
        "reference_identity_id": base.reference_identity_id,
        "observation_terms": base.observation_terms,
        "variance_strike": base.variance_strike,
        "variance_amount": base.variance_amount,
        "settlement_terms": base.settlement_terms,
        "evidence_ref": base.evidence_ref,
        "vega_notional": base.vega_notional,
    }
    mapping = {
        "terms": ("terms_id", _uuid(1)),
        "instrument": ("instrument_identity_id", _uuid(2)),
        "observation": ("observation_terms", "obs"),
        "settlement": ("settlement_terms", "settle"),
        "evidence": ("evidence_ref", _uuid(3)),
    }
    key, invalid = mapping[kind]
    values[key] = invalid
    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(**values)


def test_variance_reference_must_be_typed_and_distinct() -> None:
    base = _variance()
    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=cast(Any, _uuid(11)),
            observation_terms=base.observation_terms,
            variance_strike=base.variance_strike,
            variance_amount=base.variance_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.instrument_identity_id,
            observation_terms=base.observation_terms,
            variance_strike=base.variance_strike,
            variance_amount=base.variance_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_variance_specific_wrappers_fail_closed() -> None:
    base = _variance()
    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.reference_identity_id,
            observation_terms=base.observation_terms,
            variance_strike=cast(Any, Decimal("0.04")),
            variance_amount=base.variance_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.reference_identity_id,
            observation_terms=base.observation_terms,
            variance_strike=base.variance_strike,
            variance_amount=cast(Any, Decimal("100")),
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.reference_identity_id,
            observation_terms=base.observation_terms,
            variance_strike=base.variance_strike,
            variance_amount=base.variance_amount,
            vega_notional=cast(Any, Decimal("100")),
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_volatility_reference_and_wrappers_fail_closed() -> None:
    base = _volatility()
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.instrument_identity_id,
            observation_terms=base.observation_terms,
            volatility_strike=base.volatility_strike,
            vega_notional=base.vega_notional,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=cast(Any, _uuid(21)),
            observation_terms=base.observation_terms,
            volatility_strike=base.volatility_strike,
            vega_notional=base.vega_notional,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.reference_identity_id,
            observation_terms=base.observation_terms,
            volatility_strike=cast(Any, Decimal("0.2")),
            vega_notional=base.vega_notional,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            reference_identity_id=base.reference_identity_id,
            observation_terms=base.observation_terms,
            volatility_strike=base.volatility_strike,
            vega_notional=cast(Any, Decimal("100")),
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_correlation_swap_preserves_constituent_weights_and_strike() -> None:
    terms = _correlation()
    logical = terms.logical_values()
    assert logical[0] == "correlation-swap"
    assert logical[3] == (
        (_identity(31).logical_values(), "0.6"),
        (_identity(32).logical_values(), "0.4"),
    )
    assert logical[5] == ("0.35",)


@pytest.mark.parametrize(
    "constituents",
    [
        (),
        (CorrelationConstituent(_identity(31), Decimal("1")),),
        [
            CorrelationConstituent(_identity(31), Decimal("0.5")),
            CorrelationConstituent(_identity(32), Decimal("0.5")),
        ],
    ],
)
def test_correlation_requires_tuple_with_two_constituents(
    constituents: object,
) -> None:
    base = _correlation()
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            constituents=cast(Any, constituents),
            observation_terms=base.observation_terms,
            correlation_strike=base.correlation_strike,
            correlation_amount=base.correlation_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_correlation_rejects_duplicate_constituent_identity() -> None:
    base = _correlation()
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            constituents=(
                CorrelationConstituent(_identity(31), Decimal("0.4")),
                CorrelationConstituent(_identity(31), Decimal("0.6")),
            ),
            observation_terms=base.observation_terms,
            correlation_strike=base.correlation_strike,
            correlation_amount=base.correlation_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_correlation_rejects_instrument_as_constituent() -> None:
    base = _correlation()
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            constituents=(
                CorrelationConstituent(base.instrument_identity_id, Decimal("0.5")),
                CorrelationConstituent(_identity(32), Decimal("0.5")),
            ),
            observation_terms=base.observation_terms,
            correlation_strike=base.correlation_strike,
            correlation_amount=base.correlation_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_correlation_rejects_untyped_constituent_strike_and_amount() -> None:
    base = _correlation()
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            constituents=cast(
                Any,
                (
                    base.constituents[0],
                    "bad",
                ),
            ),
            observation_terms=base.observation_terms,
            correlation_strike=base.correlation_strike,
            correlation_amount=base.correlation_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            constituents=base.constituents,
            observation_terms=base.observation_terms,
            correlation_strike=cast(Any, Decimal("0.3")),
            correlation_amount=base.correlation_amount,
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )
    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            constituents=base.constituents,
            observation_terms=base.observation_terms,
            correlation_strike=base.correlation_strike,
            correlation_amount=cast(Any, Decimal("1000")),
            settlement_terms=base.settlement_terms,
            evidence_ref=base.evidence_ref,
        )


def test_distinct_basket_weights_do_not_collapse() -> None:
    first = _correlation()
    second = CorrelationSwapTerms(
        terms_id=first.terms_id,
        instrument_identity_id=first.instrument_identity_id,
        constituents=(
            CorrelationConstituent(_identity(31), Decimal("0.7")),
            CorrelationConstituent(_identity(32), Decimal("0.3")),
        ),
        observation_terms=first.observation_terms,
        correlation_strike=first.correlation_strike,
        correlation_amount=first.correlation_amount,
        settlement_terms=first.settlement_terms,
        evidence_ref=first.evidence_ref,
    )
    assert first.logical_values() != second.logical_values()


def test_values_are_frozen() -> None:
    value = VarianceStrike(Decimal("0.04"))
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", Decimal("0.05"))


@pytest.mark.parametrize("factory", [_variance, _volatility, _correlation])
def test_logical_values_are_repeatable(factory: Any) -> None:
    value = factory()
    assert value.logical_values() == value.logical_values()


def test_source_has_no_runtime_or_calculation_authority() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/volatility_variance_semantics.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "asyncio",
        "httpx",
        "numpy",
        "pandas",
        "requests",
        "scipy",
        "socket",
        "threading",
    }
    imported_names = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not (imported_names | imported_modules).intersection(
        forbidden_import_roots
    )

    forbidden_calls = {
        "calculate",
        "connect",
        "execute",
        "fetch",
        "observe",
        "price",
        "settle",
        "submit",
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called_names.intersection(forbidden_calls)


@pytest.mark.parametrize(
    "forbidden",
    [
        "datetime.now(",
        "uuid4(",
        "time.time(",
        "random.",
        "realized_variance =",
        "realized_volatility =",
        "realized_correlation =",
        "implied_volatility =",
        "provider_symbol",
        "private_key",
    ],
)
def test_source_contains_no_current_or_secret_material(forbidden: str) -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/volatility_variance_semantics.py"
    )
    assert forbidden not in source_path.read_text(encoding="utf-8")
