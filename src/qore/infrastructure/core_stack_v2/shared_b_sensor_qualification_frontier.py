"""Architect-B exact 177-sensor scientific qualification frontier.

Combines discovery, identity, calendar and real sensor-side acquisition
evidence. The frontier is descriptive only: it cannot admit a sensor, select
trading features, or create predictive/economic authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_SENSOR_QUALIFICATION_FRONTIER_001"
EXPECTED_REGISTRY = "QORE_SHARED_GLOBAL_SENSOR_REGISTRY_001"
EXPECTED_IDENTITY = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001"
EXPECTED_CALENDAR = "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001"
EXPECTED_ACTIVE = "SHARED_B_ACTIVE_PERCEPTION_RESOURCE_BOUNDARY_001"

_IDENTITY_NEXT_STEP_READY = {
    "CURRENT_REFERENCE_OBJECT_MAPPED",
    "CURRENT_OFFICIAL_REFERENCE_MAPPED",
    "DATED_CONTRACT_DESCRIPTOR_VERIFIED",
}


class SharedBSensorQualificationFrontierError(ValueError):
    """B-16 qualification frontier failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _key(row: dict[str, object]) -> tuple[str, int]:
    provider = row.get("provider")
    symbol_id = row.get("provider_symbol_id")
    if not isinstance(provider, str) or not provider:
        raise SharedBSensorQualificationFrontierError("provider missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedBSensorQualificationFrontierError(
            "provider_symbol_id invalid"
        )
    return provider, symbol_id


