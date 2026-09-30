from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_canonical_calendar_worklist import (
    SharedBCanonicalCalendarWorklistError,
    build_canonical_calendar_qualification_worklist,
)


def _frontier() -> dict[str, object]:
    records: list[dict[str, object]] = []
    sid = 1
    for _ in range(60):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": f"FX{sid}",
            "provider_asset_class_name": "Forex",
            "resolution_stage": "CURRENT_REFERENCE_OBJECT_MAPPED",
        })
        sid += 1
    for index in range(25):
        stage = (
            "CURRENT_OFFICIAL_REFERENCE_MAPPED"
            if index < 11
            else "LEGACY_REFERENCE_LINEAGE_ONLY"
            if index < 13
            else "PROVIDER_BINDING_UNRESOLVED"
        )
        row = {
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": f"IDX{sid}",
            "provider_asset_class_name": "Indices",
            "resolution_stage": stage,
        }
        if stage == "CURRENT_OFFICIAL_REFERENCE_MAPPED":
            row["canonical_reference_identity"] = f"INDEX:REF_{sid}"
        records.append(row)
        sid += 1
    for _ in range(73):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": f"CRY{sid}",
            "provider_asset_class_name": "Cryptocurrencies",
            "resolution_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
        })
        sid += 1
    for index in range(19):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": sid,
            "provider_symbol": f"COM{sid}",
            "provider_asset_class_name": "Metals",
            "resolution_stage": (
                "DATED_CONTRACT_DESCRIPTOR_VERIFIED"
                if index < 5
                else "CURRENT_REFERENCE_OBJECT_MAPPED"
            ),
        })
        sid += 1
    assert len(records) == 177
    return {
        "identity": "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001",
        "records": records,
    }


def _fx() -> dict[str, object]:
    return {
        "identity": "SHARED_B_FX_MARKET_HOURS_BOUNDARY_001",
        "records": [
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": sid,
                "provider_symbol": f"FX{sid}",
                "canonical_market_structure": "DISTRIBUTED_OTC",
                "canonical_calendar_status": "UNRESOLVED",
                "provider_schedule_available": False,
                "provider_schedule_timezone": None,
            }
            for sid in range(1, 61)
        ],
    }


def _commodity() -> dict[str, object]:
    start = 159
    rows = []
    for index in range(19):
        rows.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": start + index,
            "provider_symbol": f"COM{start + index}",
            "identity_kind": (
                "DATED_FUTURES_CONTRACT_DESCRIPTOR"
                if index < 5
                else "REFERENCE_OBJECT"
            ),
        })
    return {
        "identity": "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001",
        "records": rows,
    }


def test_builds_exact_177_calendar_worklist_without_promotions() -> None:
    payload = build_canonical_calendar_qualification_worklist(
        identity_frontier=_frontier(),
        fx_hours_boundary=_fx(),
        commodity_pack=_commodity(),
    )
    assert payload["sensor_count"] == 177
    assert payload["canonical_calendar_verified_count"] == 0
    assert payload["calendar_binding_verified_count"] == 0
    assert payload["qualification_record_count"] == 177
    assert payload["category_counts"] == {
        "FX_DISTRIBUTED_OTC_CALENDAR_UNRESOLVED": 60,
        "INDEX_CURRENT_REFERENCE_CALENDAR_UNRESOLVED": 11,
        "INDEX_LEGACY_CALENDAR_BINDING_FORBIDDEN": 2,
        "INDEX_IDENTITY_BLOCKED": 12,
        "CRYPTO_IDENTITY_AND_MARKET_STRUCTURE_BLOCKED": 73,
        "DATED_FUTURES_CALENDAR_VERSION_UNRESOLVED": 5,
        "COMMODITY_REFERENCE_CALENDAR_SEMANTICS_UNRESOLVED": 14,
    }
    assert payload["provider_schedule_is_canonical_calendar"] is False
    assert payload["automatic_calendar_inference"] is False
    assert payload["calendar_worklist_complete"] is True
    assert payload["canonical_calendar_registry_complete"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["b07_complete"] is False
    assert payload["b08_complete"] is False
    assert len(payload["worklist_fingerprint_sha256"]) == 64
    assert all(
        row["canonical_calendar_verified"] is False
        and row["calendar_binding_verified"] is False
        and row["calendar_binding_authorized"] is False
        for row in payload["records"]
    )


def test_fx_provider_schedule_never_becomes_canonical() -> None:
    fx = deepcopy(_fx())
    rows = fx["records"]
    assert isinstance(rows, list)
    rows[0]["provider_schedule_available"] = True
    rows[0]["provider_schedule_timezone"] = "UTC"

    payload = build_canonical_calendar_qualification_worklist(
        identity_frontier=_frontier(),
        fx_hours_boundary=fx,
        commodity_pack=_commodity(),
    )
    first = payload["records"][0]
    assert first["provider_schedule_available"] is True
    assert first["provider_schedule_timezone"] == "UTC"
    assert first["provider_schedule_is_canonical_calendar"] is False
    assert first["canonical_calendar_verified"] is False


def test_unexpected_index_stage_fails_closed() -> None:
    frontier = deepcopy(_frontier())
    rows = frontier["records"]
    assert isinstance(rows, list)
    rows[60]["resolution_stage"] = "GUESSED"
    with pytest.raises(
        SharedBCanonicalCalendarWorklistError,
        match="unexpected index identity stage",
    ):
        build_canonical_calendar_qualification_worklist(
            identity_frontier=frontier,
            fx_hours_boundary=_fx(),
            commodity_pack=_commodity(),
        )


def test_missing_commodity_binding_fails_closed() -> None:
    commodity = deepcopy(_commodity())
    rows = commodity["records"]
    assert isinstance(rows, list)
    rows.pop()
    with pytest.raises(
        SharedBCanonicalCalendarWorklistError,
        match="exact 19",
    ):
        build_canonical_calendar_qualification_worklist(
            identity_frontier=_frontier(),
            fx_hours_boundary=_fx(),
            commodity_pack=commodity,
        )
