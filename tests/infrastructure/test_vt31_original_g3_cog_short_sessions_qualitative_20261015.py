"""Authentic VT31 COG SHORT judgment vs source doctrine, not statistical certification."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import SessionId
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    run_short_mirror_tribunal,
    short_fixture,
)


@pytest.mark.parametrize("month,offset", [(1, -5), (7, -4)])
@pytest.mark.parametrize(
    "session", [SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM],
)
def test_original_g3_short_decision_and_pivot_source_for_each_session_dst(
    month, offset, session,
):
    source, at = short_fixture(session=session, month=month)
    engine = VT31CleanroomCognition()
    for bar in source:
        engine.observe_closed_m1(bar)
    result = engine.assess(session=session, as_of=at)
    assert result.decision is not None, (session, month, result.missing)
    dto = result.decision
    assert dto.side.value == "SHORT"
    assert dto.draw_family == "PRIOR_NY_CASH_SESSION_LOW"
    assert dto.draw_target == Decimal("80")
    assert dto.structure_level == Decimal("96")
    assert dto.structure_break_confirmed_at == at
    assert int(at.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
               .utcoffset().total_seconds()/3600) == offset
    assert result.research_only is True
    assert result.trade_authorized is False


def test_tribunal_six_cases_mirror_qualitative_actions_and_abstention():
    report = run_short_mirror_tribunal()
    assert len(report["cases"]) == 6
    assert {
        (x["session"], x["observed_utc_offset"]) for x in report["cases"]
    } == {
        (session.value, offset)
        for session in (SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM)
        for offset in (-5, -4)
    }
    for case in report["cases"]:
        assert case["original_cog_side"] == "SHORT"
        assert case["original_cog_target"] == "80"
        assert case["original_cog_mss_level"] == "96"
        assert case["change_only_final_mss_close_to_97"] == "WAIT"
        assert case["abstain_before_mss"] == "WAIT"
        assert case["swept_dol_cannot_retain_original_short_80"]
        assert case["pivot_close_reversal_cannot_retain_original_short_80"]
        assert case["retroactive_asof_rejected"] is True
        assert not case["methodology_certified"]
        assert not case["cognition_certified"]
        assert not case["human_independent_reviewed"]
        assert not case["trading_authorized"]


def test_original_short_nyam_profile_ttrades_dol_mismatch_both_dst():
    report = run_short_mirror_tribunal()
    nyam = [case for case in report["cases"] if case["session"] == SessionId.NY_AM.value]
    assert len(nyam) == 2
    for item in nyam:
        source = item["ttrades_am_source_check"]
        assert source is not None
        assert source["ttrades_h1_target"] == "90"
        assert source["original_cog_target"] == "80"
        assert source["source_v2"] == "REJECTED"
        assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in source["source_rejected_reasons"]
        assert source["method_claim"] == "TTRADES_NYAM_SHORT_NOT_SOURCE_CONFORMANT"
    assert all(
        x["ttrades_am_source_check"] is None
        for x in report["cases"] if x["session"] != SessionId.NY_AM.value
    )


def test_only_original_closed_m1_asof_may_be_assessed():
    source, at = short_fixture(session=SessionId.LONDON, month=1)
    engine = VT31CleanroomCognition()
    for bar in source:
        engine.observe_closed_m1(bar)
    with pytest.raises(ValueError, match="exactly latest closed M1"):
        engine.assess(session=SessionId.LONDON, as_of=at-timedelta(minutes=1))


def test_no_profit_certification_from_cognitive_behavior():
    p = run_short_mirror_tribunal()
    assert p["original_cog_directly_invoked"] is True
    assert p["original_source"]["git_blob_sha1"] == (
        "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
    )
    assert p["source_fidelity_ict_general_completed"] is False
    assert p["source_fidelity_ttrades_nyam_completed"] is False
    assert p["methodology_certified"] is False
    assert p["cognitive_certified"] is False
    assert p["owner_human_cog_ops_signatures_attested"] is False
    assert p["market_3y_replayed"] is False
    assert p["economic_scores"] is None
    assert p["broker_orders"] == p["trader_sizing"] == 0
    assert p["live_authorized"] is False
