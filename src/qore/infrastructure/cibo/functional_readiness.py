"""CF-14/CF-20 Functional Readiness Map (D5).

Readiness distinguishes semantic capability from demonstrated economic
usefulness and fails closed against self-overstatement. A function that can
semantically perform a role but has no demonstrated economic evidence is
``INSUFFICIENT_ECONOMIC_EVIDENCE``, never ``QUALIFIED``/``CERTIFIED``. Positive
states require explicit backing evidence; the map is OBSERVATION-only and can
never self-promote.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
)
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


class CiboReadinessState(StrEnum):
    """Evidence-backed readiness states (fail closed against self-overstatement)."""

    CERTIFIED = "certified"
    DEMO_VALIDATING = "demo-validating"
    QUALIFIED = "qualified"
    DEGRADED = "degraded"
    EVIDENCE_STALE = "evidence-stale"
    INSUFFICIENT_ECONOMIC_EVIDENCE = "insufficient-economic-evidence"
    BLOCKED = "blocked"


_STALE_FRESHNESS = frozenset(
    {
        CiboEvidenceFreshnessState.STALE,
        CiboEvidenceFreshnessState.INSUFFICIENT,
        CiboEvidenceFreshnessState.UNKNOWN,
    }
)


def _derive_state(
    *,
    demonstrated_economic_evidence: tuple[CiboEvidenceRef, ...],
    certification_evidence: tuple[CiboEvidenceRef, ...],
    demo_validation_evidence: tuple[CiboEvidenceRef, ...],
    degraded: bool,
    blocked: bool,
    freshness_state: CiboEvidenceFreshnessState,
) -> CiboReadinessState:
    if blocked:
        return CiboReadinessState.BLOCKED
    if degraded:
        return CiboReadinessState.DEGRADED
    if freshness_state in _STALE_FRESHNESS:
        return CiboReadinessState.EVIDENCE_STALE
    if not demonstrated_economic_evidence:
        return CiboReadinessState.INSUFFICIENT_ECONOMIC_EVIDENCE
    if certification_evidence:
        return CiboReadinessState.CERTIFIED
    if demo_validation_evidence:
        return CiboReadinessState.DEMO_VALIDATING
    return CiboReadinessState.QUALIFIED


@dataclass(frozen=True, slots=True)
class CiboFunctionalReadinessEntry:
    """One function's readiness: semantic capability vs demonstrated usefulness."""

    function_code: str
    semantic_capability_code: str
    demonstrated_economic_evidence: tuple[CiboEvidenceRef, ...]
    certification_evidence: tuple[CiboEvidenceRef, ...]
    demo_validation_evidence: tuple[CiboEvidenceRef, ...]
    degraded: bool
    blocked: bool
    freshness_state: CiboEvidenceFreshnessState
    state: CiboReadinessState
    assessed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "function_code",
            _validate_code(self.function_code, field_name="function code"),
        )
        object.__setattr__(
            self,
            "semantic_capability_code",
            _validate_code(
                self.semantic_capability_code,
                field_name="semantic capability code",
            ),
        )
        object.__setattr__(
            self,
            "demonstrated_economic_evidence",
            _validate_evidence_refs(
                self.demonstrated_economic_evidence,
                field_name="demonstrated economic evidence",
            ),
        )
        object.__setattr__(
            self,
            "certification_evidence",
            _validate_evidence_refs(
                self.certification_evidence,
                field_name="certification evidence",
            ),
        )
        object.__setattr__(
            self,
            "demo_validation_evidence",
            _validate_evidence_refs(
                self.demo_validation_evidence,
                field_name="demo validation evidence",
            ),
        )
        if type(self.degraded) is not bool:
            raise CiboFunctionalValidationError(
                "readiness degraded flag must be an exact bool"
            )
        if type(self.blocked) is not bool:
            raise CiboFunctionalValidationError(
                "readiness blocked flag must be an exact bool"
            )
        if type(self.freshness_state) is not CiboEvidenceFreshnessState:
            raise CiboFunctionalValidationError(
                "readiness requires exact CiboEvidenceFreshnessState"
            )
        if type(self.state) is not CiboReadinessState:
            raise CiboFunctionalValidationError(
                "readiness requires exact CiboReadinessState"
            )
        _validate_timestamp(self.assessed_at, field_name="readiness assessed_at")
        # Constructor/deriver parity: a stronger semantic state must not be admitted
        # by direct construction. The state must equal the deterministic derivation.
        expected = _derive_state(
            demonstrated_economic_evidence=self.demonstrated_economic_evidence,
            certification_evidence=self.certification_evidence,
            demo_validation_evidence=self.demo_validation_evidence,
            degraded=self.degraded,
            blocked=self.blocked,
            freshness_state=self.freshness_state,
        )
        if self.state is not expected:
            raise CiboFunctionalValidationError(
                "readiness state must equal the evidence-bound derivation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.function_code,
            self.semantic_capability_code,
            tuple(item.logical_values() for item in self.demonstrated_economic_evidence),
            tuple(item.logical_values() for item in self.certification_evidence),
            tuple(item.logical_values() for item in self.demo_validation_evidence),
            self.degraded,
            self.blocked,
            self.freshness_state.value,
            self.state.value,
            self.assessed_at.isoformat(),
        )


