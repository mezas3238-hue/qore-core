from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure import research_frozen_oos_evidence as frozen_module
from qore.infrastructure.research_economic_evidence import ResearchReturnBasis
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidence,
)
from qore.infrastructure.research_frozen_oos_evidence import (
    ResearchFrozenOosEvidenceId,
    ResearchFrozenOosEvidenceValidationError,
    ResearchFrozenOosFingerprint,
    build_research_frozen_oos_evidence,
    compute_research_frozen_oos_fingerprint,
)
from qore.infrastructure.research_oos_performance import (
    ResearchOosFoldPerformance,
    ResearchOosPerformanceEvidence,
    ResearchOosPerformanceEvidenceId,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.research_temporal_evaluation import ResearchTemporalEvaluationPlan
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"73000000-0000-0000-0000-{suffix:012d}")


def _plan(run: object, *, suffix: int = 1) -> ResearchTemporalEvaluationPlan:
    plan = object.__new__(ResearchTemporalEvaluationPlan)
    object.__setattr__(plan, "plan_id", suffix)
    object.__setattr__(plan, "run", run)
    object.__setattr__(plan, "folds", ())
    object.__setattr__(plan, "created_at", _BASE - timedelta(minutes=2))
    return plan


def _strategy_binding(run: object) -> ResearchRunStrategyBinding:
    binding = object.__new__(ResearchRunStrategyBinding)
    object.__setattr__(binding, "run", run)
    object.__setattr__(binding, "manifest", object())
    object.__setattr__(binding, "binding_fingerprint", object())
    return binding


def _evaluation_freeze(
    plan: ResearchTemporalEvaluationPlan,
    run: object,
    *,
    established_at: datetime = _BASE - timedelta(minutes=1),
) -> ResearchEvaluationFreezeEvidence:
    evidence = object.__new__(ResearchEvaluationFreezeEvidence)
    object.__setattr__(evidence, "evidence_id", _uuid(10))
    object.__setattr__(evidence, "strategy_binding", _strategy_binding(run))
    object.__setattr__(evidence, "plan", plan)
    object.__setattr__(evidence, "established_at", established_at)
    object.__setattr__(evidence, "fingerprint", object())
    return evidence


def _oos_performance(
    plan: ResearchTemporalEvaluationPlan,
    *,
    observed_at: datetime = _BASE,
) -> ResearchOosPerformanceEvidence:
    evidence = object.__new__(ResearchOosPerformanceEvidence)
    object.__setattr__(evidence, "evidence_id", _uuid(20))
    object.__setattr__(evidence, "plan", plan)
    object.__setattr__(evidence, "basis", object())
    object.__setattr__(evidence, "fold_performance", ())
    object.__setattr__(evidence, "observed_at", observed_at)
    return evidence


def _patch_logical_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ResearchEvaluationFreezeEvidence,
        "logical_values",
        lambda self: ("freeze", self.established_at.isoformat()),
    )
    monkeypatch.setattr(
        ResearchOosPerformanceEvidence,
        "logical_values",
        lambda self: ("oos", self.observed_at.isoformat()),
    )


def test_frozen_oos_evidence_composes_exact_plan_and_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_logical_values(monkeypatch)
    run = object()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(plan, run)
    oos = _oos_performance(plan)

    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(100)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
        certified_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(built, Success)
    assert built.value.evaluation_freeze is evaluation_freeze
    assert built.value.oos_performance is oos
    assert built.value.fingerprint == compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )


def test_frozen_oos_evidence_rejects_temporal_plan_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_logical_values(monkeypatch)
    run = object()
    frozen_plan = _plan(run, suffix=1)
    substituted_plan = _plan(run, suffix=2)

    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(200)),
        evaluation_freeze=_evaluation_freeze(frozen_plan, run),
        oos_performance=_oos_performance(substituted_plan),
        certified_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(built, Failure)
    assert "exact frozen temporal evaluation plan" in str(built.error)


def test_frozen_oos_evidence_rejects_cross_run_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_logical_values(monkeypatch)
    plan_run = object()
    binding_run = object()
    plan = _plan(plan_run)

    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(300)),
        evaluation_freeze=_evaluation_freeze(plan, binding_run),
        oos_performance=_oos_performance(plan),
        certified_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(built, Failure)
    assert "within one research run" in str(built.error)


def test_frozen_oos_evidence_enforces_process_evidence_chronology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_logical_values(monkeypatch)
    run = object()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(plan, run, established_at=_BASE)
    early_oos = _oos_performance(plan, observed_at=_BASE - timedelta(seconds=1))

    before_freeze = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(400)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=early_oos,
        certified_at=_BASE + timedelta(seconds=1),
    )
    assert isinstance(before_freeze, Failure)
    assert "must not predate evaluation freeze" in str(before_freeze.error)

    valid_oos = _oos_performance(plan, observed_at=_BASE + timedelta(seconds=1))
    early_certification = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(401)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=valid_oos,
        certified_at=_BASE,
    )
    assert isinstance(early_certification, Failure)
    assert "cannot predate OOS performance evidence" in str(early_certification.error)


