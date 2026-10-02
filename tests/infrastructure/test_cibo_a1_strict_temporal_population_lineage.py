from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.cibo_a1_strict_temporal_population_lineage import (
    A1TemporalPopulationFold,
    evaluate_a1_strict_temporal_population_lineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _folds() -> tuple[A1TemporalPopulationFold, ...]:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    folds: list[A1TemporalPopulationFold] = []
    for index, fold_id in enumerate(("WF1", "WF2", "WF3", "WF4")):
        decision_start = start + timedelta(days=index * 40)
        decision_end = decision_start + timedelta(days=30)
        folds.append(
            A1TemporalPopulationFold(
                fold_id=fold_id,
                population_sha256=_sha(f"population-{fold_id}"),
                candidate_id=(
                    "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
                ),
                code_sha="a" * 40,
                parameter_sha256=_sha("parameters"),
                protocol_binding_sha256=_sha("protocol"),
                treatment_identity="T09_SCARCITY_POLICY_V1",
                decision_start_at=decision_start,
                decision_end_at=decision_end,
                outcomes_observed_through_at=decision_end + timedelta(days=5),
                policy_frozen_before_population=True,
                retuned_after_population_start=False,
                outcomes_used_to_define_population=False,
                outcomes_pooled_across_folds=False,
            )
        )
    return tuple(folds)


def test_a1_temporal_lineage_accepts_four_disjoint_frozen_folds() -> None:
    report = evaluate_a1_strict_temporal_population_lineage(
        workstream_id="T09",
        folds=_folds(),
    )

    assert report.lineage_valid is True
    assert report.all_four_folds_required is True
    assert report.scientific_disposition_allowed_by_lineage_alone is False
    assert report.fingerprint().startswith("sha256:")


def test_a1_temporal_lineage_rejects_parameter_drift() -> None:
    folds = list(_folds())
    folds[2] = replace(folds[2], parameter_sha256=_sha("retuned"))

    with pytest.raises(CiboCapitalManagementError, match="parameter_sha256 drift"):
        evaluate_a1_strict_temporal_population_lineage(
            workstream_id="T09",
            folds=tuple(folds),
        )


def test_a1_temporal_lineage_rejects_overlapping_decision_windows() -> None:
    folds = list(_folds())
    folds[1] = replace(
        folds[1],
        decision_start_at=folds[0].decision_end_at - timedelta(hours=1),
    )

    with pytest.raises(CiboCapitalManagementError, match="windows overlap"):
        evaluate_a1_strict_temporal_population_lineage(
            workstream_id="T09",
            folds=tuple(folds),
        )


def test_a1_temporal_lineage_rejects_duplicate_population() -> None:
    folds = list(_folds())
    folds[3] = replace(
        folds[3],
        population_sha256=folds[0].population_sha256,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="four distinct populations",
    ):
        evaluate_a1_strict_temporal_population_lineage(
            workstream_id="T09",
            folds=tuple(folds),
        )


def test_a1_temporal_lineage_rejects_outcome_aware_fold_definition() -> None:
    folds = list(_folds())

    with pytest.raises(
        CiboCapitalManagementError,
        match="governance contamination",
    ):
        replace(folds[0], outcomes_used_to_define_population=True)


def test_a1_temporal_lineage_rejects_a2_workstream() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="outside A1 ownership",
    ):
        evaluate_a1_strict_temporal_population_lineage(
            workstream_id="GEN-C8",
            folds=_folds(),
        )
