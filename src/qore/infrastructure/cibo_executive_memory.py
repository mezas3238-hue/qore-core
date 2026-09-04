"""Governed, provider-neutral CIBO executive memory foundations.

Transient LLM context is never authoritative memory. Every retained fact is
provenance-bound, evidence-bound, and exposes explicit freshness, optional
bounded confidence, limitations, and append-only supersession lineage. A
summary/index references source records and never replaces their evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import utc_instant
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.kernel.temporal import canonical_instant
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboConfidence,
    contains_secret_material,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"
_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"


class CiboExecutiveMemoryError(InfrastructureError):
    """Base error for governed CIBO executive memory contracts."""

    __slots__ = ()


class CiboExecutiveMemoryValidationError(CiboExecutiveMemoryError):
    """A memory value violates a deterministic provenance invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboExecutiveMemoryValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboExecutiveMemoryValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_CODE_RE, value) is None:
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    if contains_secret_material(value):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(v) is not str for v in values):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field_name=field_name) for v in values)
    if len(set(normalized)) != len(normalized):
        raise CiboExecutiveMemoryValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_safe_text(value: str, *, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise CiboExecutiveMemoryValidationError(f"{field_name} must be non-empty text")
    if any(ch in value for ch in "\x00\n\r\t"):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must not contain control characters"
        )
    if contains_secret_material(value):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_opaque_ref(value: str, *, field_name: str) -> str:
    if type(value) is not str or fullmatch(_OPAQUE_REF_RE, value) is None:
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must use canonical opaque-reference syntax"
        )
    if contains_secret_material(value):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _revalidate_ref(ref: CiboCognitiveEvidenceRef) -> None:
    try:
        ref.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveMemoryValidationError(
            "memory evidence ref failed revalidation"
        ) from error


def _revalidate_confidence(confidence: CiboConfidence) -> None:
    try:
        confidence.revalidate()
    except CiboCognitiveValidationError as error:
        raise CiboExecutiveMemoryValidationError(
            "memory confidence failed revalidation"
        ) from error


class CiboMemoryKind(StrEnum):
    """Closed set of retained-memory kinds; never an authority grant."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    MARKET = "market"
    TRADER = "trader"
    RESEARCH = "research"
    DECISION = "decision"
    ECONOMIC = "economic"
    FAILURE_LESSON = "failure-lesson"
    LONG_TERM_ARCHIVE = "long-term-archive"


class CiboMemoryFreshnessState(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CiboMemoryFreshness:
    """Explicit freshness state; no hidden clock is ever consulted."""

    state: CiboMemoryFreshnessState
    as_of: datetime

    def __post_init__(self) -> None:
        if type(self.state) is not CiboMemoryFreshnessState:
            raise CiboExecutiveMemoryValidationError(
                "memory freshness requires CiboMemoryFreshnessState"
            )
        _validate_aware_datetime(self.as_of, field_name="memory freshness as_of")

    def revalidate(self) -> None:
        if type(self.state) is not CiboMemoryFreshnessState:
            raise CiboExecutiveMemoryValidationError(
                "memory freshness requires CiboMemoryFreshnessState"
            )
        _validate_aware_datetime(self.as_of, field_name="memory freshness as_of")

    def logical_values(self) -> tuple[object, ...]:
        return (self.state.value, canonical_instant(self.as_of))


@dataclass(frozen=True, slots=True)
class CiboMemorySourceRef:
    """Opaque sanitized reference to the origin of a retained memory fact."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_opaque_ref(self.value, field_name="memory source ref"),
        )

    def revalidate(self) -> None:
        _validate_opaque_ref(self.value, field_name="memory source ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboMemoryProvenance:
    """Explicit provenance for a retained fact; timestamps are caller-supplied."""

    source_ref: CiboMemorySourceRef
    effective_at: datetime
    recorded_at: datetime | None = None

    def __post_init__(self) -> None:
        if type(self.source_ref) is not CiboMemorySourceRef:
            raise CiboExecutiveMemoryValidationError(
                "memory provenance requires CiboMemorySourceRef"
            )
        _validate_aware_datetime(self.effective_at, field_name="memory effective_at")
        if self.recorded_at is not None:
            _validate_aware_datetime(self.recorded_at, field_name="memory recorded_at")
            if utc_instant(self.recorded_at, field="memory recorded_at") < utc_instant(
                self.effective_at, field="memory effective_at"
            ):
                raise CiboExecutiveMemoryValidationError(
                    "memory recorded_at must not predate effective_at"
                )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.source_ref) is not CiboMemorySourceRef:
            raise CiboExecutiveMemoryValidationError(
                "memory provenance requires CiboMemorySourceRef"
            )
        self.source_ref.revalidate()
        _validate_aware_datetime(self.effective_at, field_name="memory effective_at")
        if self.recorded_at is not None:
            _validate_aware_datetime(self.recorded_at, field_name="memory recorded_at")
            if utc_instant(self.recorded_at, field="memory recorded_at") < utc_instant(
                self.effective_at, field="memory effective_at"
            ):
                raise CiboExecutiveMemoryValidationError(
                    "memory recorded_at must not predate effective_at"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source_ref.logical_values(),
            canonical_instant(self.effective_at),
            None if self.recorded_at is None else canonical_instant(self.recorded_at),
        )


