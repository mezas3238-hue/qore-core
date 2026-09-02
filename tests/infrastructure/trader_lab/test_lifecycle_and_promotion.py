from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabRejectionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    apply_trader_lab_rejection,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.promotion import (
    TraderLabPromotionStatus,
    evaluate_demo_eligibility,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceRecord,
)
from qore.kernel.result import Failure, Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_EvidenceFactory = Callable[..., TraderLabStageEvidenceRecord]


def _economic_reference() -> TraderLabEvidenceReference:
    return TraderLabEvidenceReference(
        kind=TraderLabEvidenceKind.ECONOMIC_EVALUATION,
        reference_id=UUID("72000000-0000-0000-0000-00000000eeee"),
        content_digest=TraderLabEvidenceDigest("c" * 64),
        schema_version="economic.evaluation.v1",
    )


def _promote(
    lifecycle: TraderLabLifecycle,
    *,
    stage: TraderLabStage,
    candidate: TraderLabCandidateBinding,
    stage_evidence_factory: _EvidenceFactory,
    evidence_suffix: int,
    produced_at: datetime,
) -> TraderLabLifecycle:
    evidence = stage_evidence_factory(
        stage=stage,
        candidate=candidate,
        evidence_suffix=evidence_suffix,
        produced_at=produced_at,
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=stage, evidence=evidence),
    )
    assert isinstance(built, Success), built
    return built.value


def _qualify_through(
    lifecycle: TraderLabLifecycle,
    candidate: TraderLabCandidateBinding,
    stage_evidence_factory: _EvidenceFactory,
    stages: tuple[TraderLabStage, ...],
    start_suffix: int = 100,
) -> TraderLabLifecycle:
    current = lifecycle
    for index, stage in enumerate(stages):
        current = _promote(
            current,
            stage=stage,
            candidate=candidate,
            stage_evidence_factory=stage_evidence_factory,
            evidence_suffix=start_suffix + index,
            produced_at=_PROCESS_TIME + timedelta(minutes=index),
        )
    return current


def test_happy_path_full_progression(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    assert lifecycle.state is TraderLabState.DRAFT
    lifecycle = _qualify_through(
        lifecycle, candidate, stage_evidence_factory, MANDATORY_STAGES
    )
    assert lifecycle.state is TraderLabState.DEMO_ELIGIBLE
    assert lifecycle.completed_stages == MANDATORY_STAGES


def test_every_illegal_stage_skip_is_rejected(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    # Skip RESEARCH entirely.
    skip_first = stage_evidence_factory(
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        evidence_suffix=101,
        produced_at=_PROCESS_TIME,
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.REPLAY, evidence=skip_first),
    )
    assert isinstance(built, Failure)
    assert "cannot be skipped" in str(built.error)
    # A mid-chain skip is rejected the same way.
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        stage_evidence_factory=stage_evidence_factory,
        evidence_suffix=102,
        produced_at=_PROCESS_TIME,
    )
    for bad_stage in (
        TraderLabStage.OOS,
        TraderLabStage.MONTE_CARLO,
        TraderLabStage.INDEPENDENT_VALIDATION,
    ):
        evidence = stage_evidence_factory(
            stage=bad_stage,
            candidate=candidate,
            evidence_suffix=110 + MANDATORY_STAGES.index(bad_stage),
            produced_at=_PROCESS_TIME + timedelta(minutes=5),
        )
        built = apply_trader_lab_promotion(
            lifecycle,
            TraderLabPromotionRequest(stage=bad_stage, evidence=evidence),
        )
        assert isinstance(built, Failure)
        assert "cannot be skipped" in str(built.error)


