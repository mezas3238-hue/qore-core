from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration import (
    ResearchCalibrationTarget,
    ResearchConfidenceCalibrationPolicy,
    ResearchConfidenceCalibrationSnapshot,
    ResearchConfidenceOutcomeObservation,
    build_research_confidence_calibration_snapshot,
)
from qore.infrastructure.research_confidence_calibration_mapping import (
    ResearchCalibrationMappingApplicationPolicy,
    ResearchCalibrationMappingFitPolicy,
    ResearchCalibrationMappingId,
    ResearchCalibrationMappingMethodology,
    ResearchCalibrationMappingVersion,
    ResearchCalibrationTrainingObservation,
    ResearchCalibrationTrainingSet,
    ResearchConfidenceCalibrationMappingFit,
    fit_research_confidence_calibration_mapping,
)
from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationError,
    ResearchCalibrationOosValidationId,
    ResearchCalibrationOosValidationObservation,
    ResearchCalibrationOosValidationPolicy,
    ResearchCalibrationOosValidationSet,
    build_research_calibration_oos_validation_evidence,
)
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidence,
    ResearchEvaluationFreezeEvidenceId,
    ResearchEvaluationFreezeFingerprint,
)
from qore.infrastructure.research_run import (
    ResearchRunEvidence,
    ResearchRunId,
    ResearchRunInputFingerprint,
    ResearchSoftwareRevision,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlan,
    ResearchTemporalEvaluationPlanId,
    ResearchWalkForwardFold,
)
from qore.kernel.result import Failure, Success
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
)

_MARKET_BASE = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
_PROCESS_BASE = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)
_TARGET = "next-period-positive-return"
_KIND = "virtual-trader.fx"


def _analysis(
    suffix: int,
    confidence: float,
    *,
    minutes: int,
    kind: str = _KIND,
) -> SpecialistAnalysis:
    analysis = object.__new__(SpecialistAnalysis)
    object.__setattr__(analysis, "analysis_id", SpecialistAnalysisId(UUID(int=suffix)))
    object.__setattr__(analysis, "timestamp", _PROCESS_BASE + timedelta(minutes=minutes))
    object.__setattr__(analysis, "kind", SpecialistKind(kind))
    object.__setattr__(analysis, "status", SpecialistAnalysisStatus.COMPLETED)
    object.__setattr__(analysis, "confidence", SpecialistConfidence(confidence))
    object.__setattr__(analysis, "metadata", None)
    object.__setattr__(analysis, "reasons", ())
    return analysis


def _source(
    suffix: int,
    confidence: float,
    occurred: bool,
    *,
    minutes: int,
    target: str = _TARGET,
    kind: str = _KIND,
) -> ResearchConfidenceOutcomeObservation:
    return ResearchConfidenceOutcomeObservation(
        analysis=_analysis(suffix, confidence, minutes=minutes, kind=kind),
        target=ResearchCalibrationTarget(target),
        event_occurred=occurred,
    )


def _run(suffix: int = 1) -> ResearchRunEvidence:
    run = object.__new__(ResearchRunEvidence)
    object.__setattr__(run, "run_id", ResearchRunId(UUID(int=1000 + suffix)))
    object.__setattr__(
        run,
        "input_fingerprint",
        ResearchRunInputFingerprint(f"{suffix:064x}"),
    )
    object.__setattr__(run, "software_revision", ResearchSoftwareRevision(f"rev-{suffix}"))
    return run


