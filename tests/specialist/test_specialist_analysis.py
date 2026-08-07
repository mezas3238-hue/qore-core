from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistMetadata,
    SpecialistReason,
    SpecialistReasonCode,
    SpecialistValidationError,
)

_ANALYSIS_ID = SpecialistAnalysisId(
    UUID("90000000-0000-0000-0000-000000000001")
)
_CORRELATION_ID = CorrelationId(UUID("90000000-0000-0000-0000-000000000002"))
_CAUSATION_ID = CausationId(UUID("90000000-0000-0000-0000-000000000003"))
_TIMESTAMP = datetime(2026, 8, 7, 21, 0, tzinfo=UTC)


def _reason() -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode("specialist.signal-aligned"),
        summary="Explicit inputs are aligned",
        attributes={"evidence": ("a", "b")},
    )


def _metadata() -> SpecialistMetadata:
    return SpecialistMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"scope": "internal", "version": 1},
    )


def _completed() -> SpecialistAnalysis:
    return SpecialistAnalysis(
        analysis_id=_ANALYSIS_ID,
        timestamp=_TIMESTAMP,
        kind=SpecialistKind("virtual-trader.structure"),
        status=SpecialistAnalysisStatus.COMPLETED,
        metadata=_metadata(),
        confidence=SpecialistConfidence(0.75),
        reasons=(_reason(),),
    )


def test_pending_analysis_is_explicit_and_empty_of_final_assessment() -> None:
    analysis = SpecialistAnalysis(
        analysis_id=_ANALYSIS_ID,
        timestamp=_TIMESTAMP,
        kind=SpecialistKind("validation.precheck"),
        status=SpecialistAnalysisStatus.PENDING,
        metadata=_metadata(),
    )

    assert analysis.confidence is None
    assert analysis.reasons == ()
    assert analysis.metadata.correlation_id == _CORRELATION_ID
    assert analysis.metadata.causation_id == _CAUSATION_ID


def test_completed_analysis_requires_confidence() -> None:
    with pytest.raises(SpecialistValidationError, match="must have confidence"):
        SpecialistAnalysis(
            analysis_id=_ANALYSIS_ID,
            timestamp=_TIMESTAMP,
            kind=SpecialistKind("statistics.summary"),
            status=SpecialistAnalysisStatus.COMPLETED,
            metadata=_metadata(),
            reasons=(_reason(),),
        )


def test_completed_analysis_requires_reason() -> None:
    with pytest.raises(SpecialistValidationError, match="at least one reason"):
        SpecialistAnalysis(
            analysis_id=_ANALYSIS_ID,
            timestamp=_TIMESTAMP,
            kind=SpecialistKind("knowledge.review"),
            status=SpecialistAnalysisStatus.COMPLETED,
            metadata=_metadata(),
            confidence=SpecialistConfidence(0.5),
        )


def test_pending_analysis_rejects_confidence() -> None:
    with pytest.raises(SpecialistValidationError, match="must not have confidence"):
        SpecialistAnalysis(
            analysis_id=_ANALYSIS_ID,
            timestamp=_TIMESTAMP,
            kind=SpecialistKind("optimization.review"),
            status=SpecialistAnalysisStatus.PENDING,
            metadata=_metadata(),
            confidence=SpecialistConfidence(0.5),
        )


def test_pending_analysis_rejects_final_reasons() -> None:
    with pytest.raises(SpecialistValidationError, match="must not have final reasons"):
        SpecialistAnalysis(
            analysis_id=_ANALYSIS_ID,
            timestamp=_TIMESTAMP,
            kind=SpecialistKind("validation.review"),
            status=SpecialistAnalysisStatus.PENDING,
            metadata=_metadata(),
            reasons=(_reason(),),
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_confidence_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(SpecialistValidationError, match="finite float"):
        SpecialistConfidence(value)


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_confidence_rejects_values_outside_unit_interval(value: float) -> None:
    with pytest.raises(SpecialistValidationError, match="between 0.0 and 1.0"):
        SpecialistConfidence(value)


def test_confidence_rejects_bool_even_though_bool_is_numeric() -> None:
    with pytest.raises(SpecialistValidationError, match="finite float"):
        SpecialistConfidence(cast(float, True))


def test_confidence_rejects_integer_runtime_bypass() -> None:
    with pytest.raises(SpecialistValidationError, match="finite float"):
        SpecialistConfidence(cast(float, 1))


@pytest.mark.parametrize(
    "value",
    ["", "VirtualTrader", "virtual_trader", " virtual-trader", "1specialist"],
)
def test_kind_rejects_invalid_names(value: str) -> None:
    with pytest.raises(SpecialistValidationError, match="specialist kind"):
        SpecialistKind(value)


@pytest.mark.parametrize("value", ["", "Bad Code", "reason_code", "1reason"])
def test_reason_code_rejects_invalid_names(value: str) -> None:
    with pytest.raises(SpecialistValidationError, match="reason code"):
        SpecialistReasonCode(value)


def test_reason_requires_non_empty_summary() -> None:
    with pytest.raises(SpecialistValidationError, match="summary"):
        SpecialistReason(
            code=SpecialistReasonCode("specialist.reason"),
            summary="   ",
        )


def test_metadata_is_defensively_copied_and_sorted() -> None:
    attributes: dict[str, DomainMetadataValue] = {"z": 3, "a": ("x", 1)}
    metadata = SpecialistMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes=attributes,
    )
    attributes["a"] = "changed"
    attributes["new"] = 4

    assert tuple(metadata.attributes.items()) == (("a", ("x", 1)), ("z", 3))
    with pytest.raises(TypeError):
        metadata.attributes["blocked"] = "mutation"  # type: ignore[index]


