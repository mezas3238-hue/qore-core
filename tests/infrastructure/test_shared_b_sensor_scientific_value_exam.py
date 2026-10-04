from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_sensor_scientific_value_exam import (
    SensorScientificExamStatus,
    SensorScientificFoldEvidence,
    SensorScientificValuePreregistration,
    assess_sensor_exam_eligibility,
    evaluate_sensor_scientific_value,
)


NOW = datetime(2026, 10, 4, 18, 0, tzinfo=UTC)


def _worklist(*, ready: bool) -> dict[str, object]:
    row = {
        "provider": "CTRADER_DEMO",
        "provider_symbol_id": 41,
        "provider_symbol": "XAUUSD",
        "state": (
            "READY_FOR_SCIENTIFIC_VALUE_EXAM"
            if ready
            else "EVIDENCE_COMPLETION_REQUIRED"
        ),
        "missing_evidence": (
            ("SCIENTIFIC_VALUE_PROOF",)
            if ready
            else ("CANONICAL_CALENDAR_EVIDENCE", "SCIENTIFIC_VALUE_PROOF")
        ),
        "missing_evidence_count": 1 if ready else 2,
        "identity_ready": True,
        "calendar_ready": ready,
        "real_source_evidence_status": "FULL_REAL_BID_ASK_HISTORY_EVIDENCE",
        "scientific_value_proven": False,
        "causal_qualification_complete": False,
        "sensor_admitted": False,
    }
    return {
        "identity": "SHARED_B_SENSOR_QUALIFICATION_WORKLIST_001",
        "worklist_fingerprint_sha256": "a" * 64,
        "records": [row],
    }


def _prereg(*, labels_opened: bool = False) -> SensorScientificValuePreregistration:
    return SensorScientificValuePreregistration(
        sensor_key="CTRADER_DEMO:41",
        provider_symbol="XAUUSD",
        worklist_fingerprint_sha256="a" * 64,
        research_target_id="PREDECLARED_SENSOR_INFORMATION_TARGET_001",
        research_dataset_id="B16_RESEARCH_ONLY_001",
        discovery_partition_id="DISCOVERY",
        calibration_partition_id="CALIBRATION",
        validation_fold_ids=("F1", "F2", "F3", "F4"),
        minimum_fold_sample_count=100,
        minimum_incremental_value_bps=500,
        minimum_preservation_bps=9_500,
        preregistered_at=NOW,
        research_labels_opened_at=(
            NOW + timedelta(minutes=1) if labels_opened else None
        ),
    )


def _fold(fold_id: str, **overrides: object) -> SensorScientificFoldEvidence:
    values = {
        "fold_id": fold_id,
        "sample_count": 200,
        "incremental_value_bps": 750,
        "preservation_bps": 9_800,
        "anti_leakage_pass": True,
        "deterministic_replay_pass": True,
    }
    values.update(overrides)
    return SensorScientificFoldEvidence(**values)  # type: ignore[arg-type]


def test_current_incomplete_sensor_cannot_start_exam() -> None:
    result = assess_sensor_exam_eligibility(
        worklist=_worklist(ready=False),
        preregistration=_prereg(),
    )
    assert result.status is SensorScientificExamStatus.NOT_ELIGIBLE
    assert result.scientific_value_proven is False
    assert result.sensor_admission_authority is False


def test_ready_sensor_is_only_preregistered_ready_not_admitted() -> None:
    result = assess_sensor_exam_eligibility(
        worklist=_worklist(ready=True),
        preregistration=_prereg(),
    )
    assert result.status is SensorScientificExamStatus.PREREGISTERED_READY
    assert result.scientific_value_proven is False
    assert result.sensor_admission_authority is False
    assert result.productive_authority is False


def test_all_folds_stress_and_replication_are_required_for_value_pass() -> None:
    folds = tuple(_fold(f"F{i}") for i in range(1, 5))
    result = evaluate_sensor_scientific_value(
        worklist=_worklist(ready=True),
        preregistration=_prereg(labels_opened=True),
        folds=folds,
        stress_pass=True,
        temporal_replication_pass=True,
    )
    assert result.status is SensorScientificExamStatus.PASS
    assert result.fold_passes == (True, True, True, True)
    assert result.scientific_value_proven is True
    assert result.trade_authority is False
    assert result.sizing_authority is False
    assert result.risk_authority is False


def test_one_failed_fold_cannot_be_compensated() -> None:
    folds = (
        _fold("F1"),
        _fold("F2", incremental_value_bps=499),
        _fold("F3"),
        _fold("F4"),
    )
    result = evaluate_sensor_scientific_value(
        worklist=_worklist(ready=True),
        preregistration=_prereg(labels_opened=True),
        folds=folds,
        stress_pass=True,
        temporal_replication_pass=True,
    )
    assert result.status is SensorScientificExamStatus.FAIL
    assert result.fold_passes == (True, False, True, True)
    assert result.scientific_value_proven is False


def test_labels_cannot_precede_preregistration_or_use_final_holdout() -> None:
    with pytest.raises(ValueError, match="before preregistration"):
        SensorScientificValuePreregistration(
            **{
                **_prereg().__dict__,
                "research_labels_opened_at": NOW - timedelta(seconds=1),
            }
        )
