from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import CiboFunctionalAuthority
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

# Reused discipline from qore.governance.cibo_executive_dialogue: canonical
# lowercase codes, opaque refs for anything that could otherwise carry raw
# utterances, and sensitive-substring rejection. Raw text stays outside Core.
_SENSITIVE_REF_PARTS = (
    "authorization:",
    "bearer",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"
_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"


class CiboCeoDialogueError(DomainError):
    """Base error for the CEO Voice functional dialogue contracts."""

    __slots__ = ()


class CiboCeoDialogueValidationError(CiboCeoDialogueError):
    """A CEO dialogue value violates a deterministic invariant."""

    __slots__ = ()


class CiboCeoDialogueBlockedError(CiboCeoDialogueError):
    """Fail-closed result when a CEO dialogue result cannot be produced safely."""

    __slots__ = ()


class CiboCeoMode(StrEnum):
    """The bounded set of CEO dialogue modes. Free-form text is not a member."""

    EXPLAIN = "explain"
    ASK = "ask"
    DOUBT = "doubt"
    COMPARE = "compare"
    OPINE = "opine"
    STATE_UNKNOWN = "state-unknown"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboCeoDialogueValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCeoDialogueValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboCeoDialogueValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_REF_PARTS):
        raise CiboCeoDialogueValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_opaque_ref(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_OPAQUE_REF_RE, value) is None:
        raise CiboCeoDialogueValidationError(
            f"{field_name} must use canonical opaque-ref syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_REF_PARTS):
        raise CiboCeoDialogueValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboCeoDialogueValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboCeoDialogueValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_question_refs(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboCeoDialogueValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(
        _validate_opaque_ref(value, field_name=field_name) for value in values
    )
    if len(set(normalized)) != len(normalized):
        raise CiboCeoDialogueValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboCeoDialogueValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboCeoDialogueValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


_MODE_AUTHORITY = {
    CiboCeoMode.EXPLAIN: CiboFunctionalAuthority.OPINION,
    CiboCeoMode.ASK: CiboFunctionalAuthority.REQUEST,
    CiboCeoMode.DOUBT: CiboFunctionalAuthority.OBSERVATION,
    CiboCeoMode.COMPARE: CiboFunctionalAuthority.OPINION,
    CiboCeoMode.OPINE: CiboFunctionalAuthority.OPINION,
    CiboCeoMode.STATE_UNKNOWN: CiboFunctionalAuthority.OBSERVATION,
}


@dataclass(frozen=True, slots=True)
class CiboCeoDialogueResult:
    """A structured CEO dialogue result with a strict mode/authority ceiling.

    The ceiling is REQUEST: dialogue may opine, observe, or ask, but it never
    grants command or execution authority (no such field exists).
    """

    mode: CiboCeoMode
    summary_code: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[CiboEvidenceRef, ...]
    question_refs: tuple[str, ...]
    spoken_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if type(self.mode) is not CiboCeoMode:
            raise CiboCeoDialogueValidationError(
                "CEO dialogue result requires CiboCeoMode"
            )
        object.__setattr__(
            self,
            "summary_code",
            _validate_code(self.summary_code, field_name="summary code"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validate_codes(self.reason_codes, field_name="reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        object.__setattr__(
            self,
            "question_refs",
            _validate_question_refs(self.question_refs, field_name="question refs"),
        )
        _validate_timestamp(self.spoken_at, field_name="spoken_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboCeoDialogueValidationError(
                "CEO dialogue result requires CiboFunctionalAuthority"
            )
        if self.authority is not _MODE_AUTHORITY[self.mode]:
            raise CiboCeoDialogueValidationError(
                "CEO dialogue mode/authority mismatch"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mode.value,
            self.summary_code,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.question_refs,
            self.spoken_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboCeoDialogue:
    """Deterministic, stateless CEO Voice composer.

    Composes structured dialogue RESULTS (explain/ask/doubt/compare/opine/
    state-unknown) on top of the cibo_executive_dialogue code/opaque-ref
    discipline; raw utterances remain outside Core via opaque refs.
    """

    def speak(
        self,
        mode: CiboCeoMode,
        *,
        summary_code: str,
        reason_codes: tuple[str, ...],
        evidence_refs: tuple[CiboEvidenceRef, ...],
        question_refs: tuple[str, ...],
        spoken_at: datetime,
    ) -> Result[CiboCeoDialogueResult, CiboCeoDialogueError]:
        if type(mode) is not CiboCeoMode:
            return Failure(
                CiboCeoDialogueValidationError("speak requires CiboCeoMode")
            )
        try:
            normalized_summary = _validate_code(summary_code, field_name="summary code")
            normalized_reasons = _validate_codes(reason_codes, field_name="reason codes")
            normalized_evidence = _validate_evidence_refs(
                evidence_refs,
                field_name="evidence refs",
            )
            normalized_questions = _validate_question_refs(
                question_refs,
                field_name="question refs",
            )
            _validate_timestamp(spoken_at, field_name="spoken_at")
        except CiboCeoDialogueError as error:
            return Failure(error)

        try:
            return Success(
                CiboCeoDialogueResult(
                    mode=mode,
                    summary_code=normalized_summary,
                    reason_codes=normalized_reasons,
                    evidence_refs=normalized_evidence,
                    question_refs=normalized_questions,
                    spoken_at=spoken_at,
                    authority=_MODE_AUTHORITY[mode],
                )
            )
        except CiboCeoDialogueError as error:
            return Failure(error)
