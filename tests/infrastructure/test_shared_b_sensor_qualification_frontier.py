from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_sensor_qualification_frontier import (
    SharedBSensorQualificationFrontierError,
    build_sensor_qualification_frontier,
)


def _inputs() -> tuple[dict[str, object], ...]:
    sensors = []
    identities = []
    calendars = []
    for sid in range(1, 178):
        symbol = (
            "US2000" if sid == 1
            else "XAUUSD" if sid == 2
            else "XTIUSD" if sid == 3
            else f"S{sid}"
        )
        sensors.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": symbol,
            "disposition": "DISCOVERED",
        })
        stage = (
            "CURRENT_REFERENCE_OBJECT_MAPPED"
            if sid <= 74
            else "CURRENT_OFFICIAL_REFERENCE_MAPPED"
            if sid <= 85
            else "DATED_CONTRACT_DESCRIPTOR_VERIFIED"
            if sid <= 90
            else "PROVIDER_BINDING_UNRESOLVED"
        )
        identities.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": symbol,
            "resolution_stage": stage,
        })
        calendars.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": symbol,
            "calendar_binding_verified": False,
            "calendar_work_category": "UNRESOLVED",
        })
    registry = {
        "identity": "QORE_SHARED_GLOBAL_SENSOR_REGISTRY_001",
        "sensors": sensors,
        "disposition_counts": {
            "ADMITTED": 0,
            "DISCOVERED": 177,
            "OBSERVE_ONLY": 0,
            "QUALIFYING": 0,
            "REJECTED": 0,
        },
    }
    frontier = {
        "identity": "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001",
        "records": identities,
    }
    calendar = {
        "identity": "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001",
        "records": calendars,
        "canonical_calendar_verified_count": 0,
    }
    active = {
        "identity": "SHARED_B_ACTIVE_PERCEPTION_RESOURCE_BOUNDARY_001",
        "active_perception_sensor_side": {
            "real_sensor_statuses": {
                "US2000": "full_bid_ask_history",
                "XAUUSD": "full_bid_ask_history",
                "XTIUSD": "partial_bid_ask_history",
            }
        },
        "full_global_sensor_universe_active_perception_complete": False,
    }
    return registry, frontier, calendar, active


def test_exact_177_frontier_admits_nothing_without_prerequisites() -> None:
    registry, frontier, calendar, active = _inputs()
    payload = build_sensor_qualification_frontier(
        sensor_registry=registry,
        identity_frontier=frontier,
        calendar_worklist=calendar,
        active_perception_boundary=active,
    )
    assert payload["sensor_count"] == 177
    assert payload["discovered_count"] == 177
    assert payload["identity_next_step_ready_count"] == 90
    assert payload["canonical_calendar_binding_verified_count"] == 0
    assert payload["full_real_source_evidence_count"] == 2
    assert payload["partial_real_source_evidence_count"] == 1
    assert payload["no_bound_real_source_evidence_count"] == 174
    assert payload["qualification_prerequisites_satisfied_count"] == 0
    assert payload["scientific_value_proven_count"] == 0
    assert payload["causal_qualification_complete_count"] == 0
    assert payload["admitted_count"] == 0
    assert payload["automatic_sensor_admission"] is False
    assert payload["b16_complete"] is False
    assert len(payload["frontier_fingerprint_sha256"]) == 64
    assert all(row["sensor_admitted"] is False for row in payload["records"])


def test_legitimate_upstream_progress_is_consumed_not_rejected() -> None:
    registry, frontier, calendar, active = _inputs()
    identities = frontier["records"]
    calendars = calendar["records"]
    assert isinstance(identities, list)
    assert isinstance(calendars, list)

    identities[90]["resolution_stage"] = "CURRENT_REFERENCE_OBJECT_MAPPED"
    calendars[0]["calendar_binding_verified"] = True
    calendar["canonical_calendar_verified_count"] = 1

    payload = build_sensor_qualification_frontier(
        sensor_registry=registry,
        identity_frontier=frontier,
        calendar_worklist=calendar,
        active_perception_boundary=active,
    )
    assert payload["identity_next_step_ready_count"] == 91
    assert payload["canonical_calendar_binding_verified_count"] == 1
    assert payload["qualification_prerequisites_satisfied_count"] == 1

    first = payload["records"][0]
    assert first["provider_symbol"] == "US2000"
    assert first["qualification_prerequisites_satisfied"] is True
    assert (
        first["qualification_status"]
        == "PREREQUISITES_SATISFIED_SCIENTIFIC_VALUE_OPEN"
    )
    assert first["scientific_value_proven"] is False
    assert first["sensor_admitted"] is False
    assert "SCIENTIFIC_VALUE_NOT_YET_PROVEN" in first["reason_codes"]


def test_declared_calendar_count_must_match_row_evidence() -> None:
    registry, frontier, calendar, active = _inputs()
    calendars = calendar["records"]
    assert isinstance(calendars, list)
    calendars[0]["calendar_binding_verified"] = True
    with pytest.raises(
        SharedBSensorQualificationFrontierError,
        match="disagrees with row evidence",
    ):
        build_sensor_qualification_frontier(
            sensor_registry=registry,
            identity_frontier=frontier,
            calendar_worklist=calendar,
            active_perception_boundary=active,
        )


def test_unknown_real_source_status_fails_closed() -> None:
    registry, frontier, calendar, active = _inputs()
    sensor_side = active["active_perception_sensor_side"]
    assert isinstance(sensor_side, dict)
    statuses = sensor_side["real_sensor_statuses"]
    assert isinstance(statuses, dict)
    statuses["US2000"] = "fabricated_history"
    with pytest.raises(
        SharedBSensorQualificationFrontierError,
        match="unsupported real sensor evidence status",
    ):
        build_sensor_qualification_frontier(
            sensor_registry=registry,
            identity_frontier=frontier,
            calendar_worklist=calendar,
            active_perception_boundary=active,
        )


def test_provider_presence_cannot_promote_admission() -> None:
    registry, frontier, calendar, active = _inputs()
    sensors = registry["sensors"]
    assert isinstance(sensors, list)
    sensors[0]["disposition"] = "ADMITTED"
    registry["disposition_counts"] = {
        "ADMITTED": 1,
        "DISCOVERED": 176,
        "OBSERVE_ONLY": 0,
        "QUALIFYING": 0,
        "REJECTED": 0,
    }
    with pytest.raises(
        SharedBSensorQualificationFrontierError,
        match="discovery disposition drift",
    ):
        build_sensor_qualification_frontier(
            sensor_registry=registry,
            identity_frontier=frontier,
            calendar_worklist=calendar,
            active_perception_boundary=active,
        )


def test_active_perception_completion_widening_fails_closed() -> None:
    registry, frontier, calendar, active = _inputs()
    active = deepcopy(active)
    active["full_global_sensor_universe_active_perception_complete"] = True
    with pytest.raises(
        SharedBSensorQualificationFrontierError,
        match="illegally claims global completion",
    ):
        build_sensor_qualification_frontier(
            sensor_registry=registry,
            identity_frontier=frontier,
            calendar_worklist=calendar,
            active_perception_boundary=active,
        )
