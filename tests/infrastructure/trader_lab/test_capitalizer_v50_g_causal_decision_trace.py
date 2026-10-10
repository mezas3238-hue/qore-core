"""Fail-closed guards for V50-G's truthful cognitive audit trace."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    BRIDGE_ONLY,
    TRACE_IDENTITY,
    V50GCausalDecisionTrace,
    source_opportunity_id,
    trace_json_line,
)


def _opportunity() -> V49Opportunity:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    return V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="BULLISH_FVG",
        m15_setup_confirmed_at=(at + timedelta(minutes=15)).isoformat(),
        m15_protected_swing_price="1.1000",
        m1_trigger_confirmed_at=(at + timedelta(minutes=20)).isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="1.1010",
        structural_target_witness_price="1.1050",
    )


def _trace() -> V50GCausalDecisionTrace:
    opp = _opportunity()
    return V50GCausalDecisionTrace(
        identity=TRACE_IDENTITY,
        source_opportunity_id=source_opportunity_id(opp),
        symbol=opp.symbol,
        session=opp.session,
        observed_at=opp.m1_trigger_confirmed_at,
        source_h1_from=opp.h1_state_from,
        source_m15_confirmed_at=opp.m15_setup_confirmed_at,
        source_m1_confirmed_at=opp.m1_trigger_confirmed_at,
        source_trigger_family=opp.m1_trigger_family,
        state_family_id="V50:fixture",
        bridge_disposition="PASS_TO_COMPETITION",
        bridge_reasons=("CAUSAL_FIXTURE",),
        bridge_knowledge="UNKNOWN",
        experience_observations=0,
        geometry_decision="READY",
        geometry_reasons=("READY",),
        policy_geometry_only_eligible=True,
        policy_cognitive_geometry_eligible=True,
    )


def test_trace_exposes_partial_bridge_without_claiming_full_cognition() -> None:
    trace = _trace()
    assert trace.cognition_coverage == BRIDGE_ONLY
    assert not trace.master_frame_evaluated
    assert not trace.readiness_verified
    assert trace.experience_observations == 0
    assert '"outcome_visible_to_cognition":false' in trace_json_line(trace)


@pytest.mark.parametrize(
    "changes",
    [
        {"master_frame_evaluated": True},
        {"global_world_model_evaluated": True},
        {"nine_market_competition_evaluated": True},
        {"readiness_verified": True},
        {"experience_observations": 1},
        {"outcome_visible_to_cognition": True},
        {"capital_authority_granted": True},
        {"cognition_coverage": "FULL"},
        {"experience_memory_scope": "PERSISTENT"},
        {"readiness_origin": "EVIDENCE_BACKED"},
    ],
)
def test_trace_rejects_false_integration_claims(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(_trace(), **changes)


def test_trace_rejects_future_confirmations_and_naive_timestamps() -> None:
    trace = _trace()
    future = (datetime.fromisoformat(trace.observed_at) + timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError):
        replace(trace, source_m15_confirmed_at=future)
    with pytest.raises(ValueError):
        replace(trace, source_m1_confirmed_at=future)
    with pytest.raises(ValueError):
        replace(trace, observed_at="2026-01-05T12:20:00")


def test_source_id_is_repeatable_and_changes_with_trigger() -> None:
    opp = _opportunity()
    assert source_opportunity_id(opp) == source_opportunity_id(opp)
    assert source_opportunity_id(opp) != source_opportunity_id(
        replace(opp, m1_trigger_family="LIQUIDITY_SWEEP_CISD")
    )
