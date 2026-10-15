"""Methodology / cognition source profile guard on original VT31 G3 COG."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    SessionId,
)
from scripts.vt31_cog_evidence_v2_20261014 import ICT_GENERAL, TTRADES_AM
from scripts.vt31_m0_profile_shadow_attestation_20261015 import (
    classify_source_profile,
    original_cog_profile_dossier,
)
from scripts.vt31_original_cog_nyam_ttrades_source_conflict_20261014 import (
    nyam_source_fixture,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    london_fixture,
)


def genuine(stream, session, at):
    cog = VT31CleanroomCognition()
    for bar in stream:
        cog.observe_closed_m1(bar)
    return cog.assess(session=session, as_of=at)


def test_exact_same_original_cog_nyam_dol_is_accepted_only_as_ict_unknown():
    stream, _, ten = nyam_source_fixture()
    at = ten[-1].closed_at
    observation = genuine(stream, SessionId.NY_AM, at)
    as_ttrades = classify_source_profile(
        selected_profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, closed_m1=stream, assessment=observation,
    )
    as_ict = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.NY_AM,
        as_of=at, closed_m1=stream, assessment=observation,
    )
    assert as_ttrades.state == "TTRADES_PROFILE_SOURCE_REJECTED"
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in as_ttrades.reasons
    assert as_ttrades.observed_action == "LONG"
    assert as_ttrades.observed_dol == "150"
    assert as_ttrades.ttrades_opposite_h1_dol == "110"
    assert as_ict.state == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
    assert as_ict.observed_dol == as_ttrades.observed_dol
    assert "ICT_EXTERNAL_DOL_PROVENANCE_UNVERIFIED" in as_ict.reasons
    assert as_ict.method_certified is False
    assert as_ttrades.cognition_certified is False


def test_london_profile_does_not_borrow_ttrades_am_required_9am_h1():
    stream, at = london_fixture()
    observation = genuine(stream, SessionId.LONDON, at)
    ict = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.LONDON,
        as_of=at, closed_m1=stream, assessment=observation,
    )
    incorrect = classify_source_profile(
        selected_profile=TTRADES_AM, session=SessionId.LONDON,
        as_of=at, closed_m1=stream, assessment=observation,
    )
    assert ict.state == "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
    assert ict.observed_action == "LONG"
    assert incorrect.state == "PROFILE_SESSION_REJECTED"
    assert incorrect.reasons == ("TTRADES_ONLY_NY_AM",)
    assert incorrect.observed_dol == "150"
    assert not ict.live_authorized and incorrect.orders_or_sizing == 0


def test_wrong_or_undefined_methodology_profile_never_automatically_certified():
    stream, at = london_fixture()
    observation = genuine(stream, SessionId.LONDON, at)
    with pytest.raises(ValueError, match="DECLARED_METHOD_PROFILE_UNKNOWN"):
        classify_source_profile(
            selected_profile="TTRADES_FOR_ALL_SESSIONS",
            session=SessionId.LONDON, as_of=at,
            closed_m1=stream, assessment=observation,
        )


def test_same_real_cog_assessment_with_stale_asof_fails_closed():
    stream, at = london_fixture()
    observation = genuine(stream, SessionId.LONDON, at)
    backdated = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.LONDON,
        as_of=at - timedelta(minutes=1),
        closed_m1=stream, assessment=observation,
    )
    assert backdated.state == "INPUT_INVALID_REJECTED"
    assert backdated.method_certified is False
    assert backdated.cognition_certified is False


def test_future_closed_bar_or_wrong_session_assessment_rejected():
    stream, at = london_fixture()
    observation = genuine(stream, SessionId.LONDON, at)
    future = replace(stream[-1],
        opened_at=stream[-1].closed_at,
        closed_at=stream[-1].closed_at + timedelta(minutes=1),
    )
    bad = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.LONDON,
        as_of=at, closed_m1=stream + (future,), assessment=observation,
    )
    assert bad.state == "INPUT_INVALID_REJECTED"
    altered = replace(observation, session=SessionId.NY_AM)
    bad_session = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.LONDON,
        as_of=at, closed_m1=stream, assessment=altered,
    )
    assert bad_session.state == "INPUT_INVALID_REJECTED"


def test_original_g3_cog_correct_wait_is_preserved_not_faked_as_source_signal():
    stream, at = london_fixture()
    # The original on observed M1 before its confirmed London shift abstains.
    early = stream[:-1]
    early_at = early[-1].closed_at
    observation = genuine(early, SessionId.LONDON, early_at)
    assert observation.decision is None
    result = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.LONDON,
        as_of=early_at, closed_m1=early, assessment=observation,
    )
    assert result.state == "COG_ABSTAINED"
    assert result.observed_action == "WAIT"
    assert result.observed_dol is None
    assert "CONFIRMED_DISPLACEMENT_MSS" in result.reasons


def test_dossier_exposes_nonconformity_without_profit_or_signatures():
    report = original_cog_profile_dossier()
    assert [x["state"] for x in report["cases"]] == [
        "TTRADES_PROFILE_SOURCE_REJECTED",
        "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
        "ICT_CONTEXT_WITNESS_UNDERDETERMINED",
        "PROFILE_SESSION_REJECTED",
    ]
    assert report["original_g3_cog_directly_invoked"] is True
    assert report["methodology_certified"] is False
    assert report["cognition_certified"] is False
    assert report["g3_independent_2_signatures_validated"] is False
    assert report["human_source_review_completed"] is False
    assert report["economic_gate_run"] is False
    assert report["profit_factor_drawdown_sharpe_sortino"] is None
    assert report["market_3y_replay_used"] is False
    assert report["broker_orders"] == 0
    assert report["trader_lot_sizing"] == 0
    assert report["live_authorized"] is False
    assert all(
        not x["method_certified"] and not x["cognition_certified"]
        and not x["live_authorized"] and x["orders_or_sizing"] == 0
        for x in report["cases"]
    )
