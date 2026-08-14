from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure import (
    fixed_income_economics as fie,
    rate_term_structure as rts,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


_AS_OF = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
_RECORDED = datetime(2026, 8, 14, 12, 1, tzinfo=UTC)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _tenor(
    value: int = 1,
    unit: fie.FinancialTenorUnit = fie.FinancialTenorUnit.YEAR,
) -> fie.FinancialTenor:
    return fie.FinancialTenor(value=value, unit=unit)


def _day_count() -> fie.DayCountConventionCode:
    return fie.DayCountConventionCode("actual-365-fixed")


def _rate_convention() -> rts.RateCurveConvention:
    return rts.RateCurveConvention(
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(6, fie.FinancialTenorUnit.MONTH),
    )


def _yield_convention() -> fie.YieldConvention:
    return fie.YieldConvention(
        yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(6, fie.FinancialTenorUnit.MONTH),
    )


def _evidence(value: int) -> rts.RateTermStructureEvidenceRef:
    return rts.RateTermStructureEvidenceRef(_uuid(10_000 + value))


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(20_001)),
        source_id=SourceId(_uuid(20_002)),
        port_name=PortName("market-data.rates"),
    )


def _fingerprint() -> rts.RateTermStructureInputFingerprint:
    return rts.RateTermStructureInputFingerprint("a" * 64)


def _observed_provenance() -> rts.RateTermStructureProvenance:
    return rts.RateTermStructureProvenance(
        kind=rts.RateTermStructureProvenanceKind.OBSERVED,
        methodology=rts.RateTermStructureMethodologyCode("official-published"),
        evidence_ref=_evidence(1),
        source=_source(),
    )


def _computed_provenance() -> rts.RateTermStructureProvenance:
    return rts.RateTermStructureProvenance(
        kind=rts.RateTermStructureProvenanceKind.COMPUTED,
        methodology=rts.RateTermStructureMethodologyCode("bootstrapped-input-set"),
        evidence_ref=_evidence(2),
        input_fingerprint=_fingerprint(),
    )


def _node(
    value: int,
    *,
    ordinal: int | None = None,
    coordinate: rts.RateTermStructureNodeCoordinate | None = None,
    node_value: rts.RateTermStructureNodeValue | None = None,
) -> rts.RateTermStructureNode:
    return rts.RateTermStructureNode(
        node_id=rts.RateTermStructureNodeId(_uuid(30_000 + value)),
        ordinal=rts.RateTermStructureNodeOrdinal(
            value if ordinal is None else ordinal
        ),
        coordinate=coordinate or _tenor(value),
        value=node_value or rts.ZeroRate(Decimal(f"0.0{value}")),
        evidence_ref=_evidence(100 + value),
    )


def _default_convention(
    measure: rts.RateTermStructureMeasure,
) -> rts.RateTermStructureConvention | None:
    if measure in (
        rts.RateTermStructureMeasure.ZERO_RATE,
        rts.RateTermStructureMeasure.PAR_RATE,
        rts.RateTermStructureMeasure.FORWARD_RATE,
    ):
        return _rate_convention()
    if measure is rts.RateTermStructureMeasure.YIELD:
        return _yield_convention()
    return None


def _snapshot(
    *,
    measure: rts.RateTermStructureMeasure = rts.RateTermStructureMeasure.ZERO_RATE,
    nodes: tuple[rts.RateTermStructureNode, ...] | None = None,
    provenance: rts.RateTermStructureProvenance | None = None,
    as_of: datetime = _AS_OF,
    recorded_at: datetime = _RECORDED,
) -> rts.RateTermStructureSnapshot:
    return rts.RateTermStructureSnapshot(
        snapshot_id=rts.RateTermStructureSnapshotId(_uuid(40_001)),
        curve_identity_id=_identity(1),
        currency_identity_id=_identity(2),
        curve_kind=rts.RateTermStructureKindCode("government"),
        measure=measure,
        convention=_default_convention(measure),
        as_of=as_of,
        recorded_at=recorded_at,
        provenance=provenance or _observed_provenance(),
        nodes=nodes or (_node(1), _node(2)),
    )


