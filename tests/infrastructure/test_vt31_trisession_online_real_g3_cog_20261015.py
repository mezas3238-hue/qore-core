"""One ORIGINAL VT31 G3: online M1 source, H1 veto only NYAM, no leakage."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    SessionId,
)
from scripts.vt31_trisession_online_real_g3_cog_20261015 import (
    SOURCE_GAP,
    SOURCE_H1,
    SOURCE_START,
    replay_online_g3,
    sealed_ledger_index,
)


def hour_rows(month: int, hour: int, *, minute_filter=None):
    local = datetime(2025, month, 15, hour, tzinfo=NEW_YORK).astimezone(UTC)
    rows = []
    for minute in range(60):
        if minute_filter is not None and not minute_filter(minute):
            continue
        at = local + timedelta(minutes=minute)
        rows.append({
            "opened_at": at.isoformat(),
            "closed_at": (at + timedelta(minutes=1)).isoformat(),
            "open": "100", "high": "102", "low": "98", "close": "101",
        })
    return rows


@pytest.mark.parametrize("month", [1, 7])
def test_single_real_producer_across_all_three_dst_windows(month):
    rows = [
        *hour_rows(month, 3),
        *hour_rows(month, 9),
        *hour_rows(month, 10),
        *hour_rows(month, 14),
    ]
    traces, engine = replay_online_g3(rows, expected_m1=len(rows))
    d = f"2025-{month:02d}-15"
    for s in SessionId:
        trace = traces[(d, s)]
        assert trace.observed_m1 == 60
        assert trace.actual_g3_invocations == 60
        assert trace.terminal_wait_reason is None
        assert trace.positive_g3_observations <= 60
    assert traces[(d, SessionId.NY_AM)].h1_complete_at_10_ny is True
    assert traces[(d, SessionId.LONDON)].h1_complete_at_10_ny is None
    assert traces[(d, SessionId.NY_PM)].h1_complete_at_10_ny is None
    assert engine["source_bars_consumed"] == len(rows)
    assert engine["one_trader"] == "VT31"
    assert engine["framework_policy"] == G3_MSS_FRAMEWORK_POLICY
    assert engine["one_cognition"] and engine["no_execution_or_sizing"]
    assert engine["original_ops_G3_research_windows"] == 3
    assert not engine["native_VT31Trader_G3_integration_complete"]
    assert engine["M7_blocker_native_coordinator_still_defaults_OPS_to_LEGACY"]


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("missing9", [0, 12, 59])
def test_incomplete_09h_inhibits_original_nyam_cog_before_any_assessment(
    month, missing9,
):
    rows = [
        *hour_rows(month, 3),
        *hour_rows(month, 9, minute_filter=lambda x: x != missing9),
        *hour_rows(month, 10),
        *hour_rows(month, 14),
    ]
    traces, engine = replay_online_g3(rows, expected_m1=len(rows))
    d = f"2025-{month:02d}-15"
    nyam = traces[(d, SessionId.NY_AM)]
    assert nyam.observed_m1 == 60
    assert nyam.actual_g3_invocations == 0
    assert nyam.terminal_wait_reason == SOURCE_H1
    assert nyam.h1_complete_at_10_ny is False
    assert traces[(d, SessionId.LONDON)].actual_g3_invocations == 60
    assert traces[(d, SessionId.NY_PM)].actual_g3_invocations == 60
    assert engine["source_bars_consumed"] == len(rows)


@pytest.mark.parametrize("session_hour,session", [
    (3, SessionId.LONDON),
    (10, SessionId.NY_AM),
    (14, SessionId.NY_PM),
])
def test_missing_first_m1_cannot_bootstrap_original_ops(session_hour, session):
    rows = [
        *hour_rows(7, 9),
        *hour_rows(7, session_hour, minute_filter=lambda x: x >= 1),
    ]
    rows.sort(key=lambda x: x["opened_at"])
    traces, engine = replay_online_g3(rows, expected_m1=len(rows))
    tr = traces[("2025-07-15", session)]
    assert tr.terminal_wait_reason == SOURCE_START
    assert tr.actual_g3_invocations == 0
    assert tr.observed_m1 == 59
    assert engine["source_bars_consumed"] == len(rows)


@pytest.mark.parametrize("session_hour,session", [
    (3, SessionId.LONDON),
    (10, SessionId.NY_AM),
    (14, SessionId.NY_PM),
])
def test_midwindow_gap_keeps_pre_gap_asof_but_vetoes_later_cog(
    session_hour, session,
):
    rows = [
        *hour_rows(7, 9),
        *hour_rows(7, session_hour, minute_filter=lambda x: x != 2),
    ]
    rows.sort(key=lambda x: x["opened_at"])
    traces, engine = replay_online_g3(rows, expected_m1=len(rows))
    tr = traces[("2025-07-15", session)]
    assert tr.actual_g3_invocations == 2
    assert tr.terminal_wait_reason == SOURCE_GAP
    assert tr.observed_m1 == 59
    assert engine["source_bars_consumed"] == len(rows)


@pytest.mark.parametrize("month", [1, 7])
def test_london_and_nypm_not_forced_to_have_09h_ttrades_history(month):
    rows = [
        *hour_rows(month, 3),
        *hour_rows(month, 14),
    ]
    d = f"2025-{month:02d}-15"
    traces, _ = replay_online_g3(rows, expected_m1=len(rows))
    for s in (SessionId.LONDON, SessionId.NY_PM):
        assert traces[(d, s)].actual_g3_invocations == 60
    assert (d, SessionId.NY_AM) not in traces


def test_nyam_first_m1_at_10_00_not_09_59_can_access_complete_09h():
    rows = [*hour_rows(7, 9), *hour_rows(7, 10, minute_filter=lambda m: m == 0)]
    traces, _ = replay_online_g3(rows, expected_m1=len(rows))
    tr = traces[("2025-07-15", SessionId.NY_AM)]
    assert tr.actual_g3_invocations == 1
    assert tr.h1_complete_at_10_ny is True
    assert tr.terminal_wait_reason is None


def test_duplicate_or_non_monotonic_market_rejected_before_cognition():
    rows = hour_rows(7, 3)[:2]
    with pytest.raises(ValueError, match="DUPLICATE"):
        replay_online_g3(rows + rows[1:], expected_m1=3)
    with pytest.raises(ValueError, match="DUPLICATE"):
        replay_online_g3(list(reversed(rows)), expected_m1=2)


def test_mismatch_total_m1_not_silently_reinterpreted():
    rows = hour_rows(7, 3)[:2]
    with pytest.raises(AssertionError, match="M1_AND_ONE_G3"):
        replay_online_g3(rows, expected_m1=3)


def test_source_input_naive_timestamp_is_impossible_to_admit():
    rows = hour_rows(7, 3)[:1]
    rows[0]["opened_at"] = datetime(2025, 7, 15, 3).isoformat()
    with pytest.raises(ValueError):
        replay_online_g3(rows, expected_m1=1)


def test_no_lookahead_to_later_h1_completion():
    rows = [
        *hour_rows(7, 9, minute_filter=lambda m: m < 59),
        *hour_rows(7, 10, minute_filter=lambda m: m < 3),
    ]
    traces, _ = replay_online_g3(rows, expected_m1=len(rows))
    tr = traces[("2025-07-15", SessionId.NY_AM)]
    assert tr.h1_complete_at_10_ny is False
    assert tr.actual_g3_invocations == 0
    assert tr.terminal_wait_reason == SOURCE_H1


def test_sealed_future_ledger_cannot_be_provided_to_online_replay():
    # Online API deliberately accepts only a market row iterable and count.
    import inspect

    names = inspect.signature(replay_online_g3).parameters
    assert tuple(names) == ("rows", "expected_m1")
    assert "ledger" not in names


def test_untrusted_posthoc_ledger_rejected_by_digest():
    with pytest.raises(ValueError, match="POSTHOC_LEDGER"):
        sealed_ledger_index({
            "casebook_json_sha256": "fake",
            "source_sha256": "fake",
            "all_2325_day_session_records": [],
        })


def test_source_day_timezone_aware_constant():
    assert datetime(2025, 1, 15, 3, tzinfo=NEW_YORK).utcoffset() == timedelta(hours=-5)
    assert datetime(2025, 7, 15, 3, tzinfo=NEW_YORK).utcoffset() == timedelta(hours=-4)

def test_original_g3_without_explicit_optin_rejected_at_constructor():
    """G3 COG must never silently bootstrap original LEGACY OPS."""
    from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
        VT31CleanroomCognition,
    )
    from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader

    original_cog = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    with pytest.raises(ValueError, match="FRAMEWORK_MISMATCH_BEFORE_M1"):
        VT31Trader(cognition=original_cog)
    assert original_cog._observed_count == 0
