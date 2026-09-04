"""Tests for the CIBO Cognitive persistent hypothesis lifecycle substrate (CA 3.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

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
    revised = transition_hypothesis(
        refuted,
        HypothesisStatus.REVISED,
        content_code="h.regime-revised",
        reason_code="new.evidence",
    )
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


class TestHypothesisLifecycleGovernance:
    def test_confirmed_requires_governed_tests_not_evidence_for(self) -> None:
        with pytest.raises(HypothesisValidationError, match="test"):
            _hypothesis(
                status=HypothesisStatus.CONFIRMED,
                evidence_for=(_evidence("evidence:e1", HypothesisEvidencePolarity.SUPPORTS),),
            )

    def test_refuted_to_revised_requires_reason_code(self) -> None:
        refuted = _hypothesis(
            status=HypothesisStatus.REFUTED,
            contradictions=(
                _evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),
            ),
        )
        with pytest.raises(HypothesisValidationError, match="reason"):
            transition_hypothesis(refuted, HypothesisStatus.REVISED, content_code="h.changed")

    def test_refuted_to_revised_requires_material_change(self) -> None:
        refuted = _hypothesis(
            status=HypothesisStatus.REFUTED,
            contradictions=(
                _evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),
            ),
        )
        with pytest.raises(HypothesisValidationError, match="material"):
            transition_hypothesis(
                refuted, HypothesisStatus.REVISED, reason_code="new.evidence"
            )

    def test_refuted_to_revised_with_new_evidence_accepted(self) -> None:
        refuted = _hypothesis(
            status=HypothesisStatus.REFUTED,
            contradictions=(
                _evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),
            ),
        )
        revised = transition_hypothesis(
            refuted,
            HypothesisStatus.REVISED,
            reason_code="new.evidence",
            evidence_for=(_evidence("evidence:e2", HypothesisEvidencePolarity.SUPPORTS),),
        )
        assert revised.status is HypothesisStatus.REVISED

    def test_reason_code_is_retained_and_fingerprinted(self) -> None:
        born = _hypothesis()
        left = transition_hypothesis(born, HypothesisStatus.ACTIVE, reason_code="reason.a")
        right = transition_hypothesis(born, HypothesisStatus.ACTIVE, reason_code="reason.b")
        assert left.reason_code == "reason.a"
        assert right.reason_code == "reason.b"
        assert left.fingerprint != right.fingerprint

    def test_resurrection_requires_revision_then_tests_for_confirmation(self) -> None:
        refuted = _hypothesis(
            status=HypothesisStatus.REFUTED,
            contradictions=(
                _evidence("evidence:c1", HypothesisEvidencePolarity.CONTRADICTION),
            ),
        )
        with pytest.raises(HypothesisValidationError):
            transition_hypothesis(refuted, HypothesisStatus.ACTIVE)
        revised = transition_hypothesis(
            refuted,
            HypothesisStatus.REVISED,
            content_code="h.changed",
            reason_code="new.evidence",
        )
        active = transition_hypothesis(revised, HypothesisStatus.ACTIVE)
        with pytest.raises(HypothesisValidationError):
            transition_hypothesis(
                active,
                HypothesisStatus.CONFIRMED,
                evidence_for=(_evidence("evidence:e2", HypothesisEvidencePolarity.SUPPORTS),),
            )
        confirmed = transition_hypothesis(
            active,
            HypothesisStatus.CONFIRMED,
            tests=(_evidence("evidence:t1", HypothesisEvidencePolarity.TEST_RESULT),),
        )
        assert confirmed.status is HypothesisStatus.CONFIRMED

    def test_transition_retains_supplied_evidence_and_preserves_prior_history(self) -> None:
        born = _hypothesis(
            status=HypothesisStatus.BORN,
            evidence_for=(_evidence("evidence:e1", HypothesisEvidencePolarity.SUPPORTS),),
        )
        active = transition_hypothesis(
            born,
            HypothesisStatus.ACTIVE,
            evidence_for=(_evidence("evidence:e2", HypothesisEvidencePolarity.SUPPORTS),),
        )
        # The supplied evidence is retained in the new revision, and the prior
        # version's evidence/history is not silently erased (it stays durable).
        assert [e.ref.value for e in active.evidence_for] == ["evidence:e2"]
        assert [e.ref.value for e in born.evidence_for] == ["evidence:e1"]
        assert active.revision_parent == born.hypothesis_id

    def test_reason_code_reflective_mutation_fails_revalidate(self) -> None:
        born = _hypothesis()
        revised = transition_hypothesis(
            born, HypothesisStatus.ACTIVE, reason_code="reason.a"
        )
        object.__setattr__(revised, "reason_code", "UPPER-CASE-!INVALID")
        with pytest.raises(HypothesisValidationError):
            revised.revalidate()


class TestHypothesisBuilderPermutationInvariance:
    def test_evidence_for_permutation_invariant(self) -> None:
        e_a = _evidence("evidence:a", HypothesisEvidencePolarity.SUPPORTS)
        e_b = _evidence("evidence:b", HypothesisEvidencePolarity.SUPPORTS)
        e_c = _evidence("evidence:c", HypothesisEvidencePolarity.SUPPORTS)
        hid = uuid4()
        first = build_hypothesis(
            hypothesis_id=hid,
            content_code="h.content",
            status=HypothesisStatus.ACTIVE,
            evidence_for=(e_a, e_b, e_c),
        )
        second = build_hypothesis(
            hypothesis_id=hid,
            content_code="h.content",
            status=HypothesisStatus.ACTIVE,
            evidence_for=(e_c, e_a, e_b),
        )
        assert first.evidence_for == second.evidence_for
        assert first.fingerprint == second.fingerprint

    def test_evidence_for_different_multiset_differs(self) -> None:
        e_a = _evidence("evidence:a", HypothesisEvidencePolarity.SUPPORTS)
        e_b = _evidence("evidence:b", HypothesisEvidencePolarity.SUPPORTS)
        e_c = _evidence("evidence:c", HypothesisEvidencePolarity.SUPPORTS)
        hid = uuid4()
        first = build_hypothesis(
            hypothesis_id=hid,
            content_code="h.content",
            status=HypothesisStatus.ACTIVE,
            evidence_for=(e_a, e_b),
        )
        second = build_hypothesis(
            hypothesis_id=hid,
            content_code="h.content",
            status=HypothesisStatus.ACTIVE,
            evidence_for=(e_a, e_c),
        )
        third = build_hypothesis(
            hypothesis_id=hid,
            content_code="h.content",
            status=HypothesisStatus.ACTIVE,
            evidence_for=(e_a, e_b, e_c),
        )
        assert first.fingerprint != second.fingerprint
        assert first.fingerprint != third.fingerprint

    def test_evidence_for_duplicate_rejected(self) -> None:
        e_a = _evidence("evidence:a", HypothesisEvidencePolarity.SUPPORTS)
        with pytest.raises(HypothesisValidationError, match="duplicate"):
            build_hypothesis(
                hypothesis_id=uuid4(),
                content_code="h.content",
                status=HypothesisStatus.ACTIVE,
                evidence_for=(e_a, e_a),
            )


class TestHypothesisEvidenceTemporalSemantics:
    def test_dst_fold_instants_remain_distinct(self) -> None:
        tz = ZoneInfo("America/New_York")
        f0 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=0)
        f1 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=1)
        ref = CiboCognitiveEvidenceRef("evidence:fold")
        e0 = HypothesisEvidence(
            ref=ref,
            polarity=HypothesisEvidencePolarity.SUPPORTS,
            observed_at=f0,
            fingerprint=fingerprint_material((ref.value, "supports", f0)),
        )
        e1 = HypothesisEvidence(
            ref=ref,
            polarity=HypothesisEvidencePolarity.SUPPORTS,
            observed_at=f1,
            fingerprint=fingerprint_material((ref.value, "supports", f1)),
        )
        assert e0 != e1
        assert len({e0, e1}) == 2
