"""Persistent H1 context-state engine for the V49 high-frequency Scalper.

V48 coupled one fresh H1 event to one downstream opportunity. V49 preserves an H1 directional
state until an opposite H1 signal or the end of the operating session. Multiple M15 setups and
M1 triggers may therefore share one H1 state without consuming it.

The engine only manages causal state lifetime. It does not decide how an H1 bias signal is
detected, does not rank setups, and does not use outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

IDENTITY = "QORE_CAPITALIZER_V49_PERSISTENT_H1_CONTEXT"


class V49H1StateEndReason(StrEnum):
    OPPOSITE_H1_SIGNAL = "OPPOSITE_H1_SIGNAL"
    SESSION_END = "SESSION_END"


@dataclass(frozen=True, slots=True)
class V49H1BiasSignal:
    confirmed_at: datetime
    direction: CapitalizerSourceDirection
    basis_id: str

    def __post_init__(self) -> None:
        if self.confirmed_at.tzinfo is None or self.confirmed_at.utcoffset() is None:
            raise ValueError("H1 signal time must be timezone-aware")
        if not self.basis_id:
            raise ValueError("H1 signal requires causal basis")


@dataclass(frozen=True, slots=True)
class V49H1ContextState:
    identity: str
    session: CapitalizerSession
    direction: CapitalizerSourceDirection
    active_from: datetime
    active_until: datetime
    established_by: str
    end_reason: V49H1StateEndReason
    consumed_after_trade: bool = False
    outcome_used: bool = False
    economics_used: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 H1 state identity is frozen")
        if self.active_until <= self.active_from:
            raise ValueError("H1 state must have positive lifetime")
        if self.consumed_after_trade:
            raise ValueError("V49 H1 state is reusable across intrastate setups")
        if self.outcome_used or self.economics_used:
            raise ValueError("H1 state engine must remain pre-economic")

    def contains(self, moment: datetime) -> bool:
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("state lookup moment must be timezone-aware")
        return self.active_from <= moment < self.active_until


def build_h1_context_states(
    signals: tuple[V49H1BiasSignal, ...],
    *,
    session: CapitalizerSession,
    session_start: datetime,
    session_end: datetime,
) -> tuple[V49H1ContextState, ...]:
    """Build non-overlapping H1 states inside one operating session."""

    if session_start.tzinfo is None or session_start.utcoffset() is None:
        raise ValueError("session_start must be timezone-aware")
    if session_end.tzinfo is None or session_end.utcoffset() is None:
        raise ValueError("session_end must be timezone-aware")
    if session_end <= session_start:
        raise ValueError("session window must be positive")

    ordered = tuple(sorted(signals, key=lambda item: item.confirmed_at))
    if ordered != signals:
        raise ValueError("H1 bias signals must be chronological")

    prior = tuple(item for item in signals if item.confirmed_at < session_start)
    relevant_list = [
        item
        for item in signals
        if session_start <= item.confirmed_at < session_end
    ]
    if prior:
        seed = prior[-1]
        relevant_list.insert(
            0,
            V49H1BiasSignal(
                confirmed_at=session_start,
                direction=seed.direction,
                basis_id=f"SESSION_INHERITED:{seed.basis_id}",
            ),
        )
    relevant = tuple(relevant_list)

    states: list[V49H1ContextState] = []
    for index, signal in enumerate(relevant):
        if index > 0 and relevant[index - 1].direction is signal.direction:
            continue

        opposite = next(
            (
                candidate
                for candidate in relevant[index + 1 :]
                if candidate.direction is not signal.direction
            ),
            None,
        )
        end = opposite.confirmed_at if opposite is not None else session_end
        if end <= signal.confirmed_at:
            continue
        states.append(
            V49H1ContextState(
                identity=IDENTITY,
                session=session,
                direction=signal.direction,
                active_from=signal.confirmed_at,
                active_until=end,
                established_by=signal.basis_id,
                end_reason=(
                    V49H1StateEndReason.OPPOSITE_H1_SIGNAL
                    if opposite is not None
                    else V49H1StateEndReason.SESSION_END
                ),
            )
        )

    deduped: list[V49H1ContextState] = []
    for state in states:
        if deduped and state.active_from < deduped[-1].active_until:
            continue
        deduped.append(state)
    return tuple(deduped)


def state_at(
    states: tuple[V49H1ContextState, ...],
    moment: datetime,
) -> V49H1ContextState | None:
    matches = tuple(state for state in states if state.contains(moment))
    if len(matches) > 1:
        raise ValueError("H1 states must not overlap")
    return matches[0] if matches else None
