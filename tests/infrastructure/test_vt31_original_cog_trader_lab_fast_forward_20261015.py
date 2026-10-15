"""Qualitative VT31 G3 cognition 1x vs native Trader Lab 32x schedule parity."""
from __future__ import annotations

from datetime import timedelta

import pytest

from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardSchedule,
    TraderLabFastForwardStep,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import SessionId
from scripts.vt31_original_cog_trader_lab_fast_forward_20261015 import (
    FACTOR,
    _case,
    native_schedule,
    run_original_vt31_traderlab_timewarp,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize(
    "session", [SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM],
)
def test_original_cog_causal_m1_decisions_same_at_1x_and_trader_lab_32x(
    month, session,
):
    yes = _case(session=session, month=month, no_mss=False)
    no = _case(session=session, month=month, no_mss=True)
    for row, expected_action in ((yes, "SHORT"), (no, "WAIT")):
        assert row["normal_1x"] == row["traderlab_simulated_32x"]
        assert row["normal_1x"]["cog_original_traces"][0]["action"] == "WAIT"
        assert row["normal_1x"]["cog_original_traces"][1]["action"] == (
            expected_action
        )
        assert row["native_schedule_acceleration_factor"] == FACTOR
        assert row["native_schedule_all_m1_closed_instants_visited"]
        assert row["normal_simulated_elapsed_microseconds"] == (
            FACTOR * row["accelerated_wall_advance_microseconds"]
        )
        assert row["parity_by_canonical_trace_and_source_sha256"] is True
        assert row["simulated_acceleration_not_CPU_performance"] is True
        assert row["real_traderlab_candidate_L3_certified"] is False
        assert row["methodology_certified"] is False
        assert row["cognition_certified"] is False
        assert row["orders"] == row["trader_sizing"] == 0


def test_native_traderlab_schedule_visits_every_closed_m1_once():
    m1, _ = short_fixture(session=SessionId.NY_PM, month=1)
    schedule = native_schedule(m1)
    assert isinstance(schedule, TraderLabFastForwardSchedule)
    assert tuple(x.simulated_now for x in schedule.steps) == tuple(
        bar.closed_at for bar in m1
    )
    assert schedule.acceleration_factor == 32
    with pytest.raises(TraderLabValidationError):
        TraderLabFastForwardSchedule(
            steps=(
                TraderLabFastForwardStep(
                    simulated_now=m1[-1].closed_at,
                    wall_clock_advance=timedelta(seconds=1),
                ),
                TraderLabFastForwardStep(
                    simulated_now=m1[-2].closed_at,
                    wall_clock_advance=timedelta(seconds=1),
                ),
            ),
            acceleration_factor=32,
        )


def test_genuine_original_cog_parity_cannot_automatically_certify_method():
    report = run_original_vt31_traderlab_timewarp()
    assert len(report["cases"]) == 12
    assert report["all_trace_parity"] is True
    assert report["actual_native_trader_lab_schedule_used"] is True
    assert report["native_l3_real_candidate_qualified"] is False
    assert report["speedup_measured_CPU"] is False
    assert report["methodology_certified"] is False
    assert report["cognition_certified"] is False
    assert report["human_cog_ops_signatures_verified"] is False
    assert report["economic_backtest_done"] is False
    assert report["return_pf_dd_sharpe_sortino"] is None
    assert report["broker_orders"] == report["sizing"] == 0
    assert report["live"] is False
    assert report["cog_original_sha"]["git_blob_sha1"] == (
        "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
    )