def test_fingerprint_binds_logical_evidence_and_rejects_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_logical_values(monkeypatch)
    run = object()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(plan, run)
    first_oos = _oos_performance(plan, observed_at=_BASE)
    later_oos = _oos_performance(plan, observed_at=_BASE + timedelta(seconds=1))

    first = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=first_oos,
    )
    later = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=later_oos,
    )
    assert first != later

    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(500)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=first_oos,
        certified_at=_BASE + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchFrozenOosEvidenceValidationError):
        replace(
            built.value,
            fingerprint=ResearchFrozenOosFingerprint("0" * 64),
        )


def test_frozen_oos_evidence_makes_no_epistemic_or_production_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_logical_values(monkeypatch)
    run = object()
    plan = _plan(run)
    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(600)),
        evaluation_freeze=_evaluation_freeze(plan, run),
        oos_performance=_oos_performance(plan),
        certified_at=_BASE + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert not hasattr(evidence, "analyst_blind")
    assert not hasattr(evidence, "pre_registered")
    assert not hasattr(evidence, "statistically_significant")
    assert not hasattr(evidence, "production_ready")


def test_fingerprint_canonicalizes_nested_uuid_logical_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = object()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(plan, run)
    oos = _oos_performance(plan)

    monkeypatch.setattr(
        ResearchEvaluationFreezeEvidence,
        "logical_values",
        lambda self: ("freeze", _uuid(701)),
    )
    monkeypatch.setattr(
        ResearchOosPerformanceEvidence,
        "logical_values",
        lambda self: ("oos", (_uuid(702),)),
    )

    first = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )
    second = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )
    assert first == second
    assert len(first.value) == 64


class _StreamingLogical:
    def __init__(self, *values: object) -> None:
        self._values = values

    def logical_values(self) -> tuple[object, ...]:
        return self._values


def test_fingerprint_streams_valid_oos_without_whole_tree_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = object()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(plan, run)
    oos = _oos_performance(plan)

    monkeypatch.setattr(
        ResearchEvaluationFreezeEvidence,
        "logical_values",
        lambda self: ("freeze", _uuid(801)),
    )
    monkeypatch.setattr(
        ResearchTemporalEvaluationPlan,
        "logical_values",
        lambda self: ("plan", _uuid(802)),
    )
    monkeypatch.setattr(
        ResearchOosPerformanceEvidence,
        "logical_values",
        lambda self: (_ for _ in ()).throw(
            AssertionError("whole OOS logical tree must not be materialized")
        ),
    )

    statistics = object.__new__(ResearchPerformanceStatisticsSnapshot)
    object.__setattr__(
        statistics,
        "snapshot_id",
        ResearchPerformanceSnapshotId(_uuid(803)),
    )
    object.__setattr__(statistics, "run", _StreamingLogical("run", _uuid(804)))
    object.__setattr__(statistics, "basis", ResearchReturnBasis.GROSS)
    object.__setattr__(
        statistics,
        "observations",
        (
            _StreamingLogical("observation", _uuid(805), "0.01"),
            _StreamingLogical("observation", _uuid(806), "-0.02"),
        ),
    )
    object.__setattr__(statistics, "sample_size", 2)
    object.__setattr__(statistics, "positive_count", 1)
    object.__setattr__(statistics, "negative_count", 1)
    object.__setattr__(statistics, "flat_count", 0)
    object.__setattr__(statistics, "mean_return", Decimal("-0.005"))
    object.__setattr__(statistics, "minimum_return", Decimal("-0.02"))
    object.__setattr__(statistics, "maximum_return", Decimal("0.01"))
    object.__setattr__(statistics, "win_rate", Decimal("0.5"))
    object.__setattr__(
        statistics,
        "population_variance",
        Decimal("0.000225"),
    )
    object.__setattr__(statistics, "observed_at", _BASE)

    fold = object.__new__(ResearchOosFoldPerformance)
    object.__setattr__(fold, "fold", _StreamingLogical("fold", 1))
    object.__setattr__(fold, "statistics", statistics)

    object.__setattr__(
        oos,
        "evidence_id",
        ResearchOosPerformanceEvidenceId(_uuid(807)),
    )
    object.__setattr__(oos, "basis", ResearchReturnBasis.GROSS)
    object.__setattr__(oos, "fold_performance", (fold,))

    first = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )
    second = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )

    assert first == second
    assert len(first.value) == 64


def test_fingerprint_reuses_exact_immutable_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen_module._FINGERPRINT_IDENTITY_CACHE.clear()
    run = object()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(plan, run)
    oos = _oos_performance(plan)
    _patch_logical_values(monkeypatch)

    calls = 0
    original = frozen_module._canonical_json_value

    def counted(value: object) -> object:
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(frozen_module, "_canonical_json_value", counted)
    first = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )
    first_calls = calls
    second = compute_research_frozen_oos_fingerprint(
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
    )
    assert first == second
    assert first_calls > 0
    assert calls == first_calls