def test_wrong_candidate_binding_is_rejected(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate_a = candidate_factory(candidate_suffix=1)
    candidate_b = candidate_factory(candidate_suffix=2)
    lifecycle = start_trader_lab_lifecycle(candidate_a)
    evidence = stage_evidence_factory(
        stage=TraderLabStage.RESEARCH,
        candidate=candidate_b,
        evidence_suffix=120,
        produced_at=_PROCESS_TIME,
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.RESEARCH, evidence=evidence),
    )
    assert isinstance(built, Failure)
    assert "does not match" in str(built.error)


def test_stage_evidence_from_another_candidate_cannot_promote(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate_a = candidate_factory(candidate_suffix=1)
    candidate_b = candidate_factory(candidate_suffix=2)
    lifecycle = start_trader_lab_lifecycle(candidate_a)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.RESEARCH,
        candidate=candidate_a,
        stage_evidence_factory=stage_evidence_factory,
        evidence_suffix=130,
        produced_at=_PROCESS_TIME,
    )
    foreign_evidence = stage_evidence_factory(
        stage=TraderLabStage.REPLAY,
        candidate=candidate_b,
        evidence_suffix=131,
        produced_at=_PROCESS_TIME + timedelta(minutes=1),
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.REPLAY, evidence=foreign_evidence),
    )
    assert isinstance(built, Failure)
    assert "does not match" in str(built.error)


def test_duplicate_stage_and_stale_evidence_rejected(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        stage_evidence_factory=stage_evidence_factory,
        evidence_suffix=140,
        produced_at=_PROCESS_TIME,
    )
    # Re-applying a later evidence for an already-completed stage is a skip.
    replayed = stage_evidence_factory(
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        evidence_suffix=141,
        produced_at=_PROCESS_TIME + timedelta(minutes=1),
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.RESEARCH, evidence=replayed),
    )
    assert isinstance(built, Failure)
    assert "cannot be skipped" in str(built.error)

    # Stale evidence (produced before the preceding qualification) fails closed.
    stale = stage_evidence_factory(
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        evidence_suffix=142,
        produced_at=_PROCESS_TIME - timedelta(minutes=1),
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.REPLAY, evidence=stale),
    )
    assert isinstance(built, Failure)
    assert "stale" in str(built.error)


def test_version_mutation_invalidates_prior_chain(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate_v1 = candidate_factory(candidate_suffix=1, version="v1")
    lifecycle = start_trader_lab_lifecycle(candidate_v1)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.RESEARCH,
        candidate=candidate_v1,
        stage_evidence_factory=stage_evidence_factory,
        evidence_suffix=150,
        produced_at=_PROCESS_TIME,
    )
    assert lifecycle.state is TraderLabState.RESEARCH_READY

    candidate_v2 = candidate_factory(candidate_suffix=1, version="v2")
    assert candidate_v1.fingerprint != candidate_v2.fingerprint
    new_lifecycle = start_trader_lab_lifecycle(candidate_v2)
    old_evidence = stage_evidence_factory(
        stage=TraderLabStage.RESEARCH,
        candidate=candidate_v1,
        evidence_suffix=151,
        produced_at=_PROCESS_TIME + timedelta(minutes=1),
    )
    built = apply_trader_lab_promotion(
        new_lifecycle,
        TraderLabPromotionRequest(stage=TraderLabStage.RESEARCH, evidence=old_evidence),
    )
    assert isinstance(built, Failure)
    assert "does not match" in str(built.error)


def test_rejected_suspended_degraded_require_restart(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        stage_evidence_factory=stage_evidence_factory,
        evidence_suffix=160,
        produced_at=_PROCESS_TIME,
    )
    blocked = apply_trader_lab_rejection(
        lifecycle,
        TraderLabRejectionRequest(
            outcome=TraderLabState.SUSPENDED,
            evidence=_economic_reference(),
            decided_at=_PROCESS_TIME + timedelta(minutes=1),
        ),
    )
    assert isinstance(blocked, Success)
    assert blocked.value.state is TraderLabState.SUSPENDED

    # No forward promotion from a terminal blocking state.
    evidence = stage_evidence_factory(
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        evidence_suffix=161,
        produced_at=_PROCESS_TIME + timedelta(minutes=2),
    )
    built = apply_trader_lab_promotion(
        blocked.value,
        TraderLabPromotionRequest(stage=TraderLabStage.REPLAY, evidence=evidence),
    )
    assert isinstance(built, Failure)
    assert "terminal" in str(built.error)

    # A new version starts a fresh chain.
    candidate_v2 = candidate_factory(candidate_suffix=1, version="v2")
    fresh = start_trader_lab_lifecycle(candidate_v2)
    assert fresh.state is TraderLabState.DRAFT