def _canonical_uuid_ids(values: tuple[UUID, ...], *, field_name: str) -> tuple[UUID, ...]:
    if type(values) is not tuple or any(type(v) is not UUID for v in values):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must be an immutable tuple of UUIDs"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveMemoryValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values))


def _canonical_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(item) is not CiboCognitiveEvidenceRef for item in values
    ):
        raise CiboExecutiveMemoryValidationError(
            f"{field_name} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboExecutiveMemoryValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboMemoryItem:
    """One retained, evidence-bound executive memory fact."""

    item_id: UUID
    kind: CiboMemoryKind
    subject_code: str
    content: str
    provenance: CiboMemoryProvenance
    freshness: CiboMemoryFreshness
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]
    confidence: CiboConfidence | None = None
    limitations: tuple[str, ...] = ()
    supersedes: tuple[UUID, ...] = ()
    superseded_by: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if type(self.item_id) is not UUID:
            raise CiboExecutiveMemoryValidationError("memory item id must be UUID")
        if type(self.kind) is not CiboMemoryKind:
            raise CiboExecutiveMemoryValidationError("memory item requires CiboMemoryKind")
        object.__setattr__(
            self,
            "subject_code",
            _validate_code(self.subject_code, field_name="memory subject code"),
        )
        object.__setattr__(
            self,
            "content",
            _validate_safe_text(self.content, field_name="memory content"),
        )
        if type(self.provenance) is not CiboMemoryProvenance:
            raise CiboExecutiveMemoryValidationError(
                "memory item requires CiboMemoryProvenance"
            )
        if type(self.freshness) is not CiboMemoryFreshness:
            raise CiboExecutiveMemoryValidationError(
                "memory item requires CiboMemoryFreshness"
            )
        refs = _canonical_refs(self.evidence_refs, field_name="memory evidence refs")
        if not refs:
            raise CiboExecutiveMemoryValidationError(
                "memory item requires explicit backing evidence"
            )
        object.__setattr__(self, "evidence_refs", refs)
        if self.confidence is not None and type(self.confidence) is not CiboConfidence:
            raise CiboExecutiveMemoryValidationError(
                "memory confidence must be CiboConfidence or None"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="memory limitations"),
        )
        object.__setattr__(
            self,
            "supersedes",
            _canonical_uuid_ids(self.supersedes, field_name="memory supersedes"),
        )
        object.__setattr__(
            self,
            "superseded_by",
            _canonical_uuid_ids(self.superseded_by, field_name="memory superseded_by"),
        )
        if self.item_id in self.supersedes or self.item_id in self.superseded_by:
            raise CiboExecutiveMemoryValidationError(
                "memory item must not supersede or be superseded by itself"
            )
        if set(self.supersedes) & set(self.superseded_by):
            raise CiboExecutiveMemoryValidationError(
                "memory item supersedes/superseded_by must be disjoint"
            )
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.item_id) is not UUID:
            raise CiboExecutiveMemoryValidationError("memory item id must be UUID")
        if type(self.kind) is not CiboMemoryKind:
            raise CiboExecutiveMemoryValidationError("memory item requires CiboMemoryKind")
        _validate_code(self.subject_code, field_name="memory subject code")
        _validate_safe_text(self.content, field_name="memory content")
        if type(self.provenance) is not CiboMemoryProvenance:
            raise CiboExecutiveMemoryValidationError(
                "memory item requires CiboMemoryProvenance"
            )
        self.provenance.revalidate()
        if type(self.freshness) is not CiboMemoryFreshness:
            raise CiboExecutiveMemoryValidationError(
                "memory item requires CiboMemoryFreshness"
            )
        self.freshness.revalidate()
        if not self.evidence_refs:
            raise CiboExecutiveMemoryValidationError(
                "memory item requires explicit backing evidence"
            )
        if self.evidence_refs != _canonical_refs(
            self.evidence_refs,
            field_name="memory evidence refs",
        ):
            raise CiboExecutiveMemoryValidationError(
                "memory evidence refs failed canonical revalidation"
            )
        for ref in self.evidence_refs:
            _revalidate_ref(ref)
        if self.confidence is not None:
            if type(self.confidence) is not CiboConfidence:
                raise CiboExecutiveMemoryValidationError(
                    "memory confidence must be CiboConfidence or None"
                )
            _revalidate_confidence(self.confidence)
        if self.limitations != _validate_codes(
            self.limitations,
            field_name="memory limitations",
        ):
            raise CiboExecutiveMemoryValidationError(
                "memory limitations failed canonical revalidation"
            )
        if self.supersedes != _canonical_uuid_ids(
            self.supersedes,
            field_name="memory supersedes",
        ):
            raise CiboExecutiveMemoryValidationError(
                "memory supersedes failed canonical revalidation"
            )
        if self.superseded_by != _canonical_uuid_ids(
            self.superseded_by,
            field_name="memory superseded_by",
        ):
            raise CiboExecutiveMemoryValidationError(
                "memory superseded_by failed canonical revalidation"
            )
        if self.item_id in self.supersedes or self.item_id in self.superseded_by:
            raise CiboExecutiveMemoryValidationError(
                "memory item must not supersede or be superseded by itself"
            )
        if set(self.supersedes) & set(self.superseded_by):
            raise CiboExecutiveMemoryValidationError(
                "memory item supersedes/superseded_by must be disjoint"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.item_id),
            self.kind.value,
            self.subject_code,
            self.content,
            self.provenance.logical_values(),
            self.freshness.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
            None if self.confidence is None else self.confidence.logical_values(),
            self.limitations,
            tuple(str(v) for v in self.supersedes),
            tuple(str(v) for v in self.superseded_by),
        )


