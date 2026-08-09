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
    ResearchCalibrationMappingValidationError,
    ResearchCalibrationMappingVersion,
    ResearchCalibrationTrainingObservation,
    ResearchCalibrationTrainingSet,
    fit_research_confidence_calibration_mapping,
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


def _analysis(suffix: int, confidence: float, *, minutes: int) -> SpecialistAnalysis:
    analysis = object.__new__(SpecialistAnalysis)
    object.__setattr__(analysis, "analysis_id", SpecialistAnalysisId(UUID(int=suffix)))
    object.__setattr__(analysis, "timestamp", _PROCESS_BASE + timedelta(minutes=minutes))
    object.__setattr__(analysis, "kind", SpecialistKind("virtual-trader.fx"))
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
) -> ResearchConfidenceOutcomeObservation:
    return ResearchConfidenceOutcomeObservation(
        analysis=_analysis(suffix, confidence, minutes=minutes),
        target=ResearchCalibrationTarget(_TARGET),
        event_occurred=occurred,
    )


def _run(suffix: int) -> ResearchRunEvidence:
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


def _snapshot() -> ResearchConfidenceCalibrationSnapshot:
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


def _training_set(
    *,
    run: ResearchRunEvidence | None = None,
) -> ResearchCalibrationTrainingSet:
    selected_run = run or _run(1)
    freeze = _freeze(selected_run)
    snapshot = _snapshot()
    observations = tuple(
        ResearchCalibrationTrainingObservation(
            source=source,
            run=selected_run,
            score_observed_at=_MARKET_BASE + timedelta(minutes=10 + index * 20),
            outcome_observed_at=_MARKET_BASE + timedelta(minutes=20 + index * 20),
        )
        for index, source in enumerate(snapshot.observations)
    )
    return ResearchCalibrationTrainingSet(
        snapshot=snapshot,
        evaluation_freeze=freeze,
        fold_number=1,
        observations=observations,
    )


def _policy() -> ResearchCalibrationMappingFitPolicy:
    return ResearchCalibrationMappingFitPolicy(
        methodology=ResearchCalibrationMappingMethodology.ISOTONIC_PAVA,
        version=ResearchCalibrationMappingVersion("1"),
        application_policy=(
            ResearchCalibrationMappingApplicationPolicy.RIGHT_CONTINUOUS_STEP
        ),
        hyperparameters=(),
    )


def test_isotonic_mapping_fit_is_deterministic_and_research_only() -> None:
    training_set = _training_set()
    built = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4001)),
        training_set=training_set,
        policy=_policy(),
        fitted_at=_PROCESS_BASE + timedelta(minutes=1),
    )

    assert isinstance(built, Success)
    fit = built.value
    assert tuple(
        (block.lower_score, block.upper_score, block.estimated_probability, block.sample_size)
        for block in fit.blocks
    ) == (
        (Decimal("0.1"), Decimal("0.1"), Decimal("0"), 1),
        (Decimal("0.3"), Decimal("0.6"), Decimal("0.5"), 2),
        (Decimal("0.9"), Decimal("0.9"), Decimal("1"), 1),
    )
    assert fit.estimate_probability(Decimal("0")) == Decimal("0")
    assert fit.estimate_probability(Decimal("0.3")) == Decimal("0.5")
    assert fit.estimate_probability(Decimal("0.8")) == Decimal("0.5")
    assert fit.estimate_probability(Decimal("1")) == Decimal("1")
    assert fit.run_input_fingerprint == training_set.run_input_fingerprint
    assert fit.software_revision == ResearchSoftwareRevision("rev-1")
    assert fit.specialist_kind == SpecialistKind("virtual-trader.fx")
    assert fit.target == ResearchCalibrationTarget(_TARGET)
    assert not hasattr(fit, "calibrated_probability")
    assert not hasattr(fit, "is_calibrated")
    assert not hasattr(fit, "production_ready")
    assert not hasattr(fit, "capital_authorized")


def test_mapping_fingerprint_excludes_administrative_identity_and_fit_time() -> None:
    training_set = _training_set()
    first = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4101)),
        training_set=training_set,
        policy=_policy(),
        fitted_at=_PROCESS_BASE + timedelta(minutes=1),
    )
    second = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4102)),
        training_set=training_set,
        policy=_policy(),
        fitted_at=_PROCESS_BASE + timedelta(minutes=2),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.fingerprint == second.value.fingerprint


