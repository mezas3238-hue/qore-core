"""VT31 tri-session real M1 audit: EST/EDT and source completeness only."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    M1Bar,
    SessionId,
)
from scripts.vt31_m0_predecision_method_router_20261015 import PREDECLARED
from scripts.vt31_trisession_real_m1_causal_coverage_20261015 import (
    COMPLETE,
    EMPTY,
    H1_WAIT,
    PARTIAL,
    _complete_hour,
    audit_session,
    collect_tri_hour_groups,
)

DAY = "2025-07-15"


def source_hour(day: str, hour: int) -> tuple[M1Bar, ...]:
    local = datetime.fromisoformat(day).replace(hour=hour, tzinfo=NEW_YORK)
    opened = local.astimezone(UTC)
    return tuple(
        M1Bar(
            opened + timedelta(minutes=i),
            opened + timedelta(minutes=i + 1),
            Decimal("100"), Decimal("102"),
            Decimal("98"), Decimal("101"),
        )
        for i in range(60)
    )


@pytest.mark.parametrize("month,offset", [(1, 5), (7, 4)])
@pytest.mark.parametrize(
    "session,hour",
    [
        (SessionId.LONDON, 3),
        (SessionId.NY_AM, 10),
        (SessionId.NY_PM, 14),
    ],
)
def test_all_silver_bullet_sessions_real_ny_dst_and_no_certificate(
    month, offset, session, hour,
):
    day = f"2025-{month:02d}-15"
    bars = source_hour(day, hour)
    hours = {hour: bars, 9: source_hour(day, 9)}
    x = audit_session(day=day, session=session, hours=hours)
    assert x["state"] == COMPLETE
    assert x["observed_window_m1"] == 60
    assert x["missing_window_m1"] == 0
    assert x["utc_window_open"] == bars[0].opened_at.isoformat()
    assert x["utc_window_end"] == bars[-1].closed_at.isoformat()
    assert bars[0].opened_at.hour == (hour + offset) % 24
    assert x["preregistered_profile"] == PREDECLARED.profile_for(session)
    assert x["h1_09_ttrades_required"] is (session is SessionId.NY_AM)
    assert x["h1_09_ttrades_complete"] is (
        True if session is SessionId.NY_AM else None
    )
    assert not (
        x["methodology_certified"]
        or x["cognition_certified"]
        or x["trader_certified"]
        or x["cog_runtime_integrated"]
        or x["trading_or_sizing"]
    )


@pytest.mark.parametrize("session,hour", [
    (SessionId.LONDON, 3), (SessionId.NY_PM, 14),
])
def test_london_and_pm_do_not_borrow_ttrades_09h(session, hour):
    result = audit_session(
        day=DAY, session=session,
        hours={hour: source_hour(DAY, hour), 9: ()},
    )
    assert result["state"] == COMPLETE
    assert result["h1_09_ttrades_complete"] is None
    assert not result["h1_09_ttrades_required"]


@pytest.mark.parametrize("minute", [0, 1, 12, 30, 59])
def test_nyam_incomplete_h1_always_waits_without_promoting_method(minute):
    h1 = tuple(
        b for i, b in enumerate(source_hour(DAY, 9)) if i != minute
    )
    x = audit_session(
        day=DAY, session=SessionId.NY_AM,
        hours={9: h1, 10: source_hour(DAY, 10)},
    )
    assert x["state"] == H1_WAIT
    assert x["window_m1_complete"]
    assert not x["cognition_certified"]


@pytest.mark.parametrize("session,hour", [
    (SessionId.LONDON, 3),
    (SessionId.NY_AM, 10),
    (SessionId.NY_PM, 14),
])
@pytest.mark.parametrize("missing", [0, 13, 59])
def test_all_three_sessions_cannot_mask_missing_window_minute(
    session, hour, missing,
):
    bars = tuple(
        x for i, x in enumerate(source_hour(DAY, hour)) if i != missing
    )
    x = audit_session(
        day=DAY, session=session, hours={
            hour: bars, 9: source_hour(DAY, 9),
        },
    )
    assert x["state"] == PARTIAL
    assert x["observed_window_m1"] == 59
    assert x["missing_window_m1"] == 1
    assert not x["window_m1_complete"]


@pytest.mark.parametrize("session", list(SessionId))
def test_zero_bars_is_unknown_not_broker_closed(session):
    x = audit_session(
        day=DAY, session=session, hours={9: source_hour(DAY, 9)},
    )
    assert x["state"] == EMPTY
    assert x["missing_window_m1"] == 60
    assert not x["methodology_certified"]


def test_nyam_no_window_and_no_h1_returns_specific_h1_wait():
    x = audit_session(day=DAY, session=SessionId.NY_AM, hours={})
    assert x["state"] == H1_WAIT
    assert x["observed_window_m1"] == 0


@pytest.mark.parametrize("session,hour", [
    (SessionId.LONDON, 3), (SessionId.NY_AM, 10),
    (SessionId.NY_PM, 14),
])
def test_future_window_or_wrong_session_never_misclassified_complete(
    session, hour,
):
    with pytest.raises(ValueError, match="OUTSIDE_DECLARED"):
        audit_session(
            day=DAY, session=session,
            hours={hour: source_hour(DAY, 3 if hour != 3 else 10)},
        )


def test_repeated_timestamp_rejected_and_no_intrabar_guess():
    x = source_hour(DAY, 3)
    with pytest.raises(ValueError, match="DUPLICATE"):
        _complete_hour(day=DAY, hour=3, bars=x[:30] + (x[29],) + x[31:])


def test_unordered_candles_not_complete_even_with_full_count():
    x = source_hour(DAY, 14)
    assert not _complete_hour(
        day=DAY, hour=14, bars=tuple(reversed(x)),
    )


def test_excess_minutes_in_one_hour_rejected():
    x = source_hour(DAY, 10)
    with pytest.raises(ValueError, match="MORE_THAN_60"):
        _complete_hour(day=DAY, hour=10, bars=x + (x[0],))


def test_wrong_session_type_fails_closed():
    with pytest.raises(ValueError, match="UNTYPED"):
        audit_session(
            day=DAY, session="VT31_LONDON",
            hours={3: source_hour(DAY, 3)},
        )


def test_single_pass_stream_rejects_duplicate_source_minutes():
    x = source_hour(DAY, 9)
    rows = [
        {
            "opened_at": b.opened_at.isoformat(),
            "closed_at": b.closed_at.isoformat(),
            "open": str(b.open), "high": str(b.high),
            "low": str(b.low), "close": str(b.close),
        }
        for b in x[:2]
    ]
    with pytest.raises(ValueError, match="NONCAUSAL_OR_DUPLICATED"):
        collect_tri_hour_groups(rows + [rows[1]], expected_m1=3)


def test_single_pass_stream_rejects_source_count_mismatch():
    x = source_hour(DAY, 9)[0]
    rows = [{
        "opened_at": x.opened_at.isoformat(),
        "closed_at": x.closed_at.isoformat(),
        "open": str(x.open), "high": str(x.high),
        "low": str(x.low), "close": str(x.close),
    }]
    with pytest.raises(ValueError, match="BAR_COUNT_CHANGED"):
        collect_tri_hour_groups(rows, expected_m1=3)
    groups, total = collect_tri_hour_groups(rows, expected_m1=1)
    assert total == 1
    assert len(groups[DAY][9]) == 1


def test_stream_naive_timestamp_and_corrupt_ohlc_fail_closed():
    x = source_hour(DAY, 9)[0]
    record = {
        "opened_at": x.opened_at.isoformat(),
        "closed_at": x.closed_at.isoformat(),
        "open": "100", "high": "102", "low": "98", "close": "101",
    }
    bad = dict(record, opened_at=x.opened_at.replace(tzinfo=None).isoformat())
    with pytest.raises(ValueError, match="SOURCE_NAIVE_M1"):
        collect_tri_hour_groups([bad], expected_m1=1)
    bad = dict(record, low="103")
    with pytest.raises(ValueError, match="OHLC"):
        collect_tri_hour_groups([bad], expected_m1=1)
