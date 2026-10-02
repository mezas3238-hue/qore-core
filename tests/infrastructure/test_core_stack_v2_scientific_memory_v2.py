from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.scientific_memory_v2 import (
    ScientificKnowledgeState,
    ScientificMemoryEntry,
    ScientificMemoryKind,
    ScientificMemoryQuery,
    SharedScientificMemory,
)

T0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _entry(
    memory_id: str,
    kind: ScientificMemoryKind,
    *,
    learned_offset: int,
    knowledge_state: ScientificKnowledgeState,
    subject: str = "STI",
    hypothesis_id: str | None = None,
    falsification_reasons: tuple[str, ...] = (),
) -> ScientificMemoryEntry:
    learned = T0 + timedelta(minutes=learned_offset)
    return ScientificMemoryEntry(
        memory_id=memory_id,
        kind=kind,
        subject=subject,
        learned_at=learned,
        evidence_cutoff_at=learned - timedelta(seconds=1),
        knowledge_state=knowledge_state,
        source_partition="CONSUMED_RESEARCH",
        evidence_refs=(f"run:{memory_id}",),
        payload=(("status", knowledge_state.value),),
        hypothesis_id=hypothesis_id,
        falsification_reasons=falsification_reasons,
    )


def test_memory_separates_four_required_classes() -> None:
    memory = SharedScientificMemory(
        (
            _entry(
                "e1",
                ScientificMemoryKind.EPISODIC,
                learned_offset=1,
                knowledge_state=ScientificKnowledgeState.RESEARCH,
            ),
            _entry(
                "s1",
                ScientificMemoryKind.SEMANTIC,
                learned_offset=2,
                knowledge_state=ScientificKnowledgeState.REPLICATED_RESEARCH,
            ),
            _entry(
                "r1",
                ScientificMemoryKind.REGIME,
                learned_offset=3,
                knowledge_state=ScientificKnowledgeState.RESEARCH,
            ),
            _entry(
                "f1",
                ScientificMemoryKind.FAILURE,
                learned_offset=4,
                knowledge_state=ScientificKnowledgeState.FALSIFIED,
                hypothesis_id="STI6_V2",
                falsification_reasons=("FALSE_CONTINUATION_TOO_HIGH",),
            ),
        )
    )

    assert memory.entry_count == 4
    assert len(memory.fingerprint()) == 64


def test_future_learned_failure_is_suppressed_from_past_query() -> None:
    failure = _entry(
        "failure",
        ScientificMemoryKind.FAILURE,
        learned_offset=10,
        knowledge_state=ScientificKnowledgeState.FALSIFIED,
        hypothesis_id="STI5_V1",
        falsification_reasons=("REPRESENTATION_INSUFFICIENT",),
    )
    memory = SharedScientificMemory((failure,))

    past = memory.recall(
        ScientificMemoryQuery(
            as_of=T0 + timedelta(minutes=5),
            kinds=(ScientificMemoryKind.FAILURE,),
        )
    )
    assert past.unknown is True
    assert past.future_entries_suppressed == 1

    future = memory.recall(
        ScientificMemoryQuery(
            as_of=T0 + timedelta(minutes=11),
            kinds=(ScientificMemoryKind.FAILURE,),
        )
    )
    assert future.unknown is False
    assert future.entries == (failure,)


def test_failure_memory_requires_explicit_falsification_mechanism() -> None:
    with pytest.raises(ValueError, match="requires hypothesis"):
        _entry(
            "bad",
            ScientificMemoryKind.FAILURE,
            learned_offset=1,
            knowledge_state=ScientificKnowledgeState.FALSIFIED,
        )


def test_nonfailure_cannot_smuggle_falsified_state() -> None:
    with pytest.raises(ValueError, match="belongs in FAILURE"):
        _entry(
            "bad",
            ScientificMemoryKind.SEMANTIC,
            learned_offset=1,
            knowledge_state=ScientificKnowledgeState.FALSIFIED,
        )


def test_recall_is_authority_free_and_unknown_is_explicit() -> None:
    memory = SharedScientificMemory(())
    recalled = memory.recall(
        ScientificMemoryQuery(
            as_of=T0,
            kinds=(ScientificMemoryKind.SEMANTIC,),
        )
    )

    assert recalled.unknown is True
    assert recalled.entries == ()
    assert recalled.productive_authority is False


def test_query_kind_order_is_canonical() -> None:
    with pytest.raises(ValueError, match="canonical"):
        ScientificMemoryQuery(
            as_of=T0,
            kinds=(
                ScientificMemoryKind.SEMANTIC,
                ScientificMemoryKind.EPISODIC,
            ),
        )
