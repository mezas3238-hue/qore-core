from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_sensor_qualification_worklist import (
    SharedBSensorQualificationWorklistError,
    build_sensor_qualification_worklist,
)


def _frontier() -> dict[str, object]:
    records = []
    for sid in range(1, 178):
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": sid,
                "provider_symbol": (
                    "US2000" if sid == 1
                    else "XAUUSD" if sid == 2
                    else "XTIUSD" if sid == 3
                    else f"S{sid}"
                ),
                "identity_ready_for_next_qualification_step": sid <= 90,
                "canonical_calendar_binding_verified": False,
                "real_source_evidence_status": (
                    "FULL_REAL_BID_ASK_HISTORY_EVIDENCE"
                    if sid <= 2
                    else "PARTIAL_REAL_BID_ASK_HISTORY_EVIDENCE"
                    if sid == 3
                    else "NO_BOUND_REAL_CAUSAL_HISTORY_EVIDENCE"
                ),
                "scientific_value_proven": False,
                "causal_qualification_complete": False,
                "sensor_admitted": False,
            }
        )
    return {
        "identity": "SHARED_B_SENSOR_QUALIFICATION_FRONTIER_001",
        "sensor_count": 177,
        "records": records,
        "target_or_outcome_used_for_selection": False,
        "productive_authority": False,
    }


def test_current_shape_produces_exact_outcome_free_evidence_queue() -> None:
    payload = build_sensor_qualification_worklist(_frontier())
    assert payload["sensor_count"] == 177
    assert payload["gap_counts"] == {
        "CANONICAL_CALENDAR_EVIDENCE": 177,
        "CANONICAL_IDENTITY_EVIDENCE": 87,
        "FULL_REAL_CAUSAL_HISTORY_EVIDENCE": 175,
        "SCIENTIFIC_VALUE_PROOF": 177,
    }
    assert payload["minimum_missing_evidence_count"] == 2
    assert payload["nearest_evidence_completion_symbols"] == (
        "US2000",
        "XAUUSD",
    )
    assert payload["ready_for_scientific_value_exam_count"] == 0
    assert payload["causal_qualification_complete_count"] == 0
    assert payload["outcome_used"] is False
    assert payload["trade_priority_authority"] is False
    assert payload["sensor_admission_authority"] is False
    assert len(payload["worklist_fingerprint_sha256"]) == 64


def test_calendar_progress_moves_full_source_sensor_to_scientific_exam() -> None:
    frontier = _frontier()
    records = frontier["records"]
    assert isinstance(records, list)
    records[0]["canonical_calendar_binding_verified"] = True
    payload = build_sensor_qualification_worklist(frontier)
    assert payload["ready_for_scientific_value_exam_count"] == 1
    us2000 = next(
        row for row in payload["records"]
        if row["provider_symbol"] == "US2000"
    )
    assert us2000["state"] == "READY_FOR_SCIENTIFIC_VALUE_EXAM"
    assert us2000["missing_evidence"] == ("SCIENTIFIC_VALUE_PROOF",)
    assert us2000["sensor_admitted"] is False


def test_outcome_aware_or_premature_admission_fails_closed() -> None:
    bad = _frontier()
    bad["target_or_outcome_used_for_selection"] = True
    with pytest.raises(
        SharedBSensorQualificationWorklistError,
        match="outcome-aware",
    ):
        build_sensor_qualification_worklist(bad)

    bad = _frontier()
    records = bad["records"]
    assert isinstance(records, list)
    records[0]["sensor_admitted"] = True
    with pytest.raises(
        SharedBSensorQualificationWorklistError,
        match="admitted before",
    ):
        build_sensor_qualification_worklist(bad)


def test_complete_sensor_cannot_retain_evidence_gap() -> None:
    bad = deepcopy(_frontier())
    records = bad["records"]
    assert isinstance(records, list)
    records[0]["causal_qualification_complete"] = True
    with pytest.raises(
        SharedBSensorQualificationWorklistError,
        match="retains qualification evidence gaps",
    ):
        build_sensor_qualification_worklist(bad)