def test_training_set_requires_exact_snapshot_coverage_and_order() -> None:
    valid = _training_set()

    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(valid, observations=valid.observations[:-1])
    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(valid, observations=tuple(reversed(valid.observations)))


def test_training_set_rejects_wrong_run_binding() -> None:
    valid = _training_set()
    wrong_run = _run(2)
    changed = replace(valid.observations[0], run=wrong_run)

    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(valid, observations=(changed, *valid.observations[1:]))


def test_training_set_uses_explicit_simulated_times_not_analysis_timestamp() -> None:
    training_set = _training_set()

    assert all(
        item.source.analysis.timestamp > training_set.training_window.closed_at
        for item in training_set.observations
    )
    assert training_set.training_window.opened_at == _MARKET_BASE


def test_training_observation_rejects_naive_or_reverse_time() -> None:
    run = _run(1)
    source = _snapshot().observations[0]

    with pytest.raises(ResearchCalibrationMappingValidationError):
        ResearchCalibrationTrainingObservation(
            source=source,
            run=run,
            score_observed_at=datetime(2026, 1, 5, 10, 10),
            outcome_observed_at=_MARKET_BASE + timedelta(minutes=20),
        )
    with pytest.raises(ResearchCalibrationMappingValidationError):
        ResearchCalibrationTrainingObservation(
            source=source,
            run=run,
            score_observed_at=_MARKET_BASE + timedelta(minutes=30),
            outcome_observed_at=_MARKET_BASE + timedelta(minutes=20),
        )


def test_training_set_rejects_score_or_outcome_outside_in_sample_window() -> None:
    valid = _training_set()
    window = valid.training_window

    bad_score = replace(valid.observations[0], score_observed_at=window.closed_at)
    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(valid, observations=(bad_score, *valid.observations[1:]))

    bad_outcome = replace(
        valid.observations[-1],
        score_observed_at=window.closed_at - timedelta(minutes=1),
        outcome_observed_at=window.closed_at,
    )
    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(valid, observations=(*valid.observations[:-1], bad_outcome))


def test_isotonic_policy_rejects_hidden_hyperparameters() -> None:
    with pytest.raises(ResearchCalibrationMappingValidationError):
        ResearchCalibrationMappingFitPolicy(
            methodology=ResearchCalibrationMappingMethodology.ISOTONIC_PAVA,
            version=ResearchCalibrationMappingVersion("1"),
            application_policy=(
                ResearchCalibrationMappingApplicationPolicy.RIGHT_CONTINUOUS_STEP
            ),
            hyperparameters=(("smoothing", "0.1"),),
        )


def test_mapping_fit_rejects_block_and_fingerprint_tampering() -> None:
    built = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4201)),
        training_set=_training_set(),
        policy=_policy(),
        fitted_at=_PROCESS_BASE + timedelta(minutes=1),
    )
    assert isinstance(built, Success)

    altered_block = replace(
        built.value.blocks[0],
        estimated_probability=Decimal("0.1"),
    )
    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(built.value, blocks=(altered_block, *built.value.blocks[1:]))
    with pytest.raises(ResearchCalibrationMappingValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="b" * 64),
        )


def test_mapping_fit_rejects_process_time_before_freeze() -> None:
    built = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4301)),
        training_set=_training_set(),
        policy=_policy(),
        fitted_at=_PROCESS_BASE - timedelta(microseconds=1),
    )

    assert isinstance(built, Failure)
    assert "predate" in str(built.error)


def test_mapping_application_rejects_non_decimal_or_out_of_domain_score() -> None:
    built = fit_research_confidence_calibration_mapping(
        mapping_id=ResearchCalibrationMappingId(UUID(int=4401)),
        training_set=_training_set(),
        policy=_policy(),
        fitted_at=_PROCESS_BASE + timedelta(minutes=1),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchCalibrationMappingValidationError):
        built.value.estimate_probability(0.5)  # type: ignore[arg-type]
    with pytest.raises(ResearchCalibrationMappingValidationError):
        built.value.estimate_probability(Decimal("1.01"))
    with pytest.raises(ResearchCalibrationMappingValidationError):
        built.value.estimate_probability(Decimal("NaN"))
