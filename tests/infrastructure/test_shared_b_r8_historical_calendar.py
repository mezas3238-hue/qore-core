from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_r8_historical_calendar import (
    SharedBR8HistoricalCalendarError,
    build_r8_historical_calendar_frontier,
)

LEGAL_HOLIDAYS = (
    "2016-04-29", "2016-05-03", "2016-05-04", "2016-05-05",
    "2016-07-18", "2016-08-11", "2016-09-19", "2016-09-22",
    "2016-10-10", "2016-11-03", "2016-11-23", "2016-12-23",
    "2017-01-01", "2017-01-02", "2017-01-09", "2017-02-11",
    "2017-03-20", "2017-04-29", "2017-05-03", "2017-05-04",
    "2017-05-05", "2017-07-17", "2017-08-11", "2017-09-18",
    "2017-09-23", "2017-10-09", "2017-11-03", "2017-11-23",
    "2017-12-23", "2018-01-01", "2018-01-08", "2018-02-11",
    "2018-02-12", "2018-03-21", "2018-04-29", "2018-04-30",
    "2018-05-03", "2018-05-04", "2018-05-05",
)

RULE_BASED_CLOSURES = tuple(sorted({
    *LEGAL_HOLIDAYS,
    "2016-12-31",
    "2017-01-03",
    "2017-12-31",
    "2018-01-02",
    "2018-01-03",
}))


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
                "r8_legal_holiday_dates_verified": True,
                "r8_legal_holiday_dates": list(LEGAL_HOLIDAYS),
                "r8_rule_based_non_business_dates_verified": True,
                "r8_rule_based_non_business_dates": list(RULE_BASED_CLOSURES),
                "r8_rule_based_non_business_date_count": 44,
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
                    {"source_url": "https://eco.mtk.nao.ac.jp/a"},
                    {"source_url": "https://eco.mtk.nao.ac.jp/b"},
                    {"source_url": "https://eco.mtk.nao.ac.jp/c"},
                    {"source_url": "https://www.jpx.co.jp/english/equities/a"},
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
    assert payload["r8_legal_holiday_set_verified_count"] == 1
    assert payload["r8_rule_based_non_business_calendar_verified_count"] == 1
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
    assert jp225["r8_legal_holiday_dates_verified"] is True
    assert jp225["r8_rule_based_non_business_dates_verified"] is True
    assert jp225["r8_rule_based_non_business_date_count"] == 44
    assert jp225["r8_holiday_calendar_verified"] is False
    assert jp225["canonical_calendar_verified"] is False
    assert jp225["calendar_binding_verified"] is False
    assert jp225["required_evidence"] == [
        "R8_EXTRAORDINARY_NON_BUSINESS_DAY_EVIDENCE",
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