def test_rate_yield_spread_and_discount_factor_remain_semantically_distinct() -> None:
    magnitude = Decimal("0.0500")
    zero = rts.ZeroRate(magnitude)
    par = rts.ParRate(magnitude)
    forward = rts.ForwardRate(magnitude)
    bond_yield = fie.FixedIncomeYield(magnitude)
    spread = fie.FixedIncomeSpread(magnitude)
    discount = rts.DiscountFactor(magnitude)

    values: tuple[rts.RateTermStructureNodeValue, ...] = (
        zero,
        par,
        forward,
        bond_yield,
        spread,
        discount,
    )
    assert tuple(type(value) for value in values) == (
        rts.ZeroRate,
        rts.ParRate,
        rts.ForwardRate,
        fie.FixedIncomeYield,
        fie.FixedIncomeSpread,
        rts.DiscountFactor,
    )

    logical_values: list[object] = []
    for index, value in enumerate(values, start=1):
        coordinate: rts.RateTermStructureNodeCoordinate = _tenor(index)
        if isinstance(value, rts.ForwardRate):
            coordinate = rts.ForwardRatePeriod(
                None,
                _tenor(3, fie.FinancialTenorUnit.MONTH),
            )
        logical_values.append(
            rts.RateTermStructureNode(
                node_id=rts.RateTermStructureNodeId(_uuid(50_000 + index)),
                ordinal=rts.RateTermStructureNodeOrdinal(index),
                coordinate=coordinate,
                value=value,
                evidence_ref=_evidence(500 + index),
            ).logical_values()[3]
        )

    assert logical_values == [
        ("zero-rate", ("0.05",)),
        ("par-rate", ("0.05",)),
        ("forward-rate", ("0.05",)),
        ("yield", ("0.05",)),
        ("spread", ("0.05",)),
        ("discount-factor", ("0.05",)),
    ]


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_curve_numeric_contracts_reject_non_finite_decimals(value: Decimal) -> None:
    for value_type in (rts.ZeroRate, rts.ParRate, rts.ForwardRate):
        with pytest.raises(
            rts.RateTermStructureValidationError,
            match="finite Decimal",
        ):
            value_type(value)
    with pytest.raises(rts.RateTermStructureValidationError, match="finite Decimal"):
        rts.DiscountFactor(value)


def test_discount_factor_is_positive_but_not_capped_at_one() -> None:
    assert rts.DiscountFactor(Decimal("1.05")).logical_values() == ("1.05",)
    with pytest.raises(rts.RateTermStructureValidationError, match="positive"):
        rts.DiscountFactor(Decimal("0"))
    with pytest.raises(rts.RateTermStructureValidationError, match="positive"):
        rts.DiscountFactor(Decimal("-0.01"))


def test_rate_values_allow_negative_and_canonicalize_signed_zero() -> None:
    assert rts.ZeroRate(Decimal("-0.01")).logical_values() == ("-0.01",)
    assert rts.ParRate(Decimal("-0")).logical_values() == ("0",)
    assert rts.ForwardRate(Decimal("0E-1000")).logical_values() == ("0",)


def test_rate_curve_convention_retains_day_count_and_compounding() -> None:
    convention = _rate_convention()
    assert convention.logical_values() == (
        "rate-convention",
        ("actual-365-fixed",),
        ("periodic",),
        (6, "month"),
    )

    with pytest.raises(rts.RateTermStructureValidationError, match="day_count"):
        replace(convention, day_count=cast(Any, "actual-365-fixed"))
    with pytest.raises(rts.RateTermStructureValidationError, match="compounding"):
        replace(convention, compounding=cast(Any, "periodic"))
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="compounding_tenor",
    ):
        replace(convention, compounding_tenor=cast(Any, "6m"))


def test_periodic_rate_convention_requires_explicit_frequency_tenor() -> None:
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="periodic rate compounding requires compounding_tenor",
    ):
        rts.RateCurveConvention(
            day_count=_day_count(),
            compounding=fie.CompoundingConventionCode("periodic"),
            compounding_tenor=None,
        )


def test_rate_measure_requires_rate_convention_and_rejects_yield_convention() -> None:
    snapshot = _snapshot()
    with pytest.raises(rts.RateTermStructureValidationError, match="match measure"):
        replace(snapshot, convention=None)
    with pytest.raises(rts.RateTermStructureValidationError, match="match measure"):
        replace(snapshot, convention=_yield_convention())


