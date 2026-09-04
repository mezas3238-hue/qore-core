"""Tests for the CIBO Cognitive explicit causal reasoning substrate (CA 3.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.cibo_cognitive_causality import (
    CausalClaim,
    CausalClaimKind,
    CausalClaimStatus,
    CausalClaimStrength,
    CausalEvidence,
    CausalEvidencePolarity,
    CausalityValidationError,
    CausalVariable,
    ConfounderResolution,
    assert_causal_lineage_acyclic,
    build_causal_claim,
)
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveValidationError,
    fingerprint_material,
)
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

_T = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _variable(code: str) -> CausalVariable:
    return CausalVariable(code=code, fingerprint=fingerprint_material((code,)))


def _evidence(ref: str, polarity: CausalEvidencePolarity) -> CausalEvidence:
    return CausalEvidence(
        ref=CiboCognitiveEvidenceRef(ref),
        polarity=polarity,
        observed_at=_T,
        fingerprint=fingerprint_material((ref, polarity.value, _T)),
    )


_CAUSE = _variable("market.shock")
_EFFECT = _variable("volatility.spike")


def _claim(**kwargs: object) -> CausalClaim:
    params: dict[str, Any] = {
        "claim_id": uuid4(),
        "kind": CausalClaimKind.CAUSATION,
        "cause": _CAUSE,
        "effect": _EFFECT,
        "mechanism_code": "mechanism.randomization",
        "strength": CausalClaimStrength.MODERATE,
        "status": CausalClaimStatus.ACTIVE,
    }
    params.update(kwargs)
    return build_causal_claim(**params)


def test_causation_claim_builds_and_revalidates() -> None:
    claim = _claim(evidence_for=(_evidence("evidence:e1", CausalEvidencePolarity.SUPPORTS),))
    claim.revalidate()
    assert claim.kind is CausalClaimKind.CAUSATION


def test_correlation_cannot_assert_strong() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(kind=CausalClaimKind.CORRELATION, strength=CausalClaimStrength.STRONG)


def test_causation_requires_mechanism() -> None:
    with pytest.raises(CausalityValidationError, match="mechanism"):
        _claim(mechanism_code=None)


def test_causation_requires_confounder_resolution() -> None:
    with pytest.raises(CausalityValidationError, match="confounder"):
        _claim(confounders=(_variable("selection-bias"),))


def test_causation_confounder_resolution_binds_evidence() -> None:
    confounder = _variable("selection-bias")
    resolution = ConfounderResolution(
        confounder=confounder,
        evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
    )
    claim = _claim(
        confounders=(confounder,),
        confounder_resolutions=(resolution,),
    )
    claim.revalidate()
    assert claim.confounder_resolutions[0].confounder.code == "selection-bias"


def test_confounder_resolution_duplicate_rejected() -> None:
    confounder = _variable("selection-bias")
    resolution = ConfounderResolution(
        confounder=confounder,
        evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
    )
    with pytest.raises(CausalityValidationError, match="duplicate"):
        _claim(
            confounders=(confounder,),
            confounder_resolutions=(resolution, resolution),
        )


def test_correlation_forbids_mechanism_and_resolutions() -> None:
    with pytest.raises(CausalityValidationError, match="mechanism"):
        _claim(kind=CausalClaimKind.CORRELATION, mechanism_code="mechanism.x")
    confounder = _variable("selection-bias")
    resolution = ConfounderResolution(
        confounder=confounder,
        evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
    )
    with pytest.raises(CausalityValidationError, match="confounder"):
        _claim(
            kind=CausalClaimKind.CORRELATION,
            mechanism_code=None,
            confounder_resolutions=(resolution,),
        )


def test_strong_requires_backing_evidence() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(strength=CausalClaimStrength.STRONG)


def test_confirmed_requires_supporting_evidence() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(status=CausalClaimStatus.CONFIRMED)


def test_confirmed_rejects_contradiction() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(
            status=CausalClaimStatus.CONFIRMED,
            evidence_for=(_evidence("evidence:e1", CausalEvidencePolarity.SUPPORTS),),
            contradictions=(_evidence("evidence:c1", CausalEvidencePolarity.CONTRADICTION),),
        )


def test_refuted_requires_falsifying_evidence() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(status=CausalClaimStatus.REFUTED)


def test_cause_and_effect_must_be_distinct() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(effect=_CAUSE)


def test_competing_claims_coexist_with_distinct_fingerprints() -> None:
    left = _claim(evidence_for=(_evidence("evidence:e1", CausalEvidencePolarity.SUPPORTS),))
    right = _claim(
        status=CausalClaimStatus.REFUTED,
        contradictions=(_evidence("evidence:c1", CausalEvidencePolarity.CONTRADICTION),),
    )
    assert left.fingerprint != right.fingerprint
    left.revalidate()
    right.revalidate()


def test_fingerprint_mismatch_fails_closed() -> None:
    claim = _claim()
    object.__setattr__(claim, "fingerprint", fingerprint_material("forged"))
    with pytest.raises(CausalityValidationError):
        claim.revalidate()


def test_supersession_self_reference_rejected() -> None:
    claim_id = uuid4()
    with pytest.raises(CausalityValidationError):
        _claim(claim_id=claim_id, supersedes=claim_id)


def test_lineage_acyclicity() -> None:
    a_id = uuid4()
    b_id = uuid4()
    a = _claim(claim_id=a_id)
    b = _claim(claim_id=b_id, supersedes=a_id)
    assert_causal_lineage_acyclic([a, b])
    with pytest.raises(CausalityValidationError):
        a_cycle = _claim(claim_id=a_id, supersedes=b_id)
        assert_causal_lineage_acyclic([a_cycle, b])


def test_bool_laundering_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CausalVariable(code=True, fingerprint=fingerprint_material((True,)))  # type: ignore[arg-type]


def test_secret_material_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _variable("password=secret")


def test_authority_free() -> None:
    claim = _claim()
    for absent in (
        "order",
        "intent",
        "account",
        "quantity",
        "provider",
        "promotion",
        "risk",
        "execute",
    ):
        assert not hasattr(claim, absent)


class TestCausalClaimBuilderPermutationInvariance:
    def test_evidence_for_permutation_invariant(self) -> None:
        e_a = _evidence("evidence:a", CausalEvidencePolarity.SUPPORTS)
        e_b = _evidence("evidence:b", CausalEvidencePolarity.SUPPORTS)
        cid = uuid4()
        first = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism_code="mechanism.randomization",
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_a, e_b),
        )
        second = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism_code="mechanism.randomization",
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_b, e_a),
        )
        assert first.evidence_for == second.evidence_for
        assert first.fingerprint == second.fingerprint

    def test_context_variable_permutation_invariant(self) -> None:
        cid = uuid4()
        first = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            context=(_variable("context.b"), _variable("context.a")),
            mechanism_code="mechanism.randomization",
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
        )
        second = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            context=(_variable("context.a"), _variable("context.b")),
            mechanism_code="mechanism.randomization",
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
        )
        assert first.context == second.context
        assert first.fingerprint == second.fingerprint

    def test_evidence_for_different_multiset_differs(self) -> None:
        e_a = _evidence("evidence:a", CausalEvidencePolarity.SUPPORTS)
        e_b = _evidence("evidence:b", CausalEvidencePolarity.SUPPORTS)
        e_c = _evidence("evidence:c", CausalEvidencePolarity.SUPPORTS)
        cid = uuid4()
        first = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism_code="mechanism.randomization",
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_a, e_b),
        )
        second = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism_code="mechanism.randomization",
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_a, e_c),
        )
        assert first.fingerprint != second.fingerprint

    def test_evidence_for_duplicate_rejected(self) -> None:
        e_a = _evidence("evidence:a", CausalEvidencePolarity.SUPPORTS)
        with pytest.raises(CausalityValidationError, match="duplicate"):
            build_causal_claim(
                claim_id=uuid4(),
                kind=CausalClaimKind.CAUSATION,
                cause=_CAUSE,
                effect=_EFFECT,
                mechanism_code="mechanism.randomization",
                strength=CausalClaimStrength.MODERATE,
                status=CausalClaimStatus.ACTIVE,
                evidence_for=(e_a, e_a),
            )


class TestCausalEvidenceTemporalSemantics:
    def test_dst_fold_instants_remain_distinct(self) -> None:
        tz = ZoneInfo("America/New_York")
        f0 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=0)
        f1 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=1)
        ref = CiboCognitiveEvidenceRef("evidence:fold")
        e0 = CausalEvidence(
            ref=ref,
            polarity=CausalEvidencePolarity.SUPPORTS,
            observed_at=f0,
            fingerprint=fingerprint_material((ref.value, "supports", f0)),
        )
        e1 = CausalEvidence(
            ref=ref,
            polarity=CausalEvidencePolarity.SUPPORTS,
            observed_at=f1,
            fingerprint=fingerprint_material((ref.value, "supports", f1)),
        )
        assert e0 != e1
        assert len({e0, e1}) == 2
