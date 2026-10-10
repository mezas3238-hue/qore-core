"""Executable intent layer for the V49 High-Frequency Scalper.

The strategy entry policy is frozen before the reserved 1Y holdout:
- H1/M15/M1 opportunity must already be source-complete in V49 capacity logic;
- entry = causal M1 trigger confirmation close;
- stop = M15 protected swing;
- target = causal structural H1 target witness already known at decision time;
- portfolio selection = chronological first opportunities, max 3 per session/day.

This module creates deterministic trade intents only. It does not inspect future outcomes,
P&L, size positions, allocate capital, or authorize live execution.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)

IDENTITY = "QORE_CAPITALIZER_V49_HIGH_FREQUENCY_TRADER"


class V49TradeDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class V49TradeIntent:
    identity: str
    symbol: str
    session: str
    operating_date: str
    direction: V49TradeDirection
    entry_at: datetime
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    trigger_family: str
    h1_state_basis: str
    outcome_used: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 trader identity is frozen")
        if self.entry_at.tzinfo is None or self.entry_at.utcoffset() is None:
            raise ValueError("trade intent time must be timezone-aware")
        if self.direction is V49TradeDirection.LONG:
            if not self.stop_price < self.entry_price < self.target_price:
                raise ValueError("invalid long stop/entry/target geometry")
        else:
            if not self.target_price < self.entry_price < self.stop_price:
                raise ValueError("invalid short stop/entry/target geometry")
        if self.outcome_used:
            raise ValueError("trade selection cannot use future outcomes")
        if self.sizing_authority or self.execution_authority or self.capital_authority:
            raise ValueError("Trader intent grants no sizing/execution/capital authority")


def materialize_trade_intent(opportunity: V49Opportunity) -> V49TradeIntent:
    direction = (
        V49TradeDirection.LONG
        if opportunity.h1_state_direction == "BULLISH"
        else V49TradeDirection.SHORT
    )
    return V49TradeIntent(
        identity=IDENTITY,
        symbol=opportunity.symbol,
        session=opportunity.session,
        operating_date=opportunity.operating_date,
        direction=direction,
        entry_at=datetime.fromisoformat(opportunity.m1_trigger_confirmed_at),
        entry_price=Decimal(opportunity.decision_reference_price),
        stop_price=Decimal(opportunity.m15_protected_swing_price),
        target_price=Decimal(opportunity.structural_target_witness_price),
        trigger_family=opportunity.m1_trigger_family,
        h1_state_basis=opportunity.h1_state_basis,
    )


def select_portfolio_trade_intents(
    opportunities: tuple[V49Opportunity, ...],
) -> tuple[V49TradeIntent, ...]:
    """Select deterministic first-three opportunities per session/day portfolio-wide."""

    grouped: dict[tuple[str, str], list[V49Opportunity]] = defaultdict(list)
    for item in opportunities:
        grouped[(item.session, item.operating_date)].append(item)

    selected: list[V49TradeIntent] = []
    for key in sorted(grouped):
        rows = sorted(
            grouped[key],
            key=lambda item: (
                item.m1_trigger_confirmed_at,
                item.symbol,
                item.m1_trigger_family,
            ),
        )
        for item in rows[:MAX_EXECUTIONS_PER_SESSION]:
            selected.append(materialize_trade_intent(item))

    return tuple(sorted(selected, key=lambda item: (item.entry_at, item.symbol)))
