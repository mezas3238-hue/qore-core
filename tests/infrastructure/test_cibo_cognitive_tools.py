"""Tests for the CIBO Cognitive Tool Orchestration and Faculty Bus (CA-12/13/18)."""

from __future__ import annotations

from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveValidationError,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_tools import (
    FacultyCapability,
    FacultyContribution,
    FacultyContributionKind,
    FacultyDescriptor,
    FacultyId,
    FacultyRegistry,
    FacultyVersion,
    ToolId,
    ToolInput,
    ToolRequest,
    ToolResult,
    ToolResultStatus,
    ToolVersion,
    bind_tool_result,
    build_faculty_registry,
    order_contributions,
)
from qore.kernel.result import Failure, Success

_REQUEST = UUID("00000000-0000-0000-0000-0000000000d1")
_CONTRIB = UUID("00000000-0000-0000-0000-0000000000e1")
_CONTRIB_2 = UUID("00000000-0000-0000-0000-0000000000e2")


def _input(label: str = "input") -> ToolInput:
    material = (label,)
    return ToolInput(material=material, fingerprint=fingerprint_material(material))


def _request(tool_id: str = "regime", version: str = "1") -> ToolRequest:
    return ToolRequest(
        request_id=_REQUEST,
        tool_id=ToolId(tool_id),
        tool_version=ToolVersion(version),
        input=_input(),
    )


def _result(
    *,
    tool_id: str = "regime",
    version: str = "1",
    input_label: str = "input",
    output_label: str = "output",
) -> ToolResult:
    output = (output_label,)
    return ToolResult(
        request_id=_REQUEST,
        tool_id=ToolId(tool_id),
        tool_version=ToolVersion(version),
        input_fingerprint=_input(input_label).fingerprint,
        output_material=output,
        output_fingerprint=fingerprint_material(output),
        status=ToolResultStatus.SUCCESS,
        attempt=1,
    )


def test_tool_result_must_bind_exact_request_and_input_fingerprint() -> None:
    request = _request()
    result = _result()
    assert isinstance(bind_tool_result(request, result), Success)

    mismatched_input = _result(input_label="different-input")
    assert isinstance(bind_tool_result(request, mismatched_input), Failure)


def test_mismatched_tool_version_rejected() -> None:
    request = _request(version="1")
    result = _result(version="2")
    assert isinstance(bind_tool_result(request, result), Failure)


def test_mismatched_tool_id_rejected() -> None:
    request = _request(tool_id="regime")
    result = _result(tool_id="volatility")
    assert isinstance(bind_tool_result(request, result), Failure)


def test_retry_to_pass_not_representable_as_success() -> None:
    output = ("output",)
    with pytest.raises(CiboCognitiveValidationError):
        ToolResult(
            request_id=_REQUEST,
            tool_id=ToolId("regime"),
            tool_version=ToolVersion("1"),
            input_fingerprint=_input().fingerprint,
            output_material=output,
            output_fingerprint=fingerprint_material(output),
            status=ToolResultStatus.SUCCESS,
            attempt=2,
        )


def test_failure_result_carries_no_output() -> None:
    result = ToolResult(
        request_id=_REQUEST,
        tool_id=ToolId("regime"),
        tool_version=ToolVersion("1"),
        input_fingerprint=_input().fingerprint,
        output_material=None,
        output_fingerprint=None,
        status=ToolResultStatus.FAILURE,
        attempt=1,
    )
    assert result.status is ToolResultStatus.FAILURE


def test_insufficient_evidence_result_boundary() -> None:
    result = ToolResult(
        request_id=_REQUEST,
        tool_id=ToolId("regime"),
        tool_version=ToolVersion("1"),
        input_fingerprint=_input().fingerprint,
        output_material=None,
        output_fingerprint=None,
        status=ToolResultStatus.INSUFFICIENT_EVIDENCE,
        attempt=1,
    )
    assert result.status is ToolResultStatus.INSUFFICIENT_EVIDENCE


def test_tool_result_attempt_rejects_bool() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ToolResult(
            request_id=_REQUEST,
            tool_id=ToolId("regime"),
            tool_version=ToolVersion("1"),
            input_fingerprint=_input().fingerprint,
            output_material=None,
            output_fingerprint=None,
            status=ToolResultStatus.FAILURE,
            attempt=True,
        )


def test_faculty_contribution_cannot_carry_authority() -> None:
    assert set(FacultyContributionKind.__members__) == {"OBSERVATION", "OPINION", "EVIDENCE"}
    contribution = FacultyContribution(
        contribution_id=_CONTRIB,
        faculty_id=FacultyId("markets"),
        faculty_version=FacultyVersion("1"),
        kind=FacultyContributionKind.OBSERVATION,
        content="volatility rising in observed window",
    )
    assert not hasattr(contribution, "authority")
    assert not hasattr(contribution, "order")
    assert not hasattr(contribution, "account")
    assert not hasattr(contribution, "credential")


def test_duplicate_faculty_identity_version_conflict_rejected() -> None:
    descriptor = FacultyDescriptor(
        faculty_id=FacultyId("markets"),
        faculty_version=FacultyVersion("1"),
        capabilities=(FacultyCapability(name="regime", description="regime detection"),),
    )
    with pytest.raises(CiboCognitiveValidationError):
        build_faculty_registry([descriptor, descriptor])


def test_faculty_ordering_is_deterministic() -> None:
    first = FacultyContribution(
        contribution_id=_CONTRIB,
        faculty_id=FacultyId("markets"),
        faculty_version=FacultyVersion("1"),
        kind=FacultyContributionKind.OPINION,
        content="opinion a",
    )
    second = FacultyContribution(
        contribution_id=_CONTRIB_2,
        faculty_id=FacultyId("research"),
        faculty_version=FacultyVersion("2"),
        kind=FacultyContributionKind.OBSERVATION,
        content="observation b",
    )
    order_one = order_contributions([first, second])
    order_two = order_contributions([second, first])
    assert order_one == order_two
    assert order_one[0].faculty_id.value == "markets"


def test_faculty_registry_is_frozen_and_immutable() -> None:
    registry = build_faculty_registry(
        [
            FacultyDescriptor(
                faculty_id=FacultyId("markets"),
                faculty_version=FacultyVersion("1"),
                capabilities=(FacultyCapability(name="regime", description="regime detection"),),
            )
        ]
    )
    assert isinstance(registry, FacultyRegistry)
    with pytest.raises(AttributeError):
        registry.faculties = ()  # type: ignore[misc]
