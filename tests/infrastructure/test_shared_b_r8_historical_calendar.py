from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_r8_historical_calendar import (
    SharedBR8HistoricalCalendarError,
    build_r8_historical_calendar_frontier,
)


def _worklist() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for index in range(177):
        symbol_id = index + 1
        rows.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"S{symbol_id}",
                "provider_asset_class_name": "Other",
                "identity_resolution_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
                "canonical_calendar_verified": False,
                "calendar_binding_verified": False,
                "calendar_binding_authorized": False,
                "provider_schedule_is_canonical_calendar": False,
                "relational_comparability_authorized": False,
                "sensor_admission_authorized": False,
            }
        )
    rows[5] = {
        "provider": "CTRADER_DEMO",
        "provider_symbol_id": 10006,
        "provider_symbol": "JP225",
        "provider_asset_class_name": "Indices",
        "identity_resolution_stage": "CURRENT_OFFICIAL_REFERENCE_MAPPED",
        "canonical_reference_identity": "INDEX:NIKKEI_225",
        "canonical_calendar_verified": False,
        "calendar_binding_verified": False,
        "calendar_binding_authorized": False,
        "provider_schedule_is_canonical_calendar": False,
        "relational_comparability_authorized": False,
        "sensor_admission_authorized": False,
    }
    return {
        "identity": "SHARED_B_CANONICAL_CALENDAR_QUALIFICATION_WORKLIST_001",
        "sensor_count": 177,
        "canonical_calendar_verified_count": 0,
        "calendar_binding_verified_count": 0,
        "records": rows,
    }


def _manifest() -> dict[str, object]:
    return {
        "identity": (
            "QORE_SHARED_WP05_ACTIVE_PERCEPTION_V12_ACQUISITION_MANIFEST_001"
        ),
        "manifest_sha256": (
            "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
        ),
        "source_min": "2016-04-20T14:00:00.000000+00:00",
        "source_max": "2018-05-18T19:30:00.000000+00:00",
        "window_count": 2948,
    }


def _authority() -> dict[str, object]:
    return {
        "identity": "SHARED_B_R8_HISTORICAL_CALENDAR_AUTHORITY_EVIDENCE_001",
        "r8_source_manifest": {
            "manifest_sha256": (
                "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
            ),
            "source_min": "2016-04-20T14:00:00.000000+00:00",
            "source_max": "2018-05-18T19:30:00.000000+00:00",
            "window_count": 2948,
        },
        "records": [
            {
                "provider_symbol_id": 10006,
                "provider_symbol": "JP225",
                "canonical_reference_identity": "INDEX:NIKKEI_225",
                "r8_session_schedule_verified": True,
                "r8_session_timezone": "Asia/Tokyo",
                "r8_session_segments": [
                    {"start_local": "09:00:00", "end_local": "11:30:00"},
                    {"start_local": "12:30:00", "end_local": "15:00:00"},
                ],
                "calculation_frequency_ms": 5000,
                "first_calculation_time_local": "09:00:05",
                "r8_holiday_calendar_verified": False,
                "historical_exception_calendar_verified": False,
                "canonical_calendar_complete": False,
                "authorities": [
                    {
                        "source_url": (
                            "https://indexes.nikkei.co.jp/nkave/archives/"
                            "faq/faq_nikkei_stock_average_en.pdf"
                        )
                    },
                    {
                        "source_url": (
                            "https://www.jpx.co.jp/files/tse/"
                            "rules-participants/public-comment/data/"
                            "101124-ks_4.pdf"
                        )
                    },
                    {
                        "source_url": (
                            "https://www.jpx.co.jp/english/corporate/news/"
                            "news-releases/1030/20230920-01.html"
                        )
                    },
                ],
            }
        ],
    }


def test_binds_only_nikkei_r8_session_schedule() -> None:
    payload = build_r8_historical_calendar_frontier(
        calendar_worklist=_worklist(),
        r8_manifest=_manifest(),
        authority_evidence=_authority(),
    )
    assert payload["sensor_count"] == 177
    assert payload["r8_historical_session_schedule_verified_count"] == 1
    assert payload["r8_historical_holiday_calendar_verified_count"] == 0
    assert payload["canonical_calendar_verified_count"] == 0
    assert payload["calendar_binding_verified_count"] == 0
    assert payload["current_schedule_backfilled_into_r8"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["b07_complete"] is False

    jp225 = next(
        row
        for row in payload["records"]
        if row["provider_symbol"] == "JP225"
    )
    assert jp225["r8_historical_session_schedule_verified"] is True
    assert jp225["r8_holiday_calendar_verified"] is False
    assert jp225["canonical_calendar_verified"] is False
    assert jp225["calendar_binding_verified"] is False
    assert jp225["required_evidence"] == [
        "VERSIONED_TSE_HOLIDAY_CALENDAR_2016_2018",
        "R8_DATE_LEVEL_EXCEPTION_CALENDAR",
    ]


def test_rejects_backfilled_holiday_completion() -> None:
    authority = deepcopy(_authority())
    rows = authority["records"]
    assert isinstance(rows, list)
    rows[0]["r8_holiday_calendar_verified"] = True

    with pytest.raises(
        SharedBR8HistoricalCalendarError,
        match="r8_holiday_calendar_verified",
    ):
        build_r8_historical_calendar_frontier(
            calendar_worklist=_worklist(),
            r8_manifest=_manifest(),
            authority_evidence=authority,
        )


def test_rejects_r8_window_drift() -> None:
    manifest = deepcopy(_manifest())
    manifest["source_max"] = "2018-05-19T19:30:00.000000+00:00"

    with pytest.raises(
        SharedBR8HistoricalCalendarError,
        match="source_max drift",
    ):
        build_r8_historical_calendar_frontier(
            calendar_worklist=_worklist(),
            r8_manifest=manifest,
            authority_evidence=_authority(),
        )


def test_rejects_non_official_authority_url() -> None:
    authority = deepcopy(_authority())
    rows = authority["records"]
    assert isinstance(rows, list)
    authorities = rows[0]["authorities"]
    assert isinstance(authorities, list)
    authorities[0]["source_url"] = "https://example.com/nikkei"

    with pytest.raises(
        SharedBR8HistoricalCalendarError,
        match="not official",
    ):
        build_r8_historical_calendar_frontier(
            calendar_worklist=_worklist(),
            r8_manifest=_manifest(),
            authority_evidence=authority,
        )
