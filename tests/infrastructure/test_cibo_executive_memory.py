from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.infrastructure.cibo_executive_memory import (
    CiboExecutiveMemoryValidationError,
    CiboMemoryFreshness,
    CiboMemoryFreshnessState,
    CiboMemoryItem,
    CiboMemoryKind,
    CiboMemoryProvenance,
    CiboMemorySourceRef,
    CiboMemoryStore,
)
from qore.kernel.result import Failure, Success
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
)

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_ITEM_ID = UUID("40000000-0000-0000-0000-000000000001")


def _ref(value: str) -> CiboCognitiveEvidenceRef:
    return CiboCognitiveEvidenceRef(value)


def _item(
    item_id: UUID = _ITEM_ID,
    *,
    kind: CiboMemoryKind = CiboMemoryKind.SEMANTIC,
    content: str = "Retained fact content",
    supersedes: tuple[UUID, ...] = (),
) -> CiboMemoryItem:
    return CiboMemoryItem(
        item_id=item_id,
        kind=kind,
        subject_code="subject-demo",
        content=content,
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef("source:demo"),
            effective_at=_NOW,
        ),
        freshness=CiboMemoryFreshness(state=CiboMemoryFreshnessState.CURRENT, as_of=_NOW),
        evidence_refs=(_ref("evidence:demo"),),
        supersedes=supersedes,
    )


class TestMemoryItem:
    def test_item_requires_explicit_evidence(self) -> None:
        with pytest.raises(CiboExecutiveMemoryValidationError, match="evidence"):
            CiboMemoryItem(
                item_id=UUID("40000000-0000-0000-0000-000000000002"),
                kind=CiboMemoryKind.SEMANTIC,
                subject_code="subject-demo",
                content="fact",
                provenance=CiboMemoryProvenance(
                    source_ref=CiboMemorySourceRef("source:demo"),
                    effective_at=_NOW,
                ),
                freshness=CiboMemoryFreshness(
                    state=CiboMemoryFreshnessState.CURRENT,
                    as_of=_NOW,
                ),
                evidence_refs=(),
            )

    def test_item_requires_provenance_source(self) -> None:
        with pytest.raises(CiboExecutiveMemoryValidationError):
            CiboMemoryProvenance(
                source_ref=CiboMemorySourceRef("source:demo"),
                effective_at=_NOW,
                recorded_at=datetime(2026, 8, 8, 0, 0, tzinfo=UTC),
            )

    def test_item_rejects_naive_freshness(self) -> None:
        with pytest.raises(CiboExecutiveMemoryValidationError, match="timezone"):
            CiboMemoryFreshness(
                state=CiboMemoryFreshnessState.CURRENT,
                as_of=datetime(2026, 8, 9, 0, 0),
            )

    def test_source_ref_rejects_secret(self) -> None:
        with pytest.raises(CiboExecutiveMemoryValidationError, match="sensitive"):
            CiboMemorySourceRef("client_secret_demo")

    def test_item_rejects_bool_kind_laundering(self) -> None:
        with pytest.raises(CiboExecutiveMemoryValidationError):
            CiboMemoryItem(
                item_id=UUID("40000000-0000-0000-0000-000000000002"),
                kind=True,  # type: ignore[arg-type]
                subject_code="subject-demo",
                content="fact",
                provenance=CiboMemoryProvenance(
                    source_ref=CiboMemorySourceRef("source:demo"),
                    effective_at=_NOW,
                ),
                freshness=CiboMemoryFreshness(
                    state=CiboMemoryFreshnessState.CURRENT,
                    as_of=_NOW,
                ),
                evidence_refs=(_ref("evidence:demo"),),
            )

    def test_item_rejects_self_supersession(self) -> None:
        item_id = UUID("40000000-0000-0000-0000-000000000002")
        with pytest.raises(CiboExecutiveMemoryValidationError, match="itself"):
            _item(item_id=item_id, supersedes=(item_id,))

    def test_item_has_no_authority_fields(self) -> None:
        item = _item()
        for absent in ("order", "intent", "provider", "quantity", "authorization", "config"):
            assert not hasattr(item, absent)

    def test_revalidate_detects_tampered_evidence_ref(self) -> None:
        item = _item()
        object.__setattr__(item.evidence_refs[0], "value", "secret=injected")
        with pytest.raises(CiboExecutiveMemoryValidationError):
            item.revalidate()

    def test_revalidate_detects_tampered_confidence(self) -> None:
        item = _item()
        object.__setattr__(
            item,
            "confidence",
            CiboConfidence(level=CiboConfidenceLevel.LOW, evidence_refs=(_ref("evidence:c"),)),
        )
        object.__setattr__(item.confidence, "evidence_refs", ())
        with pytest.raises(CiboExecutiveMemoryValidationError):
            item.revalidate()


class TestMemoryStore:
    def test_record_returns_new_store_without_mutating_original(self) -> None:
        store = CiboMemoryStore()
        result = store.record(_item())
        assert isinstance(result, Success)
        assert store.items == ()
        assert len(result.value.items) == 1

    def test_record_rejects_duplicate_id(self) -> None:
        store = CiboMemoryStore()
        first = store.record(_item())
        assert isinstance(first, Success)
        result = first.value.record(_item())
        assert isinstance(result, Failure)
        assert isinstance(result.error, CiboExecutiveMemoryValidationError)

    def test_record_rejects_supersedes_unknown_item(self) -> None:
        store = CiboMemoryStore()
        result = store.record(
            _item(supersedes=(UUID("40000000-0000-0000-0000-000000000099"),))
        )
        assert isinstance(result, Failure)

    def test_supersession_links_without_rewriting_content(self) -> None:
        first_id = UUID("40000000-0000-0000-0000-000000000003")
        second_id = UUID("40000000-0000-0000-0000-000000000004")
        store = CiboMemoryStore()
        recorded = store.record(_item(item_id=first_id, content="original"))
        assert isinstance(recorded, Success)
        updated = recorded.value.record(
            _item(item_id=second_id, content="replacement", supersedes=(first_id,))
        )
        assert isinstance(updated, Success)
        by_id = {item.item_id: item for item in updated.value.items}
        assert by_id[first_id].content == "original"
        assert by_id[first_id].superseded_by == (second_id,)
        assert by_id[second_id].supersedes == (first_id,)

    def test_retrieve_is_deterministic(self) -> None:
        store = CiboMemoryStore()
        recorded = store.record(_item(item_id=UUID("40000000-0000-0000-0000-000000000005")))
        assert isinstance(recorded, Success)
        again = recorded.value.record(
            _item(
                item_id=UUID("40000000-0000-0000-0000-000000000006"),
                kind=CiboMemoryKind.DECISION,
            )
        )
        assert isinstance(again, Success)
        assert again.value.retrieve() == again.value.retrieve()
        assert [i.kind for i in again.value.retrieve()] == [
            CiboMemoryKind.DECISION,
            CiboMemoryKind.SEMANTIC,
        ]

    def test_summary_references_source_records_not_content(self) -> None:
        store = CiboMemoryStore()
        recorded = store.record(_item())
        assert isinstance(recorded, Success)
        summary = recorded.value.summarize()
        assert len(summary.entries) == 1
        entry = summary.entries[0]
        assert not hasattr(entry, "content")
        assert entry.item_id == UUID("40000000-0000-0000-0000-000000000001")

    def test_memory_store_cannot_mutate_certified_config(self) -> None:
        store = CiboMemoryStore()
        assert not hasattr(store, "set_config")
        assert not hasattr(store, "mutate_trader")
