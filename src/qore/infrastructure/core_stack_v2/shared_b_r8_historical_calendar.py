"""Architect-B R8 historical reference-index calendar frontier.

Bind only historically evidenced session semantics to the frozen R8 window.
A verified intraday session schedule is not a complete canonical calendar:
holidays and date-level exceptions remain separate evidence requirements.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_R8_HISTORICAL_CALENDAR_FRONTIER_001"
EXPECTED_WORKLIST = "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001"
EXPECTED_MANIFEST = (
    "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001"
)
EXPECTED_AUTHORITY = (
    "SHARED_B_R8_HISTORICAL_CALENDAR_AUTHORITY_EVIDENCE_001"
)
EXPECTED_MANIFEST_SHA256 = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)
EXPECTED_SOURCE_MIN = "2016-04-20T14:00:00.000000+00:00"
EXPECTED_SOURCE_MAX = "2018-05-18T19:30:00.000000+00:00"


class SharedBR8HistoricalCalendarError(ValueError):
    """R8 historical calendar evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _records(value: object, *, field: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise SharedBR8HistoricalCalendarError(f"{field} must be a list")
    output: list[dict[str, object]] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise SharedBR8HistoricalCalendarError(
                f"{field} rows must be objects"
            )
        output.append(cast(dict[str, object], raw))
    return output


def build_r8_historical_calendar_frontier(
    *,
    calendar_worklist: dict[str, object],
    r8_manifest: dict[str, object],
    authority_evidence: dict[str, object],
) -> dict[str, object]:
    if calendar_worklist.get("identity") != EXPECTED_WORKLIST:
        raise SharedBR8HistoricalCalendarError(
            "unexpected calendar worklist identity"
        )
    if r8_manifest.get("identity") != EXPECTED_MANIFEST:
        raise SharedBR8HistoricalCalendarError(
            "unexpected R8 manifest identity"
        )
    if authority_evidence.get("identity") != EXPECTED_AUTHORITY:
        raise SharedBR8HistoricalCalendarError(
            "unexpected authority evidence identity"
        )
    if r8_manifest.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise SharedBR8HistoricalCalendarError("R8 manifest hash drift")
    if r8_manifest.get("source_min") != EXPECTED_SOURCE_MIN:
        raise SharedBR8HistoricalCalendarError("R8 source_min drift")
    if r8_manifest.get("source_max") != EXPECTED_SOURCE_MAX:
        raise SharedBR8HistoricalCalendarError("R8 source_max drift")
    if r8_manifest.get("window_count") not in (None, 2948):
        raise SharedBR8HistoricalCalendarError("R8 window_count drift")

    frozen = authority_evidence.get("r8_source_manifest")
    if not isinstance(frozen, dict):
        raise SharedBR8HistoricalCalendarError(
            "authority R8 source manifest missing"
        )
    for key, expected in (
        ("manifest_sha256", EXPECTED_MANIFEST_SHA256),
        ("source_min", EXPECTED_SOURCE_MIN),
        ("source_max", EXPECTED_SOURCE_MAX),
        ("window_count", 2948),
    ):
        if frozen.get(key) != expected:
            raise SharedBR8HistoricalCalendarError(
                f"authority R8 manifest mismatch: {key}"
            )

    worklist_rows = _records(
        calendar_worklist.get("records"),
        field="calendar worklist records",
    )
    if len(worklist_rows) != 177:
        raise SharedBR8HistoricalCalendarError(
            "calendar worklist must contain exact 177 records"
        )
    if calendar_worklist.get("canonical_calendar_verified_count") != 0:
        raise SharedBR8HistoricalCalendarError(
            "upstream worklist unexpectedly promoted calendars"
        )
    if calendar_worklist.get("calendar_binding_verified_count") != 0:
        raise SharedBR8HistoricalCalendarError(
            "upstream worklist unexpectedly promoted bindings"
        )

    authority_rows = _records(
        authority_evidence.get("records"),
        field="authority records",
    )
    if len(authority_rows) != 1:
        raise SharedBR8HistoricalCalendarError(
            "expected exact one historical authority record"
        )
    authority = authority_rows[0]
    required_authority = {
        "provider_symbol_id": 10006,
        "provider_symbol": "JP225",
        "canonical_reference_identity": "INDEX:NIKKEI_225",
        "r8_session_schedule_verified": True,
        "r8_session_timezone": "Asia/Tokyo",
        "calculation_frequency_ms": 5000,
        "first_calculation_time_local": "09:00:05",
        "r8_holiday_calendar_verified": False,
        "historical_exception_calendar_verified": False,
        "canonical_calendar_complete": False,
    }
    for key, expected in required_authority.items():
        if authority.get(key) != expected:
            raise SharedBR8HistoricalCalendarError(
                f"Nikkei authority mismatch: {key}"
            )

    segments = authority.get("r8_session_segments")
    if segments != [
        {"start_local": "09:00:00", "end_local": "11:30:00"},
        {"start_local": "12:30:00", "end_local": "15:00:00"},
    ]:
        raise SharedBR8HistoricalCalendarError(
            "Nikkei R8 session segments drift"
        )

    authorities = authority.get("authorities")
    if not isinstance(authorities, list) or len(authorities) < 3:
        raise SharedBR8HistoricalCalendarError(
            "Nikkei official authority chain incomplete"
        )
    for raw in authorities:
        if not isinstance(raw, dict):
            raise SharedBR8HistoricalCalendarError(
                "Nikkei authority row invalid"
            )
        url = raw.get("source_url")
        if not isinstance(url, str) or not (
            url.startswith("https://indexes.nikkei.co.jp/")
            or url.startswith("https://www.jpx.co.jp/")
        ):
            raise SharedBR8HistoricalCalendarError(
                "Nikkei authority URL is not official"
            )

    output: list[dict[str, object]] = []
    jp225_count = 0
    for raw in worklist_rows:
        row = dict(raw)
        if row.get("provider_symbol") == "JP225":
            jp225_count += 1
            if row.get("provider_symbol_id") != 10006:
                raise SharedBR8HistoricalCalendarError(
                    "JP225 provider_symbol_id drift"
                )
            if row.get("canonical_reference_identity") != "INDEX:NIKKEI_225":
                raise SharedBR8HistoricalCalendarError(
                    "JP225 canonical reference identity drift"
                )
            if (
                row.get("identity_resolution_stage")
                != "CURRENT_OFFICIAL_REFERENCE_MAPPED"
            ):
                raise SharedBR8HistoricalCalendarError(
                    "JP225 identity stage is not official-current"
                )
            row.update(
                {
                    "r8_historical_session_schedule_verified": True,
                    "r8_historical_session_timezone": "Asia/Tokyo",
                    "r8_historical_session_segments": segments,
                    "r8_calculation_frequency_ms": 5000,
                    "r8_first_calculation_time_local": "09:00:05",
                    "r8_holiday_calendar_verified": False,
                    "r8_exception_calendar_verified": False,
                    "canonical_calendar_verified": False,
                    "calendar_binding_verified": False,
                    "calendar_binding_authorized": False,
                    "qualification_status": (
                        "R8_SESSION_SCHEDULE_VERIFIED_HOLIDAY_CALENDAR_OPEN"
                    ),
                    "reason_codes": [
                        "OFFICIAL_R8_SESSION_SCHEDULE_VERIFIED",
                        "VERSIONED_R8_HOLIDAY_CALENDAR_UNRESOLVED",
                        "DATE_LEVEL_R8_EXCEPTIONS_UNRESOLVED",
                    ],
                    "required_evidence": [
                        "VERSIONED_TSE_HOLIDAY_CALENDAR_2016_2018",
                        "R8_DATE_LEVEL_EXCEPTION_CALENDAR",
                    ],
                    "relational_comparability_authorized": False,
                    "sensor_admission_authorized": False,
                }
            )
        output.append(row)

    if jp225_count != 1:
        raise SharedBR8HistoricalCalendarError(
            f"expected exactly one JP225 row, got {jp225_count}"
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "R8_HISTORICAL_SESSION_SCHEDULE_PARTIAL",
        "sensor_count": 177,
        "r8_source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "r8_source_min": EXPECTED_SOURCE_MIN,
        "r8_source_max": EXPECTED_SOURCE_MAX,
        "r8_window_count": 2948,
        "r8_historical_session_schedule_verified_count": 1,
        "r8_historical_holiday_calendar_verified_count": 0,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "records": output,
        "current_schedule_backfilled_into_r8": False,
        "provider_schedule_is_canonical_calendar": False,
        "relational_comparability_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b07_complete": False,
        "b08_complete": False,
    }
    payload["frontier_fingerprint_sha256"] = _fingerprint(payload)
    return payload
