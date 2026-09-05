"""Tests for the CIBO Cognitive Evaluation Framework (CA-17)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveValidationError,
    TraderSubject,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_evaluation import (
    CapabilityEvidence,
    CapabilityEvidenceKind,
    CapabilityOutcome,
    CognitiveEvaluation,
    CognitiveEvaluationStatus,
    EvaluationDimension,
    EvaluationDimensionScore,
    InterventionAttributionDisposition,
    InterventionIdentity,
    InterventionKind,
    TraderDevelopmentAttribution,
    build_trader_development_attribution,
    capability_evidence_fingerprint,
    evaluate_cognition,
)

_EVALUATION = UUID("00000000-0000-0000-0000-0000000000a9")


def _score(dimension: EvaluationDimension, score: int = 60) -> EvaluationDimensionScore:
    return EvaluationDimensionScore(
        dimension=dimension, score=score, note=f"note for {dimension.value}"
    )


def _dimensions() -> tuple[EvaluationDimensionScore, ...]:
    return (
        _score(EvaluationDimension.EVIDENCE_SUFFICIENCY, 70),
        _score(EvaluationDimension.REPLAY_COMPLETENESS, 80),
    )


def test_missing_evidence_yields_insufficient_evidence() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=(),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.INSUFFICIENT_EVIDENCE


def test_contradictory_evidence_yields_contradictory_evidence() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=("contradiction-1",),
    )
    assert evaluation.status is CognitiveEvaluationStatus.CONTRADICTORY_EVIDENCE


def test_sufficient_for_evaluation() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION


def test_evaluation_not_applicable_for_blank_reference() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="   ",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.EVALUATION_NOT_APPLICABLE


def test_evaluation_not_applicable_for_empty_dimensions() -> None:
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    assert evaluation.status is CognitiveEvaluationStatus.EVALUATION_NOT_APPLICABLE


def test_evaluation_cannot_confer_authority() -> None:
    assert set(CognitiveEvaluationStatus.__members__) == {
        "SUFFICIENT_FOR_EVALUATION",
        "INSUFFICIENT_EVIDENCE",
        "CONTRADICTORY_EVIDENCE",
        "EVALUATION_NOT_APPLICABLE",
    }
    evaluation = evaluate_cognition(
        evaluation_id=_EVALUATION,
        evaluated_reference="episode:1",
        dimensions=_dimensions(),
        evidence_refs=("ev-1",),
        contradiction_refs=(),
    )
    for forbidden in (
        "authority",
        "order",
        "account",
        "credential",
        "promotion",
        "execute",
        "risk",
    ):
        assert not hasattr(evaluation, forbidden)


def test_dimension_score_rejects_bool() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        EvaluationDimensionScore(
            dimension=EvaluationDimension.EVIDENCE_SUFFICIENCY,
            score=True,
            note="x",
        )


def test_duplicate_dimensions_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveEvaluation(
            evaluation_id=_EVALUATION,
            evaluated_reference="episode:1",
            dimensions=(
                _score(EvaluationDimension.EVIDENCE_SUFFICIENCY),
                _score(EvaluationDimension.EVIDENCE_SUFFICIENCY),
            ),
            status=CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION,
            evidence_refs=("ev-1",),
            contradiction_refs=(),
        )


def test_inconsistent_status_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveEvaluation(
            evaluation_id=_EVALUATION,
            evaluated_reference="episode:1",
            dimensions=_dimensions(),
            status=CognitiveEvaluationStatus.SUFFICIENT_FOR_EVALUATION,
            evidence_refs=(),
            contradiction_refs=(),
        )


def test_evaluate_rejects_non_str_reference_without_leaking_exception() -> None:
    bad_reference: Any = 123
    with pytest.raises(CiboCognitiveValidationError):
        evaluate_cognition(
            evaluation_id=_EVALUATION,
            evaluated_reference=bad_reference,
            dimensions=_dimensions(),
            evidence_refs=("ev-1",),
            contradiction_refs=(),
        )


def test_evaluate_rejects_non_score_dimensions_without_leaking_exception() -> None:
    bad_dimensions: Any = ["not-a-score"]
    with pytest.raises(CiboCognitiveValidationError):
        evaluate_cognition(
            evaluation_id=_EVALUATION,
            evaluated_reference="episode:1",
            dimensions=bad_dimensions,
            evidence_refs=("ev-1",),
            contradiction_refs=(),
        )


# ---------------------------------------------------------------------------
# IA-F-INTERVENTION-ATTRIBUTION-001: typed Trader-development intervention
# attribution family (CA-17).
# ---------------------------------------------------------------------------

_ATTRIBUTION_ID = UUID("00000000-0000-0000-0000-0000000000c1")
_T_PRE = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)
_T_INT = datetime(2024, 6, 15, 0, 0, 0, tzinfo=UTC)
_T_POST = datetime(2024, 6, 30, 0, 0, 0, tzinfo=UTC)


def _trader(trader_id: str = "trader.vt-1", version: str = "v1") -> TraderSubject:
    return TraderSubject(
        trader_id=trader_id,
        trader_version=version,
        fingerprint=fingerprint_material((trader_id, version)),
    )


def _intervention(
    trader: TraderSubject,
    *,
    intervention_id: str = "cibo.dev-intervention",
    version: str = "v1",
    kind: InterventionKind = InterventionKind.DEVELOPMENT,
) -> InterventionIdentity:
    return InterventionIdentity(
        intervention_id=intervention_id,
        intervention_version=version,
        target_trader_fingerprint=trader.fingerprint,
        kind=kind,
        fingerprint=fingerprint_material(
            (intervention_id, version, trader.fingerprint.value, kind.value)
        ),
    )


def _pre(
    capability: str = "regime-detection",
    *,
    reference: str = "ev.pre",
    observed_at: datetime = _T_PRE,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        reference=reference,
        capability=capability,
        observed_at=observed_at,
        evidence_fingerprint=capability_evidence_fingerprint(
            reference=reference, capability=capability, observed_at=observed_at
        ),
    )


def _post(
    capability: str = "regime-detection",
    *,
    reference: str = "ev.post",
    outcome: CapabilityOutcome = CapabilityOutcome.IMPROVED,
    observed_at: datetime = _T_POST,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        reference=reference,
        capability=capability,
        observed_at=observed_at,
        evidence_fingerprint=capability_evidence_fingerprint(
            reference=reference,
            capability=capability,
            observed_at=observed_at,
            outcome=outcome,
        ),
        outcome=outcome,
    )


def _attribution(
    *,
    trader: TraderSubject | None = None,
    intervention: InterventionIdentity | None = None,
    pre: tuple[CapabilityEvidence, ...] | None = None,
    post: tuple[CapabilityEvidence, ...] | None = None,
    **kwargs: object,
) -> TraderDevelopmentAttribution:
    subject = trader if trader is not None else _trader()
    params: dict[str, Any] = {
        "attribution_id": _ATTRIBUTION_ID,
        "trader": subject,
        "intervention": (
            intervention if intervention is not None else _intervention(subject)
        ),
        "development_hypothesis": "curriculum improves regime classification",
        "target_capability": "regime-detection",
        "applied_at": _T_INT,
        "curriculum_refs": ("curriculum.regime.101",),
        "pre_intervention_evidence": pre if pre is not None else (_pre(),),
        "post_intervention_evidence": post if post is not None else (_post(),),
    }
    params.update(kwargs)
    return build_trader_development_attribution(**params)


def test_supported_contribution_builds_and_revalidates() -> None:
    attribution = _attribution()
    assert (
        attribution.disposition
        is InterventionAttributionDisposition.SUPPORTED_CONTRIBUTION
    )
    attribution.revalidate()


def test_profit_alone_is_never_causal_proof() -> None:
    profit = CapabilityEvidence(
        reference="pnl.x",
        capability="pnl",
        observed_at=_T_POST,
        evidence_fingerprint=capability_evidence_fingerprint(
            reference="pnl.x",
            capability="pnl",
            observed_at=_T_POST,
            kind=CapabilityEvidenceKind.ECONOMIC_OUTCOME,
        ),
        kind=CapabilityEvidenceKind.ECONOMIC_OUTCOME,
    )
    attribution = _attribution(post=(profit,))
    assert (
        attribution.disposition
        is InterventionAttributionDisposition.INSUFFICIENT_EVIDENCE
    )


def test_economic_outcome_cannot_carry_capability_outcome() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CapabilityEvidence(
            reference="pnl.x",
            capability="pnl",
            observed_at=_T_POST,
            evidence_fingerprint=fingerprint_material("pnl.x"),
            kind=CapabilityEvidenceKind.ECONOMIC_OUTCOME,
            outcome=CapabilityOutcome.IMPROVED,
        )


def test_post_outcome_cannot_be_written_into_pre_state() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(pre=(_post(),))


def test_pre_evidence_cannot_postdate_intervention() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(pre=(_pre(observed_at=_T_POST),))


def test_post_evidence_must_postdate_intervention() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(post=(_post(observed_at=_T_PRE),))


def test_intervention_version_mismatch_rejected() -> None:
    trader = _trader()
    with pytest.raises(CiboCognitiveValidationError):
        InterventionIdentity(
            intervention_id="cibo.dev-intervention",
            intervention_version="v2",
            target_trader_fingerprint=trader.fingerprint,
            kind=InterventionKind.DEVELOPMENT,
            fingerprint=fingerprint_material(
                ("cibo.dev-intervention", "v1", trader.fingerprint.value, "development")
            ),
        )


def test_cross_trader_intervention_rejected() -> None:
    trader_a = _trader(trader_id="trader.vt-1")
    trader_b = _trader(trader_id="trader.vt-2")
    intervention_for_b = _intervention(trader_b)
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(trader=trader_a, intervention=intervention_for_b)


def test_curriculum_reference_mutation_rejected() -> None:
    attribution = _attribution()
    object.__setattr__(attribution, "curriculum_refs", ("curriculum.regime.999",))
    with pytest.raises(CiboCognitiveValidationError):
        attribution.revalidate()


def test_reflective_corruption_rejected() -> None:
    attribution = _attribution()
    object.__setattr__(attribution, "post_intervention_evidence", ())
    with pytest.raises(CiboCognitiveValidationError):
        attribution.revalidate()


def test_attribution_exposes_no_authority_fields() -> None:
    attribution = _attribution()
    for forbidden in (
        "execution",
        "risk",
        "promotion",
        "demo",
        "production",
        "profit",
        "order",
        "account",
        "credential",
    ):
        assert not hasattr(attribution, forbidden)


def test_attribution_secret_material_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(development_hypothesis="api_key=sk-abcdef1234567890")
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(curriculum_refs=("sk-abcdef12345678",))


def test_attribution_subclass_laundering_rejected() -> None:
    class EvilStr(str):
        pass

    class EvilDatetime(datetime):
        pass

    class EvilTraderSubject(TraderSubject):
        def revalidate(self) -> None:
            pass

    with pytest.raises(CiboCognitiveValidationError):
        CapabilityEvidence(
            reference=EvilStr("ev.pre"),
            capability="regime-detection",
            observed_at=_T_PRE,
            evidence_fingerprint=fingerprint_material("x"),
        )
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(
            trader=EvilTraderSubject(
                trader_id="trader.vt-1",
                trader_version="v1",
                fingerprint=fingerprint_material(("trader.vt-1", "v1")),
            )
        )
    with pytest.raises(CiboCognitiveValidationError):
        _attribution(applied_at=EvilDatetime(2024, 6, 15, tzinfo=UTC))


def test_attribution_bool_int_laundering_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CapabilityEvidence(
            reference="ev.pre",
            capability="regime-detection",
            observed_at=_T_PRE,
            evidence_fingerprint=fingerprint_material("x"),
            outcome=True,  # type: ignore[arg-type]
        )


def test_supported_contribution_requires_pre_and_post_evidence() -> None:
    assert _attribution(pre=()).disposition is (
        InterventionAttributionDisposition.INSUFFICIENT_EVIDENCE
    )
    assert _attribution(post=()).disposition is (
        InterventionAttributionDisposition.INSUFFICIENT_EVIDENCE
    )


def test_non_development_intervention_is_not_applicable() -> None:
    trader = _trader()
    intervention = _intervention(trader, kind=InterventionKind.NON_DEVELOPMENT)
    attribution = _attribution(intervention=intervention)
    assert (
        attribution.disposition is InterventionAttributionDisposition.NOT_APPLICABLE
    )


def test_degraded_outcome_is_contradictory() -> None:
    attribution = _attribution(post=(_post(outcome=CapabilityOutcome.DEGRADED),))
    assert (
        attribution.disposition
        is InterventionAttributionDisposition.CONTRADICTORY_EVIDENCE
    )


def test_only_unchanged_outcome_is_insufficient() -> None:
    attribution = _attribution(post=(_post(outcome=CapabilityOutcome.UNCHANGED),))
    assert (
        attribution.disposition
        is InterventionAttributionDisposition.INSUFFICIENT_EVIDENCE
    )


def test_attribution_ordering_is_permutation_invariant() -> None:
    first = _attribution(curriculum_refs=("curriculum.regime.101", "case.regime.a"))
    second = _attribution(curriculum_refs=("case.regime.a", "curriculum.regime.101"))
    assert first.curriculum_refs == second.curriculum_refs
    assert first.fingerprint == second.fingerprint


class TestCapabilityEvidenceFingerprintRevalidation:
    def test_mutated_reference_fails_revalidate(self) -> None:
        evidence = _pre()
        object.__setattr__(evidence, "reference", "ev.mutated")
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            evidence.revalidate()

    def test_mutated_capability_fails_revalidate(self) -> None:
        evidence = _pre()
        object.__setattr__(evidence, "capability", "mutated-capability")
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            evidence.revalidate()

    def test_mutated_observed_at_fails_revalidate(self) -> None:
        evidence = _pre()
        object.__setattr__(evidence, "observed_at", _T_INT)
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            evidence.revalidate()

    def test_mutated_kind_fails_revalidate(self) -> None:
        evidence = _pre()
        object.__setattr__(evidence, "kind", CapabilityEvidenceKind.ECONOMIC_OUTCOME)
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            evidence.revalidate()

    def test_mutated_outcome_fails_revalidate(self) -> None:
        evidence = _pre()
        object.__setattr__(evidence, "outcome", CapabilityOutcome.IMPROVED)
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            evidence.revalidate()

    def test_mutated_fingerprint_fails_revalidate(self) -> None:
        evidence = _pre()
        object.__setattr__(evidence, "evidence_fingerprint", fingerprint_material("forged"))
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            evidence.revalidate()

    def test_constructor_rejects_forged_fingerprint(self) -> None:
        # The constructor path itself (__post_init__ -> revalidate) must reject a
        # mismatched fingerprint, making constructor == revalidate.
        with pytest.raises(CiboCognitiveValidationError, match="fingerprint"):
            CapabilityEvidence(
                reference="ev.forged",
                capability="discipline",
                observed_at=_T_PRE,
                evidence_fingerprint=fingerprint_material("forged"),
            )

    def test_nested_attribution_mutation_fails_revalidate(self) -> None:
        attribution = _attribution()
        object.__setattr__(
            attribution.pre_intervention_evidence[0], "capability", "mutated-capability"
        )
        with pytest.raises(CiboCognitiveValidationError):
            attribution.revalidate()


class TestCapabilityEvidenceTemporalSemantics:
    def test_dst_fold_instants_remain_distinct(self) -> None:
        tz = ZoneInfo("America/New_York")
        f0 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=0)
        f1 = datetime(2024, 11, 3, 1, 30, tzinfo=tz, fold=1)
        a = CapabilityEvidence(
            reference="ev.fold",
            capability="regime-detection",
            observed_at=f0,
            evidence_fingerprint=capability_evidence_fingerprint(
                reference="ev.fold", capability="regime-detection", observed_at=f0
            ),
        )
        b = CapabilityEvidence(
            reference="ev.fold",
            capability="regime-detection",
            observed_at=f1,
            evidence_fingerprint=capability_evidence_fingerprint(
                reference="ev.fold", capability="regime-detection", observed_at=f1
            ),
        )
        assert a != b
        assert len({a, b}) == 2

    def test_equivalent_offset_same_instant_dedups(self) -> None:
        utc = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        est = datetime(2024, 1, 1, 7, 0, tzinfo=timezone(timedelta(hours=-5)))
        a = CapabilityEvidence(
            reference="ev.x",
            capability="c",
            observed_at=utc,
            evidence_fingerprint=capability_evidence_fingerprint(
                reference="ev.x", capability="c", observed_at=utc
            ),
        )
        b = CapabilityEvidence(
            reference="ev.x",
            capability="c",
            observed_at=est,
            evidence_fingerprint=capability_evidence_fingerprint(
                reference="ev.x", capability="c", observed_at=est
            ),
        )
        assert a == b
        assert len({a, b}) == 1
