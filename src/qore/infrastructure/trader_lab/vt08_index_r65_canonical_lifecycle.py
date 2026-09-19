"""VT08 Index R65 canonical lifecycle and authority-chain qualification.

R65 consumes the exact R64 canonical economic binding. It does not retune the
R58 strategy and does not claim fresh holdout evidence. Its purpose is to drive
that exact candidate through the canonical Trader Lab lifecycle with real Core
builders and authority modules:

RESEARCH -> REPLAY -> FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO ->
RISK_REVIEW -> CIBO_REVIEW -> INDEPENDENT_VALIDATION -> ECONOMIC_EVIDENCE.

A successful R65 may reach DEMO_ELIGIBLE. Because all economic windows remain
consumed evidence, R65 deliberately does not claim TRADER_CERTIFIED, LIVE,
Production, or real-capital authority. Forward/shadow evidence remains required
for that stronger project-level certification claim.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketIngressSequence,
    RetainedMarketEventObservation,
    derive_market_event_availability_instants,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistributionId,
    ResearchBlockBootstrapPolicy,
    build_research_block_bootstrap_distribution,
)
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidence,
    ResearchEvaluationFreezeEvidenceId,
    build_research_evaluation_freeze_evidence,
)
from qore.infrastructure.research_frozen_oos_evidence import (
    ResearchFrozenOosEvidence,
    ResearchFrozenOosEvidenceId,
    build_research_frozen_oos_evidence,
)
from qore.infrastructure.research_oos_performance import (
    ResearchOosPerformanceEvidenceId,
    build_research_oos_performance_evidence,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.research_resampling_envelope import (
    ResearchResamplingEnvelopeId,
    ResearchResamplingEnvelopePolicy,
    build_research_resampling_envelope,
)
from qore.infrastructure.research_sampling_frame import (
    ResearchSamplingFrameId,
    build_research_sampling_frame,
)
from qore.infrastructure.research_serial_dependence import (
    ResearchSerialDependenceDiagnosticId,
    build_research_serial_dependence_diagnostic,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlan,
    ResearchTemporalEvaluationPlanId,
    ResearchWalkForwardFold,
    build_research_temporal_evaluation_plan,
)
from qore.infrastructure.risk_trader_lab_authority import RiskTraderLabPolicy
from qore.infrastructure.robustness_trader_lab_authority import (
    RobustnessTraderLabPolicy,
    issue_robustness_trader_lab_approval,
    review_trader_lab_candidate_robustness,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r64_canonical_economic_binding as r64,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.infrastructure.trader_lab.cohort_authority import (
    FirstCohortAuthorityInput,
    complete_first_cohort_authority_chain,
)
from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardQualificationId,
    TraderLabFastForwardSchedule,
    TraderLabFastForwardStep,
    qualify_trader_lab_fast_forward,
    reference_trader_lab_fast_forward,
)
from qore.infrastructure.trader_lab.lifecycle import (
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.robustness import (
    TraderLabExperimentId,
    TraderLabMonteCarloEvidenceId,
    TraderLabRobustnessFamily,
    TraderLabThreshold,
    build_trader_lab_experiment_registration,
    build_trader_lab_monte_carlo_experiment_evidence,
    reference_trader_lab_monte_carlo,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    build_trader_lab_stage_evidence,
    reference_replay_chronology,
    reference_research_economic,
    reference_research_evaluation_freeze,
    reference_research_frozen_oos,
)
from qore.infrastructure.traders import vt08_index_specialist_contract as specialist
from qore.kernel.result import Failure

SCHEMA = "qore.trader_lab.vt08_index_r65_canonical_lifecycle.v1"
IDENTITY = "VT08_INDEX_R65_CANONICAL_LIFECYCLE_001"

PLAN_CREATED_AT = datetime(2026, 9, 19, 20, 11, 20, tzinfo=UTC)
POLICY_REGISTERED_AT = datetime(2026, 9, 19, 20, 11, 50, tzinfo=UTC)
FREEZE_ESTABLISHED_AT = datetime(2026, 9, 19, 20, 11, 55, tzinfo=UTC)
OOS_OBSERVED_AT = datetime(2026, 9, 19, 20, 13, 10, tzinfo=UTC)
OOS_CERTIFIED_AT = datetime(2026, 9, 19, 20, 13, 20, tzinfo=UTC)

RESEARCH_AT = datetime(2026, 9, 19, 20, 13, 30, tzinfo=UTC)
REPLAY_AT = datetime(2026, 9, 19, 20, 13, 40, tzinfo=UTC)
FAST_FORWARD_AT = datetime(2026, 9, 19, 20, 13, 50, tzinfo=UTC)
OOS_AT = datetime(2026, 9, 19, 20, 14, 0, tzinfo=UTC)
STRESS_AT = datetime(2026, 9, 19, 20, 15, 0, tzinfo=UTC)
MONTE_CARLO_AT = datetime(2026, 9, 19, 20, 16, 0, tzinfo=UTC)
RISK_AT = datetime(2026, 9, 19, 20, 17, 0, tzinfo=UTC)
CIBO_AT = datetime(2026, 9, 19, 20, 18, 0, tzinfo=UTC)
INDEPENDENT_AT = datetime(2026, 9, 19, 20, 19, 0, tzinfo=UTC)

BOOTSTRAP_BLOCK_LENGTH = 5
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20_260_919
MIN_CANONICAL_SAMPLE = 1_000

_REPLAY_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77700000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("77700000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt08-index-r65"),
)


def _uid(namespace: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"qore:vt08-index:r65:{specialist.CONFIG_FINGERPRINT}:{namespace}",
    )


def _promote(
    lifecycle: TraderLabLifecycle,
    *,
    stage: TraderLabStage,
    reference: TraderLabEvidenceReference,
    produced_at: datetime,
) -> TraderLabLifecycle:
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            _uid(f"stage:{stage.value}:{produced_at.isoformat()}")
        ),
        stage=stage,
        candidate=lifecycle.candidate,
        source_reference=reference,
        produced_at=produced_at,
    )
    if isinstance(built, Failure):
        raise ValueError(f"R65 {stage.value} evidence failed: {built.error}")
    promoted = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=stage, evidence=built.value),
    )
    if isinstance(promoted, Failure):
        raise ValueError(f"R65 {stage.value} promotion failed: {promoted.error}")
    return promoted.value


def _temporal_plan(
    candidate: TraderLabCandidateBinding,
    performance: ResearchPerformanceStatisticsSnapshot,
) -> ResearchTemporalEvaluationPlan:
    run = candidate.strategy_binding.run
    observations = performance.observations
    valued = tuple(
        sorted(item.source_result.valued_at.astimezone(UTC) for item in observations)
    )
    first_oos = valued[0]
    split = datetime(2024, 1, 1, tzinfo=UTC)
    if first_oos <= run.simulated_start:
        raise ValueError("R65 requires pre-OOS context before first retained return")
    if not first_oos < split < run.simulated_end:
        raise ValueError("R65 temporal split is outside the canonical run")

    plan = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uid("temporal-plan")),
        run=run,
        folds=(
            ResearchWalkForwardFold(
                fold_number=1,
                in_sample=ResearchEvaluationWindow(
                    run.simulated_start,
                    first_oos,
                ),
                out_of_sample=ResearchEvaluationWindow(
                    first_oos,
                    split,
                ),
            ),
            ResearchWalkForwardFold(
                fold_number=2,
                in_sample=ResearchEvaluationWindow(
                    first_oos,
                    split,
                ),
                out_of_sample=ResearchEvaluationWindow(
                    split,
                    run.simulated_end,
                ),
            ),
        ),
        created_at=PLAN_CREATED_AT,
    )
    if isinstance(plan, Failure):
        raise ValueError(f"R65 temporal plan failed: {plan.error}")
    return plan.value


def _frozen_oos(
    candidate: TraderLabCandidateBinding,
    performance: ResearchPerformanceStatisticsSnapshot,
) -> tuple[ResearchEvaluationFreezeEvidence, ResearchFrozenOosEvidence]:
    plan = _temporal_plan(candidate, performance)
    freeze = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(
            _uid("evaluation-freeze")
        ),
        strategy_binding=candidate.strategy_binding,
        plan=plan,
        established_at=FREEZE_ESTABLISHED_AT,
    )
    if isinstance(freeze, Failure):
        raise ValueError(f"R65 evaluation freeze failed: {freeze.error}")

    oos = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uid("oos-performance")),
        plan=plan,
        observations=performance.observations,
        statistics_snapshot_ids=(
            ResearchPerformanceSnapshotId(_uid("oos-stats:1")),
            ResearchPerformanceSnapshotId(_uid("oos-stats:2")),
        ),
        observed_at=OOS_OBSERVED_AT,
    )
    if isinstance(oos, Failure):
        raise ValueError(f"R65 OOS evidence failed: {oos.error}")

    frozen = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uid("frozen-oos")),
        evaluation_freeze=freeze.value,
        oos_performance=oos.value,
        certified_at=OOS_CERTIFIED_AT,
    )
    if isinstance(frozen, Failure):
        raise ValueError(f"R65 frozen OOS failed: {frozen.error}")
    return freeze.value, frozen.value


def _replay_events(
    performance: ResearchPerformanceStatisticsSnapshot,
) -> tuple[RetainedMarketEventObservation, ...]:
    events: list[RetainedMarketEventObservation] = []
    lineage_id = MarketCaptureLineageId(_uid("capture-lineage"))
    session_id = MarketCaptureSessionId(_uid("capture-session"))

    ordered = tuple(
        sorted(
            performance.observations,
            key=lambda item: (
                item.source_result.valued_at.astimezone(UTC),
                str(item.observation_id.value),
            ),
        )
    )
    for index, observation in enumerate(ordered):
        valued_at = observation.source_result.valued_at.astimezone(UTC)
        boundary = valued_at + timedelta(seconds=1)
        ingress = boundary + timedelta(milliseconds=1)
        quote = QualifiedQuoteTickObservation(
            observation_id=MarketObservationId(
                _uid(f"replay-quote:{index}")
            ),
            instrument=Instrument(specialist.PORTFOLIO_INSTRUMENT),
            source=_REPLAY_SOURCE,
            observed_at=valued_at,
            bid=MarketPrice(Decimal("1")),
            ask=MarketPrice(Decimal("1.0001")),
            evidence_ref=MarketObservationEvidenceReference(
                _uid(f"replay-quote-ref:{index}")
            ),
        )
        events.append(
            RetainedMarketEventObservation(
                event_id=MarketEventObservationId(
                    _uid(f"replay-event:{index}")
                ),
                payload=quote,
                capture_lineage_id=lineage_id,
                capture_session_id=session_id,
                capture_session_ordinal=MarketCaptureSessionOrdinal(0),
                ingress_sequence=MarketIngressSequence(index),
                boundary_received_at=boundary,
                core_ingress_at=ingress,
                availability_evidence_at=ingress,
                available_at=ingress,
                availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
                availability_evidence_ref=(
                    MarketEventAvailabilityEvidenceReference(
                        _uid(f"replay-availability:{index}")
                    )
                ),
            )
        )
    return tuple(events)


def _fast_forward_reference(
    candidate: TraderLabCandidateBinding,
    events: tuple[RetainedMarketEventObservation, ...],
) -> TraderLabEvidenceReference:
    instants = derive_market_event_availability_instants(events)
    if len(instants) < 2:
        raise ValueError("R65 fast-forward requires at least two instants")
    base = instants[-1] - instants[0]
    compressed = base / 2
    schedule = TraderLabFastForwardSchedule(
        steps=tuple(
            TraderLabFastForwardStep(
                simulated_now=instant,
                wall_clock_advance=(
                    compressed if index == 0 else timedelta(0)
                ),
            )
            for index, instant in enumerate(instants)
        ),
        acceleration_factor=2,
    )
    qualified = qualify_trader_lab_fast_forward(
        qualification_id=TraderLabFastForwardQualificationId(
            _uid("fast-forward")
        ),
        candidate=candidate,
        schedule=schedule,
        observations=events,
        certified_at=FAST_FORWARD_AT,
    )
    if isinstance(qualified, Failure):
        raise ValueError(f"R65 fast-forward failed: {qualified.error}")
    return reference_trader_lab_fast_forward(
        candidate,
        qualified.value,
        observations=events,
    )


def _stress_reference(
    lifecycle: TraderLabLifecycle,
    performance: ResearchPerformanceStatisticsSnapshot,
) -> tuple[TraderLabEvidenceReference, dict[str, str]]:
    policy = RobustnessTraderLabPolicy(
        policy_id="vt08-index-r65-secondary-stress",
        scenario="secondary-plus-extra-cost",
        return_haircut=Decimal("0.001"),
        min_sample_size=MIN_CANONICAL_SAMPLE,
        min_stressed_mean_return=Decimal("0"),
        max_stressed_population_variance=Decimal("0.02"),
        registered_at=POLICY_REGISTERED_AT,
    )
    review = review_trader_lab_candidate_robustness(
        lifecycle,
        performance,
        policy=policy,
        reviewed_at=STRESS_AT,
    )
    if isinstance(review, Failure):
        raise ValueError(f"R65 robustness review failed: {review.error}")
    issuance = issue_robustness_trader_lab_approval(review.value)
    if isinstance(issuance, Failure):
        raise ValueError(f"R65 robustness issuance failed: {issuance.error}")
    return issuance.value.reference, {
        "decision": review.value.decision.value,
        "stressed_mean_return": str(review.value.stressed_mean_return),
        "stressed_population_variance": str(
            review.value.stressed_population_variance
        ),
    }


def _monte_carlo_reference(
    candidate: TraderLabCandidateBinding,
    frozen_oos: ResearchFrozenOosEvidence,
) -> tuple[TraderLabEvidenceReference, dict[str, str | int | bool]]:
    frame = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uid("sampling-frame")),
        frozen_oos=frozen_oos,
    )
    if isinstance(frame, Failure):
        raise ValueError(f"R65 sampling frame failed: {frame.error}")

    diagnostic = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(
            _uid("serial-diagnostic")
        ),
        frame=frame.value,
    )
    if isinstance(diagnostic, Failure):
        raise ValueError(f"R65 serial diagnostic failed: {diagnostic.error}")

    policy = ResearchBlockBootstrapPolicy(
        block_length=BOOTSTRAP_BLOCK_LENGTH,
        resample_count=BOOTSTRAP_RESAMPLES,
        seed=BOOTSTRAP_SEED,
    )
    distribution = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(
            _uid("bootstrap-distribution")
        ),
        diagnostic=diagnostic.value,
        policy=policy,
    )
    if isinstance(distribution, Failure):
        raise ValueError(f"R65 bootstrap failed: {distribution.error}")

    envelope = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(
            _uid("resampling-envelope")
        ),
        distribution=distribution.value,
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=500,
            upper_quantile_bps=9500,
        ),
    )
    if isinstance(envelope, Failure):
        raise ValueError(f"R65 envelope failed: {envelope.error}")

    registration = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uid("mc-registration")),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=BOOTSTRAP_BLOCK_LENGTH,
        seed=BOOTSTRAP_SEED,
        simulation_count=BOOTSTRAP_RESAMPLES,
        min_sample_size=MIN_CANONICAL_SAMPLE,
        thresholds=(
            TraderLabThreshold(
                "envelope.lower_mean",
                Decimal("0"),
                None,
            ),
        ),
        registered_at=POLICY_REGISTERED_AT,
    )
    if isinstance(registration, Failure):
        raise ValueError(f"R65 MC registration failed: {registration.error}")

    evidence = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uid("mc-evidence")),
        registration=registration.value,
        policy=policy,
        distribution=distribution.value,
        envelope=envelope.value,
    )
    if isinstance(evidence, Failure):
        raise ValueError(f"R65 MC evidence failed: {evidence.error}")
    reference = reference_trader_lab_monte_carlo(candidate, evidence.value)
    return reference, {
        "status": evidence.value.status.value,
        "sample_size": distribution.value.sample_size,
        "source_mean": str(distribution.value.source_mean),
        "lower_mean": str(envelope.value.lower_mean),
        "median_mean": str(envelope.value.median_mean),
        "upper_mean": str(envelope.value.upper_mean),
        "contains_zero": envelope.value.contains_zero,
        "lag_one_status": diagnostic.value.status.value,
        "overlap_status": frame.value.overlap_status.value,
        "overlapping_pairs": len(frame.value.overlapping_pairs),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    candidate, performance, r64_details = r64.build_binding(
        nas100_root=nas100_root,
        sp500_root=sp500_root,
        us30_root=us30_root,
    )
    evaluation_freeze, frozen_oos = _frozen_oos(candidate, performance)
    events = _replay_events(performance)

    lifecycle = start_trader_lab_lifecycle(candidate)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.RESEARCH,
        reference=reference_research_evaluation_freeze(
            candidate,
            evaluation_freeze,
        ),
        produced_at=RESEARCH_AT,
    )
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.REPLAY,
        reference=reference_replay_chronology(events),
        produced_at=REPLAY_AT,
    )
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.FAST_FORWARD,
        reference=_fast_forward_reference(candidate, events),
        produced_at=FAST_FORWARD_AT,
    )
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.OOS,
        reference=reference_research_frozen_oos(candidate, frozen_oos),
        produced_at=OOS_AT,
    )

    stress_reference, stress = _stress_reference(lifecycle, performance)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.STRESS,
        reference=stress_reference,
        produced_at=STRESS_AT,
    )

    monte_reference, monte = _monte_carlo_reference(candidate, frozen_oos)
    lifecycle = _promote(
        lifecycle,
        stage=TraderLabStage.MONTE_CARLO,
        reference=monte_reference,
        produced_at=MONTE_CARLO_AT,
    )

    economic_reference = reference_research_economic(
        candidate,
        performance.observations[-1],
    )
    authority = complete_first_cohort_authority_chain(
        FirstCohortAuthorityInput(
            lifecycle=lifecycle,
            performance=performance,
            economic_evidence=economic_reference,
            qualified_timeframes=specialist.TIMEFRAMES,
            risk_policy=RiskTraderLabPolicy(
                policy_id="vt08-index-r65-risk",
                min_sample_size=MIN_CANONICAL_SAMPLE,
                max_population_variance=Decimal("0.02"),
            ),
            risk_reviewed_at=RISK_AT,
            cibo_reviewed_at=CIBO_AT,
            independent_validated_at=INDEPENDENT_AT,
        )
    )
    if isinstance(authority, Failure):
        raise ValueError(f"R65 authority chain failed: {authority.error}")
    entry = authority.value
    final_lifecycle = entry.lifecycle
    if final_lifecycle.state is not TraderLabState.DEMO_ELIGIBLE:
        raise ValueError("R65 authority chain did not reach DEMO_ELIGIBLE")

    cibo_qualification = next(
        item
        for item in final_lifecycle.qualifications
        if item.stage is TraderLabStage.CIBO_REVIEW
    )
    independent_qualification = next(
        item
        for item in final_lifecycle.qualifications
        if item.stage is TraderLabStage.INDEPENDENT_VALIDATION
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "source_candidate_id": specialist.CANDIDATE_ID,
            "config_fingerprint": specialist.CONFIG_FINGERPRINT,
            "candidate_fingerprint": candidate.fingerprint.value,
            "strategy_binding_fingerprint": (
                candidate.strategy_binding.binding_fingerprint.value
            ),
        },
        "r64_reconciliation": {
            "combined_sample": r64_details["combined_sample"],
            "total_r": r64_details["total_r"],
            "expected_total_r": r64_details["expected_total_r"],
            "exact_match": (
                r64_details["total_r"] == r64_details["expected_total_r"]
            ),
        },
        "lifecycle": {
            "state": final_lifecycle.state.value,
            "completed_stages": [
                stage.value for stage in final_lifecycle.completed_stages
            ],
            "replay_event_count": len(events),
            "replay_scope": "all-retained-closed-economic-result-events",
            "raw_bar_replay_completeness_claim": False,
        },
        "stress": stress,
        "monte_carlo": monte,
        "risk": {
            "policy_id": "vt08-index-r65-risk",
            "min_sample_size": MIN_CANONICAL_SAMPLE,
            "max_population_variance": "0.02",
        },
        "cibo": {
            "qualified_markets": list(specialist.MARKETS),
            "qualified_timeframes": list(specialist.TIMEFRAMES),
            "stage_reference_digest": (
                cibo_qualification.evidence.source_reference.content_digest.value
            ),
        },
        "independent_validation": {
            "stage_reference_digest": (
                independent_qualification.evidence.source_reference.content_digest.value
            ),
        },
        "decision": "PASS_R65_DEMO_ELIGIBLE_FORWARD_VALIDATION_REQUIRED",
        "governance": {
            "demo_eligible": True,
            "trader_certified": False,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "forward_shadow_validation_required": True,
            "candidate_retuned": False,
            "signals_suppressed": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "decision": report["decision"],
                "lifecycle": report["lifecycle"],
                "stress": report["stress"],
                "monte_carlo": report["monte_carlo"],
                "governance": report["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
