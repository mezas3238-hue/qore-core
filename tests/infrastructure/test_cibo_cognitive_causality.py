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
    MechanismBinding,
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
_MECHANISM_REF = "evidence:mechanism"


def _mechanism_evidence() -> CausalEvidence:
    return _evidence(_MECHANISM_REF, CausalEvidencePolarity.SUPPORTS)


def _mechanism(code: str = "mechanism.randomization") -> MechanismBinding:
    return MechanismBinding(code=code, evidence=_mechanism_evidence())


def _claim(**kwargs: object) -> CausalClaim:
    params: dict[str, Any] = {
        "claim_id": uuid4(),
        "kind": CausalClaimKind.CAUSATION,
        "cause": _CAUSE,
        "effect": _EFFECT,
        "strength": CausalClaimStrength.MODERATE,
        "status": CausalClaimStatus.ACTIVE,
    }
    params.update(kwargs)
    # A CAUSATION claim must carry an evidence-bound mechanism whose evidence is
    # retained in evidence_for. Supply a default one (merged with any caller
    # evidence_for) so valid-claim tests stay concise; tests that exercise the
    # mechanism gate override ``mechanism`` explicitly.
    if params.get("kind") is CausalClaimKind.CAUSATION and "mechanism" not in params:
        mechanism = _mechanism()
        params["mechanism"] = mechanism
        supplied = params.get("evidence_for", ())
        params["evidence_for"] = tuple(supplied) + (mechanism.evidence,)
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
        _claim(mechanism=None)


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
        evidence_for=(_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),),
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
        _claim(kind=CausalClaimKind.CORRELATION, mechanism=_mechanism())
    confounder = _variable("selection-bias")
    resolution = ConfounderResolution(
        confounder=confounder,
        evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
    )
    with pytest.raises(CausalityValidationError, match="confounder"):
        _claim(
            kind=CausalClaimKind.CORRELATION,
            mechanism=None,
            confounder_resolutions=(resolution,),
        )


def test_strong_requires_backing_evidence() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(kind=CausalClaimKind.NON_CAUSAL, strength=CausalClaimStrength.STRONG)


