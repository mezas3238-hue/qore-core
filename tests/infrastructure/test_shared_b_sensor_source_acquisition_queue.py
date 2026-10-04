from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_sensor_source_acquisition_queue import (
    B16SourceAcquisitionQueueError,
    build_b16_source_acquisition_queue,
)


def _worklist() -> dict[str, object]:
    records = []
    for sid in range(1, 178):
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": sid,
                "provider_symbol": (
                    "XAUUSD" if sid == 1
                    else "US2000" if sid == 2
                    else "XTIUSD" if sid == 3
                    else f"S{sid}"
                ),
                "identity_ready": sid <= 90,
                "real_source_evidence_status": (
                    "FULL_REAL_BID_ASK_HISTORY_EVIDENCE"
                    if sid <= 2
                    else "PARTIAL_REAL_BID_ASK_HISTORY_EVIDENCE"
                    if sid == 3
                    else "NO_BOUND_REAL_CAUSAL_HISTORY_EVIDENCE"
                ),
            }
        )
    return {
        "identity": "SHARED_B_SENSOR_QUALIFICATION_WORKLIST_001",
        "records": records,
        "outcome_used": False,
        "sensor_admission_authority": False,
    }


def test_current_shape_builds_exact_source_queue_without_credentials() -> None:
    payload = build_b16_source_acquisition_queue(
        _worklist(),
        provider_credentials_available=False,
    )
    assert payload["state_counts"] == {
        "IDENTITY_BLOCKED_DO_NOT_ACQUIRE": 87,
        "PARTIAL_SOURCE_BLINDSPOT": 1,
        "READY_FOR_SOURCE_ACQUISITION": 87,
        "SOURCE_COMPLETE": 2,
    }
    assert payload["source_acquisition_candidate_count"] == 87
    assert payload["execution_ready_candidate_count"] == 0
    assert payload["execution_status"] == "BLOCKED_MISSING_PROVIDER_CREDENTIALS"
    assert payload["partial_source_blindspot_symbols"] == ("XTIUSD",)
    assert payload["target_or_outcome_read"] is False
    assert payload["sensor_admission_authority"] is False
    assert len(payload["queue_fingerprint_sha256"]) == 64


def test_credentials_only_enable_execution_not_scientific_or_trade_authority() -> None:
    payload = build_b16_source_acquisition_queue(
        _worklist(),
        provider_credentials_available=True,
    )
    assert payload["execution_ready_candidate_count"] == 87
    assert payload["execution_status"] == "READY_FOR_READ_ONLY_ACQUISITION"
    assert payload["scientific_value_decided"] is False
    assert payload["trade_priority_authority"] is False
    assert payload["broker_mutation"] is False


def test_identity_blocked_sensor_never_enters_acquisition_queue() -> None:
    payload = build_b16_source_acquisition_queue(
        _worklist(),
        provider_credentials_available=True,
    )
    blocked = [
        row
        for row in payload["records"]
        if row["state"] == "IDENTITY_BLOCKED_DO_NOT_ACQUIRE"
    ]
    assert len(blocked) == 87
    assert all(row["acquisition_execution_ready"] is False for row in blocked)


def test_outcome_aware_or_unrecognized_source_input_fails_closed() -> None:
    bad = deepcopy(_worklist())
    bad["outcome_used"] = True
    with pytest.raises(B16SourceAcquisitionQueueError, match="outcome-aware"):
        build_b16_source_acquisition_queue(
            bad,
            provider_credentials_available=False,
        )

    bad = deepcopy(_worklist())
    records = bad["records"]
    assert isinstance(records, list)
    records[10]["real_source_evidence_status"] = "MAGIC_HISTORY"
    with pytest.raises(
        B16SourceAcquisitionQueueError,
        match="unsupported source evidence status",
    ):
        build_b16_source_acquisition_queue(
            bad,
            provider_credentials_available=False,
        )
