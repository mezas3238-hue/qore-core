from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_economic_evidence import ResearchReturnObservation
from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.infrastructure.research_serial_dependence import (
    ResearchLagOneCorrelationStatus,
    ResearchSerialDependenceDiagnosticId,
    ResearchSerialDependenceValidationError,
    build_research_serial_dependence_diagnostic,
)
from qore.kernel.result import Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"75000000-0000-0000-0000-{suffix:012d}")


def _sample(value: str) -> ResearchReturnObservation:
    sample = object.__new__(ResearchReturnObservation)
    object.__setattr__(sample, "return_rate", Decimal(value))
    return sample


def _frame(*values: str) -> ResearchSamplingFrame:
    frame = object.__new__(ResearchSamplingFrame)
    object.__setattr__(frame, "samples", tuple(_sample(value) for value in values))
    return frame


def test_lag_one_correlation_detects_perfect_positive_sequence() -> None:
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(1)),
        frame=_frame("0.1", "0.2", "0.3"),
    )

    assert isinstance(built, Success)
    diagnostic = built.value
    assert diagnostic.status is ResearchLagOneCorrelationStatus.DEFINED
    assert diagnostic.sample_size == 3
    assert diagnostic.pair_count == 2
    assert diagnostic.correlation == Decimal("1")


def test_lag_one_correlation_detects_perfect_negative_sequence() -> None:
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(2)),
        frame=_frame("0.1", "-0.1", "0.1"),
    )

    assert isinstance(built, Success)
    assert built.value.status is ResearchLagOneCorrelationStatus.DEFINED
    assert built.value.correlation == Decimal("-1")


def test_lag_one_reports_insufficient_sample_without_inventing_correlation() -> None:
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(3)),
        frame=_frame("0.1", "0.2"),
    )

    assert isinstance(built, Success)
    diagnostic = built.value
    assert diagnostic.status is ResearchLagOneCorrelationStatus.INSUFFICIENT_SAMPLE
    assert diagnostic.pair_count == 1
    assert diagnostic.correlation is None


def test_lag_one_reports_zero_variance_as_undefined() -> None:
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(4)),
        frame=_frame("0.1", "0.1", "0.1"),
    )

    assert isinstance(built, Success)
    diagnostic = built.value
    assert diagnostic.status is ResearchLagOneCorrelationStatus.UNDEFINED_ZERO_VARIANCE
    assert diagnostic.pair_count == 2
    assert diagnostic.correlation is None


def test_serial_dependence_rejects_derived_metric_tampering() -> None:
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(5)),
        frame=_frame("0.1", "0.2", "0.3"),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchSerialDependenceValidationError):
        replace(built.value, correlation=Decimal("0"))
    with pytest.raises(ResearchSerialDependenceValidationError):
        replace(
            built.value,
            status=ResearchLagOneCorrelationStatus.UNDEFINED_ZERO_VARIANCE,
        )


def test_lag_one_diagnostic_makes_no_independence_or_significance_claims() -> None:
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(6)),
        frame=_frame("0.1", "0.2", "0.15", "0.25"),
    )
    assert isinstance(built, Success)
    diagnostic = built.value

    assert not hasattr(diagnostic, "iid")
    assert not hasattr(diagnostic, "independent")
    assert not hasattr(diagnostic, "stationary")
    assert not hasattr(diagnostic, "p_value")
    assert not hasattr(diagnostic, "statistically_significant")
    assert not hasattr(diagnostic, "bootstrap_ready")
