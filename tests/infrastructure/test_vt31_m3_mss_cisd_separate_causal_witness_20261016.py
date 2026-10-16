"""Independent causal M3 MSS/CISD contrasts: NO author certification."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    SessionId,
    Side,
)
from scripts import vt31_m3_mss_cisd_separate_causal_witness_20261016 as m3
from scripts.vt31_cog_v4_transactional_context_20261016 import (
    VT31TwoPhaseCognitiveCandidate,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize(
    ("scenario", "has_mss", "has_cisd"),
    [
        ("BOTH", True, True),
        ("MSS_ONLY", True, False),
        ("CISD_ONLY", False, True),
        ("NEITHER", False, False),
    ],
)
def test_four_independent_mss_cisd_geometries_per_side_and_dst(
    month, side, scenario, has_mss, has_cisd,
):
    actor, tape, at, evidence = m3.synthetic_m3_case(
        side=side, month=month, scenario=scenario,
    )
    v = m3.separate_mss_cisd_on_sealed_m1(
        actor=actor, session=SessionId.NY_AM,
        closed_m1=tape, as_of=at, **evidence,
    )
    assert v.action == m3.WAIT
    assert (v.mss_status == m3.YES_MSS) is has_mss
    assert (v.cisd_status == m3.YES_CISD) is has_cisd
    assert v.side == side.value
    assert v.as_of == at.isoformat()
    assert v.sealed_sha256 == actor.seal.sha256_total
    assert v.mss_swing_level is not None
    assert v.cisd_series_open is not None
    assert not v.mss_author_certified
    assert not v.cisd_author_certified
    assert not v.displacement_author_proven
    assert not v.am_family_approved
    assert not v.methodology_certified
    assert not v.cognition_certified
    assert v.broker_orders == v.lot_sizing == 0
    assert not v.orders_authorized


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_missing_one_source_does_not_silently_infer_from_other(month, side):
    actor, tape, at, evidence = m3.synthetic_m3_case(
        side=side, month=month, scenario="BOTH",
    )
    only_cisd = m3.separate_mss_cisd_on_sealed_m1(
        actor=actor, session=SessionId.NY_AM, closed_m1=tape, as_of=at,
        swing_index=None,
        cisd_start_index=evidence["cisd_start_index"],
        cisd_end_index=evidence["cisd_end_index"],
    )
    assert only_cisd.action == m3.WAIT
    assert only_cisd.mss_status == m3.NO_SOURCE
    assert only_cisd.cisd_status == m3.YES_CISD
    only_mss = m3.separate_mss_cisd_on_sealed_m1(
        actor=actor, session=SessionId.NY_AM, closed_m1=tape, as_of=at,
        swing_index=evidence["swing_index"],
        cisd_start_index=None, cisd_end_index=None,
    )
    assert only_mss.action == m3.WAIT
    assert only_mss.mss_status == m3.YES_MSS
    assert only_mss.cisd_status == m3.NO_SOURCE


def _call(side=Side.LONG, month=1, scenario="BOTH"):
    actor, tape, at, evidence = m3.synthetic_m3_case(
        side=side, month=month, scenario=scenario,
    )
    defaults = {
        "actor": actor, "session": SessionId.NY_AM,
        "closed_m1": tape, "as_of": at, **evidence,
    }
    return defaults


@pytest.mark.parametrize("month", [1, 7])
def test_strict_future_unclosed_pivot_right_side_is_rejected(month):
    args = _call(month=month)
    pivot_too_late = len(args["closed_m1"]) - 2
    v = m3.separate_mss_cisd_on_sealed_m1(
        **(args | {"swing_index": pivot_too_late})
    )
    assert v.action == m3.REJECT
    assert v.reason == "M3_SWING_INDEX_FUTURE_OR_UNTYPED"
    assert v.mss_status == m3.NO_SOURCE


@pytest.mark.parametrize("month", [1, 7])
def test_cisd_future_index_and_partial_series_rejected(month):
    args = _call(month=month)
    variants = [
        ({"cisd_end_index": len(args["closed_m1"]) - 1},
         "M3_CISD_SERIES_FUTURE_OR_UNTYPED"),
        ({"cisd_start_index": None},
         "M3_PARTIAL_CISD_SERIES_WITNESS"),
        ({"cisd_start_index": True},
         "M3_CISD_SERIES_FUTURE_OR_UNTYPED"),
        ({"cisd_start_index": args["cisd_end_index"] + 1},
         "M3_CISD_SERIES_FUTURE_OR_UNTYPED"),
    ]
    for change, reason in variants:
        v = m3.separate_mss_cisd_on_sealed_m1(**(args | change))
        assert v.action == m3.REJECT and v.reason == reason


def test_uncommitted_m0_does_not_admit_structural_inference():
    bad, at = ttrades_fixture(
        month=1, side=Side.LONG, min10_valid=False,
    )
    actor = VT31TwoPhaseCognitiveCandidate()
    first = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=bad, as_of=at,
    )
    assert first.action == m3.WAIT and actor.context is None
    v = m3.separate_mss_cisd_on_sealed_m1(
        actor=actor, session=SessionId.NY_AM,
        closed_m1=bad, as_of=at,
        swing_index=None, cisd_start_index=None, cisd_end_index=None,
    )
    assert v.action == m3.WAIT
    assert v.reason == "M0_CONTEXT_NOT_COMMITTED"


def test_m3_refuses_to_reclassify_new_m1_not_committed_in_v4():
    args = _call()
    tape = args["closed_m1"]
    # A newly appended and closed M1 cannot be assessed until V4 commits it.
    extension = replace(
        tape[-1],
        opened_at=tape[-1].closed_at,
        closed_at=tape[-1].closed_at + timedelta(minutes=1),
    )
    v = m3.separate_mss_cisd_on_sealed_m1(
        **(args | {
            "closed_m1": tape + (extension,),
            "as_of": extension.closed_at,
        })
    )
    assert v.action == m3.REJECT
    assert v.reason == "M3_M1_NOT_IDENTICAL_TO_COMMITTED_V4_SNAPSHOT"


@pytest.mark.parametrize("property", ["open", "high", "low", "close"])
def test_m3_rejects_historical_price_fork_not_geometric_story(property):
    args = _call()
    bars = list(args["closed_m1"])
    idx = args["cisd_start_index"]
    row = bars[idx]
    delta = Decimal("-0.05") if property == "low" else Decimal("0.05")
    bars[idx] = replace(row, **{property: getattr(row, property) + delta})
    v = m3.separate_mss_cisd_on_sealed_m1(
        **(args | {"closed_m1": tuple(bars)})
    )
    assert v.action == m3.REJECT
    assert v.reason == "M3_M1_NOT_IDENTICAL_TO_COMMITTED_V4_SNAPSHOT"


@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
def test_no_ttrades_09h_transfer_to_other_sessions(session):
    args = _call()
    v = m3.separate_mss_cisd_on_sealed_m1(
        **(args | {"session": session})
    )
    assert v.action == m3.REJECT
    assert v.reason == "M3_TTRADES_NYAM_SOURCE_ONLY"


def test_three_candle_pivot_not_invented_when_neighbour_geometries_fail():
    args = _call()
    # Pivot idx=2 of constructed five-minute tail. Tail index 1 is not the
    # declared three-bar swing high even when the final close is above it.
    idx = args["cisd_start_index"] + 1
    v = m3.separate_mss_cisd_on_sealed_m1(
        **(args | {"swing_index": idx})
    )
    assert v.action == m3.REJECT
    assert v.reason == "M3_DECLARED_SWING_IS_NOT_THREE_BAR_PIVOT"


def test_m3_source_paper_trail_does_not_equal_approval():
    r = m3.m3_independent_source_court()
    assert r["prereg_commit"] == m3.PREREG
    assert len(r["cases"]) == 16
    assert sum(x["mss_status"] == m3.YES_MSS for x in r["cases"]) == 8
    assert sum(x["cisd_status"] == m3.YES_CISD for x in r["cases"]) == 8
    assert all(x["action"] == m3.WAIT for x in r["cases"])
    assert r["mss_and_cisd_distinct"] and r["not_universal_am_gates"]
    assert not r["author_displacement_approved"]
    assert not r["author_swing_relevance_approved"]
    assert not r["author_cisd_series_selection_approved"]
    assert not r["m3_author_certified"]
    assert not r["methodology_certified"] and not r["cognition_certified"]
    assert not r["native_cog_integrated"]
    assert not r["owner_m0_signed"] and not r["human_cog_ops_signed"]
    assert r["orders"] == r["sizing"] == 0 and not r["live"]
