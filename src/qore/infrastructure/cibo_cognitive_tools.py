"""CIBO Cognitive Tool Orchestration and Specialist Faculty Bus (CA-12/13/18).

Provider-neutral typed tool orchestration substrate with deterministic tool
identity/version, a typed request/result envelope, exact input fingerprints, and
exact output/evidence fingerprints. Failures and insufficient-evidence results
carry a ``None`` output boundary, and a retry-to-pass result is never
representable as success.

A common Specialist Faculty Interface / cognition bus represents future
functional faculties (Markets, Traders, Portfolio, Profitability, Research,
Core Health) as bounded observation/opinion/evidence contributions. It
transfers no authority, preserves disagreement, orders contributions
deterministically, and exposes an immutable, versioned capability registry —
never a global mutable plugin registry.

Architecture laws honoured: provider-neutrality (12), no authority transfer
(3, 4, 13), exact fingerprints (7, 15, 19), no retry-to-pass (5, 14), no prose
replacing exact math (7), deterministic ordering (19), secret-bearing strings
fail closed (20), no global mutable state (21).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from re import compile
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    canonical_material,
    contains_secret_material,
    fingerprint_material,
    require_exact_int,
    require_exact_str,
)
from qore.kernel.result import Failure, Result, Success

_TOKEN = compile(r"[0-9A-Za-z._-]{1,128}")


class ToolOrchestrationError(CiboCognitiveError):
    """Base error for the CIBO cognitive tool/faculty substrate."""

    __slots__ = ()


class ToolOrchestrationValidationError(ToolOrchestrationError, CiboCognitiveValidationError):
    """Violation of a tool or faculty bus invariant."""

    __slots__ = ()


def _require_token(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if _TOKEN.fullmatch(text) is None:
        raise ToolOrchestrationValidationError(
            f"{field} must be a non-blank token of letters, digits, dot, underscore or hyphen"
        )
    if contains_secret_material(text):
        raise ToolOrchestrationValidationError(
            f"{field} must not carry secret-bearing material"
        )
    return text


@dataclass(frozen=True, slots=True)
class ToolId:
    """Deterministic identity of a cognitive tool."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        _require_token(self.value, field="tool id")

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ToolVersion:
    """Deterministic version of a cognitive tool."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        _require_token(self.value, field="tool version")

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ToolInput:
    """Exact, fingerprinted tool input material (no RNG, no ambient state)."""

    material: tuple[object, ...]
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.material) is not tuple:
            raise ToolOrchestrationValidationError("tool input material must be a tuple")
        for item in self.material:
            canonical_material(item)
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise ToolOrchestrationValidationError(
                "tool input fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        expected = fingerprint_material(self.material)
        if self.fingerprint != expected:
            raise ToolOrchestrationValidationError(
                "tool input fingerprint does not match its material"
            )


@dataclass(frozen=True, slots=True)
class ToolRequest:
    """Typed request envelope for a deterministic cognitive tool call."""

    request_id: UUID
    tool_id: ToolId
    tool_version: ToolVersion
    input: ToolInput

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.request_id) is not UUID:
            raise ToolOrchestrationValidationError("tool request id must be a UUID")
        if type(self.tool_id) is not ToolId:
            raise ToolOrchestrationValidationError("tool request tool id must be a ToolId")
        self.tool_id.revalidate()
        if type(self.tool_version) is not ToolVersion:
            raise ToolOrchestrationValidationError(
                "tool request tool version must be a ToolVersion"
            )
        self.tool_version.revalidate()
        if type(self.input) is not ToolInput:
            raise ToolOrchestrationValidationError("tool request input must be a ToolInput")
        self.input.revalidate()

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.request_id),
            self.tool_id.value,
            self.tool_version.value,
            self.input.fingerprint.value,
        )


class ToolResultStatus(StrEnum):
    """Explicit result boundary of a cognitive tool call."""

    SUCCESS = "success"
    FAILURE = "failure"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Typed result envelope bound to an exact request input fingerprint."""

    request_id: UUID
    tool_id: ToolId
    tool_version: ToolVersion
    input_fingerprint: CiboCognitiveFingerprint
    output_material: tuple[object, ...] | None
    output_fingerprint: CiboCognitiveFingerprint | None
    status: ToolResultStatus
    attempt: int

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.request_id) is not UUID:
            raise ToolOrchestrationValidationError("tool result request id must be a UUID")
        if type(self.tool_id) is not ToolId:
            raise ToolOrchestrationValidationError("tool result tool id must be a ToolId")
        self.tool_id.revalidate()
        if type(self.tool_version) is not ToolVersion:
            raise ToolOrchestrationValidationError(
                "tool result tool version must be a ToolVersion"
            )
        self.tool_version.revalidate()
        if type(self.input_fingerprint) is not CiboCognitiveFingerprint:
            raise ToolOrchestrationValidationError(
                "tool result input fingerprint must be a CiboCognitiveFingerprint"
            )
        self.input_fingerprint.revalidate()
        if type(self.status) is not ToolResultStatus:
            raise ToolOrchestrationValidationError(
                "tool result status must be a ToolResultStatus"
            )
        require_exact_int(self.attempt, field="tool result attempt")
        if self.attempt < 1:
            raise ToolOrchestrationValidationError("tool result attempt must be positive")
        if self.status is ToolResultStatus.SUCCESS:
            if self.attempt != 1:
                raise ToolOrchestrationValidationError(
                    "a retry-to-pass result cannot be represented as success"
                )
            if type(self.output_material) is not tuple:
                raise ToolOrchestrationValidationError(
                    "a successful tool result must carry output material"
                )
            for item in self.output_material:
                canonical_material(item)
            if type(self.output_fingerprint) is not CiboCognitiveFingerprint:
                raise ToolOrchestrationValidationError(
                    "a successful tool result must carry an output fingerprint"
                )
            self.output_fingerprint.revalidate()
            if self.output_fingerprint != fingerprint_material(self.output_material):
                raise ToolOrchestrationValidationError(
                    "tool output fingerprint does not match its material"
                )
        else:
            if self.output_material is not None or self.output_fingerprint is not None:
                raise ToolOrchestrationValidationError(
                    "a non-successful tool result must carry no output material or fingerprint"
                )


