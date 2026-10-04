from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_b_sensor_source_acquisition_preregistration import (
    B16SourceAcquisitionPreregistrationError,
    FROZEN_PILOT_INDICES,
    build_b16_source_acquisition_preregistration,
)


NOW = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)


def _queue() -> dict[str, object]:
    records = []
    for sid in range(1, 178):
        state = (
            "SOURCE_COMPLETE"
            if sid <= 2
            else "PARTIAL_SOURCE_BLINDSPOT"
            if sid == 3
            else "READY_FOR_SOURCE_ACQUISITION"
            if sid <= 90
            else "IDENTITY_BLOCKED_DO_NOT_ACQUIRE"
        )
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": sid,
                "provider_symbol": f"S{sid}",
                "state": state,
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
        "identity": "SHARED_B16_SOURCE_ACQUISITION_QUEUE_001",
        "queue_fingerprint_sha256": "a" * 64,
        "source_acquisition_candidate_count": 87,
        "records": records,
        "target_or_outcome_read": False,
        "scientific_value_decided": False,
    }


def test_preregistration_freezes_exact_87_before_provider_observation() -> None:
    payload = build_b16_source_acquisition_preregistration(
        _queue(),
        preregistered_at=NOW,
    )
    assert payload["candidate_count"] == 87
    assert payload["pilot_indices"] == FROZEN_PILOT_INDICES
    assert payload["quote_sides"] == ("BID", "ASK")
    assert payload["candidate_removal_after_observation_authorized"] is False
    assert payload["candidate_addition_after_observation_authorized"] is False
    assert payload["target_or_outcome_read"] is False
    assert payload["scientific_value_decided"] is False
    assert payload["sensor_admission_authority"] is False
    assert len(payload["candidate_set_sha256"]) == 64
    assert len(payload["preregistration_fingerprint_sha256"]) == 64


def test_partial_and_identity_blocked_sensors_are_not_candidates() -> None:
    payload = build_b16_source_acquisition_preregistration(
        _queue(),
        preregistered_at=NOW,
    )
    ids = {row["provider_symbol_id"] for row in payload["candidates"]}
    assert 3 not in ids
    assert 91 not in ids
    assert set(range(4, 91)) <= ids


def test_outcome_aware_or_candidate_count_drift_fails_closed() -> None:
    bad = deepcopy(_queue())
    bad["target_or_outcome_read"] = True
    with pytest.raises(
        B16SourceAcquisitionPreregistrationError,
        match="outcome-aware",
    ):
        build_b16_source_acquisition_preregistration(
            bad,
            preregistered_at=NOW,
        )

    bad = deepcopy(_queue())
    bad["source_acquisition_candidate_count"] = 86
    with pytest.raises(
        B16SourceAcquisitionPreregistrationError,
        match="candidate count disagrees",
    ):
        build_b16_source_acquisition_preregistration(
            bad,
            preregistered_at=NOW,
        )
