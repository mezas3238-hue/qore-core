from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import ExecutivePrincipalId, ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_REF_PARTS = (
    "authorization:",
    "bearer",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
)


class CiboExecutiveDialogueError(DomainError):
    """Base error for evidence-backed CIBO executive dialogue contracts."""

    __slots__ = ()


class CiboExecutiveDialogueValidationError(CiboExecutiveDialogueError):
    """A dialogue value violates a deterministic evidence/publicity invariant."""

    __slots__ = ()


class CiboExecutiveJudgmentState(StrEnum):
    CONFIDENT = "confident"
    CAUTIOUS = "cautious"
    UNCERTAIN = "uncertain"
    CONCERNED = "concerned"
    CRITICAL = "critical"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboExecutiveDialogueValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboExecutiveDialogueValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise CiboExecutiveDialogueValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validate_prompt_ref(value: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._:/-]*",
        value,
    ) is None:
        raise CiboExecutiveDialogueValidationError(
            "CIBO executive prompt ref must use canonical opaque-ref syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_REF_PARTS):
        raise CiboExecutiveDialogueValidationError(
            "CIBO executive prompt ref must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise CiboExecutiveDialogueValidationError(
            f"{field_name} must be a non-empty immutable tuple"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboExecutiveDialogueValidationError(
            f"{field_name} must not contain duplicates"
        )
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class CiboExecutiveDialogueTurnId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive dialogue turn id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CiboExecutivePromptRef:
    """Opaque reference to external prompt content; raw utterances stay outside Core."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_prompt_ref(self.value))

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboExecutiveQuestion:
    turn_id: CiboExecutiveDialogueTurnId
    principal_id: ExecutivePrincipalId
    prompt_ref: CiboExecutivePromptRef
    requested_scope: ExecutiveReadScope
    asked_at: datetime
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not isinstance(self.turn_id, CiboExecutiveDialogueTurnId):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive question requires CiboExecutiveDialogueTurnId"
            )
        if not isinstance(self.principal_id, ExecutivePrincipalId):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive question requires ExecutivePrincipalId"
            )
        if not isinstance(self.prompt_ref, CiboExecutivePromptRef):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive question requires CiboExecutivePromptRef"
            )
        if not isinstance(self.requested_scope, ExecutiveReadScope):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive question requires ExecutiveReadScope"
            )
        _validate_timestamp(self.asked_at, field_name="asked_at")
        if not isinstance(self.correlation_id, CorrelationId):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive question requires CorrelationId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.turn_id.logical_values(),
            self.principal_id.logical_values(),
            self.prompt_ref.logical_values(),
            self.requested_scope.value,
            self.asked_at.isoformat(),
            str(self.correlation_id.value),
        )


@dataclass(frozen=True, slots=True)
class CiboExecutiveAnswer:
    """Structured public answer; never private chain-of-thought."""

    question: CiboExecutiveQuestion
    judgment_state: CiboExecutiveJudgmentState
    summary_code: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]
    answered_at: datetime
    navigation_scope: ExecutiveReadScope | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.question, CiboExecutiveQuestion):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive answer requires CiboExecutiveQuestion"
            )
        if not isinstance(self.judgment_state, CiboExecutiveJudgmentState):
            raise CiboExecutiveDialogueValidationError(
                "CIBO executive answer requires CiboExecutiveJudgmentState"
            )
        object.__setattr__(
            self,
            "summary_code",
            _validate_code(self.summary_code, field_name="CIBO answer summary code"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validate_codes(self.reason_codes, field_name="CIBO answer reason codes"),
        )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(item, ExecutiveEvidenceRef) for item in self.evidence_refs
        ):
            raise CiboExecutiveDialogueValidationError(
                "CIBO answer requires non-empty ExecutiveEvidenceRef tuple"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise CiboExecutiveDialogueValidationError(
                "CIBO answer evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )
        _validate_timestamp(self.answered_at, field_name="answered_at")
        if self.answered_at < self.question.asked_at:
            raise CiboExecutiveDialogueValidationError(
                "CIBO answer cannot predate question"
            )
        if self.navigation_scope is not None and not isinstance(
            self.navigation_scope,
            ExecutiveReadScope,
        ):
            raise CiboExecutiveDialogueValidationError(
                "CIBO answer navigation scope must be ExecutiveReadScope"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.question.logical_values(),
            self.judgment_state.value,
            self.summary_code,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.answered_at.isoformat(),
            None if self.navigation_scope is None else self.navigation_scope.value,
        )


def build_cibo_executive_answer(
    question: CiboExecutiveQuestion,
    *,
    judgment_state: CiboExecutiveJudgmentState,
    summary_code: str,
    reason_codes: tuple[str, ...],
    evidence_refs: tuple[ExecutiveEvidenceRef, ...],
    answered_at: datetime,
    navigation_scope: ExecutiveReadScope | None = None,
) -> Result[CiboExecutiveAnswer, CiboExecutiveDialogueError]:
    if not isinstance(question, CiboExecutiveQuestion):
        return Failure(
            CiboExecutiveDialogueValidationError(
                "CIBO answer builder requires CiboExecutiveQuestion"
            )
        )
    try:
        return Success(
            CiboExecutiveAnswer(
                question=question,
                judgment_state=judgment_state,
                summary_code=summary_code,
                reason_codes=reason_codes,
                evidence_refs=evidence_refs,
                answered_at=answered_at,
                navigation_scope=navigation_scope,
            )
        )
    except CiboExecutiveDialogueError as error:
        return Failure(error)