def bind_tool_result(
    request: ToolRequest, result: ToolResult
) -> Result[ToolResult, ToolOrchestrationError]:
    """Bind a result to its exact request and input fingerprint.

    The result is accepted only when its request id, tool id, tool version, and
    input fingerprint all match the request exactly.
    """
    if type(request) is not ToolRequest:
        return Failure(ToolOrchestrationValidationError("request must be a ToolRequest"))
    if type(result) is not ToolResult:
        return Failure(ToolOrchestrationValidationError("result must be a ToolResult"))
    request.revalidate()
    result.revalidate()
    if result.request_id != request.request_id:
        return Failure(
            ToolOrchestrationValidationError("result request id does not match the request")
        )
    if result.tool_id != request.tool_id:
        return Failure(
            ToolOrchestrationValidationError("result tool id does not match the request")
        )
    if result.tool_version != request.tool_version:
        return Failure(
            ToolOrchestrationValidationError("result tool version does not match the request")
        )
    if result.input_fingerprint != request.input.fingerprint:
        return Failure(
            ToolOrchestrationValidationError(
                "result input fingerprint does not match the request input"
            )
        )
    return Success(result)


class FacultyContributionKind(StrEnum):
    """Bounded contribution kinds: observation, opinion, or evidence. No authority."""

    OBSERVATION = "observation"
    OPINION = "opinion"
    EVIDENCE = "evidence"


@dataclass(frozen=True, slots=True)
class FacultyId:
    """Deterministic identity of a specialist faculty."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        _require_token(self.value, field="faculty id")

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FacultyVersion:
    """Deterministic version of a specialist faculty."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        _require_token(self.value, field="faculty version")

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FacultyCapability:
    """An immutable, versioned capability exposed by a faculty."""

    name: str
    description: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        _require_token(self.name, field="faculty capability name")
        require_exact_str(self.description, field="faculty capability description")
        if not self.description.strip():
            raise ToolOrchestrationValidationError(
                "faculty capability description must not be blank"
            )
        if contains_secret_material(self.description):
            raise ToolOrchestrationValidationError(
                "faculty capability description must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.name, self.description)


@dataclass(frozen=True, slots=True)
class FacultyContribution:
    """Bounded observation/opinion/evidence contribution; no authority transfer."""

    contribution_id: UUID
    faculty_id: FacultyId
    faculty_version: FacultyVersion
    kind: FacultyContributionKind
    content: str
    evidence_fingerprint: CiboCognitiveFingerprint | None = None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.contribution_id) is not UUID:
            raise ToolOrchestrationValidationError(
                "faculty contribution id must be a UUID"
            )
        if type(self.faculty_id) is not FacultyId:
            raise ToolOrchestrationValidationError(
                "faculty contribution faculty id must be a FacultyId"
            )
        self.faculty_id.revalidate()
        if type(self.faculty_version) is not FacultyVersion:
            raise ToolOrchestrationValidationError(
                "faculty contribution faculty version must be a FacultyVersion"
            )
        self.faculty_version.revalidate()
        if type(self.kind) is not FacultyContributionKind:
            raise ToolOrchestrationValidationError(
                "faculty contribution kind must be a FacultyContributionKind"
            )
        require_exact_str(self.content, field="faculty contribution content")
        if not self.content.strip():
            raise ToolOrchestrationValidationError(
                "faculty contribution content must not be blank"
            )
        if contains_secret_material(self.content):
            raise ToolOrchestrationValidationError(
                "faculty contribution content must not carry secret-bearing material"
            )
        if self.evidence_fingerprint is not None:
            if type(self.evidence_fingerprint) is not CiboCognitiveFingerprint:
                raise ToolOrchestrationValidationError(
                    "faculty evidence fingerprint must be a CiboCognitiveFingerprint"
                )
            self.evidence_fingerprint.revalidate()
        if self.kind is FacultyContributionKind.EVIDENCE and self.evidence_fingerprint is None:
            raise ToolOrchestrationValidationError(
                "an evidence contribution must carry an evidence fingerprint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.contribution_id),
            self.faculty_id.value,
            self.faculty_version.value,
            self.kind.value,
            self.content,
            self.evidence_fingerprint.value if self.evidence_fingerprint is not None else None,
        )

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.faculty_id.value,
            self.faculty_version.value,
            self.kind.value,
            self.content,
            str(self.contribution_id),
        )


