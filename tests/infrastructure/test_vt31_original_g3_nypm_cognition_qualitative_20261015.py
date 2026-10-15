"""Authentic VT31 G3 cognitive judgment in NY PM, no economic certification."""
from __future__ import annotations

from datetime import timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    SessionId,
)
from scripts.vt31_original_cog_nyam_ttrades_source_conflict_20261014 import (
    bar,
)
from scripts.vt31_original_g3_nypm_cognition_qualitative_20261015 import (
    genuine_nypm_cognitive_dossier,
    ny_pm_original_fixture,
)


def test_original_cog_nypm_source_is_real_producer_not_research_proxy():
    stream, at = ny_pm_original_fixture()
    engine = VT31CleanroomCognition()
    for m1 in stream:
        engine.observe_closed_m1(m1)
    actual = engine.assess(session=SessionId.NY_PM, as_of=at)
    assert actual.decision is not None
    assert actual.decision.draw_target == 150
    assert actual.decision.structure_level == 104
    assert actual.decision.structure_break_confirmed_at == at
    assert actual.decision.draw_family == "PRIOR_NY_CASH_SESSION_HIGH"
    assert actual.decision.session is SessionId.NY_PM
    assert actual.trade_authorized is False
    assert "H1" in actual.verified_htf
    assert "M15" in actual.verified_htf


def test_nypm_dossier_shows_correct_waits_without_faking_trades():
    p = genuine_nypm_cognitive_dossier()
    assert [x["decision"] for x in p["cases"]] == [
        "LONG", "WAIT", "WAIT", "WAIT", "WAIT", "REJECT",
    ]
    assert p["source_profile_ict_general_state"] == (
        "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
    )
    assert p["source_profile_ttrades_state"] == "PROFILE_SESSION_REJECTED"
    assert p["real_original_cog_invoked"] is True
    assert p["methodology_certified"] is False
    assert p["cognitive_certified"] is False
    assert p["reviewer_signatures"] is False
    assert p["source_claim_author_certified"] is False
    assert p["trade_count_or_pnl"] is None
    assert p["orders_executed"] == 0
    assert p["trader_sizing"] == 0
    assert p["live_authorized"] is False


def test_nypm_each_scenario_keeps_own_actual_cognitive_asof():
    p = genuine_nypm_cognitive_dossier()
    rows = p["cases"]
    from datetime import datetime
    positive_at = datetime.fromisoformat(rows[0]["as_of"])
    assert datetime.fromisoformat(rows[1]["as_of"]) == (
        positive_at - timedelta(minutes=1)
    )
    assert datetime.fromisoformat(rows[2]["as_of"]) == positive_at
    for item in rows[3:5]:
        assert datetime.fromisoformat(item["as_of"]) == (
            positive_at + timedelta(minutes=1)
        )


def test_nypm_missing_one_pivot_confirmation_bar_will_not_forge_structure():
    stream, at = ny_pm_original_fixture()
    # Remove the 13:58 confirmation bar; no invented 3-candle pivot.
    removed = tuple(
        x for x in stream
        if x.opened_at != at - timedelta(minutes=5)
    )
    engine = VT31CleanroomCognition()
    for x in removed:
        engine.observe_closed_m1(x)
    response = engine.assess(session=SessionId.NY_PM, as_of=at)
    assert response.trade_authorized is False
    assert response.decision is None


def test_original_nypm_cannot_retroassess_after_later_closed_m1():
    stream, at = ny_pm_original_fixture()
    engine = VT31CleanroomCognition()
    for x in stream:
        engine.observe_closed_m1(x)
    engine.observe_closed_m1(
        bar(at, o="105", high="107", low="104", close="106"),
    )
    with pytest.raises(ValueError, match="exactly latest closed M1"):
        engine.assess(session=SessionId.NY_PM, as_of=at)
