"""Governed research-memory container for current Trader research artifacts.

This module intentionally contains no executive reasoning, deliberation, sizing,
Risk, execution, or broker authority. It exists so current Trader research
memory does not depend on the quarantined historical CIBO executive-memory
stack.

The logical serialization used by the retained VT31 dossier is kept stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.kernel.temporal import canonical_instant
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    contains_secret_material,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"
_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"


class CiboResearchMemoryError(InfrastructureError):
    __slots__ = ()


class CiboResearchMemoryValidationError(CiboResearchMemoryError):
    __slots__ = ()


class CiboResearchMemoryKind(StrEnum):
    MARKET = "market"
    RESEARCH = "research"
    LONG_TERM_ARCHIVE = "long-term-archive"


class CiboResearchMemoryFreshnessState(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


def _aware(value: datetime, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise CiboResearchMemoryValidationError(
            f"{name} must be timezone-aware datetime"
        )


def _code(value: str, name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise CiboResearchMemoryValidationError(
            f"{name} must use canonical lowercase code syntax"
        )
    if contains_secret_material(value):
        raise CiboResearchMemoryValidationError(
            f"{name} must not contain sensitive material"
        )
    return value


def _safe_text(value: str, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise CiboResearchMemoryValidationError(f"{name} must be non-empty text")
    if any(char in value for char in "\x00\n\r\t"):
        raise CiboResearchMemoryValidationError(
            f"{name} must not contain control characters"
        )
    if contains_secret_material(value):
        raise CiboResearchMemoryValidationError(
            f"{name} must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class CiboResearchMemoryFreshness:
    state: CiboResearchMemoryFreshnessState
    as_of: datetime

    def __post_init__(self) -> None:
        if type(self.state) is not CiboResearchMemoryFreshnessState:
            raise CiboResearchMemoryValidationError(
                "research-memory freshness state is invalid"
            )
        _aware(self.as_of, "research-memory freshness as_of")

    def logical_values(self) -> tuple[object, ...]:
        return (self.state.value, canonical_instant(self.as_of))


@dataclass(frozen=True, slots=True)
class CiboResearchMemorySourceRef:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or fullmatch(_OPAQUE_REF_RE, self.value) is None:
            raise CiboResearchMemoryValidationError(
                "research-memory source ref must use opaque-reference syntax"
            )
        if contains_secret_material(self.value):
            raise CiboResearchMemoryValidationError(
                "research-memory source ref must not contain sensitive material"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboResearchMemoryProvenance:
    source_ref: CiboResearchMemorySourceRef
    effective_at: datetime
    recorded_at: datetime | None = None

    def __post_init__(self) -> None:
        if type(self.source_ref) is not CiboResearchMemorySourceRef:
            raise CiboResearchMemoryValidationError(
                "research-memory provenance requires canonical source ref"
            )
        _aware(self.effective_at, "research-memory effective_at")
        if self.recorded_at is not None:
            _aware(self.recorded_at, "research-memory recorded_at")
            if self.recorded_at.astimezone(UTC) < self.effective_at.astimezone(UTC):
                raise CiboResearchMemoryValidationError(
                    "research-memory recorded_at cannot predate effective_at"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source_ref.logical_values(),
            canonical_instant(self.effective_at),
            None if self.recorded_at is None else canonical_instant(self.recorded_at),
        )


@dataclass(frozen=True, slots=True)
class CiboResearchMemoryItem:
    item_id: UUID
    kind: CiboResearchMemoryKind
    subject_code: str
    content: str
    provenance: CiboResearchMemoryProvenance
    freshness: CiboResearchMemoryFreshness
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.item_id) is not UUID:
            raise CiboResearchMemoryValidationError(
                "research-memory item id must be UUID"
            )
        if type(self.kind) is not CiboResearchMemoryKind:
            raise CiboResearchMemoryValidationError(
                "research-memory kind is invalid"
            )
        object.__setattr__(
            self,
            "subject_code",
            _code(self.subject_code, "research-memory subject"),
        )
        object.__setattr__(
            self,
            "content",
            _safe_text(self.content, "research-memory content"),
        )
        if type(self.provenance) is not CiboResearchMemoryProvenance:
            raise CiboResearchMemoryValidationError(
                "research-memory provenance is invalid"
            )
        if type(self.freshness) is not CiboResearchMemoryFreshness:
            raise CiboResearchMemoryValidationError(
                "research-memory freshness is invalid"
            )
        if (
            type(self.evidence_refs) is not tuple
            or not self.evidence_refs
            or any(type(item) is not CiboCognitiveEvidenceRef for item in self.evidence_refs)
        ):
            raise CiboResearchMemoryValidationError(
                "research-memory requires immutable cognitive evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise CiboResearchMemoryValidationError(
                "research-memory evidence refs must be unique"
            )
        ordered_refs = tuple(sorted(self.evidence_refs, key=lambda item: item.value))
        for ref in ordered_refs:
            try:
                ref.revalidate()
            except CiboCognitiveValidationError as error:
                raise CiboResearchMemoryValidationError(
                    "research-memory evidence ref failed revalidation"
                ) from error
        object.__setattr__(self, "evidence_refs", ordered_refs)
        if type(self.limitations) is not tuple:
            raise CiboResearchMemoryValidationError(
                "research-memory limitations must be tuple"
            )
        normalized = tuple(
            sorted(_code(item, "research-memory limitation") for item in self.limitations)
        )
        if len(normalized) != len(set(normalized)):
            raise CiboResearchMemoryValidationError(
                "research-memory limitations must be unique"
            )
        object.__setattr__(self, "limitations", normalized)

    def logical_values(self) -> tuple[object, ...]:
        # Keep the former executive-memory logical tuple shape so the existing
        # VT31 research-memory fingerprint is invariant under this decoupling.
        return (
            str(self.item_id),
            self.kind.value,
            self.subject_code,
            self.content,
            self.provenance.logical_values(),
            self.freshness.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
            None,
            self.limitations,
            (),
            (),
        )


@dataclass(frozen=True, slots=True)
class CiboResearchMemoryStore:
    items: tuple[CiboResearchMemoryItem, ...] = ()

    def __post_init__(self) -> None:
        if type(self.items) is not tuple or any(
            type(item) is not CiboResearchMemoryItem for item in self.items
        ):
            raise CiboResearchMemoryValidationError(
                "research-memory store items are invalid"
            )
        ids = tuple(item.item_id for item in self.items)
        if len(ids) != len(set(ids)):
            raise CiboResearchMemoryValidationError(
                "research-memory store item ids must be unique"
            )

    def record(
        self,
        item: CiboResearchMemoryItem,
    ) -> Result[CiboResearchMemoryStore, CiboResearchMemoryError]:
        if type(item) is not CiboResearchMemoryItem:
            return Failure(
                CiboResearchMemoryValidationError(
                    "research-memory record requires canonical item"
                )
            )
        if any(existing.item_id == item.item_id for existing in self.items):
            return Failure(
                CiboResearchMemoryValidationError(
                    "research-memory item id already retained"
                )
            )
        return Success(CiboResearchMemoryStore(items=self.items + (item,)))

    def retrieve(
        self,
        *,
        kind: CiboResearchMemoryKind | None = None,
    ) -> tuple[CiboResearchMemoryItem, ...]:
        if kind is not None and type(kind) is not CiboResearchMemoryKind:
            raise CiboResearchMemoryValidationError(
                "research-memory retrieve kind is invalid"
            )
        ordered = tuple(
            sorted(self.items, key=lambda item: (item.kind.value, str(item.item_id)))
        )
        if kind is None:
            return ordered
        return tuple(item for item in ordered if item.kind is kind)
