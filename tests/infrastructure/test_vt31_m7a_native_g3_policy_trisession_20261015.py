"""M7-A: original VT31Trader native G3 to original G3 OPS, fail-closed."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    LEGACY_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from scripts.vt31_trisession_online_real_g3_cog_20261015 import (
    SOURCE_GAP,
    SOURCE_H1,
    replay_online_g3,
)

DAY = "2025-07-15"


def bar(at: datetime) -> M1Bar:
    return M1Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("98"),
        close=Decimal("101"),
    )


def hour_rows(month: int, hour: int, *, omit: int | None = None):
    opened = datetime(
        2025, month, 15, hour, tzinfo=NEW_YORK,
    ).astimezone(UTC)
    return [
        {
            "opened_at": (opened + timedelta(minutes=i)).isoformat(),
            "closed_at": (
                opened + timedelta(minutes=i + 1)
            ).isoformat(),
            "open": "100",
            "high": "102",
            "low": "98",
            "close": "101",
        }
        for i in range(60) if i != omit
    ]


def test_default_native_coordinator_stays_legacy_research_only():
    trader = VT31Trader()
    assert trader.framework_policy == LEGACY_FRAMEWORK_POLICY
    assert trader.cognition.framework_policy == LEGACY_FRAMEWORK_POLICY
    opened = datetime(2025, 7, 15, 3, tzinfo=NEW_YORK).astimezone(UTC)
    observed = trader.on_closed_m1(bar(opened))
    assert observed.cognition is not None
    assert trader._windows[(DAY, SessionId.LONDON)].framework_policy == (
        LEGACY_FRAMEWORK_POLICY
    )
    assert not observed.order_authorized
    assert not observed.position_authorized
    assert not trader.snapshot()["certified"]


@pytest.mark.parametrize("month", [1, 7])
def test_explicit_g3_native_coordinator_three_sessions_dst(month):
    trader = VT31Trader(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    d = f"2025-{month:02d}-15"
    for hour, session in (
        (3, SessionId.LONDON),
        (10, SessionId.NY_AM),
        (14, SessionId.NY_PM),
    ):
        opened = datetime(
            2025, month, 15, hour, tzinfo=NEW_YORK,
        ).astimezone(UTC)
        for minute in range(3):
            observed = trader.on_closed_m1(
                bar(opened + timedelta(minutes=minute)),
            )
            assert observed.session_window is session
            assert observed.cognition is not None
            assert observed.cognition.as_of == observed.observed_at
            assert not observed.order_authorized
            assert not observed.position_authorized
        assert trader._windows[(d, session)].framework_policy == (
            G3_MSS_FRAMEWORK_POLICY
        )
    snapshot = trader.snapshot()
    assert snapshot["source_windows_seen"] == 3
    assert snapshot["single_cognitive_memory"]
    assert snapshot["registered_trader_count"] == 1
    assert snapshot["G3_opt_in_research_only"]
    assert snapshot["explicit_framework_policy"] == G3_MSS_FRAMEWORK_POLICY
    assert not snapshot["methodology_certified"]
    assert not snapshot["cognition_certified"]
    assert not snapshot["live_authorized"]


@pytest.mark.parametrize("framework", [
    "ICT_GENERAL_2023",
    "TTRADES_NY_AM_2025",
    "FAKE_G4",
])
def test_unrecognized_framework_rejected_pre_ingress(framework):
    with pytest.raises(ValueError, match="UNKNOWN_EXPLICIT_FRAMEWORK"):
        VT31Trader(framework_policy=framework)


@pytest.mark.parametrize("framework,cognition", [
    (
        G3_MSS_FRAMEWORK_POLICY,
        VT31CleanroomCognition(framework_policy=LEGACY_FRAMEWORK_POLICY),
    ),
    (
        LEGACY_FRAMEWORK_POLICY,
        VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY),
    ),
    (
        None,
        VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY),
    ),
])
def test_mismatched_source_framework_rejected_before_market(
    framework, cognition,
):
    with pytest.raises(ValueError, match="FRAMEWORK_MISMATCH_BEFORE_M1"):
        VT31Trader(cognition=cognition, framework_policy=framework)
    assert cognition._observed_count == 0
    assert cognition.latest_assessment is None


def test_mutation_of_policy_rejected_before_cognition_or_ops():
    trader = VT31Trader(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    original = trader.cognition._observed_count
    trader.cognition.framework_policy = LEGACY_FRAMEWORK_POLICY
    opened = datetime(2025, 7, 15, 3, tzinfo=NEW_YORK).astimezone(UTC)
    with pytest.raises(ValueError, match="POLICY_CHANGED_AFTER_CONSTRUCTION"):
        trader.on_closed_m1(bar(opened))
    assert trader.cognition._observed_count == original
    assert trader.snapshot()["source_windows_seen"] == 0
    with pytest.raises(ValueError, match="POLICY_CHANGED_AFTER_CONSTRUCTION"):
        trader.research_observe_incomplete_source_m1(bar(opened))
    assert trader.cognition._observed_count == original


@pytest.mark.parametrize("month", [1, 7])
def test_native_and_reference_same_online_small_casebook(month):
    rows = [
        *hour_rows(month, 3),
        *hour_rows(month, 9),
        *hour_rows(month, 10),
        *hour_rows(month, 14),
    ]
    reference, r_summary = replay_online_g3(
        rows, expected_m1=len(rows),
    )
    native, n_summary = replay_online_g3(
        rows, expected_m1=len(rows), native_trader_g3=True,
    )
    assert {
        key: value.record() for key, value in native.items()
    } == {
        key: value.record() for key, value in reference.items()
    }
    assert n_summary["native_VT31Trader_G3_integration_complete"]
    assert not r_summary["native_VT31Trader_G3_integration_complete"]
    assert n_summary["original_ops_G3_research_windows"] == 3
    assert n_summary["source_bars_consumed"] == len(rows)


def test_native_missing_nyam_h1_does_not_poison_london_or_nypm():
    rows = [
        *hour_rows(7, 3),
        *hour_rows(7, 9, omit=59),
        *hour_rows(7, 10),
        *hour_rows(7, 14),
    ]
    native, runtime = replay_online_g3(
        rows, expected_m1=len(rows), native_trader_g3=True,
    )
    assert native[(DAY, SessionId.NY_AM)].terminal_wait_reason == SOURCE_H1
    assert native[(DAY, SessionId.NY_AM)].actual_g3_invocations == 0
    assert native[(DAY, SessionId.LONDON)].actual_g3_invocations == 60
    assert native[(DAY, SessionId.NY_PM)].actual_g3_invocations == 60
    assert runtime["source_bars_consumed"] == len(rows)


def test_native_midwindow_gap_preserves_two_prior_online_assessments():
    rows = [*hour_rows(7, 9), *hour_rows(7, 14, omit=2)]
    native, _ = replay_online_g3(
        rows, expected_m1=len(rows), native_trader_g3=True,
    )
    pm = native[(DAY, SessionId.NY_PM)]
    assert pm.actual_g3_invocations == 2
    assert pm.terminal_wait_reason == SOURCE_GAP
    assert pm.observed_m1 == 59
