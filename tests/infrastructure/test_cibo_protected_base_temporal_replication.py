from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_protected_base_overlay import ProtectedBaseClass
from qore.infrastructure.cibo_protected_base_policy_gate import (
    ProtectedBaseCandidateRole,
    ProtectedBaseEconomicObservation,
    ProtectedBaseGateStatus,
    ProtectedBasePolicyCandidate,
)
from qore.infrastructure.cibo_protected_base_temporal_replication import (
    ProtectedBaseTemporalFoldEvidence,
    ProtectedBaseTemporalFoldResult,
    ProtectedBaseTemporalVerdict,
    evaluate_protected_base_temporal_replication,
)

FROZEN = datetime(2026, 9, 30, 10, tzinfo=UTC)
FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _candidate(
    *,
    candidate_id: str,
    role: ProtectedBaseCandidateRole,
    amount: str,
    protection_class: ProtectedBaseClass,
) -> ProtectedBasePolicyCandidate:
    return ProtectedBasePolicyCandidate(
        candidate_id=candidate_id,
        role=role,
        policy_id=f"policy-{candidate_id}",
        policy_sha256=(
            "sha256:"
            + ("1" if role is ProtectedBaseCandidateRole.CONTROL else "2") * 64
        ),
        frozen_at=FROZEN,
        protected_base_usd=Decimal(amount),
        protection_class=protection_class,
    )


CONTROL = _candidate(
    candidate_id="control",
    role=ProtectedBaseCandidateRole.CONTROL,
    amount="0",
    protection_class=ProtectedBaseClass.ACCOUNTING_PROTECTED,
)
TREATMENT = _candidate(
    candidate_id="protect-60",
    role=ProtectedBaseCandidateRole.TREATMENT,
    amount="60",
    protection_class=ProtectedBaseClass.POLICY_PROTECTED,
)


def _observation(
    *,
    candidate: ProtectedBasePolicyCandidate,
    fold_id: str,
    population: str,
    treatment: bool,
) -> ProtectedBaseEconomicObservation:
    start = FROZEN + timedelta(days=1)
    return ProtectedBaseEconomicObservation(
        candidate=candidate,
        population_sha256="sha256:" + population * 64,
        provider_surface_sha256="sha256:" + "a" * 64,
        fold_ids=(fold_id,),
        horizon_start=start,
        horizon_end=start + timedelta(hours=1),
        ending_realized_capital_usd=Decimal("110"),
        minimum_original_base_usd=Decimal("75" if treatment else "70"),
        maximum_drawdown_usd=Decimal("4.5" if treatment else "5"),
        p99_drawdown_usd=Decimal("4.5"),
        peak_plausible_loss_usd=Decimal("6"),
        peak_margin_occupancy_usd=Decimal("20"),
        p95_recovery_minutes=Decimal("50"),
        minimum_optionality_usd=Decimal("15"),
        provider_failure_incidence=Decimal("0.01"),
        capital_risk_time_productivity=Decimal("1.2"),
    )


def _folds() -> tuple[ProtectedBaseTemporalFoldEvidence, ...]:
    return tuple(
        ProtectedBaseTemporalFoldEvidence(
            fold_id=fold_id,
            observations=(
                _observation(
                    candidate=CONTROL,
                    fold_id=fold_id,
                    population=str(index),
                    treatment=False,
                ),
                _observation(
                    candidate=TREATMENT,
                    fold_id=fold_id,
                    population=str(index),
                    treatment=True,
                ),
            ),
        )
        for index, fold_id in enumerate(FOLDS, start=1)
    )


def test_protected_base_requires_strict_four_fold_replication() -> None:
    report = evaluate_protected_base_temporal_replication(
        treatment_candidate_id="protect-60",
        folds=_folds(),
    )

    assert report.verdict is ProtectedBaseTemporalVerdict.REPLICATED
    assert all(item.passed for item in report.fold_results)
    assert report.certification_ready is False


def test_one_failed_fold_falsifies_protected_base_replication() -> None:
    folds = list(_folds())
    failed_observation = replace(
        folds[2].observations[1],
        ending_realized_capital_usd=Decimal("109"),
    )
    folds[2] = replace(
        folds[2],
        observations=(folds[2].observations[0], failed_observation),
    )

    report = evaluate_protected_base_temporal_replication(
        treatment_candidate_id="protect-60",
        folds=tuple(folds),
    )

    assert report.verdict is ProtectedBaseTemporalVerdict.FALSIFIED
    assert report.fold_results[2].passed is False


def test_reused_population_is_invalid_replication() -> None:
    folds = list(_folds())
    reused = tuple(
        replace(
            observation,
            population_sha256=folds[0].observations[0].population_sha256,
        )
        for observation in folds[3].observations
    )
    folds[3] = replace(folds[3], observations=reused)

    with pytest.raises(
        CiboCapitalManagementError,
        match="requires distinct populations",
    ):
        evaluate_protected_base_temporal_replication(
            treatment_candidate_id="protect-60",
            folds=tuple(folds),
        )

def test_protected_base_fold_result_rejects_manual_pass_drift() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="pass/status drift",
    ):
        ProtectedBaseTemporalFoldResult(
            fold_id="WF1",
            passed=True,
            treatment_status=ProtectedBaseGateStatus.REJECTED_NO_STRICT_IMPROVEMENT,
            failed_dimensions=("NO_STRICT_IMPROVEMENT",),
        )

