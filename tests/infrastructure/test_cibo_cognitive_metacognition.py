"""Tests for the CIBO Cognitive strong metacognition substrate (CA 3.3)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from qore.infrastructure.cibo_cognitive_common import fingerprint_material
from qore.infrastructure.cibo_cognitive_metacognition import (
    MetacognitionValidationError,
    MetacognitiveFinding,
    build_metacognitive_audit,
    build_reasoning_transition,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboDeliberationRole,
    CiboReasoningMode,
)


def _ref(value: str) -> CiboCognitiveEvidenceRef:
    return CiboCognitiveEvidenceRef(value)


def test_escalation_requires_evidence() -> None:
    with pytest.raises(MetacognitionValidationError):
        build_reasoning_transition(
            from_mode=CiboReasoningMode.HIGH,
            to_mode=CiboReasoningMode.MAX,
            reason_code="insufficient.evidence",
        )


def test_escalation_with_evidence_ok() -> None:
    transition = build_reasoning_transition(
        from_mode=CiboReasoningMode.HIGH,
        to_mode=CiboReasoningMode.MAX,
        reason_code="insufficient.evidence",
        evidence_refs=(_ref("evidence:x"),),
    )
    transition.revalidate()


def test_self_loop_rejected() -> None:
    with pytest.raises(MetacognitionValidationError):
        build_reasoning_transition(
            from_mode=CiboReasoningMode.MAX,
            to_mode=CiboReasoningMode.MAX,
            reason_code="loop",
            evidence_refs=(_ref("evidence:x"),),
        )


def test_deescalation_ok_without_evidence() -> None:
    transition = build_reasoning_transition(
        from_mode=CiboReasoningMode.MAX,
        to_mode=CiboReasoningMode.HIGH,
        reason_code="resolved",
    )
    transition.revalidate()


def test_audit_sufficient_requires_reason_codes() -> None:
    with pytest.raises(MetacognitionValidationError):
        build_metacognitive_audit(
            audit_id=uuid4(),
            reasoning_mode=CiboReasoningMode.HIGH,
            evidence_sufficiency=MetacognitiveFinding.SUFFICIENT,
        )


def test_sufficient_must_not_suppress_missing_specialists() -> None:
    with pytest.raises(MetacognitionValidationError):
        build_metacognitive_audit(
            audit_id=uuid4(),
            reasoning_mode=CiboReasoningMode.HIGH,
            evidence_sufficiency=MetacognitiveFinding.SUFFICIENT,
            missing_roles=(CiboDeliberationRole("critic"),),
            reason_codes=("sufficient",),
        )


def test_insufficient_evidence_requires_reason_codes() -> None:
    with pytest.raises(MetacognitionValidationError):
        build_metacognitive_audit(
            audit_id=uuid4(),
            reasoning_mode=CiboReasoningMode.FAST,
            evidence_sufficiency=MetacognitiveFinding.INSUFFICIENT_EVIDENCE,
        )


def test_missing_specialist_finding() -> None:
    audit = build_metacognitive_audit(
        audit_id=uuid4(),
        reasoning_mode=CiboReasoningMode.HIGH,
        evidence_sufficiency=MetacognitiveFinding.MISSING_SPECIALIST,
        missing_roles=(CiboDeliberationRole("critic"),),
        reason_codes=("missing-critic",),
    )
    audit.revalidate()
    assert audit.evidence_sufficiency is MetacognitiveFinding.MISSING_SPECIALIST


def test_fingerprint_mismatch_fails_closed() -> None:
    audit = build_metacognitive_audit(
        audit_id=uuid4(),
        reasoning_mode=CiboReasoningMode.HIGH,
        evidence_sufficiency=MetacognitiveFinding.INSUFFICIENT_EVIDENCE,
        reason_codes=("insufficient",),
    )
    object.__setattr__(audit, "fingerprint", fingerprint_material("forged"))
    with pytest.raises(MetacognitionValidationError):
        audit.revalidate()


def test_deterministic_replay() -> None:
    audit_id = uuid4()
    left = build_metacognitive_audit(
        audit_id=audit_id,
        reasoning_mode=CiboReasoningMode.MAX,
        evidence_sufficiency=MetacognitiveFinding.UNRESOLVED_CONTRADICTION,
        reason_codes=("contradiction",),
    )
    right = build_metacognitive_audit(
        audit_id=audit_id,
        reasoning_mode=CiboReasoningMode.MAX,
        evidence_sufficiency=MetacognitiveFinding.UNRESOLVED_CONTRADICTION,
        reason_codes=("contradiction",),
    )
    assert left.fingerprint == right.fingerprint
    assert left.logical_values() == right.logical_values()


def test_authority_free() -> None:
    audit = build_metacognitive_audit(
        audit_id=uuid4(),
        reasoning_mode=CiboReasoningMode.MAX,
        evidence_sufficiency=MetacognitiveFinding.INSUFFICIENT_EVIDENCE,
        reason_codes=("insufficient",),
    )
    for absent in ("order", "intent", "account", "quantity", "provider", "promotion", "authority"):
        assert not hasattr(audit, absent)