def test_yield_measure_requires_certified_yield_convention() -> None:
    snapshot = _snapshot(
        measure=rts.RateTermStructureMeasure.YIELD,
        nodes=(
            _node(1, node_value=fie.FixedIncomeYield(Decimal("0.04"))),
        ),
    )
    assert isinstance(snapshot.convention, fie.YieldConvention)
    assert snapshot.logical_values()[5][0] == "yield-convention"

    with pytest.raises(rts.RateTermStructureValidationError, match="match measure"):
        replace(snapshot, convention=None)
    with pytest.raises(rts.RateTermStructureValidationError, match="match measure"):
        replace(snapshot, convention=_rate_convention())


def test_spread_and_discount_factor_reject_rate_or_yield_convention() -> None:
    spread = _snapshot(
        measure=rts.RateTermStructureMeasure.SPREAD,
        nodes=(
            _node(1, node_value=fie.FixedIncomeSpread(Decimal("0.001"))),
        ),
    )
    discount = _snapshot(
        measure=rts.RateTermStructureMeasure.DISCOUNT_FACTOR,
        nodes=(
            _node(1, node_value=rts.DiscountFactor(Decimal("0.98"))),
        ),
    )
    assert spread.convention is None
    assert discount.convention is None

    with pytest.raises(rts.RateTermStructureValidationError, match="match measure"):
        replace(spread, convention=_rate_convention())
    with pytest.raises(rts.RateTermStructureValidationError, match="match measure"):
        replace(discount, convention=_yield_convention())


def test_forward_period_is_structural_and_has_no_fixed_seconds_contract() -> None:
    period = rts.ForwardRatePeriod(
        start_tenor=_tenor(3, fie.FinancialTenorUnit.MONTH),
        period_tenor=_tenor(6, fie.FinancialTenorUnit.MONTH),
    )
    assert period.logical_values() == (
        "forward-period",
        (3, "month"),
        (6, "month"),
    )
    assert not hasattr(period, "seconds")
    assert not hasattr(period, "fixed_seconds")

    with pytest.raises(rts.RateTermStructureValidationError, match="start_tenor"):
        replace(period, start_tenor=cast(Any, "3m"))
    with pytest.raises(rts.RateTermStructureValidationError, match="period_tenor"):
        replace(period, period_tenor=cast(Any, "6m"))


def test_node_ordinal_is_strict_positive_int() -> None:
    with pytest.raises(rts.RateTermStructureValidationError, match="positive int"):
        rts.RateTermStructureNodeOrdinal(cast(int, True))
    with pytest.raises(rts.RateTermStructureValidationError, match="positive int"):
        rts.RateTermStructureNodeOrdinal(0)


def test_codes_and_input_fingerprint_fail_closed() -> None:
    assert rts.RateTermStructureKindCode("ois").logical_values() == ("ois",)
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="canonical lowercase",
    ):
        rts.RateTermStructureKindCode("OIS")
    with pytest.raises(rts.RateTermStructureValidationError, match="sha256"):
        rts.RateTermStructureInputFingerprint("A" * 64)
    with pytest.raises(rts.RateTermStructureValidationError, match="sha256"):
        rts.RateTermStructureInputFingerprint("a" * 63)
    with pytest.raises(rts.RateTermStructureValidationError, match="sha256"):
        rts.RateTermStructureInputFingerprint("token=secret")


def test_observed_provenance_requires_source_and_rejects_computed_fingerprint() -> None:
    provenance = _observed_provenance()
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="requires external source",
    ):
        replace(provenance, source=None)
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="must not claim computed input fingerprint",
    ):
        replace(provenance, input_fingerprint=_fingerprint())
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="ExternalSourceDescriptor",
    ):
        replace(provenance, source=cast(Any, "provider"))


def test_computed_provenance_requires_input_fingerprint_and_may_retain_source() -> None:
    provenance = _computed_provenance()
    assert provenance.source is None
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="requires input fingerprint",
    ):
        replace(provenance, input_fingerprint=None)

    with_source = replace(provenance, source=_source())
    assert with_source.source == _source()


