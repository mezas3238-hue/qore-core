"""Tests for the CIBO Cognitive Attention / Routing / Calibration seam (CA-05/06/09)."""

from __future__ import annotations

from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_attention import (
    AttentionEvidenceRef,
    AttentionSignal,
    AttentionSignalKind,
    CalibrationNote,
    ReasoningDepthHint,
    ReasoningRequest,
    ReasoningRouteDecision,
    ReasoningRoutingOutcome,
    calibration_requires_abstention,
    route_reasoning,
    select_context,
)
from qore.infrastructure.cibo_cognitive_common import CiboCognitiveValidationError

_SIGNAL_A = UUID("00000000-0000-0000-0000-0000000000b1")
_SIGNAL_B = UUID("00000000-0000-0000-0000-0000000000b2")
_REQUEST = UUID("00000000-0000-0000-0000-0000000000c1")


def _signal(
    *,
    signal_id: UUID = _SIGNAL_A,
    kind: AttentionSignalKind = AttentionSignalKind.ANOMALY,
    severity: int = 50,
    evidence: tuple[str, ...] = ("ev-1",),
) -> AttentionSignal:
    return AttentionSignal(
        signal_id=signal_id,
        kind=kind,
        summary="market anomaly summary",
        evidence_refs=tuple(AttentionEvidenceRef(reference_id=item) for item in evidence),
        severity=severity,
        priority_reason="explicit priority reason",
    )


def test_select_context_ranks_by_bounded_score() -> None:
    low = _signal(signal_id=_SIGNAL_A, severity=10)
    high = _signal(signal_id=_SIGNAL_B, severity=90)
    result = select_context([low, high])
    assert [item.signal.signal_id for item in result.ranked] == [_SIGNAL_B, _SIGNAL_A]
    assert result.ranked[0].score == 90


def test_attention_priority_cannot_invent_evidence() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        AttentionSignal(
            signal_id=_SIGNAL_A,
            kind=AttentionSignalKind.CONTRADICTION,
            summary="no evidence cited",
            evidence_refs=(),
            severity=80,
            priority_reason="invented priority",
        )


def test_equal_priority_ordering_is_permutation_invariant() -> None:
    first = _signal(signal_id=_SIGNAL_A, severity=50, evidence=("ev-a",))
    second = _signal(signal_id=_SIGNAL_B, severity=50, evidence=("ev-b",))
    order_one = select_context([first, second])
    order_two = select_context([second, first])
    assert [item.signal.signal_id for item in order_one.ranked] == [
        item.signal.signal_id for item in order_two.ranked
    ]


def test_severity_rejects_bool_laundering() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _signal(severity=True)


def test_severity_rejects_out_of_range() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _signal(severity=101)
    with pytest.raises(CiboCognitiveValidationError):
        _signal(severity=-1)


def test_route_reasoning_abstains_when_evidence_missing() -> None:
    request = ReasoningRequest(
        request_id=_REQUEST,
        depth_hint=ReasoningDepthHint("max"),
        missing_evidence=("market regime snapshot",),
        justification="need deeper reasoning about regime shift",
    )
    outcome = route_reasoning(request)
    assert outcome.decision is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE
    assert outcome.requested_evidence == ("market regime snapshot",)


def test_route_reasoning_proceeds_when_evidence_complete() -> None:
    request = ReasoningRequest(
        request_id=_REQUEST,
        depth_hint=ReasoningDepthHint("high"),
        missing_evidence=(),
        justification="all required evidence present",
    )
    outcome = route_reasoning(request)
    assert outcome.decision is ReasoningRouteDecision.PROCEED
    assert outcome.requested_evidence == ()


def test_depth_hint_rejects_unknown_mode() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ReasoningDepthHint("council_override")


def test_abstention_outcome_requires_requested_evidence() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ReasoningRoutingOutcome(
            decision=ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE,
            reasons=("insufficient evidence",),
            requested_evidence=(),
        )


def test_routing_reason_rejects_secret_bearing_material() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ReasoningRoutingOutcome(
            decision=ReasoningRouteDecision.PROCEED,
            reasons=("authorization: Bearer abcdef1234567890",),
            requested_evidence=(),
        )


def test_calibration_requires_abstention() -> None:
    note = CalibrationNote(confidence_band=30, note="low confidence", abstention_required=True)
    assert calibration_requires_abstention(note) is True
    note = CalibrationNote(confidence_band=80, note="confident", abstention_required=False)
    assert calibration_requires_abstention(note) is False


def test_calibration_rejects_bool_confidence_band() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CalibrationNote(confidence_band=True, note="x", abstention_required=False)
