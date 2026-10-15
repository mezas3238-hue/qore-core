"""One VT31 with immutable pre-session source profile; no trade authority."""
from __future__ import annotations

from datetime import timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    SessionId,
    Side,
    window_bounds,
)
from scripts.vt31_cog_evidence_v2_20261014 import TTRADES_AM
from scripts.vt31_m0_explicit_source_profile_router_20261015 import (
    ICT,
    QORE,
    PreSessionMethodRouter,
    SourceProfileBinding,
    profile_router_court,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)


def binding(*, profile=TTRADES_AM, month=7, side=Side.LONG,
            valid=True, session=SessionId.NY_AM):
    bars,at=ttrades_fixture(side=side,month=month,min10_valid=valid)
    start,_=window_bounds(at,session)
    return bars,at,SourceProfileBinding(
        profile=profile,session=session,selected_at=start,
    )


@pytest.mark.parametrize("month",[1,7])
@pytest.mark.parametrize("side",[Side.LONG,Side.SHORT])
def test_sourcefirst_uses_real_original_g3_but_never_promotes_to_trade(month,side):
    bars,at,b=binding(month=month,side=side,valid=True)
    ans=PreSessionMethodRouter(b).assess(
        as_of=at,closed_m1=bars,
    )
    assert ans.status=="TTRADES_SOURCE_FIRST_CONTEXT_RESEARCH_ONLY"
    assert ans.source_bound_research_dto_available
    assert ans.ttrades_source_first_adapter_called
    assert ans.genuine_original_g3_cog_called
    assert ans.source_dol_provenance=="TTRADES_09_H1_OPPOSITE_NOT_PRIOR_CASH"
    assert not ans.ops_authorized
    assert not ans.author_method_complete_certified
    assert not ans.trader_certified
    assert ans.broker_orders_ack_fills==ans.lot_sizing==0


@pytest.mark.parametrize("month",[1,7])
@pytest.mark.parametrize("side",[Side.LONG,Side.SHORT])
def test_conflicting_source_min10_stays_wait_not_fake_author_dol(month,side):
    bars,at,b=binding(month=month,side=side,valid=False)
    ans=PreSessionMethodRouter(b).assess(
        as_of=at,closed_m1=bars,
    )
    assert ans.status=="WAIT_TTRADES_AUTHOR_DOL_QORE_MIN10_CONFLICT"
    assert not ans.source_bound_research_dto_available
    assert not ans.ops_authorized
    assert not ans.method_source_status=="RESEARCH_TTRADES_CONTEXT_CONFORMANT_NOT_CERTIFIED"


@pytest.mark.parametrize("profile",[ICT,QORE])
def test_other_profiles_use_same_original_g3_without_claiming_ttrades(profile):
    bars,at,b=binding(profile=profile,month=1,valid=True)
    ans=PreSessionMethodRouter(b).assess(
        as_of=at,closed_m1=bars,
    )
    assert ans.profile==profile
    assert ans.genuine_original_g3_cog_called
    assert not ans.ttrades_source_first_adapter_called
    assert not ans.source_bound_research_dto_available
    assert "TTRADES_09H" not in ans.source_dol_provenance
    assert not ans.cognitive_certified


@pytest.mark.parametrize("session",[SessionId.LONDON,SessionId.NY_PM])
def test_ttrades_never_inherits_other_session_ict_clock(session):
    _,_,b=binding(session=session)
    with pytest.raises(ValueError,match="TTRADES_NYAM_ONLY"):
        PreSessionMethodRouter(b)


def test_post_session_profile_switch_forbidden_even_if_code_would_find_source():
    bars,at,b=binding()
    start,_=window_bounds(at,b.session)
    illegal=SourceProfileBinding(
        profile=b.profile,session=b.session,
        selected_at=start+timedelta(minutes=1),
    )
    with pytest.raises(ValueError,match="SELECTED_AFTER_SESSION"):
        PreSessionMethodRouter(illegal).assess(as_of=at,closed_m1=bars)


def test_day_after_selection_cannot_recycle_source_profile():
    bars,at,b=binding()
    yesterday=SourceProfileBinding(
        profile=b.profile,session=b.session,
        selected_at=b.selected_at-timedelta(days=1),
    )
    with pytest.raises(ValueError,match="SAME_NY_DAY"):
        PreSessionMethodRouter(yesterday).assess(as_of=at,closed_m1=bars)


def test_incomplete_time_line_future_bar_refused():
    bars,at,b=binding()
    with pytest.raises(ValueError,match="ASOF"):
        PreSessionMethodRouter(b).assess(
            as_of=at-timedelta(minutes=1),closed_m1=bars,
        )


def test_unrecognized_source_identity_cannot_make_method_decision():
    _,_,b=binding()
    with pytest.raises(ValueError,match="UNKNOWN_METHOD_SOURCE_PROFILE"):
        PreSessionMethodRouter(SourceProfileBinding(
            profile="AUTODETECT_BEST_PROFIT",session=b.session,
            selected_at=b.selected_at,
        ))


def test_pre_registered_8_real_g3_research_scenarios_have_no_certificate():
    p=profile_router_court()
    assert p["real_g3_cognition_source_first_evaluations"]==8
    assert sum(x["source_bound_research_dto_available"] for x in p["cases"])==4
    assert sum(x["status"]=="WAIT_TTRADES_AUTHOR_DOL_QORE_MIN10_CONFLICT"
               for x in p["cases"])==4
    assert p["M6_dual_human_signatures_verified"] is False
    assert p["methodology_certified"] is False
    assert p["cognition_certified"] is False
    assert p["broker_orders_fills"]==0
