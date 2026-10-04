from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_sensor_source_pilot_reducer import (
    FROZEN_PILOT_INDICES,
    B16SourcePilotReducerError,
    reduce_b16_source_pilot,
)


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def _prereg() -> dict[str, object]:
    candidates = [
        {
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": f"S{sid}",
        }
        for sid in range(1, 88)
    ]
    return {
        "identity": "SHARED_B16_SOURCE_ACQUISITION_PREREGISTRATION_001",
        "candidates": candidates,
        "candidate_set_sha256": _sha(candidates),
        "pilot_indices": FROZEN_PILOT_INDICES,
        "target_or_outcome_read": False,
        "research_labels_opened": False,
        "fresh_holdout_opened": False,
        "scientific_value_decided": False,
        "broker_mutation": False,
        "productive_authority": False,
    }


def _raw() -> dict[str, object]:
    reports = []
    for sid in range(1, 88):
        reports.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": sid,
                "provider_symbol": f"S{sid}",
                "technical_error": False,
                "window_reports": [
                    {
                        "manifest_index": index,
                        "bid_tick_count": 10,
                        "ask_tick_count": 10,
                    }
                    for index in FROZEN_PILOT_INDICES
                ],
            }
        )
    prereg = _prereg()
    return {
        "identity": "SHARED_B16_SOURCE_PILOT_RAW_001",
        "candidate_set_sha256": prereg["candidate_set_sha256"],
        "pilot_indices": FROZEN_PILOT_INDICES,
        "candidate_reports": reports,
        "target_or_outcome_read": False,
        "research_labels_opened": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }


def test_full_pilot_history_only_authorizes_full_source_acquisition() -> None:
    payload = reduce_b16_source_pilot(
        preregistration=_prereg(),
        raw_report=_raw(),
    )
    assert payload["state_counts"] == {"FULL_PILOT_HISTORY": 87}
    assert all(
        row["full_r8_source_acquisition_authorized"] is True
        for row in payload["records"]
    )
    assert payload["scientific_value_decided"] is False
    assert payload["sensor_admission_authority"] is False


def test_partial_no_history_and_technical_error_are_distinct() -> None:
    raw = _raw()
    reports = raw["candidate_reports"]
    assert isinstance(reports, list)
    reports[0]["window_reports"][0]["bid_tick_count"] = 0
    for window in reports[1]["window_reports"]:
        window["bid_tick_count"] = 0
        window["ask_tick_count"] = 0
    reports[2]["technical_error"] = True
    reports[2]["window_reports"] = []

    payload = reduce_b16_source_pilot(
        preregistration=_prereg(),
        raw_report=raw,
    )
    assert payload["state_counts"] == {
        "FULL_PILOT_HISTORY": 84,
        "NO_PILOT_HISTORY": 1,
        "PARTIAL_PILOT_HISTORY": 1,
        "TECHNICAL_ERROR": 1,
    }
    records = {row["provider_symbol_id"]: row for row in payload["records"]}
    assert records[1]["full_r8_source_acquisition_authorized"] is False
    assert records[2]["full_r8_source_acquisition_authorized"] is False
    assert records[3]["full_r8_source_acquisition_authorized"] is False


def test_candidate_drift_or_outcome_state_fails_closed() -> None:
    raw = _raw()
    reports = raw["candidate_reports"]
    assert isinstance(reports, list)
    reports[0]["provider_symbol"] = "INJECTED"
    with pytest.raises(
        B16SourcePilotReducerError,
        match="unpreregistered",
    ):
        reduce_b16_source_pilot(
            preregistration=_prereg(),
            raw_report=raw,
        )

    bad = deepcopy(_raw())
    bad["target_or_outcome_read"] = True
    with pytest.raises(
        B16SourcePilotReducerError,
        match="forbidden raw state",
    ):
        reduce_b16_source_pilot(
            preregistration=_prereg(),
            raw_report=bad,
        )
