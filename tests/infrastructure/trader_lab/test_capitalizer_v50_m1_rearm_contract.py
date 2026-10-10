from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_v50_m1_rearm_contract import (
    V50RearmState,
    V50RearmTicket,
    arm_v50_reassessment,
    observe_new_m1_event,
)


def _ticket() -> V50RearmTicket:
    return arm_v50_reassessment(
        symbol="AUDUSD",
        session="ASIA",
        decision_at=datetime(2026, 1, 5, 2, 0, tzinfo=UTC),
        h1_state_id="H1:1",
        m15_setup_id="M15:1",
        m1_event_id="M1:1",
    )


def test_waiting_rearm_does_not_consume_max3_or_relax_stop() -> None:
    ticket = _ticket()
    assert ticket.state is V50RearmState.WAITING_NEW_M1_CAUSAL_EVENT
    assert ticket.max3_slot_consumed is False
    assert ticket.stop_relaxation_allowed is False
    assert ticket.post_entry_stop_widening_allowed is False


def test_new_m1_event_rearms_only_if_parent_thesis_is_still_valid() -> None:
    ticket = _ticket()
    result = observe_new_m1_event(
        ticket,
        observed_at=ticket.last_evaluated_at + timedelta(minutes=3),
        m1_event_id="M1:2",
        h1_still_valid=True,
        m15_still_valid=True,
        session_open=True,
        opposite_h1_event=False,
    )
    assert result.state is V50RearmState.READY_FOR_REEVALUATION
    assert result.rearm_count == 1
    assert result.last_m1_event_id == "M1:2"


def test_identical_m1_evidence_cannot_create_fake_rearm() -> None:
    ticket = _ticket()
    result = observe_new_m1_event(
        ticket,
        observed_at=ticket.last_evaluated_at + timedelta(minutes=1),
        m1_event_id="M1:1",
        h1_still_valid=True,
        m15_still_valid=True,
        session_open=True,
        opposite_h1_event=False,
    )
    assert result.state is V50RearmState.WAITING_NEW_M1_CAUSAL_EVENT
    assert result.rearm_count == 0


def test_opposite_h1_event_cancels_before_new_m1_structure() -> None:
    ticket = _ticket()
    result = observe_new_m1_event(
        ticket,
        observed_at=ticket.last_evaluated_at + timedelta(minutes=2),
        m1_event_id="M1:2",
        h1_still_valid=True,
        m15_still_valid=True,
        session_open=True,
        opposite_h1_event=True,
    )
    assert result.state is V50RearmState.CANCELLED_OPPOSITE_H1


def test_rearm_chronology_cannot_move_backwards() -> None:
    ticket = _ticket()
    with pytest.raises(ValueError):
        observe_new_m1_event(
            ticket,
            observed_at=ticket.last_evaluated_at,
            m1_event_id="M1:2",
            h1_still_valid=True,
            m15_still_valid=True,
            session_open=True,
            opposite_h1_event=False,
        )