def _freeze(run: ResearchRunEvidence) -> ResearchEvaluationFreezeEvidence:
    fold = ResearchWalkForwardFold(
        fold_number=1,
        in_sample=ResearchEvaluationWindow(
            opened_at=_MARKET_BASE,
            closed_at=_MARKET_BASE + timedelta(hours=4),
        ),
        out_of_sample=ResearchEvaluationWindow(
            opened_at=_MARKET_BASE + timedelta(hours=4),
            closed_at=_MARKET_BASE + timedelta(hours=8),
        ),
    )
    plan = object.__new__(ResearchTemporalEvaluationPlan)
    object.__setattr__(plan, "plan_id", ResearchTemporalEvaluationPlanId(UUID(int=2001)))
    object.__setattr__(plan, "run", run)
    object.__setattr__(plan, "folds", (fold,))
    freeze = object.__new__(ResearchEvaluationFreezeEvidence)
    object.__setattr__(
        freeze,
        "evidence_id",
        ResearchEvaluationFreezeEvidenceId(UUID(int=3001)),
    )
    object.__setattr__(
        freeze,
        "fingerprint",
        ResearchEvaluationFreezeFingerprint("a" * 64),
    )
    object.__setattr__(freeze, "plan", plan)
    object.__setattr__(freeze, "established_at", _PROCESS_BASE)
    return freeze


def _training_snapshot() -> ResearchConfidenceCalibrationSnapshot:
    built = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=4),
        observations=(
            _source(1, 0.1, False, minutes=1),
            _source(2, 0.3, True, minutes=2),
            _source(3, 0.6, False, minutes=3),
            _source(4, 0.9, True, minutes=4),
        ),
    )
    assert isinstance(built, Success)
    return built.value


def _mapping_fit(*, run: ResearchRunEvidence | None = None) -> ResearchConfidenceCalibrationMappingFit:
    selected_run = run or _run()
    freeze = _freeze(selected_run)
    snapshot = _training_snapshot()
    training_observations = tuple(
        ResearchCalibrationTrainingObservation(
            source=source,
            run=selected_run,
            score_observed_at=_MARKET_BASE + timedelta(minutes=10 + index * 20),
            outcome_observed_at=_MARKET_BASE + timedelta(minutes=20 + index * 20),
        )
        for index, source in enumerate(snapshot.observations)
    )
    training_set = ResearchCalibrationTrainingSet(
        snapshot=snapshot,
        evaluation_freeze=freeze,
        fold_number=1,
        observations=training_observations,
    )
    policy = ResearchCalibrationMappingFitPolicy(
        methodology=ResearchCalibrationMappingMethodology.ISOTONIC_PAVA,
        version=ResearchCalibrationMappingVersion("1"),
        application_policy=(
            ResearchCalibrationMappingApplicationPolicy.RIGHT_CONTINUOUS_STEP
        ),
        hyperparameters=(),
    )
    built = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4001)),
        training_set=training_set,
        policy=policy,
        fitted_at=_PROCESS_BASE + timedelta(minutes=1),
    )
    assert isinstance(built, Success)
    return built.value


def _validation_observation(
    fit: ResearchConfidenceCalibrationMappingFit,
    *,
    suffix: int,
    confidence: float,
    occurred: bool,
    market_minutes: int,
    recorded_minutes: int,
    target: str = _TARGET,
    kind: str = _KIND,
    run: ResearchRunEvidence | None = None,
) -> ResearchCalibrationOosValidationObservation:
    return ResearchCalibrationOosValidationObservation(
        source=_source(
            suffix,
            confidence,
            occurred,
            minutes=100 + suffix,
            target=target,
            kind=kind,
        ),
        run=run or fit.training_set.evaluation_freeze.plan.run,
        score_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=market_minutes),
        outcome_observed_at=_MARKET_BASE + timedelta(
            hours=4,
            minutes=market_minutes + 5,
        ),
        recorded_at=_PROCESS_BASE + timedelta(minutes=recorded_minutes),
    )


def _validation_set(
    fit: ResearchConfidenceCalibrationMappingFit | None = None,
) -> ResearchCalibrationOosValidationSet:
    selected_fit = fit or _mapping_fit()
    observations = (
        _validation_observation(
            selected_fit,
            suffix=11,
            confidence=0.2,
            occurred=True,
            market_minutes=10,
            recorded_minutes=2,
        ),
        _validation_observation(
            selected_fit,
            suffix=12,
            confidence=0.4,
            occurred=True,
            market_minutes=30,
            recorded_minutes=3,
        ),
        _validation_observation(
            selected_fit,
            suffix=13,
            confidence=0.8,
            occurred=False,
            market_minutes=50,
            recorded_minutes=4,
        ),
        _validation_observation(
            selected_fit,
            suffix=14,
            confidence=0.95,
            occurred=False,
            market_minutes=70,
            recorded_minutes=5,
        ),
    )
    return ResearchCalibrationOosValidationSet(
        mapping_fit=selected_fit,
        fold_number=1,
        observations=observations,
    )


