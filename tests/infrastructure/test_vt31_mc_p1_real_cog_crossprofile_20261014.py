"""Adversarial TRUE COG producer vs TTrades NY AM; methodology != software PASS."""
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    SessionId,
    Side,
)
from scripts.vt31_mc_p1_real_cog_crossprofile_witness_20261014 import (
    _bar,
    audit_actual_cog_cross_profile,
    synthetic_real_cog_case,
)
from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
    assess_ttrades_am_context,
    ict_2023_profile_scope,
)


def test_true_engine_emits_causal_mss_dto_without_ttrades_h1_raid() -> None:
    engine, h9, h10, at = synthetic_real_cog_case()
    a = engine.assess(session=SessionId.NY_AM, as_of=at)
    d = a.decision
    assert d is not None, a.missing
    assert d.side is Side.LONG
    assert d.framework_policy == G3_MSS_FRAMEWORK_POLICY
    assert d.draw_family == "PRIOR_NY_CASH_SESSION_HIGH"
    assert d.draw_target == Decimal("150")
    assert d.mss_anchor_close == Decimal("107")
    assert d.structure_break_confirmed_at == h10[-1].closed_at
    assert "H1" in a.verified_htf and "M15" in a.verified_htf
    assert max(x.high for x in h9) == Decimal("110")
    assert min(x.low for x in h9) == Decimal("90")
    assert max(x.high for x in h10) < Decimal("110")
    assert min(x.low for x in h10) > Decimal("90")
    assert a.trade_authorized is False


def test_real_cog_dto_is_rejected_by_distinct_ttrades_am_primary_source() -> None:
    engine, h9, h10, at = synthetic_real_cog_case()
    assessment = engine.assess(session=SessionId.NY_AM, as_of=at)
    assert assessment.decision is not None
    actual = assess_ttrades_am_context(
        cognition=assessment.decision,
        previous_ny_9am=h9,
        current_ny_10am=h10,
    )
    assert actual.status == "REJECTED"
    assert "NO_PRE_SIGNAL_9AM_H1_SWEEP" in actual.reason_codes
    assert "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in actual.reason_codes
    assert not actual.execution_authorized
    assert not actual.methodology_certified
    assert not actual.cognitive_certified


def test_cog_cannot_backdate_evaluation_after_future_market_input() -> None:
    engine, _, h10, at = synthetic_real_cog_case()
    engine.observe_closed_m1(_bar(
        h10[-1].closed_at,
        op="107", high="111", low="105", close="110",
    ))
    with pytest.raises(ValueError, match="exactly latest closed M1"):
        engine.assess(session=SessionId.NY_AM, as_of=at)


def test_ttrades_cannot_take_future_source_m1_as_proof() -> None:
    engine, h9, h10, at = synthetic_real_cog_case()
    a = engine.assess(session=SessionId.NY_AM, as_of=at)
    assert a.decision is not None
    future = _bar(at, op="107", high="112", low="105", close="110")
    check = assess_ttrades_am_context(
        cognition=a.decision,
        previous_ny_9am=h9,
        current_ny_10am=h10 + (future,),
    )
    assert "FUTURE_M1_IN_SOURCE" in check.reason_codes
    assert "COG_AS_OF_NOT_LAST_CLOSED_M1" in check.reason_codes
    assert check.status == "REJECTED"


def test_ttrades_hour9_veto_not_applied_universally_to_ict_london_nypm() -> None:
    for session in (SessionId.LONDON, SessionId.NY_PM):
        profile = ict_2023_profile_scope(session)
        assert profile["allowed_session"]
        assert profile["9am_H1_raid_universal_required"] is False
        assert profile["methodology_certified"] is False


def test_report_does_not_pretend_a_cognition_or_trader_certificate() -> None:
    report = audit_actual_cog_cross_profile()
    assert report["status"] == "ACTUAL_COG_NOT_TTRADES_AM_SOURCE_CONFORMANT"
    assert report["cog_decision_authentic"] is True
    assert report["cog_target"] == "150"
    assert report["cog_mss_anchor"] == "107"
    assert set(report["ttrades_am_rejection_reasons"]) >= {
        "NO_PRE_SIGNAL_9AM_H1_SWEEP",
        "DOL_NOT_OPPOSITE_9AM_H1_EXTREME",
    }
    assert report["trading_authorized"] is False
    assert report["method_certified"] is False
    assert report["cognitive_certified"] is False


def test_all_window_event_clocks_true_m1_and_source_before_signal() -> None:
    engine, h9, h10, at = synthetic_real_cog_case()
    d = engine.assess(session=SessionId.NY_AM, as_of=at).decision
    assert d is not None
    assert h9[-1].closed_at == h10[0].opened_at
    assert d.draw_level_observed_at < h9[0].opened_at
    assert d.structure_level_confirmed_at < d.structure_break_confirmed_at
    assert d.structure_break_confirmed_at <= d.observed_at
    assert h10[-1].closed_at - h10[0].opened_at == timedelta(minutes=6)