def test_cibo_review_cannot_self_promote(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    through_cibo = MANDATORY_STAGES[: MANDATORY_STAGES.index(TraderLabStage.INDEPENDENT_VALIDATION)]
    lifecycle = _qualify_through(
        lifecycle, candidate, stage_evidence_factory, through_cibo
    )
    assert lifecycle.state is TraderLabState.CIBO_REVIEWED
    decision = evaluate_demo_eligibility(
        lifecycle, economic_evidence=_economic_reference()
    )
    assert decision.status is TraderLabPromotionStatus.NOT_ELIGIBLE_INCOMPLETE


def test_missing_risk_review_blocks_promotion(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    through_mc = MANDATORY_STAGES[: MANDATORY_STAGES.index(TraderLabStage.RISK_REVIEW)]
    lifecycle = _qualify_through(
        lifecycle, candidate, stage_evidence_factory, through_mc
    )
    assert lifecycle.state is TraderLabState.MONTE_CARLO_QUALIFIED
    decision = evaluate_demo_eligibility(
        lifecycle, economic_evidence=_economic_reference()
    )
    assert decision.status is TraderLabPromotionStatus.NOT_ELIGIBLE_INCOMPLETE


def test_demo_eligible_requires_full_chain_and_economic_evidence(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    lifecycle = _qualify_through(
        lifecycle, candidate, stage_evidence_factory, MANDATORY_STAGES
    )
    assert lifecycle.state is TraderLabState.DEMO_ELIGIBLE

    missing_economic = evaluate_demo_eligibility(lifecycle)
    assert (
        missing_economic.status
        is TraderLabPromotionStatus.NOT_ELIGIBLE_MISSING_ECONOMIC_EVIDENCE
    )

    with_economic = evaluate_demo_eligibility(
        lifecycle, economic_evidence=_economic_reference()
    )
    assert with_economic.status is TraderLabPromotionStatus.DEMO_ELIGIBLE
    assert with_economic.reasons == ()


def test_blocked_state_reports_not_eligible_blocked(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    blocked = apply_trader_lab_rejection(
        lifecycle,
        TraderLabRejectionRequest(
            outcome=TraderLabState.REJECTED,
            evidence=_economic_reference(),
            decided_at=_PROCESS_TIME,
        ),
    )
    assert isinstance(blocked, Success)
    decision = evaluate_demo_eligibility(
        blocked.value, economic_evidence=_economic_reference()
    )
    assert decision.status is TraderLabPromotionStatus.NOT_ELIGIBLE_BLOCKED_STATE


def test_canonical_stage_ordering_is_deterministic(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    lifecycle = start_trader_lab_lifecycle(candidate)
    lifecycle = _qualify_through(
        lifecycle, candidate, stage_evidence_factory, MANDATORY_STAGES
    )
    assert lifecycle.completed_stages == MANDATORY_STAGES
    assert MANDATORY_STAGES == (
        TraderLabStage.RESEARCH,
        TraderLabStage.REPLAY,
        TraderLabStage.FAST_FORWARD,
        TraderLabStage.OOS,
        TraderLabStage.STRESS,
        TraderLabStage.MONTE_CARLO,
        TraderLabStage.RISK_REVIEW,
        TraderLabStage.CIBO_REVIEW,
        TraderLabStage.INDEPENDENT_VALIDATION,
    )