def derive_readiness(
    *,
    function_code: str,
    semantic_capability_code: str,
    demonstrated_economic_evidence: tuple[CiboEvidenceRef, ...],
    certification_evidence: tuple[CiboEvidenceRef, ...] = (),
    demo_validation_evidence: tuple[CiboEvidenceRef, ...] = (),
    degraded: bool = False,
    blocked: bool = False,
    freshness_state: CiboEvidenceFreshnessState,
    assessed_at: datetime,
) -> Result[CiboFunctionalReadinessEntry, CiboFunctionalError]:
    """Derive one evidence-bound readiness entry (never self-overstated)."""
    try:
        state = _derive_state(
            demonstrated_economic_evidence=demonstrated_economic_evidence,
            certification_evidence=certification_evidence,
            demo_validation_evidence=demo_validation_evidence,
            degraded=degraded,
            blocked=blocked,
            freshness_state=freshness_state,
        )
        return Success(
            CiboFunctionalReadinessEntry(
                function_code=function_code,
                semantic_capability_code=semantic_capability_code,
                demonstrated_economic_evidence=demonstrated_economic_evidence,
                certification_evidence=certification_evidence,
                demo_validation_evidence=demo_validation_evidence,
                degraded=degraded,
                blocked=blocked,
                freshness_state=freshness_state,
                state=state,
                assessed_at=assessed_at,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class CiboFunctionalReadinessMap:
    """Deterministic, OBSERVATION-only functional readiness map."""

    entries: tuple[CiboFunctionalReadinessEntry, ...]
    assessed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple) or any(
            not isinstance(item, CiboFunctionalReadinessEntry) for item in self.entries
        ):
            raise CiboFunctionalValidationError(
                "readiness map entries must be a tuple of CiboFunctionalReadinessEntry"
            )
        revalidated = tuple(
            CiboFunctionalReadinessEntry(
                function_code=item.function_code,
                semantic_capability_code=item.semantic_capability_code,
                demonstrated_economic_evidence=item.demonstrated_economic_evidence,
                certification_evidence=item.certification_evidence,
                demo_validation_evidence=item.demo_validation_evidence,
                degraded=item.degraded,
                blocked=item.blocked,
                freshness_state=item.freshness_state,
                state=item.state,
                assessed_at=item.assessed_at,
            )
            for item in self.entries
        )
        codes = tuple(item.function_code for item in revalidated)
        if len(set(codes)) != len(codes):
            raise CiboFunctionalValidationError(
                "readiness map function codes must be unique"
            )
        object.__setattr__(
            self,
            "entries",
            tuple(sorted(revalidated, key=lambda item: item.function_code)),
        )
        _validate_timestamp(self.assessed_at, field_name="readiness map assessed_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "readiness map requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OBSERVATION:
            raise CiboFunctionalValidationError(
                "readiness map authority must be OBSERVATION"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(item.logical_values() for item in self.entries),
            self.assessed_at.isoformat(),
            self.authority.value,
        )


def build_readiness_map(
    entries: tuple[CiboFunctionalReadinessEntry, ...],
    *,
    assessed_at: datetime,
) -> Result[CiboFunctionalReadinessMap, CiboFunctionalError]:
    """Assemble a deterministic readiness map (no self-promotion)."""
    try:
        return Success(
            CiboFunctionalReadinessMap(
                entries=entries,
                assessed_at=assessed_at,
                authority=CiboFunctionalAuthority.OBSERVATION,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


__all__ = [
    "CiboReadinessState",
    "CiboFunctionalReadinessEntry",
    "derive_readiness",
    "CiboFunctionalReadinessMap",
    "build_readiness_map",
]
