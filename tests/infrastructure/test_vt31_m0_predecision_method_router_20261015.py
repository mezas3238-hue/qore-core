"""VT31 M0 source profile PRESELECTED before M1 cognition, one trader."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    ICT_GENERAL,
    TTRADES_AM,
)
from scripts.vt31_m0_predecision_method_router_20261015 import (
    PREDECLARED,
    POLICY_ID,
    FrozenMethodProfilePolicy,
    route_preselected_method,
    source_identity_court,
)
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
def test_predeclared_nyam_ttrades_returns_correct_source_dol_or_justified_wait(
    month, side, compatible,
):
    bars, at = ttrades_fixture(
        side=side, month=month, min10_valid=compatible,
    )
    v = route_preselected_method(
        policy=PREDECLARED, session=SessionId.NY_AM,
        closed_m1=bars, as_of=at,
    )
    assert v.selected_profile_before_ingress == TTRADES_AM
    assert v.state == (SUCCESS if compatible else MIN10_CONFLICT)
    assert v.original_cog_invoked is True
    assert v.original_cog_side == side.value
    assert v.research_proposal_dto_only == compatible
    assert v.original_cog_dol == (
        "150" if side is Side.LONG else ("60" if compatible else "80")
    )
    assert v.ttrades_9h_author_dol == (
        ("120" if compatible else "110") if side is Side.LONG
        else ("80" if compatible else "90")
    )
    assert v.native_g3_production_integrated is False
    assert v.policy_owner_signed is False
    assert v.author_method_certified is False
    assert v.cognition_certified is False
    assert v.independent_cog_ops_roles_signed is False
    assert v.oms_or_live_authorized is False


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_ict_sessions_use_original_g3_but_do_not_fake_author_ict_approval(
    month, session, side,
):
    history, at = short_fixture(session=session, month=month)
    if side is Side.LONG:
        history = mirror_long_history(history)
    verdict = route_preselected_method(
        policy=PREDECLARED, session=session,
        closed_m1=history, as_of=at,
    )
    assert verdict.selected_profile_before_ingress == ICT_GENERAL
    assert verdict.original_cog_invoked
    assert verdict.original_cog_side == side.value
    assert verdict.original_cog_dol == ("150" if side is Side.LONG else "80")
    assert verdict.state == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
    assert not verdict.research_proposal_dto_only
    assert not verdict.author_method_certified


def test_policy_frozen_and_cannot_turn_london_into_ttrades_without_research_review():
    with pytest.raises(ValueError, match="METHOD_PROFILE_MATRIX_NOT_PREREGISTERED"):
        replace(PREDECLARED, ordered_session_map=(
            (SessionId.LONDON, TTRADES_AM),
            (SessionId.NY_AM, TTRADES_AM),
            (SessionId.NY_PM, ICT_GENERAL),
        ))
    with pytest.raises(ValueError, match="UNAUTHORIZED_OR_UNVERSIONED_METHOD_POLICY"):
        replace(PREDECLARED, policy_id="VT31_APPROVED_FAKE")
    assert PREDECLARED.policy_id == POLICY_ID
    assert PREDECLARED.profile_for(SessionId.LONDON) == ICT_GENERAL
    assert PREDECLARED.profile_for(SessionId.NY_AM) == TTRADES_AM
    assert PREDECLARED.profile_for(SessionId.NY_PM) == ICT_GENERAL


def test_unselected_policy_missing_method_or_future_history_fails_before_cog():
    bars, at = ttrades_fixture(
        side=Side.LONG, month=1, min10_valid=True,
    )
    common = {"session": SessionId.NY_AM, "closed_m1": bars, "as_of": at}
    with pytest.raises(ValueError, match="M0_EXPLICIT_IMMUTABLE_PROFILE_POLICY_REQUIRED"):
        route_preselected_method(policy=None, **common)
    with pytest.raises(ValueError, match="M0_POLICY_OR_M1_INGRESS_ASOF_CAUSALITY_VIOLATION"):
        route_preselected_method(
            policy=PREDECLARED,
            **(common | {"as_of": at - timedelta(minutes=1)}),
        )
    with pytest.raises(ValueError, match="M0_POLICY_OR_M1_INGRESS_ASOF_CAUSALITY_VIOLATION"):
        route_preselected_method(
            policy=PREDECLARED,
            **(common | {"closed_m1": bars + (bars[-1],)}),
        )
    with pytest.raises(ValueError, match="SESSION_UNKNOWN_OR_NOT_TYPED"):
        route_preselected_method(
            policy=PREDECLARED, **(common | {"session": "LONDON"}),
        )


def test_16_causal_cases_are_research_not_certificates():
    data = source_identity_court()
    assert len(data["cases"]) == 16
    assert len({x["case"] for x in data["cases"]}) == 16
    assert sum(x["state"] == SUCCESS for x in data["cases"]) == 4
    assert sum(x["state"] == MIN10_CONFLICT for x in data["cases"]) == 4
    assert sum(
        x["state"] == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
        for x in data["cases"]
    ) == 8
    assert data["source_g3_original_sha"]["git_blob_sha1"] == (
        "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
    )
    assert data["single_vt31_method_profile_preselected_before_M1"] is True
    assert data["research_only_not_connected_to_original_ops"] is True
    assert data["owner_policy_approved"] is False
    assert data["ict_original_author_case_certified"] is False
    assert data["ttrades_all_four_entries_certified"] is False
    assert data["native_g3_profile_selector_integrated"] is False
    assert data["methodology_certified"] is False
    assert data["cognition_certified"] is False
    assert data["dual_cog_ops_human_signatures"] is False
    assert data["historical_real_data_or_PNL"] is None
    assert data["orders"] == data["sizing"] == 0
    assert data["live"] is False