def test_oos_validation_reports_mapping_probability_diagnostics_without_authority() -> None:
    validation_set = _validation_set()
    built = build_research_calibration_oos_validation_evidence(
        validation_id=ResearchCalibrationOosValidationId(UUID(int=5001)),
        validation_set=validation_set,
        policy=ResearchCalibrationOosValidationPolicy(bin_count=4),
        validated_at=_PROCESS_BASE + timedelta(minutes=6),
    )

    assert isinstance(built, Success)
    evidence = built.value
    assert evidence.sample_size == 4
    assert evidence.mean_estimated_probability == Decimal("0.5")
    assert evidence.empirical_event_rate == Decimal("0.5")
    assert evidence.brier_score == Decimal("0.625")
    assert evidence.expected_calibration_error == Decimal("0.5")
    assert tuple(
        (
            item.index,
            item.sample_size,
            item.mean_estimated_probability,
            item.empirical_event_rate,
            item.absolute_gap,
        )
        for item in evidence.bins
    ) == (
        (0, 1, Decimal("0"), Decimal("1"), Decimal("1")),
        (2, 2, Decimal("0.5"), Decimal("0.5"), Decimal("0.0")),
        (3, 1, Decimal("1"), Decimal("0"), Decimal("1")),
    )
    assert evidence.target == ResearchCalibrationTarget(_TARGET)
    assert evidence.specialist_kind == SpecialistKind(_KIND)
    assert evidence.run_input_fingerprint == validation_set.run_input_fingerprint
    assert evidence.software_revision == ResearchSoftwareRevision("rev-1")
    assert not hasattr(evidence, "calibrated_probability")
    assert not hasattr(evidence, "is_calibrated")
    assert not hasattr(evidence, "strategy_approved")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")


def test_oos_validation_fingerprint_excludes_admin_id_and_validation_time() -> None:
    validation_set = _validation_set()
    first = build_research_calibration_oos_validation_evidence(
        validation_id=ResearchCalibrationOosValidationId(UUID(int=5101)),
        validation_set=validation_set,
        policy=ResearchCalibrationOosValidationPolicy(bin_count=4),
        validated_at=_PROCESS_BASE + timedelta(minutes=6),
    )
    second = build_research_calibration_oos_validation_evidence(
        validation_id=ResearchCalibrationOosValidationId(UUID(int=5102)),
        validation_set=validation_set,
        policy=ResearchCalibrationOosValidationPolicy(bin_count=4),
        validated_at=_PROCESS_BASE + timedelta(minutes=7),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.fingerprint == second.value.fingerprint


def test_oos_validation_rejects_fit_data_reuse() -> None:
    fit = _mapping_fit()
    valid = _validation_set(fit)
    reused = ResearchCalibrationOosValidationObservation(
        source=fit.training_set.observations[0].source,
        run=fit.training_set.evaluation_freeze.plan.run,
        score_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=5),
        outcome_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=6),
        recorded_at=_PROCESS_BASE + timedelta(minutes=2),
    )

    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(reused, *valid.observations[1:]))


def test_oos_validation_rejects_wrong_target_or_specialist_kind() -> None:
    fit = _mapping_fit()
    valid = _validation_set(fit)
    wrong_target = _validation_observation(
        fit,
        suffix=11,
        confidence=0.2,
        occurred=True,
        market_minutes=10,
        recorded_minutes=2,
        target="different-target",
    )
    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(wrong_target, *valid.observations[1:]))

    wrong_kind = _validation_observation(
        fit,
        suffix=11,
        confidence=0.2,
        occurred=True,
        market_minutes=10,
        recorded_minutes=2,
        kind="virtual-trader.equity",
    )
    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(wrong_kind, *valid.observations[1:]))


