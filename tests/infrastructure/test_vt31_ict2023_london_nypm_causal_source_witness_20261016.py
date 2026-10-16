"""ICT original 2023 London/PM research source; not TTrades 2025 NYAM."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    SessionId,
    Side,
)
from scripts import vt31_ict2023_london_nypm_causal_source_witness_20261016 as ict


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("sufficient", [True, False])
def test_16_original_ict_session_geometries_all_wait_author_cases(
    month, session, side, sufficient,
):
    _, v = ict.synthetic_london_pm_case(
        month=month, session=session, side=side, sufficient=sufficient,
    )
    assert v.action == "WAIT"
    assert v.geometry_state == (ict.WITNESS if sufficient else ict.SHORTFALL)
    assert v.projected_framework_handles == ("15" if sufficient else "5")
    assert v.side == side.value
    assert not v.primary_author_example_verified
    assert not v.dol_origin_verified
    assert not v.chosen_fvg_author_verified
    assert not v.chosen_mss_author_verified
    assert not v.entry_retest_confirmed
    assert not v.method_certified and not v.cognition_certified
    assert v.broker_orders == v.lot_sizing == 0


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
def test_dst_ny_local_clocks_not_fixed_utc(month, session):
    args, _ = ict.synthetic_london_pm_case(
        month=month, session=session, side=Side.LONG, sufficient=True,
    )
    local_open = args["closed_m1"][0].opened_at.astimezone(NEW_YORK)
    assert local_open.month == month
    assert local_open.hour == (3 if session is SessionId.LONDON else 14)
    assert local_open.minute == 0
    assert local_open.utcoffset().total_seconds() == (
        -5*3600 if month == 1 else -4*3600
    )


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
def test_unclosed_future_fvg_cannot_be_promoted(session):
    args, _ = ict.synthetic_london_pm_case(
        month=1, session=session, side=Side.LONG, sufficient=True,
    )
    changed_as_of = args["closed_m1"][-1].opened_at
    v = ict.ict2023_london_pm_source_witness(
        **(args | {"as_of": changed_as_of})
    )
    assert v.action == ict.REJECT
    assert v.reason == "SOURCE_TIME_GAP_FUTURE_OR_ASOF_CONTRADICTION"


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
def test_fvg_wick_overlap_and_missing_mss_do_not_promote(session):
    args, _ = ict.synthetic_london_pm_case(
        month=7, session=session, side=Side.LONG, sufficient=True,
    )
    bars = list(args["closed_m1"])
    third = bars[-1]
    bars[-1] = replace(third, low=bars[-3].high)
    no_fvg = ict.ict2023_london_pm_source_witness(
        **(args | {"closed_m1": tuple(bars)})
    )
    assert no_fvg.action == "WAIT"
    assert no_fvg.reason == "ICT2023_THREE_CLOSED_M1_FVG_NOT_PRESENT"
    bars = list(args["closed_m1"])
    middle = bars[4]
    bars[4] = replace(middle, close=Decimal("104"))
    no_mss = ict.ict2023_london_pm_source_witness(
        **(args | {"closed_m1": tuple(bars)})
    )
    assert no_mss.action == "WAIT"
    assert no_mss.reason == "ICT2023_MSS_GEOMETRY_INCOMPLETE"


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_target_observed_only_after_window_is_rejected(side):
    args, _ = ict.synthetic_london_pm_case(
        month=1, session=SessionId.NY_PM,
        side=side, sufficient=True,
    )
    v = ict.ict2023_london_pm_source_witness(
        **(args | {"target_observed_at": args["closed_m1"][3].closed_at})
    )
    assert v.action == ict.REJECT
    assert v.reason == "SOURCE_WINDOW_OR_DOL_SELECTION_NOT_PRECOMMITTED"


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
def test_future_mss_neighbour_or_fvg_index_is_rejected(session):
    args, _ = ict.synthetic_london_pm_case(
        month=1, session=session,
        side=Side.SHORT, sufficient=True,
    )
    for alternate in (
        {"swing_index": len(args["closed_m1"])-2},
        {"mss_confirm_index": 2},
        {"fvg_first_index": 4},
        {"swing_index": True},
    ):
        v = ict.ict2023_london_pm_source_witness(**(args | alternate))
        assert v.action == ict.REJECT
        assert v.reason == "SOURCE_MSS_FVG_INDICES_NOT_CAUSAL_OR_NOT_TYPED"


def test_ttrades_nyam_cannot_be_implicitly_routed_to_ict2023():
    args, _ = ict.synthetic_london_pm_case(
        month=1, session=SessionId.LONDON,
        side=Side.LONG, sufficient=True,
    )
    wrong_profile = ict.ict2023_london_pm_source_witness(
        **(args | {"profile": "TTRADES_NY_AM_2025"})
    )
    assert wrong_profile.action == ict.REJECT
    assert wrong_profile.reason == "ICT2023_PROFILE_NOT_FROZEN_LONDON_PM"
    wrong_session = ict.ict2023_london_pm_source_witness(
        **(args | {"session": SessionId.NY_AM})
    )
    assert wrong_session.action == ict.REJECT
    assert wrong_session.reason == "ICT2023_RESEARCH_LONDON_OR_NYPM_ONLY"


def test_mismatched_side_and_backward_dol_never_authorize():
    args, _ = ict.synthetic_london_pm_case(
        month=7, session=SessionId.LONDON,
        side=Side.LONG, sufficient=True,
    )
    backwards = ict.ict2023_london_pm_source_witness(
        **(args | {"target_level": Decimal("99")})
    )
    assert backwards.action == ict.REJECT
    assert backwards.reason == "ICT2023_TARGET_NOT_IN_DIRECTION_OF_STRUCTURE"
    short_on_long = ict.ict2023_london_pm_source_witness(
        **(args | {"side": Side.SHORT})
    )
    assert short_on_long.action == "WAIT"
    assert short_on_long.reason == "ICT2023_MSS_GEOMETRY_INCOMPLETE"


def test_window_expiration_does_not_make_entry_valid():
    args, _ = ict.synthetic_london_pm_case(
        month=7, session=SessionId.NY_PM,
        side=Side.LONG, sufficient=True,
    )
    six = args["closed_m1"]
    shift = timedelta(hours=1)
    future = tuple(replace(
        x, opened_at=x.opened_at+shift, closed_at=x.closed_at+shift
    ) for x in six)
    v = ict.ict2023_london_pm_source_witness(
        **(args | {
            "closed_m1": future,
            "as_of": future[-1].closed_at,
        })
    )
    assert v.action == ict.REJECT
    assert v.reason == "SOURCE_WINDOW_OR_DOL_SELECTION_NOT_PRECOMMITTED"


def test_dossier_three_sessions_lineage_without_fake_certificate():
    r = ict.ict_three_session_source_court()
    assert r["prereg_commit"] == ict.PREREG
    assert len(r["cases"]) == 16
    assert sum(x["geometry_state"] == ict.WITNESS for x in r["cases"]) == 8
    assert sum(x["geometry_state"] == ict.SHORTFALL for x in r["cases"]) == 8
    assert all(x["action"] == "WAIT" for x in r["cases"])
    assert r["ttrades_nyam_profile_not_used"]
    assert r["source_ict2023_found"]
    assert r["projected_10handles_not_trade_profit"]
    assert not r["london_author_certified"]
    assert not r["nypm_author_certified"]
    assert not r["entry_retest_author_homologated"]
    assert not r["methodology_certified"] and not r["cognition_certified"]
    assert not r["human_cog_ops_signed"] and not r["owner_profile_signed"]
    assert not r["native_g3_connected"]
    assert r["orders"] == r["sizing"] == 0 and not r["live"]
