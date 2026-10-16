"""VT31 native strict pre-COG source admission: real original COG/OPS no edits."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    LEGACY_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from scripts.vt31_trisession_online_real_g3_cog_20261015 import (
    replay_online_g3,
)

DAY = "2025-07-15"


def candle(day: str, hour: int, minute: int) -> M1Bar:
    start = datetime.fromisoformat(day).replace(
        tzinfo=NEW_YORK, hour=hour, minute=minute,
    ).astimezone(UTC)
    return M1Bar(
        opened_at=start, closed_at=start + timedelta(minutes=1),
        open=Decimal("100"), high=Decimal("101"),
        low=Decimal("99"), close=Decimal("100"),
    )


def rows(month: int, hour: int, *, omit: int | None = None):
    day = f"2025-{month:02d}-15"
    return [
        {
            "opened_at": x.opened_at.isoformat(),
            "closed_at": x.closed_at.isoformat(),
            "open": str(x.open), "high": str(x.high),
            "low": str(x.low), "close": str(x.close),
        }
        for minute in range(60) if minute != omit
        for x in [candle(day, hour, minute)]
    ]


def new_trader() -> VT31Trader:
    return VT31Trader(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
        strict_source_admission=True,
    )


@pytest.mark.parametrize("month,offset", [(1, 5), (7, 4)])
def test_one_native_trader_all_three_ict_clocks_DST(month, offset):
    trader = new_trader()
    day = f"2025-{month:02d}-15"
    n = 0
    for hour, session in (
        (3, SessionId.LONDON),
        (9, None),
        (10, SessionId.NY_AM),
        (14, SessionId.NY_PM),
    ):
        for minute in range(60):
            c = candle(day, hour, minute)
            assert c.opened_at.hour == (hour + offset) % 24
            result = trader.on_closed_m1(c)
            n += 1
            assert not result.order_authorized
            assert not result.position_authorized
            if session is None:
                assert result.cognition is None
                assert result.session_window is None
            else:
                assert result.cognition is not None
                assert result.session_window is session
                assert result.source_wait_reason is None
                assert result.cognition.as_of == c.closed_at
                assert result.source_h1_09_complete is (
                    True if session is SessionId.NY_AM else None
                )
    assert n == trader.total_closed_m1
    assert trader.total_source_windows_seen == 3
    snapshot = trader.snapshot()
    assert snapshot["registered_trader_count"] == 1
    assert snapshot["strict_source_admission_research_only"] is True
    assert snapshot["source_method_profiles_unsigned"] == {
        "VT31_LONDON": "ICT_GENERAL_2023",
        "VT31_NY_AM": "TTRADES_NY_AM_2025",
        "VT31_NY_PM": "ICT_GENERAL_2023",
    }
    assert not snapshot["methodology_certified"]
    assert not snapshot["cognition_certified"]
    assert not snapshot["certified"]


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("missing_09", [0, 1, 39, 59])
def test_missing_any_09h_m1_forces_nyam_wait_before_original_cog(
    month, missing_09,
):
    trader = new_trader()
    day = f"2025-{month:02d}-15"
    london = trader.on_closed_m1(candle(day, 3, 0))
    assert london.cognition is not None
    for minute in range(60):
        if minute != missing_09:
            trader.on_closed_m1(candle(day, 9, minute))
    for minute in range(60):
        result = trader.on_closed_m1(candle(day, 10, minute))
        assert result.source_wait_reason == "SOURCE_09H_INCOMPLETE_WAIT"
        assert result.source_h1_09_complete is False
        assert result.cognition is None
        assert result.operational_phase is None
    assert (day, SessionId.NY_AM) not in trader._windows
    pm = trader.on_closed_m1(candle(day, 14, 0))
    assert pm.cognition is not None
    assert pm.source_h1_09_complete is None
    assert trader.snapshot()["source_windows_seen"] == 2
    assert trader.cognition._observed_count == 121


@pytest.mark.parametrize("hour,session", [
    (3, SessionId.LONDON),
    (14, SessionId.NY_PM),
])
def test_ict_general_does_not_borrow_ttrades_h1(hour, session):
    trader = new_trader()
    out = trader.on_closed_m1(candle(DAY, hour, 0))
    assert out.cognition is not None
    assert out.session_window is session
    assert out.source_wait_reason is None
    assert out.source_h1_09_complete is None


@pytest.mark.parametrize("hour,session", [
    (3, SessionId.LONDON),
    (10, SessionId.NY_AM),
    (14, SessionId.NY_PM),
])
def test_missing_first_m1_waits_without_bootstrapping_ops(hour, session):
    trader = new_trader()
    if hour == 10:
        for minute in range(60):
            trader.on_closed_m1(candle(DAY, 9, minute))
    out = trader.on_closed_m1(candle(DAY, hour, 1))
    assert out.source_wait_reason == "SOURCE_START_MISSING_WAIT"
    assert out.cognition is None
    assert out.operational_phase is None
    assert (DAY, session) not in trader._windows


@pytest.mark.parametrize("hour,session", [
    (3, SessionId.LONDON),
    (10, SessionId.NY_AM),
    (14, SessionId.NY_PM),
])
def test_first_two_asof_survive_midwindow_gap_but_no_further_COG(
    hour, session,
):
    trader = new_trader()
    if hour == 10:
        for minute in range(60):
            trader.on_closed_m1(candle(DAY, 9, minute))
    first = trader.on_closed_m1(candle(DAY, hour, 0))
    second = trader.on_closed_m1(candle(DAY, hour, 1))
    assert first.cognition is not None and second.cognition is not None
    assert first.cognition.as_of < second.cognition.as_of
    for minute in range(3, 60):
        out = trader.on_closed_m1(candle(DAY, hour, minute))
        assert out.source_wait_reason == "SOURCE_GAP_WAIT"
        assert out.cognition is None
        assert out.operational_phase is None
    assert (DAY, session) in trader._windows
    assert trader._windows[(DAY, session)].last_closed == (
        second.observed_at
    )
    assert trader.total_closed_m1 == (59 if hour != 10 else 119)


def test_other_day_09h_cannot_pretend_to_complete_nyam_current_day():
    trader = new_trader()
    for minute in range(60):
        trader.on_closed_m1(candle("2025-07-14", 9, minute))
    out = trader.on_closed_m1(candle(DAY, 10, 0))
    assert out.source_wait_reason == "SOURCE_09H_INCOMPLETE_WAIT"
    assert out.source_h1_09_complete is False
    assert out.cognition is None


def test_unadmitted_nyam_does_not_call_original_cog_even_once():
    trader = new_trader()
    initial = trader.cognition._observed_count
    out = trader.on_closed_m1(candle(DAY, 10, 0))
    assert out.source_wait_reason == "SOURCE_09H_INCOMPLETE_WAIT"
    assert trader.cognition.latest_assessment is None
    assert trader.cognition._observed_count == initial + 1


@pytest.mark.parametrize("bad", ["true", 1, None])
def test_strict_admission_must_be_real_boolean(bad):
    with pytest.raises(ValueError, match="REQUIRES_BOOL"):
        VT31Trader(
            framework_policy=G3_MSS_FRAMEWORK_POLICY,
            strict_source_admission=bad,
        )


def test_no_legacy_silent_strict_opt_in():
    with pytest.raises(ValueError, match="REQUIRES_EXPLICIT_G3"):
        VT31Trader(strict_source_admission=True)
    with pytest.raises(ValueError, match="REQUIRES_EXPLICIT_G3"):
        VT31Trader(
            framework_policy=LEGACY_FRAMEWORK_POLICY,
            strict_source_admission=True,
        )


def test_strict_opt_in_immutable_even_when_public_value_changes():
    trader = new_trader()
    trader.strict_source_admission = False
    with pytest.raises(ValueError, match="POLICY_CHANGED_AFTER_CONSTRUCTION"):
        trader.on_closed_m1(candle(DAY, 9, 0))
    with pytest.raises(ValueError, match="POLICY_CHANGED_AFTER_CONSTRUCTION"):
        trader.research_observe_incomplete_source_m1(candle(DAY, 10, 0))
    assert trader.cognition._observed_count == 0


@pytest.mark.parametrize("month", [1, 7])
def test_new_native_mode_same_all_session_online_m1_witnesses(month):
    market = [
        *rows(month, 3), *rows(month, 9),
        *rows(month, 10), *rows(month, 14),
    ]
    ref, _ = replay_online_g3(market, expected_m1=len(market))
    native, rt = replay_online_g3(
        market, expected_m1=len(market),
        native_trader_g3=True, native_strict_source_admission=True,
    )
    assert {k: v.record() for k, v in native.items()} == {
        k: v.record() for k, v in ref.items()
    }
    assert rt["native_strict_preCOG_M0_source_admission"]
    assert rt["native_VT31Trader_G3_integration_complete"]


def test_refuses_native_strict_when_native_trader_not_selected():
    with pytest.raises(ValueError, match="REQUIRES_NATIVE_G3"):
        replay_online_g3([], expected_m1=0, native_strict_source_admission=True)


def test_default_native_existing_non_strict_behavior_unchanged():
    trader = VT31Trader(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    out = trader.on_closed_m1(candle(DAY, 10, 0))
    assert out.cognition is not None
    assert out.source_wait_reason is None
    assert not trader.snapshot()["strict_source_admission_research_only"]