def test_confirmed_requires_supporting_evidence() -> None:
    with pytest.raises(CausalityValidationError):
        _claim(kind=CausalClaimKind.NON_CAUSAL, status=CausalClaimStatus.CONFIRMED)


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
        mechanism = _mechanism()
        first = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_a, e_b, mechanism.evidence),
        )
        second = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_b, e_a, mechanism.evidence),
        )
        assert first.evidence_for == second.evidence_for
        assert first.fingerprint == second.fingerprint

    def test_context_variable_permutation_invariant(self) -> None:
        cid = uuid4()
        mechanism = _mechanism()
        first = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            context=(_variable("context.b"), _variable("context.a")),
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(mechanism.evidence,),
        )
        second = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            context=(_variable("context.a"), _variable("context.b")),
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(mechanism.evidence,),
        )
        assert first.context == second.context
        assert first.fingerprint == second.fingerprint

    def test_evidence_for_different_multiset_differs(self) -> None:
        e_a = _evidence("evidence:a", CausalEvidencePolarity.SUPPORTS)
        e_b = _evidence("evidence:b", CausalEvidencePolarity.SUPPORTS)
        e_c = _evidence("evidence:c", CausalEvidencePolarity.SUPPORTS)
        cid = uuid4()
        mechanism = _mechanism()
        first = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_a, e_b, mechanism.evidence),
        )
        second = build_causal_claim(
            claim_id=cid,
            kind=CausalClaimKind.CAUSATION,
            cause=_CAUSE,
            effect=_EFFECT,
            mechanism=mechanism,
            strength=CausalClaimStrength.MODERATE,
            status=CausalClaimStatus.ACTIVE,
            evidence_for=(e_a, e_c, mechanism.evidence),
        )
        assert first.fingerprint != second.fingerprint

    def test_evidence_for_duplicate_rejected(self) -> None:
        e_a = _evidence("evidence:a", CausalEvidencePolarity.SUPPORTS)
        mechanism = _mechanism()
        with pytest.raises(CausalityValidationError, match="duplicate"):
            build_causal_claim(
                claim_id=uuid4(),
                kind=CausalClaimKind.CAUSATION,
                cause=_CAUSE,
                effect=_EFFECT,
                mechanism=mechanism,
                strength=CausalClaimStrength.MODERATE,
                status=CausalClaimStatus.ACTIVE,
                evidence_for=(e_a, e_a, mechanism.evidence),
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


class TestCorrection010ConfounderResolutionProvenance:
    """R6 F3 closure: confounder-resolution evidence must be SUPPORTS polarity
    AND provenance-retained by exact canonical identity in ``evidence_for``."""

    def _resolution(self, polarity: CausalEvidencePolarity) -> ConfounderResolution:
        return ConfounderResolution(
            confounder=_variable("selection-bias"),
            evidence=_evidence("evidence:conf", polarity),
        )

    def test_contradiction_polarity_resolution_rejected(self) -> None:
        with pytest.raises(CausalityValidationError, match="SUPPORTS"):
            _claim(
                confounders=(_variable("selection-bias"),),
                confounder_resolutions=(
                    self._resolution(CausalEvidencePolarity.CONTRADICTION),
                ),
            )

    @pytest.mark.parametrize(
        "polarity",
        (
            CausalEvidencePolarity.AGAINST,
            CausalEvidencePolarity.LIMITATION,
        ),
    )
    def test_non_supports_polarity_resolution_rejected(
        self, polarity: CausalEvidencePolarity
    ) -> None:
        with pytest.raises(CausalityValidationError, match="SUPPORTS"):
            _claim(
                confounders=(_variable("selection-bias"),),
                confounder_resolutions=(self._resolution(polarity),),
            )

    def test_supports_but_unretained_resolution_rejected(self) -> None:
        with pytest.raises(CausalityValidationError, match="retained"):
            _claim(
                confounders=(_variable("selection-bias"),),
                confounder_resolutions=(self._resolution(CausalEvidencePolarity.SUPPORTS),),
                evidence_for=(_evidence("evidence:other", CausalEvidencePolarity.SUPPORTS),),
            )

    def test_mismatched_identity_resolution_rejected(self) -> None:
        # Same reference at a different instant is a different evidence identity
        # and must not satisfy provenance.
        later = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
        resolution = ConfounderResolution(
            confounder=_variable("selection-bias"),
            evidence=CausalEvidence(
                ref=CiboCognitiveEvidenceRef("evidence:conf"),
                polarity=CausalEvidencePolarity.SUPPORTS,
                observed_at=_T,
                fingerprint=fingerprint_material(("evidence:conf", "supports", _T)),
            ),
        )
        with pytest.raises(CausalityValidationError, match="retained"):
            _claim(
                confounders=(_variable("selection-bias"),),
                confounder_resolutions=(resolution,),
                evidence_for=(
                    CausalEvidence(
                        ref=CiboCognitiveEvidenceRef("evidence:conf"),
                        polarity=CausalEvidencePolarity.SUPPORTS,
                        observed_at=later,
                        fingerprint=fingerprint_material(
                            ("evidence:conf", "supports", later)
                        ),
                    ),
                ),
            )

    def test_supports_retained_resolution_accepted(self) -> None:
        confounder = _variable("selection-bias")
        resolution = ConfounderResolution(
            confounder=confounder,
            evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
        )
        claim = _claim(
            confounders=(confounder,),
            confounder_resolutions=(resolution,),
            evidence_for=(_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),),
            status=CausalClaimStatus.CONFIRMED,
        )
        claim.revalidate()
        assert claim.status is CausalClaimStatus.CONFIRMED

    def test_reflective_polarity_corruption_fails_revalidate(self) -> None:
        confounder = _variable("selection-bias")
        resolution = ConfounderResolution(
            confounder=confounder,
            evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
        )
        claim = _claim(
            confounders=(confounder,),
            confounder_resolutions=(resolution,),
            evidence_for=(_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),),
        )
        object.__setattr__(
            claim.confounder_resolutions[0].evidence,
            "polarity",
            CausalEvidencePolarity.CONTRADICTION,
        )
        # Any reflective corruption of retained resolution evidence must fail
        # closed: either the polarity invariant or the fingerprint integrity
        # check fires (the fingerprint check fires first for a polarity flip).
        with pytest.raises(CausalityValidationError):
            claim.revalidate()


