from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.production_readiness_evidence import (
    ProductionReadinessCheck,
    ProductionReadinessEvidenceValidationError,
    ProductionReadinessRecord,
    ProductionReadinessStatus,
    ProductionReadinessVerdict,
    aggregate_production_readiness,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 10, 30, tzinfo=UTC)


def _record(
    check: ProductionReadinessCheck,
    *,
    status: ProductionReadinessStatus = ProductionReadinessStatus.PASS,
) -> ProductionReadinessRecord:
    return ProductionReadinessRecord(
        check=check,
        status=status,
        observed_at=_NOW,
        code=f"{check.value}.{status.value}",
    )


def _complete_records() -> tuple[ProductionReadinessRecord, ...]:
    return tuple(_record(check) for check in ProductionReadinessCheck)


def test_complete_readiness_passes() -> None:
    result = aggregate_production_readiness(
        _complete_records(),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.verdict is ProductionReadinessVerdict.PASS
    assert result.value.passed is True


def test_any_failed_dimension_forces_fail() -> None:
    records = tuple(
        _record(
            check,
            status=(
                ProductionReadinessStatus.FAIL
                if check is ProductionReadinessCheck.SAFETY_VALIDATION
                else ProductionReadinessStatus.PASS
            ),
        )
        for check in ProductionReadinessCheck
    )

    result = aggregate_production_readiness(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.verdict is ProductionReadinessVerdict.FAIL
    assert result.value.passed is False


def test_missing_dimension_is_rejected() -> None:
    records = tuple(
        _record(check)
        for check in ProductionReadinessCheck
        if check is not ProductionReadinessCheck.OPERATIONS
    )

    result = aggregate_production_readiness(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProductionReadinessEvidenceValidationError)


def test_duplicate_dimension_is_rejected() -> None:
    records = _complete_records() + (_record(ProductionReadinessCheck.CORE_RUNTIME),)

    result = aggregate_production_readiness(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProductionReadinessEvidenceValidationError)


def test_input_order_is_normalized() -> None:
    result = aggregate_production_readiness(
        tuple(reversed(_complete_records())),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert tuple(record.check for record in result.value.records) == tuple(
        ProductionReadinessCheck
    )


def test_record_cannot_postdate_evaluation() -> None:
    records = tuple(
        ProductionReadinessRecord(
            check=check,
            status=ProductionReadinessStatus.PASS,
            observed_at=(
                _NOW + timedelta(seconds=2)
                if check is ProductionReadinessCheck.SAFETY_VALIDATION
                else _NOW
            ),
            code=f"{check.value}.pass",
        )
        for check in ProductionReadinessCheck
    )

    result = aggregate_production_readiness(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProductionReadinessEvidenceValidationError)
