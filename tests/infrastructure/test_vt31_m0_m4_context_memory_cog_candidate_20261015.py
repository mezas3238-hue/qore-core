"""VT31 single research COG V2: frozen M0 source, later M4 M1-tape lineage."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar, SessionId, Side,
)
from scripts import vt31_m0_m4_context_memory_cog_candidate_20261015 as cg
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    PROFILE, Swing,
)
from scripts.vt31_original_cog_traderlab_32x_long_short_20261015 import (
    mirror_long_history,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)


def _m1(open_at, o, hi, lo, cl):
    return M1Bar(
        opened_at=open_at, closed_at=open_at + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(hi), low=Decimal(lo), close=Decimal(cl),
    )


def _later_ob(side: Side, month: int):
    start, at = ttrades_fixture(
        side=side, month=month, min10_valid=True,
    )
    assert at == start[-1].closed_at
    if side is Side.LONG:
        new = (
            _m1(at, "103", "104", "100", "101"),
            _m1(at+timedelta(minutes=1), "101", "109", "99", "106"),
            _m1(at+timedelta(minutes=2), "104", "106", "102", "105"),
            _m1(at+timedelta(minutes=3), "102", "104", "99", "102"),
        )
    else:
        new = (
            _m1(at, "101", "104", "100", "103"),
            _m1(at+timedelta(minutes=1), "103", "104", "95", "97"),
            _m1(at+timedelta(minutes=2), "100", "102", "98", "100"),
            _m1(at+timedelta(minutes=3), "102", "104", "100", "101"),
        )
    whole = start + new
    evidence = {
        "family": "ORDER_BLOCK_RETEST", "profile": PROFILE,
        "side": side.value, "as_of": whole[-1].closed_at,
        "first_raid_at": at - timedelta(minutes=1),
        "displacement_at": at + timedelta(minutes=2),
        "retest": _to_candle(new[-1]),
        "opposing_candles": (_to_candle(new[0]),),
        "confluence_level": "H1_09_CONTEXT_RESEARCH_ONLY",
        "confluence_confirmed_at": at - timedelta(minutes=1),
    }
    return start, whole, evidence


def _to_candle(b: M1Bar) -> Candle:
    return Candle(b.opened_at, b.open, b.high, b.low, b.close)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_two_phase_later_ob_is_source_bound_but_always_wait(month, side):
    original, extended, evidence = _later_ob(side, month)
    actor = cg.VT31M0M4CognitiveCandidate()
    first = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=original,
        as_of=original[-1].closed_at,
    )
    assert first.action == "WAIT"
    assert first.reason == "M0_SOURCE_CONTEXT_REMEMBERED_M4_NOT_YET_PROVEN"
    assert actor.context is not None and actor.context.side == side.value
    assert len(actor.context.prefix_sha256) == 64
    assert actor.context.prefix_sha256 == cg.tape_sha256(original)
    later = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=extended,
        as_of=extended[-1].closed_at, family_evidence=evidence,
    )
    assert later.action == "WAIT"
    assert later.reason == "M4_STRUCTURE_RESEARCH_ONLY_M3_M4_M5_AUTHOR_NOT_CERTIFIED"
    assert later.m4_source_status == "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
    assert later.m4_judge_invoked
    assert later.side_context == side.value
    assert not later.methodology_certified and not later.cognition_certified
    assert not later.operations_authorized
    assert later.trader_sizing == later.broker_orders == 0


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_compatible_source_context_can_wait_for_unproven_m4(month, side):
    old, future, _ = _later_ob(side, month)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(session=SessionId.NY_AM, closed_m1=old,
                          as_of=old[-1].closed_at)
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=future,
        as_of=future[-1].closed_at,
    )
    assert v.action == "WAIT" and v.reason == "M4_FAMILY_EVIDENCE_NOT_PROVEN"
    assert not v.m4_judge_invoked


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_min10_source_conflict_never_creates_m4_context(month, side):
    old, at = ttrades_fixture(
        side=side, month=month, min10_valid=False,
    )
    actor = cg.VT31M0M4CognitiveCandidate()
    v = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=old, as_of=at,
    )
    assert v.action == "WAIT"
    assert not v.source_context_remembered
    assert actor.context is None
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=old, as_of=at,
        family_evidence={},
    )
    assert v.action == "WAIT" and not v.m4_judge_invoked


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_ict_sessions_remain_author_unknown_no_ttrades_family(month, session, side):
    history, at = short_fixture(session=session, month=month)
    if side is Side.LONG:
        history = mirror_long_history(history)
    actor = cg.VT31M0M4CognitiveCandidate()
    v = actor.capture_context(
        session=session, closed_m1=history, as_of=at,
    )
    assert v.action == "WAIT"
    assert v.m0_source_status == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
    assert actor.context is None
    assert not v.m4_judge_invoked


@pytest.mark.parametrize("month", [1, 7])
def test_frozen_prefix_changes_are_rejected_before_m4(monkeypatch, month):
    old, future, evidence = _later_ob(Side.LONG, month)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(
        session=SessionId.NY_AM, closed_m1=old, as_of=old[-1].closed_at,
    )
    changes = list(future)
    changes[400] = replace(changes[400], high=changes[400].high + Decimal("0.01"))
    _trap(monkeypatch)
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=tuple(changes),
        as_of=future[-1].closed_at, family_evidence=evidence,
    )
    assert v.action == "REJECT"
    assert v.reason == "SOURCE_M1_PREFIX_FORK_OR_GAP"
    assert not v.m4_judge_invoked


@pytest.mark.parametrize("month", [1, 7])
def test_same_m1_forged_candle_ohlc_is_rejected_before_m4(monkeypatch, month):
    old, future, evidence = _later_ob(Side.SHORT, month)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(
        session=SessionId.NY_AM, closed_m1=old, as_of=old[-1].closed_at,
    )
    forged = replace(evidence["retest"], high=evidence["retest"].high + Decimal("1"))
    _trap(monkeypatch)
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=future,
        as_of=future[-1].closed_at,
        family_evidence=evidence | {"retest": forged},
    )
    assert v.action == "REJECT"
    assert v.reason == "M4_CANDLE_OHLC_NOT_IN_CLOSED_M1_TAPE"
    assert not v.m4_judge_invoked


def test_source_stream_gap_and_retroactive_asof_are_rejected_precog(monkeypatch):
    old, future, evidence = _later_ob(Side.LONG, 1)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(
        session=SessionId.NY_AM, closed_m1=old, as_of=old[-1].closed_at,
    )
    _trap(monkeypatch)
    gap = old + future[len(old)+1:]
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=gap,
        as_of=future[-1].closed_at, family_evidence=evidence,
    )
    assert v.action == "REJECT"
    assert v.reason == "SOURCE_M1_PREFIX_FORK_OR_GAP"
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=old,
        as_of=old[-1].closed_at, family_evidence=evidence,
    )
    assert v.action == "REJECT"
    assert v.reason == "RETEST_TIME_NOT_STRICT_NYAM_PROGRESS"


def test_cross_session_disallowed_and_duplicate_minute_is_not_replayable():
    old, future, evidence = _later_ob(Side.LONG, 7)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(session=SessionId.NY_AM, closed_m1=old,
                          as_of=old[-1].closed_at)
    cross = actor.assess_later_retest(
        session=SessionId.NY_PM, closed_m1=future,
        as_of=future[-1].closed_at, family_evidence=evidence,
    )
    assert cross.action == "REJECT"
    assert cross.reason == "SOURCE_SESSION_CHANGED_AFTER_M0"
    first = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=future,
        as_of=future[-1].closed_at, family_evidence=evidence,
    )
    assert first.action == "WAIT"
    duplicate = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=future,
        as_of=future[-1].closed_at, family_evidence=evidence,
    )
    assert duplicate.action == "REJECT"
    assert duplicate.reason == "RETEST_TIME_NOT_STRICT_NYAM_PROGRESS"


def test_m4_first_raid_swapped_or_wrong_side_rejected_without_judge(monkeypatch):
    old, future, evidence = _later_ob(Side.SHORT, 1)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(
        session=SessionId.NY_AM, closed_m1=old, as_of=old[-1].closed_at,
    )
    _trap(monkeypatch)
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=future,
        as_of=future[-1].closed_at,
        family_evidence=evidence | {
            "first_raid_at": evidence["first_raid_at"] + timedelta(minutes=1),
        },
    )
    assert v.action == "REJECT"
    assert v.reason == "M4_RETROACTIVE_RAID_DISPLACEMENT_OR_ASOF"


def test_invalid_swings_cannot_claim_breaker_source_without_raw_extrema(monkeypatch):
    old, future, evidence = _later_ob(Side.LONG, 1)
    actor = cg.VT31M0M4CognitiveCandidate()
    actor.capture_context(
        session=SessionId.NY_AM, closed_m1=old, as_of=old[-1].closed_at,
    )
    _trap(monkeypatch)
    arbitrary = Swing(
        "LOW", Decimal("999"), future[-3].opened_at,
        future[-2].closed_at,
    )
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=future,
        as_of=future[-1].closed_at,
        family_evidence={
            "family": "BREAKER_RETEST", "profile": PROFILE,
            "side": "LONG", "as_of": future[-1].closed_at,
            "first_raid_at": evidence["first_raid_at"],
            "displacement_at": evidence["displacement_at"],
            "retest": evidence["retest"], "swing_legs": (arbitrary,),
        },
    )
    assert v.action == "REJECT"
    assert v.reason == "M4_SWING_NOT_VERIFIED_IN_CLOSED_M1_TAPE"


def test_dossier_no_claim_of_certification_or_trade():
    record = cg.qualitative_context_court()
    assert record["prereg_commit"] == cg.PREREG
    assert len(record["cases"]) == 8
    assert sum(c["source_context_remembered"] for c in record["cases"]) == 4
    assert all(c["action"] == "WAIT" for c in record["cases"])
    assert not record["owner_method_policy_signed"]
    assert not record["human_cog_ops_review"]
    assert not record["native_cog_production_integrated"]
    assert not record["author_m3_m4_m5_complete"]
    assert not record["methodology_certified"] and not record["cognition_certified"]
    assert not record["operations_authorized"]
    assert record["broker_orders"] == record["sizing"] == 0


def _trap(monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("UNTRUSTED_SOURCE_REACHED_M4_JUDGE")
    monkeypatch.setattr(cg, "adjudicate_closed_m1_retest", forbidden)
