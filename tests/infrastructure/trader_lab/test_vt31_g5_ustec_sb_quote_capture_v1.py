"""Pre-price-source-only VT31 USTEC historical BID/ASK capture contract tests."""
from datetime import datetime
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt31_g5_ustec_sb_quote_capture_v1 import (
    DAYS_NY,
    EXPECTED_OFFSETS,
    HOURS_NY,
    IDENTITY,
    MAX_REQUESTS_ALL,
    frozen_windows,
)


def test_frozen_pilot_days_are_in_exposed_dev_not_fresh_holdout() -> None:
    assert DAYS_NY == ("2024-06-12", "2025-01-15")
    assert HOURS_NY == (("LONDON", 3), ("NY_AM", 10), ("NY_PM", 14))
    assert IDENTITY.startswith("VT31_G5_")
    assert MAX_REQUESTS_ALL == 300


def test_new_york_silver_bullet_summer_dst_source_hours() -> None:
    expected = [
        ("LONDON", "2024-06-12T07:00:00+00:00", "2024-06-12T08:00:00+00:00"),
        ("NY_AM", "2024-06-12T14:00:00+00:00", "2024-06-12T15:00:00+00:00"),
        ("NY_PM", "2024-06-12T18:00:00+00:00", "2024-06-12T19:00:00+00:00"),
    ]
    rows = frozen_windows()
    assert len(rows) == 6
    assert [
        (w["session"], w["start_utc"], w["end_utc"])
        for w in rows if w["day_ny"] == "2024-06-12"
    ] == expected


def test_new_york_silver_bullet_winter_est_source_hours() -> None:
    expected = [
        ("LONDON", "2025-01-15T08:00:00+00:00", "2025-01-15T09:00:00+00:00"),
        ("NY_AM", "2025-01-15T15:00:00+00:00", "2025-01-15T16:00:00+00:00"),
        ("NY_PM", "2025-01-15T19:00:00+00:00", "2025-01-15T20:00:00+00:00"),
    ]
    rows = frozen_windows()
    assert [
        (w["session"], w["start_utc"], w["end_utc"])
        for w in rows if w["day_ny"] == "2025-01-15"
    ] == expected


def test_per_window_utc_ranges_unchanged_one_hour_and_offset_correct() -> None:
    rows = frozen_windows()
    ny = ZoneInfo("America/New_York")
    for w in rows:
        begin = datetime.fromisoformat(w["start_utc"])
        end = datetime.fromisoformat(w["end_utc"])
        assert (end - begin).total_seconds() == 3600
        actual_ny = begin.astimezone(ny)
        assert actual_ny.date().isoformat() == w["day_ny"]
        assert actual_ny.hour in (3, 10, 14)
        assert int(actual_ny.utcoffset().total_seconds() / 3600) == EXPECTED_OFFSETS[w["day_ny"]]


def test_no_broker_mutations_in_capture_source_contract() -> None:
    from inspect import getsource
    from qore.infrastructure.trader_lab import vt31_g5_ustec_sb_quote_capture_v1 as m

    source = getsource(m.capture)
    assert "ProtoOAGetTickDataReq" not in source or "_native_fetch" in source
    assert "client.request(" in source  # symbol list source-only
    assert "ProtoOASymbolsListReq" in source
    assert "ProtoOANewOrderReq" not in source
    assert "ProtoOAAmendOrderReq" not in source
    assert "ProtoOACancelOrderReq" not in source
    assert "oauth_refresh_attempts" in source
    assert "live_authorized" in source
