"""Architect-B distributed OTC FX market-hours boundary.

This contract separates global market structure from provider availability.
Independent authority evidence supports distributed OTC structure and 24-hour
daily operation, but it does not establish one venue or exact universal weekly
open/close timestamps. Provider schedules remain provider observability only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Final

IDENTITY: Final = "SHARED_B_FX_MARKET_HOURS_BOUNDARY_001"
EXPECTED_PROVIDER_IDENTITY: Final = (
    "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
)
EXPECTED_AUTHORITY_IDENTITY: Final = (
    "SHARED_B_FX_MARKET_HOURS_AUTHORITY_EVIDENCE_001"
)


class SharedBFxMarketHoursError(ValueError):
    """FX market-hours evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_fx_market_hours_boundary(
    *,
    provider_schedule: dict[str, object],
    authority_evidence: dict[str, object],
) -> dict[str, object]:
    if provider_schedule.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise SharedBFxMarketHoursError("unexpected provider schedule identity")
    if authority_evidence.get("identity") != EXPECTED_AUTHORITY_IDENTITY:
        raise SharedBFxMarketHoursError("unexpected authority evidence identity")

    conclusions = authority_evidence.get("frozen_conclusions")
    if not isinstance(conclusions, dict):
        raise SharedBFxMarketHoursError("authority conclusions missing")
    required = {
        "canonical_market_structure": "DISTRIBUTED_OTC",
        "single_canonical_venue_exists": False,
        "daily_24_hour_operation_supported": True,
        "exact_universal_weekly_boundary_verified": False,
        "provider_schedule_is_canonical_market_hours": False,
        "canonical_market_closed_state_derivable_from_provider_schedule": False,
        "unknown_required_when_global_market_state_unresolved": True,
    }
    for key, expected in required.items():
        if conclusions.get(key) != expected:
            raise SharedBFxMarketHoursError(
                f"authority conclusion mismatch: {key}"
            )

    authorities = authority_evidence.get("authorities")
    if not isinstance(authorities, list) or len(authorities) < 3:
        raise SharedBFxMarketHoursError(
            "FX market-hours evidence requires frozen authorities"
        )
    authority_ids: list[str] = []
    for row in authorities:
        if not isinstance(row, dict):
            raise SharedBFxMarketHoursError("authority row invalid")
        authority_id = row.get("authority_id")
        source_url = row.get("source_url")
        if (
            not isinstance(authority_id, str)
            or not authority_id
            or not isinstance(source_url, str)
            or not source_url.startswith("https://")
        ):
            raise SharedBFxMarketHoursError(
                "authority identity/url invalid"
            )
        authority_ids.append(authority_id)
    if len(authority_ids) != len(set(authority_ids)):
        raise SharedBFxMarketHoursError("authority ids must be unique")
    authority_ids = sorted(authority_ids)

    symbols = provider_schedule.get("symbols")
    if not isinstance(symbols, list):
        raise SharedBFxMarketHoursError("provider symbols missing")

    rows: list[dict[str, object]] = []
    for raw in symbols:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("provider_asset_class_name", "")).casefold() != "forex":
            continue
        provider = raw.get("provider")
        symbol = raw.get("provider_symbol")
        symbol_id = raw.get("provider_symbol_id")
        if (
            not isinstance(provider, str)
            or not provider
            or not isinstance(symbol, str)
            or not symbol
            or type(symbol_id) is not int
            or symbol_id <= 0
        ):
            raise SharedBFxMarketHoursError(
                "provider FX identity incomplete"
            )
        rows.append(
            {
                "provider": provider,
                "provider_symbol": symbol,
                "provider_symbol_id": symbol_id,
                "canonical_market_structure": "DISTRIBUTED_OTC",
                "canonical_single_venue": None,
                "daily_24_hour_operation_supported": True,
                "exact_universal_weekly_boundary_verified": False,
                "canonical_calendar_status": "UNRESOLVED",
                "canonical_market_open_derivable_from_provider_schedule": False,
                "provider_schedule_available": bool(
                    raw.get("provider_schedule_available")
                ),
                "provider_schedule_timezone": raw.get(
                    "provider_schedule_timezone"
                ),
                "provider_schedule_role": (
                    "PROVIDER_OBSERVABILITY_ONLY"
                ),
                "market_closed_if_provider_closed": False,
                "unknown_required_when_global_market_state_unresolved": True,
                "authority_ids": tuple(authority_ids),
                "calendar_binding_authorized": False,
                "relational_comparability_authorized": False,
                "sensor_admission_authorized": False,
            }
        )

    def _row_key(row: dict[str, object]) -> tuple[str, int]:
        symbol_id = row.get("provider_symbol_id")
        if type(symbol_id) is not int:
            raise SharedBFxMarketHoursError(
                "provider FX symbol id lost integer type"
            )
        return (str(row.get("provider", "")), symbol_id)

    rows.sort(key=_row_key)
    keys = [
        (row["provider"], row["provider_symbol_id"])
        for row in rows
    ]
    if len(rows) != 60:
        raise SharedBFxMarketHoursError(
            f"expected exact 60 FX provider sensors, got {len(rows)}"
        )
    if len(keys) != len(set(keys)):
        raise SharedBFxMarketHoursError("duplicate FX provider identity")

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "FX_DISTRIBUTED_OTC_HOURS_BOUNDARY_FROZEN",
        "fx_sensor_count": len(rows),
        "canonical_market_structure": "DISTRIBUTED_OTC",
        "single_canonical_venue_count": 0,
        "daily_24_hour_operation_supported": True,
        "exact_universal_weekly_boundary_verified": False,
        "canonical_calendar_verified_count": 0,
        "provider_schedule_is_canonical_market_hours": False,
        "canonical_market_closed_state_derivable_from_provider_schedule": False,
        "unknown_required_when_global_market_state_unresolved": True,
        "records": rows,
        "calendar_mapping_complete": False,
        "relational_claims_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    payload["boundary_fingerprint_sha256"] = _fingerprint(payload)
    return payload
