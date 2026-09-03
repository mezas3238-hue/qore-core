"""Tests for the CIBO Cognitive World Model substrate (CA-04)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_world_model import (
    WorldModelContradiction,
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSnapshot,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_world_model_snapshot,
    project_world_state,
)
from qore.kernel.result import Failure, Success

_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-0000000000a1")
_AS_OF = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _fp(label: str) -> CiboCognitiveFingerprint:
    return fingerprint_material(label)


def _reference(
    *,
    domain: WorldModelDomain = WorldModelDomain.MARKET,
    source: str = "source-a",
    version: str = "1",
    as_of: datetime = _AS_OF,
    status: WorldModelReferenceStatus = WorldModelReferenceStatus.CURRENT,
    label: str | None = "provider-neutral market evidence",
) -> WorldModelReference:
    return WorldModelReference(
        domain=domain,
        source_id=WorldModelSourceId(source),
        source_version=WorldModelSourceVersion(version),
        as_of=as_of,
        status=status,
        evidence_fingerprint=_fp(f"{source}:{version}"),
        evidence_label=label,
    )


def test_snapshot_builds_and_projects() -> None:
    ref = _reference()
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[ref],
        staleness_threshold=timedelta(days=1),
    )
    assert snapshot.fingerprint.value == snapshot.fingerprint.value
    assert snapshot.references_for(WorldModelDomain.MARKET) == (ref,)
    assert project_world_state(snapshot, WorldModelDomain.MARKET) == Success((ref,))


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=datetime(2024, 6, 1, 12, 0, 0),
            references=[_reference()],
        )
    with pytest.raises(CiboCognitiveValidationError):
        _reference(as_of=datetime(2024, 6, 1, 12, 0, 0))


def test_secret_bearing_evidence_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _reference(label="api_key=sk-abcdef1234567890")
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=_AS_OF,
            references=[
                _reference(label="-----BEGIN PRIVATE KEY-----"),
            ],
        )


def test_contradictory_sources_cannot_collapse() -> None:
    first = _reference(source="source-a")
    second = _reference(source="source-b")
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[first, second],
    )
    result = snapshot.resolved_reference(WorldModelDomain.MARKET)
    assert isinstance(result, Failure)

    contradiction = WorldModelContradiction(
        left=first, right=second, reason="sources disagree on regime"
    )
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[first, second],
        contradictions=[contradiction],
    )
    assert isinstance(snapshot.resolved_reference(WorldModelDomain.MARKET), Failure)


def test_single_source_resolves_without_contradiction() -> None:
    ref = _reference()
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
    )
    result = snapshot.resolved_reference(WorldModelDomain.MARKET)
    assert isinstance(result, Success)
    assert result.value == ref


def test_stale_source_cannot_masquerade_as_current() -> None:
    old = datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=_AS_OF,
            references=[_reference(as_of=old, status=WorldModelReferenceStatus.CURRENT)],
            staleness_threshold=timedelta(days=1),
        )


def test_stale_source_is_explicitly_allowed() -> None:
    old = datetime(2024, 5, 1, 12, 0, 0, tzinfo=UTC)
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID,
        as_of=_AS_OF,
        references=[_reference(as_of=old, status=WorldModelReferenceStatus.STALE)],
        staleness_threshold=timedelta(days=1),
    )
    assert snapshot.stale_references()
    assert isinstance(snapshot.resolved_reference(WorldModelDomain.MARKET), Success)


def test_future_reference_rejected() -> None:
    future = datetime(2024, 6, 2, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID,
            as_of=_AS_OF,
            references=[_reference(as_of=future)],
        )


def test_missing_reference_requires_no_evidence_fingerprint() -> None:
    ref = WorldModelReference(
        domain=WorldModelDomain.RESEARCH,
        source_id=WorldModelSourceId("research-a"),
        source_version=WorldModelSourceVersion("2"),
        as_of=_AS_OF,
        status=WorldModelReferenceStatus.MISSING,
        evidence_fingerprint=None,
        evidence_label=None,
    )
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
    )
    assert WorldModelDomain.RESEARCH in snapshot.missing_domains()
    assert snapshot.references_for(WorldModelDomain.RESEARCH) == ()


def test_reflective_corruption_fails_recursive_revalidation() -> None:
    ref = _reference()
    object.__setattr__(ref, "evidence_label", "password=hunter2secret")
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
        )


def test_nested_reflective_corruption_fails() -> None:
    ref = _reference()
    object.__setattr__(ref.source_id, "value", "bad value with space")
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[ref]
        )


def test_bool_cannot_launder_as_identity_or_version() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceId(True)  # type: ignore[arg-type]
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceVersion(False)  # type: ignore[arg-type]


def test_subclass_laundering_rejected() -> None:
    class EvilStr(str):
        pass

    with pytest.raises(CiboCognitiveValidationError):
        WorldModelSourceId(EvilStr("source-a"))


def test_snapshot_ordering_is_permutation_invariant() -> None:
    refs = [_reference(source="a"), _reference(source="b"), _reference(source="c")]
    snapshot_one = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=refs
    )
    snapshot_two = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=list(reversed(refs))
    )
    assert snapshot_one.references == snapshot_two.references
    assert snapshot_one.fingerprint == snapshot_two.fingerprint


def test_contradiction_requires_same_domain() -> None:
    first = _reference(domain=WorldModelDomain.MARKET)
    second = _reference(domain=WorldModelDomain.PORTFOLIO)
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelContradiction(left=first, right=second, reason="cross-domain")


def test_snapshot_is_frozen() -> None:
    snapshot = build_world_model_snapshot(
        snapshot_id=_SNAPSHOT_ID, as_of=_AS_OF, references=[_reference()]
    )
    assert isinstance(snapshot, WorldModelSnapshot)
    with pytest.raises(AttributeError):
        snapshot.as_of = _AS_OF  # type: ignore[misc]
