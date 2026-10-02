"""Factorized causal-state belief for Shared Core.

A single categorical posterior can mix two different questions:

1. Is a meaningful near-term event likely at all?
2. Conditional on an event, is the causal direction adverse or favorable?

NO_EVENT should answer the first question. It must not erase directional
information for the second. This module factorizes an existing causal-state
posterior into event readiness and conditional directional belief.

The component is outcome-blind and authority-free. It carries no strategy,
sizing, capital, risk, stop, target, order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.causal_state_filter import (
    FilteredCausalStateBelief,
)


@dataclass(frozen=True, slots=True)
class FactorizedCausalState:
    as_of_iso: str
    event_bps: int
    no_event_bps: int
    directional_evidence_bps: int
    adverse_conditional_bps: int
    favorable_conditional_bps: int
    directional_margin_bps: int
    dominant_direction: str
    evidence_count: int
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "event_bps",
            "no_event_bps",
            "directional_evidence_bps",
            "adverse_conditional_bps",
            "favorable_conditional_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if not -10_000 <= self.directional_margin_bps <= 10_000:
            raise ValueError("directional_margin_bps must be within -10000..10000")
        if self.dominant_direction not in {"ADVERSE", "FAVORABLE", "CONTESTED"}:
            raise ValueError("dominant_direction is invalid")
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("factorized causal state cannot carry trading authority")


def _conditional_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 5_000
    return max(0, min(10_000, numerator * 10_000 // denominator))


def factorize_causal_state(
    belief: FilteredCausalStateBelief,
    *,
    adverse_states: frozenset[str],
    favorable_states: frozenset[str],
    no_event_state: str,
) -> FactorizedCausalState:
    """Separate event readiness from conditional causal direction."""

    if not adverse_states or not favorable_states:
        raise ValueError("adverse and favorable state sets must be non-empty")
    if adverse_states & favorable_states:
        raise ValueError("adverse and favorable state sets must be disjoint")
    if no_event_state in adverse_states or no_event_state in favorable_states:
        raise ValueError("no_event_state must be direction-neutral")

    adverse = sum(belief.probability_bps(state) for state in adverse_states)
    favorable = sum(belief.probability_bps(state) for state in favorable_states)
    no_event = belief.probability_bps(no_event_state)
    directional = adverse + favorable
    adverse_conditional = _conditional_bps(adverse, directional)
    favorable_conditional = _conditional_bps(favorable, directional)
    margin = adverse_conditional - favorable_conditional

    if margin > 0:
        dominant = "ADVERSE"
    elif margin < 0:
        dominant = "FAVORABLE"
    else:
        dominant = "CONTESTED"

    return FactorizedCausalState(
        as_of_iso=belief.as_of.isoformat(),
        event_bps=max(0, min(10_000, 10_000 - no_event)),
        no_event_bps=no_event,
        directional_evidence_bps=max(0, min(10_000, directional)),
        adverse_conditional_bps=adverse_conditional,
        favorable_conditional_bps=favorable_conditional,
        directional_margin_bps=margin,
        dominant_direction=dominant,
        evidence_count=belief.evidence_count,
    )
