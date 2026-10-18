"""VT31 M5 source-bound extrema cannot masquerade as author-approved stop."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts import vt31_m5_three_session_displacement_swing_witness_20261018 as m5
from scripts.vt31_cog_v4_transactional_context_20261016 import (
    VT31TwoPhaseCognitiveCandidate,
)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM])
def test_twelve_session_side_dst_source_swing_references_are_only_wait(
    month, side, session,
):
    kwargs, out = m5.synthetic_m5_case(
        session=session, side=side, month=month,
    )
    assert out.action == "WAIT" and out.geometry_state == m5.CANDIDATE
    assert out.session == session.value and out.side == side.value
    assert out.candidate_unique
    assert out.candidate_extreme_reference is not None
    assert out.swing_opened_at == m5.utc(
        kwargs["closed_m1"][kwargs["candidate_swing_index"]].opened_at
    ).isoformat()
    assert out.displacement_closed_at == m5.utc(
        kwargs["closed_m1"][kwargs["displacement_index"]].closed_at
    ).isoformat()
    assert not out.displacement_causing_swing_author_certified
    assert not out.protected_swing_author_certified
    assert out.stop_tick_price is None
    assert not out.native_g3_integrated
    assert not out.methodology_certified and not out.cognition_certified
    assert not out.human_cog_ops_signed and not out.owner_m0_signed
    assert out.broker_orders == out.lot_sizing == 0


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM])
def test_declared_swing_must_be_same_unique_pre_displacement_extreme(session):
    kwargs, _ = m5.synthetic_m5_case(
        session=session, side=Side.LONG, month=1,
    )
    anchor = (
        len(kwargs["closed_m1"]) - 4
        if session is SessionId.NY_AM else 0
    )
    bad = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"candidate_swing_index": anchor})
    )
    assert bad.action == "REJECT"
    assert bad.reason == "M5_PROPOSED_SWING_IS_NOT_SOURCE_EXTREME" if session is SessionId.NY_AM else bad.action == "WAIT"


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_ict_tied_extrema_never_select_causing_swing(month, side):
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.LONDON, side=side, month=month,
    )
    tape = list(kwargs["closed_m1"])
    low = tape[0].low
    high = tape[0].high
    if side is Side.LONG:
        tape[2] = replace(tape[2], low=low)
    else:
        tape[2] = replace(tape[2], high=high)
    verdict = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"closed_m1": tuple(tape)})
    )
    assert verdict.action == "WAIT"
    assert verdict.reason == "M5_PRE_DISPLACEMENT_EXTREMA_TIED_CAUSE_UNKNOWN"
    assert verdict.stop_tick_price is None


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM])
def test_future_or_displacement_swing_fails_before_source(session):
    kwargs, _ = m5.synthetic_m5_case(
        session=session, side=Side.SHORT, month=7,
    )
    for candidate in (kwargs["displacement_index"], len(kwargs["closed_m1"])):
        out = m5.adjudicate_m5_swing_reference(
            **(kwargs | {"candidate_swing_index": candidate})
        )
        assert out.action == "REJECT"
        assert out.reason == "M5_SWING_OR_DISPLACEMENT_FUTURE_OR_UNTYPED"


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_nyam_seal_fork_blocks_spoofed_candidate_without_stop(side):
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.NY_AM, side=side, month=1,
    )
    tape = list(kwargs["closed_m1"])
    row = tape[-1]
    tape[-1] = replace(
        row, close=row.close + (Decimal("0.01") if side is Side.LONG else Decimal("-0.01")),
    )
    verdict = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"closed_m1": tuple(tape)})
    )
    assert verdict.action == "REJECT"
    assert verdict.reason == "M5_NYAM_FULL_M1_SOURCE_SEAL_FORK"
    assert verdict.stop_tick_price is None


def test_nyam_without_v4_context_has_no_source_proof():
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.NY_AM, side=Side.LONG, month=7,
    )
    absent = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"nyam_actor": None})
    )
    assert absent.action == "WAIT"
    assert absent.reason == "M5_NYAM_COG_V4_NOT_PROVIDED"
    blank = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"nyam_actor": VT31TwoPhaseCognitiveCandidate()})
    )
    assert blank.action == "WAIT"
    assert blank.reason == "M5_NYAM_M0_SOURCE_TOKEN_NOT_COMMITTED"


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM])
def test_swap_side_and_profile_never_promotes_another_session(session):
    kwargs, _ = m5.synthetic_m5_case(
        session=session, side=Side.LONG, month=1,
    )
    profile = m5.ICT_GENERAL if session is SessionId.NY_AM else m5.PROFILE
    p = m5.adjudicate_m5_swing_reference(**(kwargs | {"profile": profile}))
    assert p.action == "REJECT"
    assert p.reason == "M5_METHODOLOGY_PROFILE_CROSSED"
    if session is SessionId.NY_AM:
        wrong_side = m5.adjudicate_m5_swing_reference(
            **(kwargs | {"side": Side.SHORT})
        )
        assert wrong_side.action == "WAIT" or wrong_side.reason == "M5_NYAM_SOURCE_SESSION_SIDE_OR_DATE_CONFLICT"


def test_ict_dol_recheck_rejects_post_session_source_claim():
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.NY_PM, side=Side.LONG, month=1,
    )
    source = dict(kwargs["ict_setup"])
    source["target_observed_at"] = kwargs["closed_m1"][3].closed_at
    v = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"ict_setup": source})
    )
    assert v.action == "REJECT"
    assert v.reason == "M5_ICT2023_RECHECK_REJECTED"


def test_ict_cannot_fake_ny_am_context_with_its_source_dict():
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.LONDON, side=Side.LONG, month=7,
    )
    v = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"session": SessionId.NY_AM})
    )
    assert v.action == "REJECT"
    assert v.reason == "M5_METHODOLOGY_PROFILE_CROSSED"


def test_ict_bad_displacement_link_does_not_pass_context():
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.NY_PM, side=Side.SHORT, month=7,
    )
    verdict = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"displacement_index": kwargs["displacement_index"] + 1})
    )
    assert verdict.action == "REJECT"
    assert verdict.reason == "M5_DISPLACEMENT_NOT_SAME_ICT_MSS_EVENT"


def test_gap_and_unclosed_m1_rejected_even_if_structural_wick_looks_valid():
    kwargs, _ = m5.synthetic_m5_case(
        session=SessionId.LONDON, side=Side.LONG, month=1,
    )
    tape = kwargs["closed_m1"]
    gap = tape[:2] + tape[3:]
    bad = m5.adjudicate_m5_swing_reference(
        **(kwargs | {
            "closed_m1": gap,
            "displacement_index": kwargs["displacement_index"] - 1,
        })
    )
    assert bad.action == "REJECT"
    assert bad.reason == "M5_TAPE_ASOF_GAP_OR_FUTURE"
    row = tape[-1]
    fake = replace(
        row,
        opened_at=row.opened_at + timedelta(minutes=1),
        closed_at=row.closed_at + timedelta(minutes=1),
    )
    missed = m5.adjudicate_m5_swing_reference(
        **(kwargs | {"closed_m1": tape[:-1] + (fake,)})
    )
    assert missed.action == "REJECT"
    assert missed.reason == "M5_TAPE_ASOF_GAP_OR_FUTURE"


def test_m5_dossier_all_sessions_and_no_stop_trading():
    report = m5.m5_three_session_court()
    assert report["prereg_commit"] == m5.PREREG
    assert len(report["cases"]) == 12
    assert len({x["session"] for x in report["cases"]}) == 3
    assert sum(x["candidate_unique"] for x in report["cases"]) == 12
    assert all(x["action"] == "WAIT" for x in report["cases"])
    assert all(x["stop_tick_price"] is None for x in report["cases"])
    assert report["source_10handle_interpretation_disputed"]
    assert report["synthetic_m1_not_real_market_or_author_charts"]
    assert not report["causing_swing_author_certified"]
    assert not report["stop_tick_price_certified"]
    assert not report["m5_methodology_certified"] and not report["cognition_certified"]
    assert not report["owner_m0_signed"] and not report["human_cog_ops_signed"]
    assert not report["native_g3_connected"]
    assert report["broker_orders"] == report["sizing"] == 0 and not report["live"]
