"""V50-R architecture-only M1 cognitive re-arm contract.

This contract is intentionally non-economic. It defines how a source-complete H1->M15->M1
opportunity may remain cognitively alive after V50 Geometry returns WAIT_STOP_BREATHING.

Core law:
- do NOT consume a MAX3 slot;
- do NOT widen/relax the execution stop;
- preserve the H1/M15 thesis only while its causal validity/freshness remains intact;
- require a genuinely new M1 causal structure before reconsideration;
- every reconsideration gets a new decision timestamp and rebuilds stop/target geometry from
  information available at that timestamp;
- no current/future outcome is visible;
- no infinite polling / no repeated identical evidence.

This module does not generate economics, approve trades, or promote runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V50_R_M1_COGNITIVE_REARM_CONTRACT"


class V50RearmState(StrEnum):
    NOT_ARMED = "NOT_ARMED"
    WAITING_NEW_M1_CAUSAL_EVENT = "WAITING_NEW_M1_CAUSAL_EVENT"
    READY_FOR_REEVALUATION = "READY_FOR_REEVALUATION"
    EXPIRED_H1 = "EXPIRED_H1"
    EXPIRED_M15 = "EXPIRED_M15"
    EXPIRED_SESSION = "EXPIRED_SESSION"
    CANCELLED_OPPOSITE_H1 = "CANCELLED_OPPOSITE_H1"


@dataclass(frozen=True, slots=True)
class V50RearmTicket:
    identity: str
    source_symbol: str
    source_session: str
    original_decision_at: datetime
    last_evaluated_at: datetime
    state: V50RearmState
    h1_state_id: str
    m15_setup_id: str
    last_m1_event_id: str
    rearm_count: int
    max3_slot_consumed: bool = False
    stop_relaxation_allowed: bool = False
    post_entry_stop_widening_allowed: bool = False
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    grants_entry_authority: bool = False
    rule_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50-R re-arm identity")
        for value in (self.original_decision_at, self.last_evaluated_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("V50-R timestamps must be timezone-aware")
        if self.last_evaluated_at < self.original_decision_at:
            raise ValueError("V50-R chronology cannot go backwards")
        if not all(
            (
                self.source_symbol,
                self.source_session,
                self.h1_state_id,
                self.m15_setup_id,
                self.last_m1_event_id,
            )
        ):
            raise ValueError("V50-R requires causal provenance identities")
        if self.rearm_count < 0:
            raise ValueError("V50-R rearm_count cannot be negative")
        if self.max3_slot_consumed:
            raise ValueError("waiting/re-arm state cannot consume MAX3 slot")
        if self.stop_relaxation_allowed or self.post_entry_stop_widening_allowed:
            raise ValueError("V50-R cannot relax or widen execution risk")
        if self.current_outcome_visible or self.future_bars_visible:
            raise ValueError("V50-R cannot see current/future outcome")
        if self.grants_entry_authority or self.rule_promotion_allowed:
            raise ValueError("V50-R contract is architecture-only")


def arm_v50_reassessment(
    *,
    symbol: str,
    session: str,
    decision_at: datetime,
    h1_state_id: str,
    m15_setup_id: str,
    m1_event_id: str,
) -> V50RearmTicket:
    return V50RearmTicket(
        identity=IDENTITY,
        source_symbol=symbol,
        source_session=session,
        original_decision_at=decision_at,
        last_evaluated_at=decision_at,
        state=V50RearmState.WAITING_NEW_M1_CAUSAL_EVENT,
        h1_state_id=h1_state_id,
        m15_setup_id=m15_setup_id,
        last_m1_event_id=m1_event_id,
        rearm_count=0,
    )


def observe_new_m1_event(
    ticket: V50RearmTicket,
    *,
    observed_at: datetime,
    m1_event_id: str,
    h1_still_valid: bool,
    m15_still_valid: bool,
    session_open: bool,
    opposite_h1_event: bool,
) -> V50RearmTicket:
    """Advance only on genuinely new causal evidence or terminal expiry."""

    if observed_at <= ticket.last_evaluated_at:
        raise ValueError("V50-R reevaluation requires later causal time")
    if opposite_h1_event:
        state = V50RearmState.CANCELLED_OPPOSITE_H1
    elif not h1_still_valid:
        state = V50RearmState.EXPIRED_H1
    elif not m15_still_valid:
        state = V50RearmState.EXPIRED_M15
    elif not session_open:
        state = V50RearmState.EXPIRED_SESSION
    elif m1_event_id == ticket.last_m1_event_id:
        state = V50RearmState.WAITING_NEW_M1_CAUSAL_EVENT
    else:
        state = V50RearmState.READY_FOR_REEVALUATION

    return V50RearmTicket(
        identity=IDENTITY,
        source_symbol=ticket.source_symbol,
        source_session=ticket.source_session,
        original_decision_at=ticket.original_decision_at,
        last_evaluated_at=observed_at,
        state=state,
        h1_state_id=ticket.h1_state_id,
        m15_setup_id=ticket.m15_setup_id,
        last_m1_event_id=(
            m1_event_id
            if state is V50RearmState.READY_FOR_REEVALUATION
            else ticket.last_m1_event_id
        ),
        rearm_count=(
            ticket.rearm_count + 1
            if state is V50RearmState.READY_FOR_REEVALUATION
            else ticket.rearm_count
        ),
    )
