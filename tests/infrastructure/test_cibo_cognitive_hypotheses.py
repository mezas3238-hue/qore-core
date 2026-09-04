"""Tests for the CIBO Cognitive persistent hypothesis lifecycle substrate (CA 3.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from qore.infrastructure.cibo_cognitive_common import fingerprint_material
from qore.infrastructure.cibo_cognitive_hypotheses import (
    Hypothesis,
    HypothesisEvidence,
    HypothesisEvidencePolarity,
    HypothesisStatus,
    HypothesisValidationError,
    assert_hypothesis_lineage_acyclic,
    build_hypothesis,
    transition_hypothesis,
)
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

_T = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _evidence(ref: str, polarity: HypothesisEvidencePolarity) -> HypothesisEvidence:
    return HypothesisEvidence(
        ref=CiboCognitiveEvidenceRef(ref),
        polarity=polarity,
        observed_at=_T,
        fingerprint=fingerprint_material((ref, polarity.value, _T)),
    )


def _hypothesis(
    status: HypothesisStatus = HypothesisStatus.BORN, **kwargs: object
) -> Hypothesis:
    params: dict[str, Any] = {
        "hypothesis_id": uuid4(),
        "content_code": "h.regime",
        "status": status,
    }
    params.update(kwargs)
    return build_hypothesis(**params)


def test_born_to_active_to_under_test() -> None:
    born = _hypothesis()
    active = transition_hypothesis(born, HypothesisStatus.ACTIVE)
    under_test = transition_hypothesis(active, HypothesisStatus.UNDER_TEST)
    assert active.revision == 1
    assert under_test.revision == 2
    assert active.revision_parent == born.hypothesis_id


def test_direct_confirmed_fabrication_rejected() -> None:
    with pytest.raises(HypothesisValidationError):
        _hypothesis(status=HypothesisStatus.CONFIRMED)


def test_confirmed_with_supporting_evidence() -> None:
    hypothesis = _hypothesis(
        status=HypothesisStatus.CONFIRMED,
        tests=(_evidence("evidence:t1", HypothesisEvidencePolarity.TEST_RESULT),),
    )
    hypothesis.revalidate()


def test_confirmed_rejects_contradiction() -> None:
    with pytest.raises(HypothesisValidationError):
        _hypothesis(
            status=HypothesisStatus.CONFIRMED,
            tests=(_evidence("evidence:t1", HypothesisEvidencePolarity.TEST_RESULT),),
            contradictions=(_evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),),
        )


def test_refuted_requires_falsifying_evidence() -> None:
    with pytest.raises(HypothesisValidationError):
        _hypothesis(status=HypothesisStatus.REFUTED)


def test_refuted_resurrection_without_revision_rejected() -> None:
    refuted = _hypothesis(
        status=HypothesisStatus.REFUTED,
        contradictions=(_evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),),
    )
    with pytest.raises(HypothesisValidationError):
        transition_hypothesis(refuted, HypothesisStatus.ACTIVE)


def test_refuted_to_revised_to_active_is_valid() -> None:
    refuted = _hypothesis(
        status=HypothesisStatus.REFUTED,
        contradictions=(_evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),),
    )
    revised = transition_hypothesis(refuted, HypothesisStatus.REVISED)
    active = transition_hypothesis(revised, HypothesisStatus.ACTIVE)
    assert active.status is HypothesisStatus.ACTIVE


def test_superseded_requires_supersedes_id() -> None:
    active = _hypothesis(status=HypothesisStatus.ACTIVE)
    with pytest.raises(HypothesisValidationError):
        transition_hypothesis(active, HypothesisStatus.SUPERSEDED)


def test_superseded_is_terminal() -> None:
    active = _hypothesis(status=HypothesisStatus.ACTIVE)
    other_id = uuid4()
    superseded = transition_hypothesis(
        active, HypothesisStatus.SUPERSEDED, supersedes=other_id
    )
    with pytest.raises(HypothesisValidationError):
        transition_hypothesis(superseded, HypothesisStatus.ACTIVE)


def test_supersession_cycle_rejected() -> None:
    a_id = uuid4()
    b_id = uuid4()
    a = _hypothesis(hypothesis_id=a_id, status=HypothesisStatus.ACTIVE)
    b = _hypothesis(hypothesis_id=b_id, status=HypothesisStatus.ACTIVE, supersedes=a_id)
    assert_hypothesis_lineage_acyclic([a, b])
    with pytest.raises(HypothesisValidationError):
        a_cycle = _hypothesis(hypothesis_id=a_id, status=HypothesisStatus.ACTIVE, supersedes=b_id)
        assert_hypothesis_lineage_acyclic([a_cycle, b])


def test_causal_binding_optional_and_validated() -> None:
    claim_id = uuid4()
    claim_fp = fingerprint_material("claim")
    hypothesis = _hypothesis(
        status=HypothesisStatus.ACTIVE, causal_claim_ref=(claim_id, claim_fp)
    )
    hypothesis.revalidate()
    with pytest.raises(HypothesisValidationError):
        _hypothesis(status=HypothesisStatus.ACTIVE, causal_claim_ref=("not-a-uuid",))


def test_id_content_mismatch_fails_fingerprint() -> None:
    hypothesis = _hypothesis(status=HypothesisStatus.ACTIVE)
    object.__setattr__(hypothesis, "content_code", "h.changed")
    with pytest.raises(HypothesisValidationError):
        hypothesis.revalidate()


def test_no_mutation_in_place() -> None:
    born = _hypothesis()
    active = transition_hypothesis(born, HypothesisStatus.ACTIVE)
    assert born.status is HypothesisStatus.BORN
    assert active.status is HypothesisStatus.ACTIVE
    assert born.hypothesis_id == active.hypothesis_id


def test_authority_free() -> None:
    hypothesis = _hypothesis(status=HypothesisStatus.ACTIVE)
    for absent in ("order", "intent", "account", "quantity", "provider", "promotion", "risk"):
        assert not hasattr(hypothesis, absent)