@dataclass(frozen=True, slots=True)
class FacultyDescriptor:
    """Immutable faculty identity/version with its sorted capability set."""

    faculty_id: FacultyId
    faculty_version: FacultyVersion
    capabilities: tuple[FacultyCapability, ...]

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.faculty_id) is not FacultyId:
            raise ToolOrchestrationValidationError(
                "faculty descriptor faculty id must be a FacultyId"
            )
        self.faculty_id.revalidate()
        if type(self.faculty_version) is not FacultyVersion:
            raise ToolOrchestrationValidationError(
                "faculty descriptor faculty version must be a FacultyVersion"
            )
        self.faculty_version.revalidate()
        if type(self.capabilities) is not tuple:
            raise ToolOrchestrationValidationError("faculty capabilities must be a tuple")
        for capability in self.capabilities:
            if type(capability) is not FacultyCapability:
                raise ToolOrchestrationValidationError(
                    "faculty capabilities must contain only FacultyCapability values"
                )
            capability.revalidate()
        names = [capability.name for capability in self.capabilities]
        if len(names) != len(set(names)):
            raise ToolOrchestrationValidationError("faculty capabilities must be unique")
        ordered = tuple(sorted(self.capabilities, key=lambda c: c.name))
        if self.capabilities != ordered:
            raise ToolOrchestrationValidationError(
                "faculty capabilities must be canonically ordered"
            )


@dataclass(frozen=True, slots=True)
class FacultyRegistry:
    """Immutable, versioned capability registry (no global mutable plugin state)."""

    faculties: tuple[FacultyDescriptor, ...]

    def __post_init__(self) -> None:
        if type(self.faculties) is not tuple:
            raise ToolOrchestrationValidationError("faculty registry faculties must be a tuple")
        seen: set[tuple[str, str]] = set()
        for descriptor in self.faculties:
            if type(descriptor) is not FacultyDescriptor:
                raise ToolOrchestrationValidationError(
                    "faculty registry must contain only FacultyDescriptor values"
                )
            descriptor.revalidate()
            key = (descriptor.faculty_id.value, descriptor.faculty_version.value)
            if key in seen:
                raise ToolOrchestrationValidationError(
                    "faculty registry must not contain duplicate faculty identity/version"
                )
            seen.add(key)
        ordered = tuple(
            sorted(self.faculties, key=lambda d: (d.faculty_id.value, d.faculty_version.value))
        )
        if self.faculties != ordered:
            raise ToolOrchestrationValidationError("faculty registry must be canonically ordered")


def build_faculty_registry(
    descriptors: Sequence[FacultyDescriptor],
) -> FacultyRegistry:
    """Build an immutable, versioned faculty capability registry."""
    if not isinstance(descriptors, Sequence):
        raise ToolOrchestrationValidationError("descriptors must be a sequence")
    return FacultyRegistry(faculties=tuple(descriptors))


def order_contributions(
    contributions: Sequence[FacultyContribution],
) -> tuple[FacultyContribution, ...]:
    """Order contributions deterministically, preserving disagreement (no merge)."""
    if not isinstance(contributions, Sequence):
        raise ToolOrchestrationValidationError("contributions must be a sequence")
    items = []
    for contribution in contributions:
        if type(contribution) is not FacultyContribution:
            raise ToolOrchestrationValidationError(
                "contributions must contain only FacultyContribution values"
            )
        contribution.revalidate()
        items.append(contribution)
    return tuple(sorted(items, key=lambda c: c.sort_key()))


__all__ = [
    "FacultyCapability",
    "FacultyContribution",
    "FacultyContributionKind",
    "FacultyDescriptor",
    "FacultyId",
    "FacultyRegistry",
    "FacultyVersion",
    "ToolId",
    "ToolInput",
    "ToolOrchestrationError",
    "ToolOrchestrationValidationError",
    "ToolRequest",
    "ToolResult",
    "ToolResultStatus",
    "ToolVersion",
    "bind_tool_result",
    "build_faculty_registry",
    "order_contributions",
]