@dataclass(frozen=True, slots=True)
class CiboMemorySummaryEntry:
    """A source-record reference; it never replaces the source evidence."""

    item_id: UUID
    kind: CiboMemoryKind
    subject_code: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.item_id) is not UUID:
            raise CiboExecutiveMemoryValidationError("summary entry id must be a UUID")
        if type(self.kind) is not CiboMemoryKind:
            raise CiboExecutiveMemoryValidationError(
                "summary entry kind must be a CiboMemoryKind"
            )
        _validate_code(self.subject_code, field_name="summary entry subject code")

    def logical_values(self) -> tuple[object, ...]:
        return (str(self.item_id), self.kind.value, self.subject_code)


@dataclass(frozen=True, slots=True)
class CiboMemorySummary:
    """Deterministic index over retained items; references only, no content."""

    entries: tuple[CiboMemorySummaryEntry, ...] = ()

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.entries) is not tuple or any(
            type(entry) is not CiboMemorySummaryEntry for entry in self.entries
        ):
            raise CiboExecutiveMemoryValidationError(
                "summary entries must be an immutable tuple of CiboMemorySummaryEntry"
            )
        for entry in self.entries:
            entry.revalidate()

    def logical_values(self) -> tuple[object, ...]:
        return tuple(entry.logical_values() for entry in self.entries)


def _link_superseded_by(item: CiboMemoryItem, superseding_id: UUID) -> CiboMemoryItem:
    return CiboMemoryItem(
        item_id=item.item_id,
        kind=item.kind,
        subject_code=item.subject_code,
        content=item.content,
        provenance=item.provenance,
        freshness=item.freshness,
        evidence_refs=item.evidence_refs,
        confidence=item.confidence,
        limitations=item.limitations,
        supersedes=item.supersedes,
        superseded_by=tuple(sorted({*item.superseded_by, superseding_id})),
    )


