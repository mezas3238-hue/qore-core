"""Architect B4 exact 177-sensor temporal disposition registry.

B-07 closes epistemically by assigning every governed sensor an explicit
calendar/market-hours disposition. A terminal UNKNOWN/BLOCKED disposition is
not a verified canonical calendar and cannot authorize comparability.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import cast

IDENTITY = "SHARED_B4_TEMPORAL_DISPOSITION_REGISTRY_001"
EXPECTED_WORKLIST = "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001"
EXPECTED_R8 = "SHARED_B_R8_HISTORICAL_CALENDAR_FRONTIER_001"
EXPECTED_SENSOR_COUNT = 177


class SharedB4TemporalDispositionError(ValueError):
    """B4 temporal disposition reconciliation failed closed."""


class TemporalDisposition(StrEnum):
    DISTRIBUTED_OTC_CALENDAR_UNRESOLVED = (
        "DISTRIBUTED_OTC_CALENDAR_UNRESOLVED"
    )
    R8_HISTORICAL_SESSION_PARTIAL = "R8_HISTORICAL_SESSION_PARTIAL"
    CURRENT_INDEX_CALENDAR_UNRESOLVED = "CURRENT_INDEX_CALENDAR_UNRESOLVED"
    LEGACY_HISTORICAL_VERSION_REQUIRED = "LEGACY_HISTORICAL_VERSION_REQUIRED"
    IDENTITY_BLOCKED = "IDENTITY_BLOCKED"
    IDENTITY_AND_MARKET_STRUCTURE_BLOCKED = (
        "IDENTITY_AND_MARKET_STRUCTURE_BLOCKED"
    )
    VERSIONED_SESSION_CALENDAR_REQUIRED = "VERSIONED_SESSION_CALENDAR_REQUIRED"
    REFERENCE_TEMPORAL_SEMANTICS_REQUIRED = (
        "REFERENCE_TEMPORAL_SEMANTICS_REQUIRED"
    )


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
    if not isinstance(provider, str) or not provider.strip():
        raise SharedB4TemporalDispositionError("provider missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedB4TemporalDispositionError("provider_symbol_id invalid")
    return provider, symbol_id


def _base_disposition(category: str) -> TemporalDisposition:
    mapping = {
        "FX_DISTRIBUTED_OTC_CALENDAR_UNRESOLVED": (
            TemporalDisposition.DISTRIBUTED_OTC_CALENDAR_UNRESOLVED
        ),
        "INDEX_CURRENT_REFERENCE_CALENDAR_UNRESOLVED": (
            TemporalDisposition.CURRENT_INDEX_CALENDAR_UNRESOLVED
        ),
        "INDEX_LEGACY_CALENDAR_BINDING_FORBIDDEN": (
            TemporalDisposition.LEGACY_HISTORICAL_VERSION_REQUIRED
        ),
        "INDEX_IDENTITY_BLOCKED": TemporalDisposition.IDENTITY_BLOCKED,
        "CRYPTO_IDENTITY_AND_MARKET_STRUCTURE_BLOCKED": (
            TemporalDisposition.IDENTITY_AND_MARKET_STRUCTURE_BLOCKED
        ),
        "DATED_FUTURES_CALENDAR_VERSION_UNRESOLVED": (
            TemporalDisposition.VERSIONED_SESSION_CALENDAR_REQUIRED
        ),
        "COMMODITY_REFERENCE_CALENDAR_SEMANTICS_UNRESOLVED": (
            TemporalDisposition.REFERENCE_TEMPORAL_SEMANTICS_REQUIRED
        ),
    }
    try:
        return mapping[category]
    except KeyError as exc:
        raise SharedB4TemporalDispositionError(
            f"unsupported calendar work category: {category}"
        ) from exc


def build_temporal_disposition_registry(
    *,
    calendar_worklist: dict[str, object],
    r8_historical_frontier: dict[str, object],
) -> dict[str, object]:
    """Bind all sensors to explicit temporal truth without calendar fabrication."""

    if calendar_worklist.get("identity") != EXPECTED_WORKLIST:
        raise SharedB4TemporalDispositionError("unexpected calendar worklist")
    if r8_historical_frontier.get("identity") != EXPECTED_R8:
        raise SharedB4TemporalDispositionError("unexpected R8 calendar frontier")
    for payload, label in (
        (calendar_worklist, "calendar worklist"),
        (r8_historical_frontier, "R8 frontier"),
    ):
        if payload.get("sensor_count") != EXPECTED_SENSOR_COUNT:
            raise SharedB4TemporalDispositionError(f"{label} is not exact 177")
        if source_payload.get("canonical_calendar_verified_count") != 0:
            raise SharedB4TemporalDispositionError(
                f"{label} unexpectedly claims canonical calendars"
            )
        if source_payload.get("calendar_binding_verified_count") != 0:
            raise SharedB4TemporalDispositionError(
                f"{label} unexpectedly claims calendar bindings"
            )
    if calendar_worklist.get("provider_schedule_is_canonical_calendar") is not False:
        raise SharedB4TemporalDispositionError(
            "provider schedule cannot be canonical calendar"
        )
    if r8_historical_frontier.get("provider_schedule_is_canonical_calendar") is not False:
        raise SharedB4TemporalDispositionError(
            "R8 frontier promoted provider schedule"
        )

    work_rows = calendar_worklist.get("records")
    r8_rows = r8_historical_frontier.get("records")
    if not isinstance(work_rows, list) or len(work_rows) != EXPECTED_SENSOR_COUNT:
        raise SharedB4TemporalDispositionError("calendar worklist records invalid")
    if not isinstance(r8_rows, list) or len(r8_rows) != EXPECTED_SENSOR_COUNT:
        raise SharedB4TemporalDispositionError("R8 frontier records invalid")

    r8_by_key: dict[tuple[str, int], dict[str, object]] = {}
    for raw in r8_rows:
        if not isinstance(raw, dict):
            raise SharedB4TemporalDispositionError("R8 row invalid")
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in r8_by_key:
            raise SharedB4TemporalDispositionError("duplicate R8 provider key")
        r8_by_key[key] = row

    records: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    seen: set[tuple[str, int]] = set()
    r8_partial_count = 0

    for raw in work_rows:
        if not isinstance(raw, dict):
            raise SharedB4TemporalDispositionError("calendar worklist row invalid")
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in seen:
            raise SharedB4TemporalDispositionError("duplicate worklist provider key")
        seen.add(key)
        r8 = r8_by_key.get(key)
        if r8 is None:
            raise SharedB4TemporalDispositionError("R8 frontier missing sensor")
        if row.get("provider_symbol") != r8.get("provider_symbol"):
            raise SharedB4TemporalDispositionError("provider symbol drift")

        category = row.get("calendar_work_category")
        if not isinstance(category, str) or not category:
            raise SharedB4TemporalDispositionError(
                "calendar work category missing"
            )
        disposition = _base_disposition(category)
        if r8.get("r8_historical_session_schedule_verified") is True:
            if row.get("provider_symbol") != "JP225":
                raise SharedB4TemporalDispositionError(
                    "unexpected R8 historical session promotion"
                )
            if category != "INDEX_CURRENT_REFERENCE_CALENDAR_UNRESOLVED":
                raise SharedB4TemporalDispositionError(
                    "R8 partial calendar category mismatch"
                )
            disposition = TemporalDisposition.R8_HISTORICAL_SESSION_PARTIAL
            r8_partial_count += 1

        counts[disposition.value] = counts.get(disposition.value, 0) + 1
        records.append(
            {
                "provider": key[0],
                "provider_symbol_id": key[1],
                "provider_symbol": row.get("provider_symbol"),
                "provider_asset_class_name": row.get(
                    "provider_asset_class_name"
                ),
                "calendar_work_category": category,
                "temporal_disposition": disposition.value,
                "temporal_disposition_terminal": True,
                "canonical_calendar_verified": False,
                "calendar_binding_verified": False,
                "provider_schedule_is_canonical_calendar": False,
                "r8_historical_session_partial": (
                    disposition
                    is TemporalDisposition.R8_HISTORICAL_SESSION_PARTIAL
                ),
                "required_evidence": row.get("required_evidence", []),
                "reason_codes": row.get("reason_codes", []),
                "relational_comparability_authorized": False,
                "sensor_admission_authorized": False,
            }
        )

    if set(r8_by_key) != seen:
        raise SharedB4TemporalDispositionError("R8/worklist population mismatch")
    if r8_partial_count != 1:
        raise SharedB4TemporalDispositionError(
            f"expected exactly one R8 partial session, got {r8_partial_count}"
        )

    records.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    counts = dict(sorted(counts.items()))
    expected_counts = {
        TemporalDisposition.DISTRIBUTED_OTC_CALENDAR_UNRESOLVED.value: 60,
        TemporalDisposition.R8_HISTORICAL_SESSION_PARTIAL.value: 1,
        TemporalDisposition.CURRENT_INDEX_CALENDAR_UNRESOLVED.value: 10,
        TemporalDisposition.LEGACY_HISTORICAL_VERSION_REQUIRED.value: 2,
        TemporalDisposition.IDENTITY_BLOCKED.value: 12,
        TemporalDisposition.IDENTITY_AND_MARKET_STRUCTURE_BLOCKED.value: 73,
        TemporalDisposition.VERSIONED_SESSION_CALENDAR_REQUIRED.value: 5,
        TemporalDisposition.REFERENCE_TEMPORAL_SEMANTICS_REQUIRED.value: 14,
    }
    if counts != dict(sorted(expected_counts.items())):
        raise SharedB4TemporalDispositionError(
            f"temporal disposition count drift: {counts}"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "B07_EPISTEMIC_TEMPORAL_DISPOSITION_CLOSED",
        "sensor_count": EXPECTED_SENSOR_COUNT,
        "temporal_disposition_complete_count": len(records),
        "temporal_disposition_coverage_complete": len(records)
        == EXPECTED_SENSOR_COUNT,
        "disposition_counts": counts,
        "r8_historical_session_partial_count": r8_partial_count,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "comparability_eligible_count": 0,
        "records": records,
        "calendar_worklist_fingerprint_sha256": calendar_worklist.get(
            "worklist_fingerprint_sha256"
        ),
        "r8_frontier_fingerprint_sha256": r8_historical_frontier.get(
            "frontier_fingerprint_sha256"
        ),
        "unknown_or_blocked_temporal_state_is_valid": True,
        "provider_schedule_is_canonical_calendar": False,
        "current_schedule_backfilled_into_history": False,
        "automatic_calendar_inference": False,
        "relational_comparability_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b07_epistemic_closure_complete": True,
        "b07_all_canonical_calendars_verified": False,
    }
    payload["registry_fingerprint_sha256"] = _fingerprint(payload)
    return payload
