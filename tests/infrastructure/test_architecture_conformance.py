from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.architecture_conformance import (
    ArchitectureConformanceCheck,
    ArchitectureConformanceRecord,
    ArchitectureConformanceStatus,
    ArchitectureConformanceValidationError,
    ArchitectureConformanceVerdict,
    aggregate_architecture_conformance,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 10, 20, tzinfo=UTC)


def _record(
    check: ArchitectureConformanceCheck,
    *,
    status: ArchitectureConformanceStatus = ArchitectureConformanceStatus.PASS,
) -> ArchitectureConformanceRecord:
    return ArchitectureConformanceRecord(
        check=check,
        status=status,
        observed_at=_NOW,
        code=f"{check.value}.{status.value}",
    )


def _complete_records() -> tuple[ArchitectureConformanceRecord, ...]:
    return tuple(_record(check) for check in ArchitectureConformanceCheck)


def test_complete_conformance_passes() -> None:
    result = aggregate_architecture_conformance(
        _complete_records(),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.verdict is ArchitectureConformanceVerdict.PASS
    assert result.value.passed is True


def test_any_failed_dimension_forces_fail_verdict() -> None:
    records = tuple(
        _record(
            check,
            status=(
                ArchitectureConformanceStatus.FAIL
                if check is ArchitectureConformanceCheck.DEPENDENCY_DIRECTION
                else ArchitectureConformanceStatus.PASS
            ),
        )
        for check in ArchitectureConformanceCheck
    )

    result = aggregate_architecture_conformance(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.verdict is ArchitectureConformanceVerdict.FAIL
    assert result.value.passed is False


def test_missing_dimension_is_rejected() -> None:
    records = tuple(
        _record(check)
        for check in ArchitectureConformanceCheck
        if check is not ArchitectureConformanceCheck.SECRET_SAFETY
    )

    result = aggregate_architecture_conformance(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ArchitectureConformanceValidationError)


def test_duplicate_dimension_is_rejected() -> None:
    records = _complete_records() + (
        _record(ArchitectureConformanceCheck.CORE_ISOLATION),
    )

    result = aggregate_architecture_conformance(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ArchitectureConformanceValidationError)


def test_input_order_is_normalized() -> None:
    result = aggregate_architecture_conformance(
        tuple(reversed(_complete_records())),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert tuple(record.check for record in result.value.records) == tuple(
        ArchitectureConformanceCheck
    )


def test_record_cannot_postdate_evaluation() -> None:
    records = tuple(
        ArchitectureConformanceRecord(
            check=check,
            status=ArchitectureConformanceStatus.PASS,
            observed_at=(
                _NOW + timedelta(seconds=2)
                if check is ArchitectureConformanceCheck.SECRET_SAFETY
                else _NOW
            ),
            code=f"{check.value}.pass",
        )
        for check in ArchitectureConformanceCheck
    )

    result = aggregate_architecture_conformance(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ArchitectureConformanceValidationError)


def test_evidence_code_rejects_sensitive_material() -> None:
    with pytest.raises(ArchitectureConformanceValidationError):
        ArchitectureConformanceRecord(
            check=ArchitectureConformanceCheck.SECRET_SAFETY,
            status=ArchitectureConformanceStatus.FAIL,
            observed_at=_NOW,
            code="client_secret.exposed",
        )