def test_oos_validation_rejects_wrong_run_binding() -> None:
    fit = _mapping_fit()
    valid = _validation_set(fit)
    wrong = replace(valid.observations[0], run=_run(2))

    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(wrong, *valid.observations[1:]))


def test_oos_validation_rejects_noncanonical_or_duplicate_observations() -> None:
    valid = _validation_set()

    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=tuple(reversed(valid.observations)))
    duplicate = replace(valid.observations[1], source=valid.observations[0].source)
    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(valid.observations[0], duplicate, *valid.observations[2:]))


def test_oos_validation_separates_simulated_window_from_process_record_time() -> None:
    fit = _mapping_fit()
    valid = _validation_set(fit)
    window = valid.validation_window

    assert all(
        window.opened_at <= item.score_observed_at < window.closed_at
        for item in valid.observations
    )
    assert all(item.recorded_at >= fit.fitted_at for item in valid.observations)
    assert all(item.source.analysis.timestamp > window.closed_at for item in valid.observations)


def test_oos_validation_rejects_out_of_window_and_pre_fit_record() -> None:
    fit = _mapping_fit()
    valid = _validation_set(fit)
    window = valid.validation_window

    outside = replace(
        valid.observations[-1],
        score_observed_at=window.closed_at,
        outcome_observed_at=window.closed_at,
    )
    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(*valid.observations[:-1], outside))

    pre_fit = replace(
        valid.observations[0],
        recorded_at=fit.fitted_at - timedelta(microseconds=1),
    )
    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(valid, observations=(pre_fit, *valid.observations[1:]))


def test_oos_validation_observation_rejects_naive_or_reverse_times() -> None:
    fit = _mapping_fit()
    source = _source(21, 0.5, True, minutes=121)
    run = fit.training_set.evaluation_freeze.plan.run

    with pytest.raises(ResearchCalibrationOosValidationError):
        ResearchCalibrationOosValidationObservation(
            source=source,
            run=run,
            score_observed_at=datetime(2026, 1, 5, 14, 10),
            outcome_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=20),
            recorded_at=_PROCESS_BASE + timedelta(minutes=2),
        )
    with pytest.raises(ResearchCalibrationOosValidationError):
        ResearchCalibrationOosValidationObservation(
            source=source,
            run=run,
            score_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=20),
            outcome_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=10),
            recorded_at=_PROCESS_BASE + timedelta(minutes=2),
        )
    with pytest.raises(ResearchCalibrationOosValidationError):
        ResearchCalibrationOosValidationObservation(
            source=source,
            run=run,
            score_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=10),
            outcome_observed_at=_MARKET_BASE + timedelta(hours=4, minutes=20),
            recorded_at=datetime(2026, 8, 9, 20, 2),
        )


def test_oos_validation_rejects_metric_and_fingerprint_tampering() -> None:
    built = build_research_calibration_oos_validation_evidence(
        validation_id=ResearchCalibrationOosValidationId(UUID(int=5201)),
        validation_set=_validation_set(),
        policy=ResearchCalibrationOosValidationPolicy(bin_count=4),
        validated_at=_PROCESS_BASE + timedelta(minutes=6),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(built.value, brier_score=Decimal("0.1"))
    with pytest.raises(ResearchCalibrationOosValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="b" * 64),
        )


def test_oos_validation_rejects_validation_time_before_latest_record() -> None:
    validation_set = _validation_set()
    built = build_research_calibration_oos_validation_evidence(
        validation_id=ResearchCalibrationOosValidationId(UUID(int=5301)),
        validation_set=validation_set,
        policy=ResearchCalibrationOosValidationPolicy(bin_count=4),
        validated_at=_PROCESS_BASE + timedelta(minutes=4),
    )

    assert isinstance(built, Failure)
    assert "predate" in str(built.error)


def test_oos_validation_policy_requires_bounded_integer_bin_count() -> None:
    for value in (1, 101, 2.0):
        with pytest.raises(ResearchCalibrationOosValidationError):
            ResearchCalibrationOosValidationPolicy(bin_count=value)  # type: ignore[arg-type]