def build_sensor_qualification_frontier(
    *,
    sensor_registry: dict[str, object],
    identity_frontier: dict[str, object],
    calendar_worklist: dict[str, object],
    active_perception_boundary: dict[str, object],
) -> dict[str, object]:
    if sensor_registry.get("identity") != EXPECTED_REGISTRY:
        raise SharedBSensorQualificationFrontierError(
            "unexpected sensor registry identity"
        )
    if identity_frontier.get("identity") != EXPECTED_IDENTITY:
        raise SharedBSensorQualificationFrontierError(
            "unexpected identity frontier"
        )
    if calendar_worklist.get("identity") != EXPECTED_CALENDAR:
        raise SharedBSensorQualificationFrontierError(
            "unexpected calendar worklist"
        )
    if active_perception_boundary.get("identity") != EXPECTED_ACTIVE:
        raise SharedBSensorQualificationFrontierError(
            "unexpected active-perception boundary"
        )

    sensors = sensor_registry.get("sensors")
    identities = identity_frontier.get("records")
    calendars = calendar_worklist.get("records")
    if not isinstance(sensors, list) or len(sensors) != 177:
        raise SharedBSensorQualificationFrontierError(
            "sensor registry must be exact 177"
        )
    if not isinstance(identities, list) or len(identities) != 177:
        raise SharedBSensorQualificationFrontierError(
            "identity frontier must be exact 177"
        )
    if not isinstance(calendars, list) or len(calendars) != 177:
        raise SharedBSensorQualificationFrontierError(
            "calendar worklist must be exact 177"
        )
    if sensor_registry.get("disposition_counts") != {
        "ADMITTED": 0,
        "DISCOVERED": 177,
        "OBSERVE_ONLY": 0,
        "QUALIFYING": 0,
        "REJECTED": 0,
    }:
        raise SharedBSensorQualificationFrontierError(
            "discovery disposition drift"
        )
    if calendar_worklist.get("canonical_calendar_verified_count") != 0:
        raise SharedBSensorQualificationFrontierError(
            "calendar authority unexpectedly widened"
        )

    identity_by_key: dict[tuple[str, int], dict[str, object]] = {}
    for raw in identities:
        if not isinstance(raw, dict):
            raise SharedBSensorQualificationFrontierError(
                "identity row invalid"
            )
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in identity_by_key:
            raise SharedBSensorQualificationFrontierError(
                "duplicate identity key"
            )
        identity_by_key[key] = row

    calendar_by_key: dict[tuple[str, int], dict[str, object]] = {}
    for raw in calendars:
        if not isinstance(raw, dict):
            raise SharedBSensorQualificationFrontierError(
                "calendar row invalid"
            )
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in calendar_by_key:
            raise SharedBSensorQualificationFrontierError(
                "duplicate calendar key"
            )
        calendar_by_key[key] = row

    active = active_perception_boundary.get("active_perception_sensor_side")
    if not isinstance(active, dict):
        raise SharedBSensorQualificationFrontierError(
            "active-perception sensor side missing"
        )
    statuses = active.get("real_sensor_statuses")
    if statuses != {
        "US2000": "full_bid_ask_history",
        "XAUUSD": "full_bid_ask_history",
        "XTIUSD": "partial_bid_ask_history",
    }:
        raise SharedBSensorQualificationFrontierError(
            "real sensor evidence drift"
        )
    if active_perception_boundary.get(
        "full_global_sensor_universe_active_perception_complete"
    ) is not False:
        raise SharedBSensorQualificationFrontierError(
            "active perception illegally claims global completion"
        )

    output: list[dict[str, object]] = []
    reference_ready_count = 0
    full_source_count = 0
    partial_source_count = 0
    no_bound_source_count = 0

    for raw in sensors:
        if not isinstance(raw, dict):
            raise SharedBSensorQualificationFrontierError(
                "sensor registry row invalid"
            )
        sensor = cast(dict[str, object], raw)
        key = _key(sensor)
        identity_row = identity_by_key.get(key)
        calendar_row = calendar_by_key.get(key)
        if identity_row is None or calendar_row is None:
            raise SharedBSensorQualificationFrontierError(
                "sensor lacks identity/calendar qualification row"
            )
        if sensor.get("provider_symbol") != identity_row.get("provider_symbol"):
            raise SharedBSensorQualificationFrontierError(
                "identity symbol drift"
            )
        if sensor.get("provider_symbol") != calendar_row.get("provider_symbol"):
            raise SharedBSensorQualificationFrontierError(
                "calendar symbol drift"
            )

        stage = str(identity_row.get("resolution_stage"))
        identity_next_step_ready = stage in _IDENTITY_NEXT_STEP_READY
        if identity_next_step_ready:
            reference_ready_count += 1

        symbol = str(sensor.get("provider_symbol"))
        source_status = statuses.get(symbol)
        if source_status == "full_bid_ask_history":
            source_evidence = "FULL_REAL_BID_ASK_HISTORY_EVIDENCE"
            full_source_count += 1
        elif source_status == "partial_bid_ask_history":
            source_evidence = "PARTIAL_REAL_BID_ASK_HISTORY_EVIDENCE"
            partial_source_count += 1
        else:
            source_evidence = "NO_BOUND_REAL_CAUSAL_HISTORY_EVIDENCE"
            no_bound_source_count += 1

        reasons: list[str] = []
        if not identity_next_step_ready:
            reasons.append("IDENTITY_QUALIFICATION_PREREQUISITE_OPEN")
        if calendar_row.get("calendar_binding_verified") is not True:
            reasons.append("CANONICAL_CALENDAR_BINDING_UNVERIFIED")
        if source_evidence == "NO_BOUND_REAL_CAUSAL_HISTORY_EVIDENCE":
            reasons.append("REAL_CAUSAL_SOURCE_EVIDENCE_NOT_BOUND")
        elif source_evidence == "PARTIAL_REAL_BID_ASK_HISTORY_EVIDENCE":
            reasons.append("REAL_CAUSAL_SOURCE_EVIDENCE_PARTIAL")
        reasons.append("SCIENTIFIC_VALUE_NOT_YET_PROVEN")

        output.append(
            {
                "provider": key[0],
                "provider_symbol_id": key[1],
                "provider_symbol": symbol,
                "registry_disposition": sensor.get("disposition"),
                "identity_resolution_stage": stage,
                "identity_ready_for_next_qualification_step": (
                    identity_next_step_ready
                ),
                "calendar_work_category": calendar_row.get(
                    "calendar_work_category"
                ),
                "canonical_calendar_binding_verified": False,
                "real_source_evidence_status": source_evidence,
                "qualification_status": "NOT_ADMITTED_PREREQUISITES_OPEN",
                "scientific_value_proven": False,
                "causal_qualification_complete": False,
                "sensor_admitted": False,
                "reason_codes": sorted(set(reasons)),
                "target_or_outcome_used_for_selection": False,
                "execution_authority": False,
                "risk_authority": False,
                "sizing_authority": False,
                "capital_authority": False,
            }
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    if reference_ready_count != 90:
        raise SharedBSensorQualificationFrontierError(
            f"expected 90 identity-next-step rows, got {reference_ready_count}"
        )
    if (full_source_count, partial_source_count, no_bound_source_count) != (
        2,
        1,
        174,
    ):
        raise SharedBSensorQualificationFrontierError(
            "real-source qualification counts drift"
        )
    if len(output) != 177:
        raise SharedBSensorQualificationFrontierError(
            "qualification frontier lost sensors"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_177_SENSOR_QUALIFICATION_FRONTIER_FROZEN",
        "sensor_count": 177,
        "discovered_count": 177,
        "identity_next_step_ready_count": reference_ready_count,
        "canonical_calendar_binding_verified_count": 0,
        "full_real_source_evidence_count": full_source_count,
        "partial_real_source_evidence_count": partial_source_count,
        "no_bound_real_source_evidence_count": no_bound_source_count,
        "scientific_value_proven_count": 0,
        "causal_qualification_complete_count": 0,
        "admitted_count": 0,
        "records": output,
        "provider_presence_is_scientific_admission": False,
        "automatic_sensor_admission": False,
        "target_or_outcome_used_for_selection": False,
        "r6_r5_read_for_selection": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b16_complete": False,
    }
    payload["frontier_fingerprint_sha256"] = _fingerprint(payload)
    return payload
