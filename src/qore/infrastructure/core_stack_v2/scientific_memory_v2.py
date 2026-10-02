"""Governed scientific memory for Shared.

The memory separates four knowledge classes:
- EPISODIC: closed causal episodes;
- SEMANTIC: generalized research knowledge;
- REGIME: historically bounded regime knowledge;
- FAILURE: falsified hypotheses and their mechanisms.

Entries become queryable only after their evidence was available and the entry
was learned. Runtime queries can never see future-learned knowledge. Research
memory cannot self-promote into certified/productive knowledge.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ScientificMemoryKind(StrEnum):
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    REGIME = "REGIME"
    FAILURE = "FAILURE"


class ScientificKnowledgeState(StrEnum):
    RESEARCH = "RESEARCH"
    REPLICATED_RESEARCH = "REPLICATED_RESEARCH"
    FALSIFIED = "FALSIFIED"
    CERTIFIED = "CERTIFIED"


@dataclass(frozen=True, slots=True)
class ScientificMemoryEntry:
    memory_id: str
    kind: ScientificMemoryKind
    subject: str
    learned_at: datetime
    evidence_cutoff_at: datetime
    knowledge_state: ScientificKnowledgeState
    source_partition: str
    evidence_refs: tuple[str, ...]
    payload: tuple[tuple[str, str], ...]
    hypothesis_id: str | None = None
    falsification_reasons: tuple[str, ...] = ()
    productive_admitted: bool = False

    def __post_init__(self) -> None:
        if not self.memory_id.strip() or not self.subject.strip():
            raise ValueError("scientific memory identity must be explicit")
        for value in (self.learned_at, self.evidence_cutoff_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("scientific memory timestamps must be aware")
        if self.evidence_cutoff_at > self.learned_at:
            raise ValueError("memory cannot be learned before its evidence exists")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("scientific memory evidence refs must be canonical")
        if self.payload != tuple(sorted(self.payload)):
            raise ValueError("scientific memory payload must be canonical")
        if len({key for key, _ in self.payload}) != len(self.payload):
            raise ValueError("scientific memory payload keys must be unique")
        if self.kind is ScientificMemoryKind.FAILURE:
            if self.knowledge_state is not ScientificKnowledgeState.FALSIFIED:
                raise ValueError("failure memory must be FALSIFIED knowledge")
            if not self.hypothesis_id or not self.falsification_reasons:
                raise ValueError(
                    "failure memory requires hypothesis and falsification reasons"
                )
        elif self.knowledge_state is ScientificKnowledgeState.FALSIFIED:
            raise ValueError("falsified knowledge belongs in FAILURE memory")
        if self.productive_admitted:
            raise ValueError(
                "research scientific memory cannot self-promote to production"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["knowledge_state"] = self.knowledge_state.value
        payload["learned_at"] = self.learned_at.astimezone(UTC).isoformat()
        payload["evidence_cutoff_at"] = (
            self.evidence_cutoff_at.astimezone(UTC).isoformat()
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ScientificMemoryQuery:
    as_of: datetime
    kinds: tuple[ScientificMemoryKind, ...]
    subject_prefix: str | None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("scientific memory query as_of must be aware")
        expected = tuple(sorted(set(self.kinds), key=lambda item: item.value))
        if not expected or self.kinds != expected:
            raise ValueError("scientific memory query kinds must be canonical")
        if self.subject_prefix is not None and not self.subject_prefix.strip():
            raise ValueError("subject_prefix must be non-empty when present")


@dataclass(frozen=True, slots=True)
class ScientificMemoryRecall:
    as_of: datetime
    entries: tuple[ScientificMemoryEntry, ...]
    unknown: bool
    future_entries_suppressed: int
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("scientific memory recall as_of must be aware")
        if self.unknown != (not self.entries):
            raise ValueError("scientific memory UNKNOWN flag must match recall")
        if self.future_entries_suppressed < 0:
            raise ValueError("future_entries_suppressed cannot be negative")
        if self.productive_authority:
            raise ValueError("scientific memory recall grants no authority")


class SharedScientificMemory:
    """Immutable, causally queryable scientific memory registry."""

    def __init__(self, entries: tuple[ScientificMemoryEntry, ...]) -> None:
        ordered = tuple(
            sorted(
                entries,
                key=lambda item: (
                    item.learned_at.astimezone(UTC),
                    item.memory_id,
                ),
            )
        )
        if len({item.memory_id for item in ordered}) != len(ordered):
            raise ValueError("duplicate scientific memory id")
        self._entries = ordered

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def fingerprint(self) -> str:
        raw = json.dumps(
            [item.fingerprint() for item in self._entries],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def recall(self, query: ScientificMemoryQuery) -> ScientificMemoryRecall:
        eligible: list[ScientificMemoryEntry] = []
        future_suppressed = 0
        allowed = set(query.kinds)
        for item in self._entries:
            if item.kind not in allowed:
                continue
            if (
                query.subject_prefix is not None
                and not item.subject.startswith(query.subject_prefix)
            ):
                continue
            if item.learned_at > query.as_of:
                future_suppressed += 1
                continue
            if item.evidence_cutoff_at > query.as_of:
                raise ValueError("memory registry contains causal time violation")
            eligible.append(item)

        return ScientificMemoryRecall(
            as_of=query.as_of,
            entries=tuple(eligible),
            unknown=not eligible,
            future_entries_suppressed=future_suppressed,
        )
