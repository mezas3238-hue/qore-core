"""Tests for the CIBO Cognitive Replay / Audit and handoff seam (CA-16/14/15)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveValidationError,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_replay import (
    CognitiveHandoff,
    CognitiveHandoffKind,
    CognitiveUtterance,
    CognitiveUtteranceKind,
    ReplayEpisode,
    ReplayToolCall,
    build_replay_episode,
    replay_episode,
)

_EPISODE = UUID("00000000-0000-0000-0000-0000000000f1")
_SNAPSHOT = UUID("00000000-0000-0000-0000-0000000000f2")
_REQUEST = UUID("00000000-0000-0000-0000-0000000000f3")
_RECORDED_AT = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _episode(
    *,
    tool_calls: Sequence[ReplayToolCall] = (),
    evidence_refs: Sequence[str] = ("ev-1",),
) -> ReplayEpisode:
    return build_replay_episode(
        episode_id=_EPISODE,
        recorded_at=_RECORDED_AT,
        world_snapshot_id=_SNAPSHOT,
        attention_reasons=("anomaly detected",),
        goal_plan_state="plan:0",
        tool_calls=tool_calls,
        counterfactuals=(),
        uncertainties=(),
        contradictions=(),
        evidence_refs=evidence_refs,
        changes_after=(),
        handoff_reference=None,
    )


def test_replay_is_deterministic_over_recorded_inputs() -> None:
    episode = _episode()
    first = replay_episode(episode)
    second = replay_episode(episode)
    assert first.view == second.view
    assert first.fingerprint == second.fingerprint


def test_replay_with_changed_input_rejected() -> None:
    episode = _episode()
    object.__setattr__(episode, "evidence_refs", ("tampered-evidence",))
    with pytest.raises(CiboCognitiveValidationError):
        replay_episode(episode)


def test_replay_reconstructs_tool_calls() -> None:
    call = ReplayToolCall(
        request_id=_REQUEST,
        input_fingerprint=fingerprint_material("tool-input"),
        result_fingerprint=fingerprint_material("tool-output"),
    )
    episode = _episode(tool_calls=[call])
    reconstruction = replay_episode(episode)
    assert reconstruction.view[5] == (call.logical_values(),)


def test_audit_record_cannot_omit_source_evidence() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _episode(evidence_refs=())


def test_handoff_is_authority_free() -> None:
    assert set(CognitiveHandoffKind.__members__) == {"RECOMMENDATION", "FORMAL_REQUEST"}
    handoff = CognitiveHandoff(
        handoff_id=_REQUEST,
        kind=CognitiveHandoffKind.FORMAL_REQUEST,
        source_reference="cognitive-output:42",
        summary="request external policy review of regime shift",
        evidence_refs=("ev-1",),
    )
    for forbidden in (
        "order",
        "account",
        "credential",
        "promotion",
        "authority",
        "risk",
        "execute",
    ):
        assert not hasattr(handoff, forbidden)
    assert handoff.kind is CognitiveHandoffKind.FORMAL_REQUEST


def test_handoff_requires_evidence() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveHandoff(
            handoff_id=_REQUEST,
            kind=CognitiveHandoffKind.RECOMMENDATION,
            source_reference="cognitive-output:42",
            summary="recommendation without evidence",
            evidence_refs=(),
        )


def test_dialogue_opinion_cannot_become_formal_signal_implicitly() -> None:
    assert set(CognitiveUtteranceKind.__members__) == {"OPINION", "DIALOGUE"}
    utterance = CognitiveUtterance(
        utterance_id=_REQUEST,
        kind=CognitiveUtteranceKind.OPINION,
        content="market feels choppy",
        source="faculty:markets",
    )
    assert not hasattr(utterance, "decision")
    assert not hasattr(utterance, "outcome")
    assert not hasattr(utterance, "signal")


def test_handoff_rejects_secret_bearing_summary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveHandoff(
            handoff_id=_REQUEST,
            kind=CognitiveHandoffKind.RECOMMENDATION,
            source_reference="cognitive-output:42",
            summary="authorization: Bearer abcdef1234567890",
            evidence_refs=("ev-1",),
        )


def test_build_replay_rejects_non_sequence_tool_calls_without_leaking_exception() -> None:
    bad_calls: Any = None
    with pytest.raises(CiboCognitiveValidationError):
        build_replay_episode(
            episode_id=_EPISODE,
            recorded_at=_RECORDED_AT,
            world_snapshot_id=_SNAPSHOT,
            tool_calls=bad_calls,
            evidence_refs=("ev-1",),
        )


def test_build_replay_rejects_non_call_items_without_leaking_exception() -> None:
    bad_calls: Any = ["not-a-call"]
    with pytest.raises(CiboCognitiveValidationError):
        build_replay_episode(
            episode_id=_EPISODE,
            recorded_at=_RECORDED_AT,
            world_snapshot_id=_SNAPSHOT,
            tool_calls=bad_calls,
            evidence_refs=("ev-1",),
        )


def test_build_replay_rejects_non_datetime_recorded_at_without_leaking_exception() -> None:
    bad_recorded_at: Any = "2024-06-01T12:00:00+00:00"
    with pytest.raises(CiboCognitiveValidationError):
        build_replay_episode(
            episode_id=_EPISODE,
            recorded_at=bad_recorded_at,
            world_snapshot_id=_SNAPSHOT,
            evidence_refs=("ev-1",),
        )