def test_reason_attributes_are_defensively_copied_and_sorted() -> None:
    attributes: dict[str, DomainMetadataValue] = {"z": 3, "a": "x"}
    reason = SpecialistReason(
        code=SpecialistReasonCode("specialist.reason"),
        summary="Reason",
        attributes=attributes,
    )
    attributes["a"] = "changed"

    assert tuple(reason.attributes.items()) == (("a", "x"), ("z", 3))


@pytest.mark.parametrize("reserved", ["correlation_id", "causation_id"])
def test_metadata_rejects_reserved_keys(reserved: str) -> None:
    with pytest.raises(SpecialistValidationError, match="reserved specialist metadata"):
        SpecialistMetadata(
            correlation_id=_CORRELATION_ID,
            attributes={reserved: "shadow"},
        )


def test_metadata_and_reason_reject_empty_keys() -> None:
    with pytest.raises(SpecialistValidationError, match="keys must not be empty"):
        SpecialistMetadata(
            correlation_id=_CORRELATION_ID,
            attributes={" ": "x"},
        )
    with pytest.raises(SpecialistValidationError, match="keys must not be empty"):
        SpecialistReason(
            code=SpecialistReasonCode("specialist.reason"),
            summary="Reason",
            attributes={"": "x"},
        )


@pytest.mark.parametrize("invalid", [["mutable"], {"mutable": True}, {"mutable"}])
def test_metadata_rejects_mutable_values(invalid: object) -> None:
    with pytest.raises(SpecialistValidationError, match="immutable scalars or tuples"):
        SpecialistMetadata(
            correlation_id=_CORRELATION_ID,
            attributes={"bad": cast(DomainMetadataValue, invalid)},
        )


def test_metadata_rejects_mutable_values_nested_inside_tuple() -> None:
    invalid = cast(DomainMetadataValue, ("ok", ["mutable"]))

    with pytest.raises(SpecialistValidationError, match="immutable scalars or tuples"):
        SpecialistMetadata(
            correlation_id=_CORRELATION_ID,
            attributes={"bad": invalid},
        )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_metadata_rejects_non_finite_floats(invalid: float) -> None:
    with pytest.raises(SpecialistValidationError, match="floats must be finite"):
        SpecialistMetadata(
            correlation_id=_CORRELATION_ID,
            attributes={"bad": invalid},
        )


def test_analysis_rejects_mutable_reason_container_runtime_bypass() -> None:
    with pytest.raises(SpecialistValidationError, match="immutable tuple"):
        SpecialistAnalysis(
            analysis_id=_ANALYSIS_ID,
            timestamp=_TIMESTAMP,
            kind=SpecialistKind("validation.review"),
            status=SpecialistAnalysisStatus.COMPLETED,
            metadata=_metadata(),
            confidence=SpecialistConfidence(0.8),
            reasons=cast(tuple[SpecialistReason, ...], [_reason()]),
        )


def test_analysis_rejects_non_reason_values_runtime_bypass() -> None:
    with pytest.raises(SpecialistValidationError, match="SpecialistReason"):
        SpecialistAnalysis(
            analysis_id=_ANALYSIS_ID,
            timestamp=_TIMESTAMP,
            kind=SpecialistKind("validation.review"),
            status=SpecialistAnalysisStatus.COMPLETED,
            metadata=_metadata(),
            confidence=SpecialistConfidence(0.8),
            reasons=cast(tuple[SpecialistReason, ...], ("not-a-reason",)),
        )


def test_logical_values_are_stable_and_value_based() -> None:
    first = _completed()
    second = _completed()

    assert first.logical_values() == second.logical_values()
    assert first.logical_values() == (
        "90000000-0000-0000-0000-000000000001",
        "2026-08-07T21:00:00+00:00",
        "virtual-trader.structure",
        "completed",
        (
            "90000000-0000-0000-0000-000000000002",
            "90000000-0000-0000-0000-000000000003",
            (("scope", "internal"), ("version", 1)),
        ),
        0.75,
        (
            (
                "specialist.signal-aligned",
                "Explicit inputs are aligned",
                (("evidence", ("a", "b")),),
            ),
        ),
    )


def test_identity_timestamp_and_trace_are_only_the_supplied_values() -> None:
    analysis = _completed()

    assert analysis.analysis_id is _ANALYSIS_ID
    assert analysis.timestamp is _TIMESTAMP
    assert analysis.metadata.correlation_id is _CORRELATION_ID
    assert analysis.metadata.causation_id is _CAUSATION_ID
