from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_m1_rearm_capacity import (
    V50RearmAttempt,
)


def test_rearm_attempt_is_pre_economic_and_does_not_consume_slot() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    attempt = V50RearmAttempt(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price=str(Decimal("99")),
        trigger_confirmed_at=(at + timedelta(minutes=5)).isoformat(),
        trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
        attempt_index=2,
        geometry_decision="READY",
        cognitive_disposition="PASS_TO_COMPETITION",
        geometry_ready=True,
        cognitive_geometry_ready=True,
    )
    assert attempt.attempt_index == 2
    assert attempt.slot_consumed_during_wait is False
    assert attempt.stop_relaxed is False
    assert attempt.outcome_used is False
    assert attempt.economics_used is False
    assert attempt.fresh_holdout_used is False


def test_v49_opportunity_contract_remains_pre_economic_for_rearm_payload() -> None:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    row = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=(at + timedelta(minutes=5)).isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )
    assert row.outcome_used is False
    assert row.economics_used is False
    assert row.daily_used is False
    assert row.h4_used is False
