"""Pre-outcome runtime composition for CE2I T13 shadow evidence.

This module joins the already-durable Phase20D evidence/policy decision with the
preregistered T13 recommendation and treatment ledgers. It never changes the
baseline policy, sizing, QORE Risk authorization or broker execution.

The composition is intentionally after the baseline policy has been physically
sealed and before any same-epoch outcome exists. Existing complete T13 seals
are accepted idempotently on restart; incomplete chains still fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardDecisionEvidence,
    Phase20ForwardDecisionRecord,
    phase20_forward_evidence_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_policy import (
    T13_SHADOW_POLICY_FROZEN_AT,
    T13_SHADOW_POLICY_ID,
    Phase20T13ShadowRecommendation,
    evaluate_phase20_t13_shadow_decision,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    DurableT13ShadowDecisionStore,
    T13ShadowDecisionSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment import (
    build_phase20_t13_shadow_treatment,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    DurableT13ShadowTreatmentStore,
    T13ShadowTreatmentSeal,
)


@dataclass(frozen=True, slots=True)
class Phase20T13RuntimeShadowSeal:
    decision_evidence_sha256: str
    recommendation_generation: int
    treatment_generation: int
    recommendation_sha256: str
    treatment_sha256: str
    reserve_triggered: bool
    reserved_risk_usd: Decimal
    selection_changed: bool
    baseline_selected_signal_fingerprints: tuple[str, ...]
    treatment_selected_signal_fingerprints: tuple[str, ...]
    broker_mutation_performed: bool = False
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_evidence_sha256",
            "recommendation_sha256",
            "treatment_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 runtime {name} must be canonical SHA-256"
                )
        for name in (
            "recommendation_generation",
            "treatment_generation",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T13 runtime {name} must be positive int"
                )
        if (
            not isinstance(self.reserved_risk_usd, Decimal)
            or not self.reserved_risk_usd.is_finite()
            or self.reserved_risk_usd < 0
        ):
            raise CiboCapitalManagementError(
                "Phase20 T13 runtime reserved risk must be finite non-negative"
            )
        for name in (
            "reserve_triggered",
            "selection_changed",
            "broker_mutation_performed",
            "runtime_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T13 runtime {name} must be bool"
                )
        if self.broker_mutation_performed or self.runtime_authority:
            raise CiboCapitalManagementError(
                "Phase20 T13 runtime shadow cannot mutate execution"
            )


def seal_phase20_t13_runtime_shadow(
    *,
    evidence: Phase20ForwardDecisionEvidence,
    decision_record: Phase20ForwardDecisionRecord,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
    recommendation_store: DurableT13ShadowDecisionStore,
    treatment_store: DurableT13ShadowTreatmentStore,
) -> Phase20T13RuntimeShadowSeal | None:
    """Seal recommendation + treatment after baseline, before any outcome."""

    if not isinstance(evidence, Phase20ForwardDecisionEvidence):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime requires canonical forward evidence"
        )
    if not isinstance(decision_record, Phase20ForwardDecisionRecord):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime requires canonical policy record"
        )
    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime requires canonical evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime requires canonical policy book"
        )
    if not isinstance(
        recommendation_store,
        DurableT13ShadowDecisionStore,
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime recommendation store is invalid"
        )
    if not isinstance(treatment_store, DurableT13ShadowTreatmentStore):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime treatment store is invalid"
        )
    if evidence.decision_at < T13_SHADOW_POLICY_FROZEN_AT:
        return None

    evidence_sha = phase20_forward_evidence_sha256(evidence)
    if decision_record.evidence_sha256 != evidence_sha:
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime policy/evidence digest drift"
        )
    decision = evidence_book.decision_for_sha(evidence_sha)
    if decision is None:
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime requires durable forward decision"
        )
    baseline = policy_book.decision_for_evidence(evidence_sha)
    if baseline is None:
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime requires durable baseline policy"
        )

    current_recommendations = recommendation_store.load()
    current_treatments = treatment_store.load()
    existing_recommendation = current_recommendations.decision_for_evidence(
        evidence_sha
    )
    existing_treatment = current_treatments.decision_for_evidence(
        evidence_sha
    )
    if existing_treatment is not None:
        if existing_recommendation is None:
            raise CiboCapitalManagementError(
                "Phase20 T13 runtime treatment exists without recommendation"
            )
        return _runtime_seal(
            recommendation=existing_recommendation,
            treatment=existing_treatment,
            baseline_policy_record_sha256=baseline.policy_record_sha256,
            recommendation_generation=current_recommendations.generation,
            treatment_generation=current_treatments.generation,
        )

    recommendation = (
        _recommendation_from_seal(existing_recommendation)
        if existing_recommendation is not None
        else evaluate_phase20_t13_shadow_decision(
            evidence_book=evidence_book,
            decision=decision,
        )
    )
    if existing_recommendation is None:
        current_recommendations = recommendation_store.seal_recommendation(
            recommendation,
            evidence_book=evidence_book,
            expected_generation=current_recommendations.generation,
        )
        existing_recommendation = (
            current_recommendations.decision_for_evidence(evidence_sha)
        )
        if existing_recommendation is None:
            raise CiboCapitalManagementError(
                "Phase20 T13 runtime recommendation seal missing after write"
            )

    treatment = build_phase20_t13_shadow_treatment(
        evidence=evidence,
        baseline_policy=baseline,
        recommendation=recommendation,
    )
    current_treatments = treatment_store.seal_treatment(
        treatment,
        evidence_book=evidence_book,
        baseline_policy_book=policy_book,
        recommendation_book=current_recommendations,
        expected_generation=current_treatments.generation,
    )
    existing_treatment = current_treatments.decision_for_evidence(
        evidence_sha
    )
    if existing_treatment is None:
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime treatment seal missing after write"
        )

    return _runtime_seal(
        recommendation=existing_recommendation,
        treatment=existing_treatment,
        baseline_policy_record_sha256=baseline.policy_record_sha256,
        recommendation_generation=current_recommendations.generation,
        treatment_generation=current_treatments.generation,
    )


def _recommendation_from_seal(
    seal: T13ShadowDecisionSeal,
) -> Phase20T13ShadowRecommendation:
    return Phase20T13ShadowRecommendation(
        policy_id=T13_SHADOW_POLICY_ID,
        policy_sha256=seal.policy_sha256,
        decision_epoch_id=seal.decision_epoch_id,
        decision_evidence_sha256=seal.decision_evidence_sha256,
        decision_at=seal.decision_at,
        causal_pressure_active=seal.reserve_triggered,
        arrival_evidence_available=seal.reserve_triggered,
        reserve_triggered=seal.reserve_triggered,
        reserved_risk_usd=seal.reserved_risk_usd,
        minimum_seed_risk_usd=seal.minimum_seed_risk_usd,
        hard_risk_headroom_usd=seal.hard_risk_headroom_usd,
        full_seed_preserved=seal.full_seed_preserved,
        source_decision_sha256s=seal.source_decision_sha256s,
        source_outcome_evidence_ids=seal.source_outcome_evidence_ids,
    )


def _runtime_seal(
    *,
    recommendation: T13ShadowDecisionSeal,
    treatment: T13ShadowTreatmentSeal,
    baseline_policy_record_sha256: str,
    recommendation_generation: int,
    treatment_generation: int,
) -> Phase20T13RuntimeShadowSeal:
    if (
        treatment.recommendation_sha256
        != recommendation.recommendation_sha256
        or treatment.decision_evidence_sha256
        != recommendation.decision_evidence_sha256
        or treatment.t13_policy_sha256 != recommendation.policy_sha256
        or treatment.baseline_policy_record_sha256
        != baseline_policy_record_sha256
        or treatment.reserve_triggered != recommendation.reserve_triggered
        or treatment.shadow_reserved_risk_usd
        != recommendation.reserved_risk_usd
    ):
        raise CiboCapitalManagementError(
            "Phase20 T13 runtime durable chain binding drift"
        )
    return Phase20T13RuntimeShadowSeal(
        decision_evidence_sha256=treatment.decision_evidence_sha256,
        recommendation_generation=recommendation_generation,
        treatment_generation=treatment_generation,
        recommendation_sha256=recommendation.recommendation_sha256,
        treatment_sha256=treatment.treatment_sha256,
        reserve_triggered=treatment.reserve_triggered,
        reserved_risk_usd=treatment.shadow_reserved_risk_usd,
        selection_changed=treatment.selection_changed,
        baseline_selected_signal_fingerprints=(
            treatment.baseline_selected_signal_fingerprints
        ),
        treatment_selected_signal_fingerprints=(
            treatment.treatment_selected_signal_fingerprints
        ),
        broker_mutation_performed=False,
        runtime_authority=False,
    )