class TestIAR9CausalEvidenceChannelPolarity:
    """IA closure: evidence channel != caller-selected polarity."""

    @pytest.mark.parametrize(
        ("field", "wrong_polarity"),
        (
            ("evidence_for", CausalEvidencePolarity.CONTRADICTION),
            ("evidence_against", CausalEvidencePolarity.SUPPORTS),
            ("contradictions", CausalEvidencePolarity.SUPPORTS),
            ("limitations", CausalEvidencePolarity.SUPPORTS),
        ),
    )
    def test_builder_rejects_cross_channel_polarity_laundering(
        self, field: str, wrong_polarity: CausalEvidencePolarity
    ) -> None:
        evidence = _evidence(f"evidence:ia-r9-{field}", wrong_polarity)
        with pytest.raises(CausalityValidationError, match="must carry only"):
            _claim(**{field: (evidence,)})

    @pytest.mark.parametrize(
        ("field", "wrong_polarity"),
        (
            ("evidence_for", CausalEvidencePolarity.CONTRADICTION),
            ("evidence_against", CausalEvidencePolarity.SUPPORTS),
            ("contradictions", CausalEvidencePolarity.SUPPORTS),
            ("limitations", CausalEvidencePolarity.SUPPORTS),
        ),
    )
    def test_revalidate_rejects_reflective_cross_channel_replacement(
        self, field: str, wrong_polarity: CausalEvidencePolarity
    ) -> None:
        claim = _claim()
        evidence = _evidence(f"evidence:ia-r9-reflect-{field}", wrong_polarity)
        object.__setattr__(claim, field, (evidence,))
        with pytest.raises(CausalityValidationError, match="must carry only"):
            claim.revalidate()


class TestCorrection011MechanismBindingAuthority:
    """RF-3 FULL-FAMILY recertification: CORRELATION != CAUSATION. A caller
    label is not an authority root for CAUSATION/STRONG/CONFIRMED — the mechanism
    must be a typed, evidence-bound binding whose evidence is SUPPORTS-polarity
    and provenance-retained in the claim's evidence_for, distinct from every
    confounder-resolution observation."""

    def test_causation_requires_evidence_bound_mechanism_not_label(self) -> None:
        # The bare-label API no longer exists; a missing mechanism fails closed.
        with pytest.raises(CausalityValidationError, match="mechanism"):
            _claim(mechanism=None)

    def test_mechanism_evidence_must_be_retained_in_evidence_for(self) -> None:
        confounder = _variable("selection-bias")
        mechanism = MechanismBinding(
            code="mechanism.randomization",
            evidence=_evidence("evidence:unretained", CausalEvidencePolarity.SUPPORTS),
        )
        resolution = ConfounderResolution(
            confounder=confounder,
            evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
        )
        with pytest.raises(CausalityValidationError, match="mechanism binding evidence"):
            _claim(
                confounders=(confounder,),
                mechanism=mechanism,
                confounder_resolutions=(resolution,),
                evidence_for=(_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),),
            )

    def test_mechanism_evidence_reused_as_confounder_resolution_rejected(self) -> None:
        confounder = _variable("selection-bias")
        shared = _evidence("evidence:shared", CausalEvidencePolarity.SUPPORTS)
        mechanism = MechanismBinding(code="mechanism.randomization", evidence=shared)
        resolution = ConfounderResolution(confounder=confounder, evidence=shared)
        with pytest.raises(CausalityValidationError, match="distinct"):
            _claim(
                confounders=(confounder,),
                mechanism=mechanism,
                confounder_resolutions=(resolution,),
                evidence_for=(shared,),
            )

    def test_mechanism_evidence_must_be_supports_polarity(self) -> None:
        with pytest.raises(CausalityValidationError, match="SUPPORTS"):
            MechanismBinding(
                code="mechanism.randomization",
                evidence=_evidence("evidence:against", CausalEvidencePolarity.AGAINST),
            )

    def test_evidence_bound_mechanism_accepted(self) -> None:
        confounder = _variable("selection-bias")
        mechanism = _mechanism()
        resolution = ConfounderResolution(
            confounder=confounder,
            evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
        )
        claim = _claim(
            confounders=(confounder,),
            mechanism=mechanism,
            confounder_resolutions=(resolution,),
            evidence_for=(
                mechanism.evidence,
                _evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
            ),
            strength=CausalClaimStrength.STRONG,
            status=CausalClaimStatus.CONFIRMED,
        )
        claim.revalidate()
        assert claim.mechanism is not None
        assert claim.mechanism.code == "mechanism.randomization"

    def test_reflective_mechanism_polarity_corruption_fails_revalidate(self) -> None:
        confounder = _variable("selection-bias")
        mechanism = _mechanism()
        resolution = ConfounderResolution(
            confounder=confounder,
            evidence=_evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
        )
        claim = _claim(
            confounders=(confounder,),
            mechanism=mechanism,
            confounder_resolutions=(resolution,),
            evidence_for=(
                mechanism.evidence,
                _evidence("evidence:conf", CausalEvidencePolarity.SUPPORTS),
            ),
        )
        assert claim.mechanism is not None
        object.__setattr__(
            claim.mechanism.evidence,
            "polarity",
            CausalEvidencePolarity.CONTRADICTION,
        )
        with pytest.raises(CausalityValidationError):
            claim.revalidate()
