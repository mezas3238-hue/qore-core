"""Architect-B canonical calendar qualification worklist.

Builds an exact 177-sensor calendar-evidence worklist from already sealed B
identity, FX-hours and commodity evidence. This is a qualification matrix, not
a calendar mapper: no row is promoted to VERIFIED without exact canonical
calendar evidence.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001"
EXPECTED_FRONTIER_IDENTITY = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001"
EXPECTED_FX_IDENTITY = "SHARED_B_FX_MARKET_HOURS_BOUNDARY_001"
EXPECTED_COMMODITY_IDENTITY = "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"


class SharedBCanonicalCalendarWorklistError(ValueError):
    """Calendar worklist evidence failed closed."""


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
        raise SharedBCanonicalCalendarWorklistError("provider missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedBCanonicalCalendarWorklistError(
            "provider_symbol_id invalid"
        )
    return (provider, symbol_id)


def build_canonical_calendar_qualification_worklist(
    *,
    identity_frontier: dict[str, object],
    fx_hours_boundary: dict[str, object],
    commodity_pack: dict[str, object],
) -> dict[str, object]:
    if identity_frontier.get("identity") != EXPECTED_FRONTIER_IDENTITY:
        raise SharedBCanonicalCalendarWorklistError(
            "unexpected identity frontier"
        )
    if fx_hours_boundary.get("identity") != EXPECTED_FX_IDENTITY:
        raise SharedBCanonicalCalendarWorklistError(
            "unexpected FX hours boundary"
        )
    if commodity_pack.get("identity") != EXPECTED_COMMODITY_IDENTITY:
        raise SharedBCanonicalCalendarWorklistError(
            "unexpected commodity pack"
        )

    frontier_rows = identity_frontier.get("records")
    fx_rows = fx_hours_boundary.get("records")
    commodity_rows = commodity_pack.get("records")
    if not isinstance(frontier_rows, list) or len(frontier_rows) != 177:
        raise SharedBCanonicalCalendarWorklistError(
            "identity frontier must contain exact 177 records"
        )
    if not isinstance(fx_rows, list) or len(fx_rows) != 60:
        raise SharedBCanonicalCalendarWorklistError(
            "FX boundary must contain exact 60 records"
        )
    if not isinstance(commodity_rows, list) or len(commodity_rows) != 19:
        raise SharedBCanonicalCalendarWorklistError(
            "commodity pack must contain exact 19 records"
        )

    fx_by_key: dict[tuple[str, int], dict[str, object]] = {}
    for raw in fx_rows:
        if not isinstance(raw, dict):
            raise SharedBCanonicalCalendarWorklistError("FX row invalid")
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in fx_by_key:
            raise SharedBCanonicalCalendarWorklistError("duplicate FX key")
        if row.get("canonical_market_structure") != "DISTRIBUTED_OTC":
            raise SharedBCanonicalCalendarWorklistError(
                "FX market structure drift"
            )
        if row.get("canonical_calendar_status") != "UNRESOLVED":
            raise SharedBCanonicalCalendarWorklistError(
                "FX calendar was unexpectedly promoted"
            )
        fx_by_key[key] = row

    commodity_by_key: dict[tuple[str, int], dict[str, object]] = {}
    for raw in commodity_rows:
        if not isinstance(raw, dict):
            raise SharedBCanonicalCalendarWorklistError(
                "commodity row invalid"
            )
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in commodity_by_key:
            raise SharedBCanonicalCalendarWorklistError(
                "duplicate commodity key"
            )
        commodity_by_key[key] = row

    output: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    category_counts: dict[str, int] = {}

    for raw in frontier_rows:
        if not isinstance(raw, dict):
            raise SharedBCanonicalCalendarWorklistError(
                "frontier row invalid"
            )
        row = cast(dict[str, object], raw)
        key = _key(row)
        if key in seen:
            raise SharedBCanonicalCalendarWorklistError(
                "duplicate frontier key"
            )
        seen.add(key)

        provider_symbol = row.get("provider_symbol")
        asset_class = row.get("provider_asset_class_name")
        stage = row.get("resolution_stage")
        if not isinstance(provider_symbol, str) or not provider_symbol:
            raise SharedBCanonicalCalendarWorklistError(
                "provider symbol missing"
            )
        if not isinstance(asset_class, str) or not asset_class:
            raise SharedBCanonicalCalendarWorklistError(
                "provider asset class missing"
            )

        base: dict[str, object] = {
            "provider": key[0],
            "provider_symbol_id": key[1],
            "provider_symbol": provider_symbol,
            "provider_asset_class_name": asset_class,
            "identity_resolution_stage": stage,
            "canonical_calendar_verified": False,
            "calendar_binding_verified": False,
            "calendar_binding_authorized": False,
            "provider_schedule_is_canonical_calendar": False,
            "relational_comparability_authorized": False,
            "sensor_admission_authorized": False,
        }

        if asset_class.casefold() == "forex":
            fx = fx_by_key.get(key)
            if fx is None:
                raise SharedBCanonicalCalendarWorklistError(
                    "FX frontier row lacks FX boundary evidence"
                )
            category = "FX_DISTRIBUTED_OTC_CALENDAR_UNRESOLVED"
            base.update(
                {
                    "calendar_semantic_kind": "DISTRIBUTED_OTC_MARKET_STATE",
                    "canonical_market_structure": "DISTRIBUTED_OTC",
                    "canonical_single_venue": None,
                    "qualification_status": "EVIDENCE_PARTIAL_CALENDAR_UNRESOLVED",
                    "reason_codes": [
                        "DISTRIBUTED_OTC_NO_SINGLE_CANONICAL_VENUE",
                        "EXACT_UNIVERSAL_WEEKLY_BOUNDARY_UNVERIFIED",
                        "PROVIDER_SCHEDULE_OBSERVABILITY_ONLY",
                    ],
                    "required_evidence": [
                        "GOVERNED_DISTRIBUTED_FX_WEEKLY_MARKET_STATE_SEMANTICS",
                        "HOLIDAY_AND_EXCEPTION_SEMANTICS",
                    ],
                    "provider_schedule_available": fx.get(
                        "provider_schedule_available"
                    ),
                    "provider_schedule_timezone": fx.get(
                        "provider_schedule_timezone"
                    ),
                }
            )
        elif asset_class.casefold() == "indices":
            if stage == "CURRENT_OFFICIAL_REFERENCE_MAPPED":
                category = "INDEX_CURRENT_REFERENCE_CALENDAR_UNRESOLVED"
                base.update(
                    {
                        "calendar_semantic_kind": "REFERENCE_INDEX_CALCULATION",
                        "canonical_reference_identity": row.get(
                            "canonical_reference_identity"
                        ),
                        "qualification_status": "IDENTITY_READY_CALENDAR_UNRESOLVED",
                        "reason_codes": [
                            "REFERENCE_INDEX_IS_NOT_ITSELF_A_TRADING_VENUE",
                            "OFFICIAL_CALCULATION_CALENDAR_NOT_YET_BOUND",
                        ],
                        "required_evidence": [
                            "OFFICIAL_REFERENCE_INDEX_CALCULATION_CALENDAR",
                            "VERSIONED_HOLIDAY_AND_EXCEPTION_RULES",
                        ],
                    }
                )
            elif stage == "LEGACY_REFERENCE_LINEAGE_ONLY":
                category = "INDEX_LEGACY_CALENDAR_BINDING_FORBIDDEN"
                base.update(
                    {
                        "calendar_semantic_kind": "LEGACY_REFERENCE_INDEX",
                        "qualification_status": "LEGACY_VERSION_BLOCKED",
                        "reason_codes": [
                            "LEGACY_CONSTITUENT_COUNT_NOT_CURRENT_BINDING",
                            "CURRENT_CALENDAR_CANNOT_BE_BACKFILLED_TO_LEGACY_IDENTITY",
                        ],
                        "required_evidence": [
                            "EXACT_HISTORICAL_REFERENCE_VERSION",
                            "VERSIONED_HISTORICAL_CALCULATION_CALENDAR",
                        ],
                    }
                )
            elif stage == "PROVIDER_BINDING_UNRESOLVED":
                category = "INDEX_IDENTITY_BLOCKED"
                base.update(
                    {
                        "calendar_semantic_kind": "UNKNOWN_REFERENCE_INDEX",
                        "qualification_status": "IDENTITY_BLOCKED",
                        "reason_codes": [
                            "OFFICIAL_REFERENCE_BINDING_UNRESOLVED",
                        ],
                        "required_evidence": [
                            "EXPLICIT_PROVIDER_TO_OFFICIAL_INDEX_BINDING",
                            "OFFICIAL_REFERENCE_INDEX_CALCULATION_CALENDAR",
                        ],
                    }
                )
            else:
                raise SharedBCanonicalCalendarWorklistError(
                    f"unexpected index identity stage: {stage}"
                )
        elif asset_class.casefold() == "cryptocurrencies":
            category = "CRYPTO_IDENTITY_AND_MARKET_STRUCTURE_BLOCKED"
            base.update(
                {
                    "calendar_semantic_kind": "CRYPTO_MARKET_STRUCTURE_UNKNOWN",
                    "qualification_status": "IDENTITY_AND_STRUCTURE_BLOCKED",
                    "reason_codes": [
                        "PROVIDER_NEUTRAL_ASSET_IDENTITY_UNPROVEN",
                        "CANONICAL_MARKET_STRUCTURE_UNPROVEN",
                        "PROVIDER_SCHEDULE_CANNOT_DEFINE_GLOBAL_CRYPTO_MARKET",
                    ],
                    "required_evidence": [
                        "PROVIDER_NEUTRAL_CRYPTO_ASSET_IDENTITY",
                        "GOVERNED_CRYPTO_MARKET_STRUCTURE",
                        "CANONICAL_TEMPORAL_SEMANTICS",
                    ],
                }
            )
        else:
            commodity = commodity_by_key.get(key)
            if commodity is None:
                raise SharedBCanonicalCalendarWorklistError(
                    "non-FX/index/crypto row lacks commodity evidence"
                )
            if commodity.get("identity_kind") == "DATED_FUTURES_CONTRACT_DESCRIPTOR":
                category = "DATED_FUTURES_CALENDAR_VERSION_UNRESOLVED"
                base.update(
                    {
                        "calendar_semantic_kind": "CENTRALIZED_FUTURES_CONTRACT",
                        "qualification_status": "PRODUCT_VENUE_READY_CALENDAR_VERSION_UNRESOLVED",
                        "reason_codes": [
                            "DATED_CONTRACT_IDENTITY_VERIFIED",
                            "EXACT_VERSIONED_SESSION_CALENDAR_NOT_BOUND",
                            "HISTORICAL_SESSION_RULES_CANNOT_USE_CURRENT_SCHEDULE_BY_DEFAULT",
                        ],
                        "required_evidence": [
                            "VERSIONED_COMEX_GC_SESSION_CALENDAR",
                            "VERSIONED_HOLIDAY_AND_EXCEPTION_RULES",
                        ],
                    }
                )
            else:
                category = "COMMODITY_REFERENCE_CALENDAR_SEMANTICS_UNRESOLVED"
                base.update(
                    {
                        "calendar_semantic_kind": "REFERENCE_OBJECT",
                        "qualification_status": "REFERENCE_OBJECT_SEMANTICS_UNRESOLVED",
                        "reason_codes": [
                            "REFERENCE_OBJECT_IS_NOT_TRADABLE_PRODUCT_PROOF",
                            "FUTURES_CALENDAR_CANNOT_BE_ASSIGNED_TO_SPOT_LIKE_REFERENCE",
                        ],
                        "required_evidence": [
                            "TRADABLE_OR_REFERENCE_MARKET_STRUCTURE",
                            "GOVERNED_REFERENCE_OBJECT_TEMPORAL_SEMANTICS",
                        ],
                    }
                )

        base["calendar_work_category"] = category
        category_counts[category] = category_counts.get(category, 0) + 1
        output.append(base)

    if set(fx_by_key) - seen:
        raise SharedBCanonicalCalendarWorklistError(
            "FX boundary contains sensors outside frontier"
        )
    if set(commodity_by_key) - seen:
        raise SharedBCanonicalCalendarWorklistError(
            "commodity pack contains sensors outside frontier"
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    expected_counts = {
        "FX_DISTRIBUTED_OTC_CALENDAR_UNRESOLVED": 60,
        "INDEX_CURRENT_REFERENCE_CALENDAR_UNRESOLVED": 11,
        "INDEX_LEGACY_CALENDAR_BINDING_FORBIDDEN": 2,
        "INDEX_IDENTITY_BLOCKED": 12,
        "CRYPTO_IDENTITY_AND_MARKET_STRUCTURE_BLOCKED": 73,
        "DATED_FUTURES_CALENDAR_VERSION_UNRESOLVED": 5,
        "COMMODITY_REFERENCE_CALENDAR_SEMANTICS_UNRESOLVED": 14,
    }
    if category_counts != expected_counts:
        raise SharedBCanonicalCalendarWorklistError(
            f"unexpected calendar category counts: {category_counts}"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_177_SENSOR_CALENDAR_WORKLIST_FROZEN",
        "sensor_count": 177,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "qualification_record_count": len(output),
        "category_counts": category_counts,
        "records": output,
        "provider_schedule_is_canonical_calendar": False,
        "automatic_calendar_inference": False,
        "calendar_worklist_complete": True,
        "canonical_calendar_registry_complete": False,
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
    payload["worklist_fingerprint_sha256"] = _fingerprint(payload)
    return payload
