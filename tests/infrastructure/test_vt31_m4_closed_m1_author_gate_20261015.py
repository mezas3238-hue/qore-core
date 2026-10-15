"""VT31 M4 V2: source retest OHLC must exist at cognitive as_of."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from scripts import vt31_m4_closed_m1_author_gate_20261015 as m4
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    Candle,
    adjudicate_breaker,
    adjudicate_ob,
)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize("family", ["ORDER_BLOCK_RETEST", "BREAKER_RETEST"])
def test_eight_complete_m1_witnesses_admitted_but_cog_must_wait(
    month, side, family,
):
    args = m4.fixture_case(family=family, side=side, month=month)
    result = m4.adjudicate_closed_m1_retest(**args)
    assert result.state == m4.OBSERVED
    assert result.legacy_source_gate_invoked is True
    assert result.cognitive_action == "WAIT"
    assert result.source_v1_status == (
        "RESEARCH_OB_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
        if family == "ORDER_BLOCK_RETEST"
        else "RESEARCH_BREAKER_STRUCTURE_WITNESSED_AUTHOR_FINAL_PENDING"
    )
    assert not result.displacement_causing_stop_certified
    assert not result.author_method_certified
    assert not result.cognition_certified
    assert not result.broker_order_authorized
    assert not result.lot_sizing_performed


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", ["LONG", "SHORT"])
@pytest.mark.parametrize("family", ["ORDER_BLOCK_RETEST", "BREAKER_RETEST"])
def test_legacy_accepts_not_yet_closed_retest_but_v2_blocks(
    monkeypatch, month, side, family,
):
    args = m4.fixture_case(family=family, side=side, month=month)
    # V1 accepted full OHLC although as_of equals candle OPEN (not M1 close).
    legacy_args = {k: v for k, v in args.items() if k != "family"}
    legacy_args["as_of"] = args["retest"].at
    if family == "ORDER_BLOCK_RETEST":
        assert adjudicate_ob(**legacy_args).status.startswith("RESEARCH_OB_")
        _trap(monkeypatch, "adjudicate_ob")
    else:
        assert adjudicate_breaker(**legacy_args).status.startswith("RESEARCH_BREAKER_")
        _trap(monkeypatch, "adjudicate_breaker")
    guarded = m4.adjudicate_closed_m1_retest(
        **(args | {"as_of": args["retest"].at})
    )
    assert guarded.state == m4.REJECTED
    assert guarded.reason == "RETEST_M1_NOT_EXACTLY_CLOSED_AT_ASOF"
    assert guarded.source_v1_status is None
    assert not guarded.legacy_source_gate_invoked


@pytest.mark.parametrize("family", ["ORDER_BLOCK_RETEST", "BREAKER_RETEST"])
@pytest.mark.parametrize("delta", [-2, 1])
def test_stale_or_future_retest_never_reaches_source_judge(
    monkeypatch, family, delta,
):
    args = m4.fixture_case(family=family, side="LONG", month=1)
    _trap(monkeypatch, "adjudicate_ob" if family.startswith("ORDER") else "adjudicate_breaker")
    verdict = m4.adjudicate_closed_m1_retest(
        **(args | {"as_of": args["as_of"] + timedelta(minutes=delta)})
    )
    assert verdict.state == m4.REJECTED
    assert not verdict.legacy_source_gate_invoked


@pytest.mark.parametrize("family", ["ORDER_BLOCK_RETEST", "BREAKER_RETEST"])
def test_naive_timestamps_never_convert_through_runner_locale(monkeypatch, family):
    args = m4.fixture_case(family=family, side="SHORT", month=7)
    _trap(monkeypatch, "adjudicate_ob" if family.startswith("ORDER") else "adjudicate_breaker")
    for part in ("as_of", "first_raid_at", "displacement_at"):
        malformed = args | {part: args[part].replace(tzinfo=None)}
        verdict = m4.adjudicate_closed_m1_retest(**malformed)
        assert verdict.state == m4.REJECTED
        assert verdict.reason == "NAIVE_OR_INVALID_SOURCE_TIMESTAMP"


@pytest.mark.parametrize("family", ["ORDER_BLOCK_RETEST", "BREAKER_RETEST"])
def test_cross_profile_and_unknown_side_reject_before_source(monkeypatch, family):
    args = m4.fixture_case(family=family, side="LONG", month=1)
    _trap(monkeypatch, "adjudicate_ob" if family.startswith("ORDER") else "adjudicate_breaker")
    for replacement in ({"profile": "ICT_GENERAL_2023"}, {"side": "MAYBE"}):
        verdict = m4.adjudicate_closed_m1_retest(**(args | replacement))
        assert verdict.state == m4.REJECTED
        assert not verdict.legacy_source_gate_invoked


def test_ob_candle_not_yet_closed_before_displacement_is_rejected_precog(monkeypatch):
    args = m4.fixture_case(family="ORDER_BLOCK_RETEST", side="LONG", month=7)
    bad = replace(
        args["opposing_candles"][0],
        at=args["displacement_at"],
    )
    _trap(monkeypatch, "adjudicate_ob")
    verdict = m4.adjudicate_closed_m1_retest(
        **(args | {"opposing_candles": (bad,)})
    )
    assert verdict.state == m4.REJECTED
    assert verdict.reason == "OB_SOURCE_CANDLE_NOT_CLOSED_AT_DISPLACEMENT"


def test_future_htf_confluence_does_not_pass_pre_cog(monkeypatch):
    args = m4.fixture_case(family="ORDER_BLOCK_RETEST", side="SHORT", month=1)
    _trap(monkeypatch, "adjudicate_ob")
    verdict = m4.adjudicate_closed_m1_retest(
        **(args | {
            "confluence_confirmed_at": args["displacement_at"] + timedelta(minutes=1),
        })
    )
    assert verdict.state == m4.REJECTED
    assert verdict.reason == "FUTURE_HTF_OR_POI_CONFLUENCE"


def test_breaker_zone_future_and_swing_confirmation_future_blocked(monkeypatch):
    args = m4.fixture_case(family="BREAKER_RETEST", side="LONG", month=7)
    _trap(monkeypatch, "adjudicate_breaker")
    future_zone = replace(
        args["zone_candles"][0], at=args["retest"].at,
    )
    v = m4.adjudicate_closed_m1_retest(
        **(args | {"zone_candles": (future_zone,)})
    )
    assert v.state == m4.REJECTED
    assert v.reason == "BREAKER_ZONE_CANDLE_FUTURE_OR_NOT_CLOSED"
    future_swing = replace(
        args["swing_legs"][-1],
        confirmed_at=args["as_of"] + timedelta(minutes=1),
    )
    v = m4.adjudicate_closed_m1_retest(
        **(args | {"swing_legs": args["swing_legs"][:-1] + (future_swing,)})
    )
    assert v.state == m4.REJECTED
    assert v.reason == "SWING_NOT_CONFIRMED_BEFORE_RETEST"


@pytest.mark.parametrize("family", ["ORDER_BLOCK_RETEST", "BREAKER_RETEST"])
def test_synthetic_intrabar_stop_target_ambiguity_remains_wait(family):
    args = m4.fixture_case(family=family, side="LONG", month=1)
    verdict = m4.adjudicate_closed_m1_retest(
        **(args | {"intrabar_stop_target_ambiguous": True})
    )
    assert verdict.state == m4.INSUFFICIENT
    assert verdict.source_v1_status == "SOURCE_STRUCTURE_UNDECIDABLE_INTRABAR"
    assert verdict.cognitive_action == "WAIT"


def test_multicandle_author_zone_not_promoted_from_v1_proxy():
    args = m4.fixture_case(family="ORDER_BLOCK_RETEST", side="LONG", month=7)
    prior = replace(
        args["opposing_candles"][0],
        at=args["opposing_candles"][0].at - timedelta(minutes=1),
    )
    result = m4.adjudicate_closed_m1_retest(
        **(args | {"opposing_candles": (prior, args["opposing_candles"][0])})
    )
    assert result.state == m4.INSUFFICIENT
    assert result.source_v1_status == "AUTHOR_ZONE_SELECTION_UNDERDETERMINED"
    assert result.cognitive_action == "WAIT"


@pytest.mark.parametrize("month", [1, 7])
def test_session_shift_after_ny_11_fails_author_window(month):
    args = m4.fixture_case(
        family="ORDER_BLOCK_RETEST", side="LONG", month=month,
    )
    shifted = {
        k: v + timedelta(hours=2)
        for k, v in args.items()
        if k in ("as_of", "first_raid_at", "displacement_at")
    }
    shifted["retest"] = replace(
        args["retest"], at=args["retest"].at + timedelta(hours=2)
    )
    shifted["opposing_candles"] = tuple(
        replace(c, at=c.at + timedelta(hours=2))
        for c in args["opposing_candles"]
    )
    shifted["confluence_confirmed_at"] = (
        args["confluence_confirmed_at"] + timedelta(hours=2)
    )
    v = m4.adjudicate_closed_m1_retest(**(args | shifted))
    assert v.state == m4.REJECTED
    assert v.reason == "RETEST_OUTSIDE_TTRADES_NYAM_WINDOW"


def test_preregistered_16_cases_not_certified_and_retest_bar_states():
    dossier = m4.m4_closed_m1_court()
    cases = dossier["cases"]
    assert dossier["prereg_commit"] == "ce4047201ec27ac4a3e98d854c07606e6e2f30d2"
    assert len(cases) == 16
    assert len({c["case"] for c in cases}) == 16
    assert sum(x["state"] == m4.OBSERVED for x in cases) == 8
    assert sum(x["state"] == m4.REJECTED for x in cases) == 8
    assert all(x["cognitive_action"] == "WAIT" for x in cases)
    assert not dossier["methodology_certified"]
    assert not dossier["cognition_certified"]
    assert not dossier["owner_signed_m0"]
    assert not dossier["dual_cog_ops_signatures"]
    assert not dossier["stop_causing_displacement_identified"]
    assert dossier["broker_orders"] == dossier["sizing"] == 0
    assert not dossier["live"]


def _trap(monkeypatch, name):
    def forbidden(**kwargs):
        pytest.fail("NOT_CAUSALLY_AVAILABLE_M1_REACHED_OLD_M4_SOURCE_JUDGE")
    monkeypatch.setattr(m4, name, forbidden)