def test_provenance_kind_and_methodology_reject_raw_strings() -> None:
    provenance = _observed_provenance()
    with pytest.raises(rts.RateTermStructureValidationError, match="provenance kind"):
        replace(provenance, kind=cast(Any, "observed"))
    with pytest.raises(rts.RateTermStructureValidationError, match="methodology"):
        replace(provenance, methodology=cast(Any, "official-published"))


def test_snapshot_canonicalizes_equal_instants_to_identical_logical_material() -> None:
    offset = timezone(timedelta(hours=-4))
    left = _snapshot()
    right = _snapshot(
        as_of=_AS_OF.astimezone(offset),
        recorded_at=_RECORDED.astimezone(offset),
    )

    assert left.logical_values() == right.logical_values()
    assert left.logical_values()[6] == "2026-08-14T12:00:00.000000+00:00"
    assert left.logical_values()[7] == "2026-08-14T12:01:00.000000+00:00"


def test_snapshot_rejects_naive_timestamps_and_reverse_recording_chronology() -> None:
    snapshot = _snapshot()
    with pytest.raises(rts.RateTermStructureValidationError, match="timezone-aware"):
        replace(snapshot, as_of=datetime(2026, 8, 14, 12, 0))
    with pytest.raises(rts.RateTermStructureValidationError, match="must not predate"):
        replace(
            snapshot,
            recorded_at=_AS_OF - timedelta(microseconds=1),
        )


def test_snapshot_requires_distinct_curve_and_currency_identity() -> None:
    snapshot = _snapshot()
    with pytest.raises(rts.RateTermStructureValidationError, match="must differ"):
        replace(snapshot, currency_identity_id=snapshot.curve_identity_id)
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="EconomicIdentityId",
    ):
        replace(snapshot, curve_identity_id=cast(Any, _uuid(1)))


def test_snapshot_rejects_raw_measure_and_wrong_curve_kind_type() -> None:
    snapshot = _snapshot()
    with pytest.raises(rts.RateTermStructureValidationError, match="measure"):
        replace(snapshot, measure=cast(Any, "zero-rate"))
    with pytest.raises(rts.RateTermStructureValidationError, match="curve_kind"):
        replace(snapshot, curve_kind=cast(Any, "government"))


def test_nodes_require_non_empty_immutable_tuple() -> None:
    snapshot = _snapshot()
    with pytest.raises(rts.RateTermStructureValidationError, match="non-empty tuple"):
        replace(snapshot, nodes=())
    with pytest.raises(rts.RateTermStructureValidationError, match="non-empty tuple"):
        replace(snapshot, nodes=cast(Any, list(snapshot.nodes)))


def test_snapshot_rejects_duplicate_node_ids_ordinals_and_coordinates() -> None:
    first = _node(1)
    second = _node(2)

    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="ids must be unique",
    ):
        _snapshot(nodes=(first, replace(second, node_id=first.node_id)))

    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="ordinals must be unique",
    ):
        _snapshot(nodes=(first, replace(second, ordinal=first.ordinal)))

    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="coordinates must be unique",
    ):
        _snapshot(nodes=(first, replace(second, coordinate=first.coordinate)))


def test_snapshot_requires_contiguous_ordinals_from_one() -> None:
    first = _node(1)
    third = _node(3, ordinal=3)
    with pytest.raises(rts.RateTermStructureValidationError, match="contiguous from 1"):
        _snapshot(nodes=(first, third))


def test_measure_requires_matching_coordinate_and_value_types() -> None:
    cases: tuple[
        tuple[rts.RateTermStructureMeasure, rts.RateTermStructureNodeValue],
        ...,
    ] = (
        (rts.RateTermStructureMeasure.ZERO_RATE, rts.ParRate(Decimal("0.01"))),
        (rts.RateTermStructureMeasure.PAR_RATE, rts.ZeroRate(Decimal("0.01"))),
        (rts.RateTermStructureMeasure.YIELD, rts.ZeroRate(Decimal("0.01"))),
        (rts.RateTermStructureMeasure.SPREAD, fie.FixedIncomeYield(Decimal("0.01"))),
        (
            rts.RateTermStructureMeasure.DISCOUNT_FACTOR,
            rts.ZeroRate(Decimal("0.99")),
        ),
    )
    for measure, value in cases:
        with pytest.raises(
            rts.RateTermStructureValidationError,
            match="must match measure",
        ):
            _snapshot(
                measure=measure,
                nodes=(_node(1, node_value=value),),
            )