def _supersession_cycle(items: tuple[CiboMemoryItem, ...]) -> bool:
    """Return whether the supersedes graph contains a cycle (lineage corruption)."""
    by_id = {item.item_id: item for item in items}
    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(node: UUID) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for superseded_id in by_id[node].supersedes:
            if superseded_id in by_id and visit(superseded_id):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(item.item_id) for item in items)


@dataclass(frozen=True, slots=True)
class CiboMemoryStore:
    """Pure, deterministic in-memory seam for governed executive memory.

    Recording is append-only and functional: it returns a new store. Supersession
    adds lineage links without rewriting the superseded fact's content.
    """

    items: tuple[CiboMemoryItem, ...] = ()

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.items) is not tuple or any(
            type(item) is not CiboMemoryItem for item in self.items
        ):
            raise CiboExecutiveMemoryValidationError(
                "memory store items must be an immutable tuple of CiboMemoryItem"
            )
        by_id = {item.item_id: item for item in self.items}
        if len(by_id) != len(self.items):
            raise CiboExecutiveMemoryValidationError(
                "memory store items must have unique ids"
            )
        for item in self.items:
            item.revalidate()
            for superseded_id in item.supersedes:
                if superseded_id not in by_id:
                    raise CiboExecutiveMemoryValidationError(
                        "memory supersedes references an unknown item"
                    )
                if item.item_id not in by_id[superseded_id].superseded_by:
                    raise CiboExecutiveMemoryValidationError(
                        "memory supersedes lineage is not symmetric"
                    )
            for superseding_id in item.superseded_by:
                if superseding_id not in by_id:
                    raise CiboExecutiveMemoryValidationError(
                        "memory superseded_by references an unknown item"
                    )
                if item.item_id not in by_id[superseding_id].supersedes:
                    raise CiboExecutiveMemoryValidationError(
                        "memory superseded_by lineage is not symmetric"
                    )
        if _supersession_cycle(self.items):
            raise CiboExecutiveMemoryValidationError(
                "memory supersession lineage must be acyclic"
            )

    def record(
        self,
        item: CiboMemoryItem,
    ) -> Result[CiboMemoryStore, CiboExecutiveMemoryError]:
        """Retain one validated fact; reject duplicates and fabricated lineage."""
        if type(item) is not CiboMemoryItem:
            return Failure(
                CiboExecutiveMemoryValidationError("record requires CiboMemoryItem")
            )
        try:
            item.revalidate()
        except CiboExecutiveMemoryError as error:
            return Failure(
                CiboExecutiveMemoryValidationError(
                    f"memory item failed revalidation: {error}"
                )
            )
        existing_ids = {entry.item_id for entry in self.items}
        if item.item_id in existing_ids:
            return Failure(
                CiboExecutiveMemoryValidationError("memory item id already retained")
            )
        if item.superseded_by:
            return Failure(
                CiboExecutiveMemoryValidationError(
                    "memory item must not pre-claim superseded_by lineage"
                )
            )
        for superseded_id in item.supersedes:
            if superseded_id not in existing_ids:
                return Failure(
                    CiboExecutiveMemoryValidationError(
                        "memory supersedes references an unknown item"
                    )
                )
        rebuilt: list[CiboMemoryItem] = []
        for entry in self.items:
            if entry.item_id in item.supersedes:
                rebuilt.append(_link_superseded_by(entry, item.item_id))
            else:
                rebuilt.append(entry)
        rebuilt.append(item)
        return Success(CiboMemoryStore(items=tuple(rebuilt)))

    def retrieve(self, *, kind: CiboMemoryKind | None = None) -> tuple[CiboMemoryItem, ...]:
        """Deterministically return retained items, optionally filtered by kind."""
        if kind is not None and type(kind) is not CiboMemoryKind:
            raise CiboExecutiveMemoryValidationError("retrieve kind must be CiboMemoryKind")
        ordered = tuple(
            sorted(self.items, key=lambda entry: (entry.kind.value, str(entry.item_id)))
        )
        if kind is None:
            return ordered
        return tuple(entry for entry in ordered if entry.kind is kind)

    def summarize(self) -> CiboMemorySummary:
        """Build a source-referencing index; it never fabricates facts."""
        entries = tuple(
            CiboMemorySummaryEntry(
                item_id=entry.item_id,
                kind=entry.kind,
                subject_code=entry.subject_code,
            )
            for entry in self.retrieve()
        )
        return CiboMemorySummary(entries=entries)
