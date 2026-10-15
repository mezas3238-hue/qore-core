"""VT31 M0-A temporal and complete NY 09-H1 gate: no COG on invalid input."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    SessionId,
    Side,
)
from scripts import vt31_m0_temporal_admission_20261015 as guard
from scripts.vt31_m0_predecision_method_router_20261015 import PREDECLARED
from scripts.vt31_original_cog_traderlab_32x_long_short_20261015 import (
    mirror_long_history,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    MIN10_CONFLICT,
    SUCCESS,
    ttrades_fixture,
)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("compatible", [False, True])
def test_ttrades_est_edt_full_h1_admitted_no_premature_certification(
    month, side, compatible,
):
    bars, at = ttrades_fixture(
        side=side, month=month, min10_valid=compatible,
    )
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=bars, as_of=at,
    )
    assert v.state == guard.ADMITTED
    assert v.research_source_state == (
        SUCCESS if compatible else MIN10_CONFLICT
    )
    assert v.research_source_side == side.value
    assert v.gate_did_invoke_router
    assert v.original_cog_claim_from_router
    assert not v.orders_authorized
    assert not v.methodology_certified
    assert not v.cognition_certified
    assert not v.sizing_performed


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_other_windows_admit_original_ict_research_but_keep_unknown(
    month, session, side,
):
    bars, at = short_fixture(session=session, month=month)
    if side is Side.LONG:
        bars = mirror_long_history(bars)
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=session, closed_m1=bars, as_of=at,
    )
    assert v.state == guard.ADMITTED
    assert v.research_source_state == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
    assert v.research_source_side == side.value
    assert v.gate_did_invoke_router
    assert not v.orders_authorized


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("wrong_session", [SessionId.LONDON, SessionId.NY_PM])
def test_nyam_bars_cannot_be_spoofed_as_another_session_before_cog(
    monkeypatch, month, wrong_session,
):
    bars, at = ttrades_fixture(
        side=Side.SHORT, month=month, min10_valid=True,
    )
    _trap_cog(monkeypatch)
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=wrong_session,
        closed_m1=bars, as_of=at,
    )
    assert v.state == guard.REJECTED
    assert v.reason == "M1_LAST_BAR_OUTSIDE_DECLARED_NY_WINDOW"
    assert not v.gate_did_invoke_router


@pytest.mark.parametrize("month", [1, 7])
def test_wrong_london_to_nyam_cannot_borrow_incomplete_nine_hour(
    monkeypatch, month,
):
    bars, at = short_fixture(session=SessionId.LONDON, month=month)
    _trap_cog(monkeypatch)
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=bars, as_of=at,
    )
    assert v.state == guard.REJECTED
    assert not v.gate_did_invoke_router


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("missing_minute", [0, 12, 59])
def test_incomplete_h1_causes_source_wait_before_any_cog(
    monkeypatch, month, missing_minute,
):
    bars, at = ttrades_fixture(
        side=Side.LONG, month=month, min10_valid=True,
    )
    day = at.astimezone(NEW_YORK).date()
    incomplete = tuple(
        b for b in bars
        if not (
            b.opened_at.astimezone(NEW_YORK).date() == day
            and b.opened_at.astimezone(NEW_YORK).hour == 9
            and b.opened_at.astimezone(NEW_YORK).minute == missing_minute
        )
    )
    _trap_cog(monkeypatch)
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=incomplete, as_of=at,
    )
    assert v.state == guard.H1_WAIT
    assert v.reason == "CLOSED_NY_09H_SOURCE_REQUIRES_EXACT_60_M1"
    assert not v.gate_did_invoke_router
    assert not v.orders_authorized


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("time_delta", [-1, 1])
def test_asof_cannot_be_backdated_or_advanced_without_matching_closed_m1(
    monkeypatch, month, time_delta,
):
    bars, at = ttrades_fixture(
        side=Side.SHORT, month=month, min10_valid=False,
    )
    _trap_cog(monkeypatch)
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=bars, as_of=at + timedelta(minutes=time_delta),
    )
    assert v.state == guard.REJECTED
    assert v.reason == "ASOF_MUST_EQUAL_LAST_CLOSED_M1"


@pytest.mark.parametrize("malformation", ["NAIVE", "REVERSED", "DUPLICATE", "EMPTY"])
def test_malformed_stream_never_invokes_router_or_cog(monkeypatch, malformation):
    bars, at = ttrades_fixture(
        side=Side.SHORT, month=1, min10_valid=True,
    )
    if malformation == "NAIVE":
        at = at.replace(tzinfo=None)
    elif malformation == "REVERSED":
        bars = tuple(reversed(bars))
        at = bars[-1].closed_at
    elif malformation == "DUPLICATE":
        bars = bars + (bars[-1],)
    elif malformation == "EMPTY":
        bars = ()
    _trap_cog(monkeypatch)
    v = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=bars, as_of=at,
    )
    assert v.state == guard.REJECTED
    assert not v.gate_did_invoke_router


def test_unsigned_method_swap_and_untyped_session_fail_closed(monkeypatch):
    bars, at = ttrades_fixture(
        side=Side.LONG, month=1, min10_valid=True,
    )
    _trap_cog(monkeypatch)
    v = guard.guarded_method_route(
        policy=None, session=SessionId.NY_AM, closed_m1=bars, as_of=at,
    )
    assert v.state == guard.REJECTED
    assert v.reason == "UNSIGNED_OR_CHANGED_M0_PROFILE_POLICY"
    wrong = guard.guarded_method_route(
        policy=PREDECLARED, session="VT31_NY_AM",
        closed_m1=bars, as_of=at,
    )
    assert wrong.state == guard.REJECTED
    assert wrong.reason == "UNTYPED_SESSION"


def test_future_m1_and_same_timestamp_double_ingress_rejected(monkeypatch):
    bars, at = ttrades_fixture(
        side=Side.LONG, month=7, min10_valid=True,
    )
    _trap_cog(monkeypatch)
    duplicated = bars + (bars[-1],)
    out = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=duplicated, as_of=at,
    )
    assert out.state == guard.REJECTED
    future = replace(
        bars[-1], opened_at=at, closed_at=at + timedelta(minutes=1),
    )
    out = guard.guarded_method_route(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=bars + (future,), as_of=at,
    )
    assert out.state == guard.REJECTED


def test_all_16_research_scenarios_preserve_source_status_and_g3_sha():
    record = guard.admission_court()
    cases = record["cases"]
    assert len(cases) == 16
    assert len({case["case"] for case in cases}) == 16
    assert all(case["state"] == guard.ADMITTED for case in cases)
    assert sum(c["research_source_state"] == SUCCESS for c in cases) == 4
    assert sum(c["research_source_state"] == MIN10_CONFLICT for c in cases) == 4
    assert sum(
        c["research_source_state"] == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
        for c in cases
    ) == 8
    assert record["source_g3_original_sha"]["git_blob_sha1"] == (
        "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
    )
    assert not record["methodology_certified"]
    assert not record["cognition_certified"]
    assert not record["policy_owner_signed"]
    assert not record["two_independent_human_reviews"]
    assert not record["live"]
    assert record["broker_orders"] == record["sizing"] == 0


def _trap_cog(monkeypatch):
    def forbidden_route(**kwargs):
        pytest.fail("INVALID_TEMPORAL_INPUT_REACHED_ROUTER_OR_COG")

    monkeypatch.setattr(guard, "route_preselected_method", forbidden_route)