def test_yield_spread_and_discount_factor_measures_reuse_certified_types() -> None:
    yield_snapshot = _snapshot(
        measure=rts.RateTermStructureMeasure.YIELD,
        nodes=(
            _node(1, node_value=fie.FixedIncomeYield(Decimal("0.04"))),
            _node(2, node_value=fie.FixedIncomeYield(Decimal("0.045"))),
        ),
    )
    spread_snapshot = _snapshot(
        measure=rts.RateTermStructureMeasure.SPREAD,
        nodes=(
            _node(1, node_value=fie.FixedIncomeSpread(Decimal("0.001"))),
            _node(2, node_value=fie.FixedIncomeSpread(Decimal("0.0015"))),
        ),
    )
    discount_snapshot = _snapshot(
        measure=rts.RateTermStructureMeasure.DISCOUNT_FACTOR,
        nodes=(
            _node(1, node_value=rts.DiscountFactor(Decimal("0.98"))),
            _node(2, node_value=rts.DiscountFactor(Decimal("0.95"))),
        ),
    )

    assert isinstance(yield_snapshot.nodes[0].value, fie.FixedIncomeYield)
    assert isinstance(spread_snapshot.nodes[0].value, fie.FixedIncomeSpread)
    assert isinstance(discount_snapshot.nodes[0].value, rts.DiscountFactor)


def test_forward_rate_measure_requires_forward_period_and_forward_rate() -> None:
    period = rts.ForwardRatePeriod(
        start_tenor=_tenor(3, fie.FinancialTenorUnit.MONTH),
        period_tenor=_tenor(3, fie.FinancialTenorUnit.MONTH),
    )
    forward_node = _node(
        1,
        coordinate=period,
        node_value=rts.ForwardRate(Decimal("0.03")),
    )
    snapshot = _snapshot(
        measure=rts.RateTermStructureMeasure.FORWARD_RATE,
        nodes=(forward_node,),
    )
    assert snapshot.nodes[0].coordinate == period

    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="must match measure",
    ):
        _snapshot(
            measure=rts.RateTermStructureMeasure.FORWARD_RATE,
            nodes=(_node(1, node_value=rts.ForwardRate(Decimal("0.03"))),),
        )
    with pytest.raises(
        rts.RateTermStructureValidationError,
        match="must match measure",
    ):
        _snapshot(
            nodes=(
                _node(
                    1,
                    coordinate=period,
                    node_value=rts.ZeroRate(Decimal("0.03")),
                ),
            ),
        )


def test_snapshot_logical_order_is_caller_order_independent() -> None:
    first = _node(1)
    second = _node(2)
    left = _snapshot(nodes=(first, second))
    right = _snapshot(nodes=(second, first))

    assert left.nodes == (first, second)
    assert right.nodes == (first, second)
    assert left.logical_values() == right.logical_values()


def test_secret_like_material_cannot_enter_id_or_fingerprint_contracts() -> None:
    with pytest.raises(rts.RateTermStructureValidationError, match="UUID"):
        rts.RateTermStructureEvidenceRef(cast(Any, "token=secret"))
    with pytest.raises(rts.RateTermStructureValidationError, match="UUID"):
        rts.RateTermStructureNodeId(cast(Any, "password=secret"))
    with pytest.raises(rts.RateTermStructureValidationError, match="sha256"):
        rts.RateTermStructureInputFingerprint("secret=" + "a" * 57)


def test_snapshot_has_no_curve_engine_or_valuation_methods() -> None:
    snapshot = _snapshot(provenance=_computed_provenance())
    for attribute in (
        "bootstrap",
        "interpolate",
        "extrapolate",
        "discount",
        "present_value",
        "duration",
        "convexity",
    ):
        assert not hasattr(snapshot, attribute)


def test_logical_values_are_deterministic_and_secret_free() -> None:
    snapshot = _snapshot(provenance=_computed_provenance())
    material = repr(snapshot.logical_values()).lower()

    assert snapshot.logical_values() == _snapshot(
        provenance=_computed_provenance()
    ).logical_values()
    assert "token=" not in material
    assert "password=" not in material
    assert "secret=" not in material
