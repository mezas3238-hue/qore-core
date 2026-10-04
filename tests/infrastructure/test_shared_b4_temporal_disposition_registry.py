from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b4_temporal_disposition_registry import (
    SharedB4TemporalDispositionError,
    build_temporal_disposition_registry,
)


def _worklist() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    sid = 1
    categories = (
        ("FX_DISTRIBUTED_OTC_CALENDAR_UNRESOLVED", 60, "Forex"),
        ("INDEX_CURRENT_REFERENCE_CALENDAR_UNRESOLVED", 11, "Indices"),
        ("INDEX_LEGACY_CALENDAR_BINDING_FORBIDDEN", 2, "Indices"),
        ("INDEX_IDENTITY_BLOCKED", 12, "Indices"),
        ("CRYPTO_IDENTITY_AND_MARKET_STRUCTURE_BLOCKED", 73, "Cryptocurrencies"),
        ("DATED_FUTURES_CALENDAR_VERSION_UNRESOLVED", 5, "Metals"),
        ("COMMODITY_REFERENCE_CALENDAR_SEMANTICS_UNRESOLVED", 14, "Metals"),
    )
    for category, count, asset_class in categories:
        for _ in range(count):
            symbol = "JP225" if sid == 61 else f"S{sid}"
            rows.append(
                {
                    "provider": "CTRADER_DEMO",
                    "provider_symbol_id": sid,
                    "provider_symbol": symbol,
                    "provider_asset_class_name": asset_class,
                    "calendar_work_category": category,
                    "canonical_calendar_verified": False,
                    "calendar_binding_verified": False,
                    "provider_schedule_is_canonical_calendar": False,
                    "required_evidence": ["EXPLICIT_EVIDENCE_REQUIRED"],
                    "reason_codes": ["NOT_YET_VERIFIED"],
                }
            )
            sid += 1
    assert len(rows) == 177
    return {
        "identity": "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001",
        "sensor_count": 177,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "provider_schedule_is_canonical_calendar": False,
        "records": rows,
        "worklist_fingerprint_sha256": "a" * 64,
    }


def _r8() -> dict[str, object]:
    work = _worklist()
    rows = deepcopy(work["records"])
    assert isinstance(rows, list)
    rows[60]["r8_historical_session_schedule_verified"] = True
    return {
        "identity": "SHARED_B_R8_HISTORICAL_CALENDAR_FRONTIER_001",
        "sensor_count": 177,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "provider_schedule_is_canonical_calendar": False,
        "records": rows,
        "frontier_fingerprint_sha256": "b" * 64,
    }


def test_closes_exact_177_temporal_dispositions_without_fabrication() -> None:
    out = build_temporal_disposition_registry(
        calendar_worklist=_worklist(),
        r8_historical_frontier=_r8(),
    )
    assert out["status"] == "B07_EPISTEMIC_TEMPORAL_DISPOSITION_CLOSED"
    assert out["sensor_count"] == 177
    assert out["temporal_disposition_complete_count"] == 177
    assert out["temporal_disposition_coverage_complete"] is True
    assert out["r8_historical_session_partial_count"] == 1
    assert out["canonical_calendar_verified_count"] == 0
    assert out["calendar_binding_verified_count"] == 0
    assert out["comparability_eligible_count"] == 0
    assert out["disposition_counts"] == {
        "CURRENT_INDEX_CALENDAR_UNRESOLVED": 10,
        "DISTRIBUTED_OTC_CALENDAR_UNRESOLVED": 60,
        "IDENTITY_AND_MARKET_STRUCTURE_BLOCKED": 73,
        "IDENTITY_BLOCKED": 12,
        "LEGACY_HISTORICAL_VERSION_REQUIRED": 2,
        "R8_HISTORICAL_SESSION_PARTIAL": 1,
        "REFERENCE_TEMPORAL_SEMANTICS_REQUIRED": 14,
        "VERSIONED_SESSION_CALENDAR_REQUIRED": 5,
    }
    assert out["unknown_or_blocked_temporal_state_is_valid"] is True
    assert out["provider_schedule_is_canonical_calendar"] is False
    assert out["b07_epistemic_closure_complete"] is True
    assert out["b07_all_canonical_calendars_verified"] is False
    assert out["relational_comparability_authorized"] is False
    assert len(str(out["registry_fingerprint_sha256"])) == 64


def test_rejects_provider_schedule_promotion() -> None:
    work = _worklist()
    work["provider_schedule_is_canonical_calendar"] = True
    with pytest.raises(
        SharedB4TemporalDispositionError,
        match="provider schedule",
    ):
        build_temporal_disposition_registry(
            calendar_worklist=work,
            r8_historical_frontier=_r8(),
        )


def test_rejects_unrecognized_calendar_category() -> None:
    work = _worklist()
    rows = work["records"]
    assert isinstance(rows, list)
    rows[-1]["calendar_work_category"] = "GUESSED_CALENDAR"
    with pytest.raises(
        SharedB4TemporalDispositionError,
        match="unsupported calendar work category",
    ):
        build_temporal_disposition_registry(
            calendar_worklist=work,
            r8_historical_frontier=_r8(),
        )


def test_rejects_r8_partial_on_wrong_sensor() -> None:
    r8 = _r8()
    rows = r8["records"]
    assert isinstance(rows, list)
    rows[60].pop("r8_historical_session_schedule_verified")
    rows[61]["r8_historical_session_schedule_verified"] = True
    with pytest.raises(
        SharedB4TemporalDispositionError,
        match="unexpected R8 historical session promotion",
    ):
        build_temporal_disposition_registry(
            calendar_worklist=_worklist(),
            r8_historical_frontier=r8,
        )
