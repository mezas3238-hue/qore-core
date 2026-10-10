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

from qore.infrastructure.trader_lab.capitalizer_a1_multi_hypothesis_research import (
    A1MultiHypothesisBarrier,
)
from qore.infrastructure.trader_lab.capitalizer_a1_trader_cognition_port import (
    A1TraderCognitionPacket,
    prepare_trader_cognition_packet,
)
from qore.infrastructure.trader_lab.capitalizer_a1_full_frame_research_adapter import (
    A1CausalSettledMemory,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
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
    *,
    master_frame_barriers: tuple[A1MultiHypothesisBarrier, ...] | None = None,
    settled_memory: A1CausalSettledMemory | None = None,
) -> tuple[V49TradeIntent, ...]:
    """Source-frozen MAX3 Trader intent selection, optionally Master-Frame-gated.

    Legacy two-argument calls retain EXACT original baseline behavior. Master
    mode requires complete observed nine-market barriers and chosen-settled
    memory. PASS is only a research trade intent, never execution authority.
    """

    if master_frame_barriers is not None:
        if settled_memory is None:
            raise ValueError("Master Frame mode requires a causal settled-memory ledger")
        return select_master_frame_trade_intents(
            opportunities, barriers=master_frame_barriers, settled_memory=settled_memory
        ).trade_intents
    if settled_memory is not None:
        raise ValueError("settled memory without Master Frame barriers is unsafe")

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


@dataclass(frozen=True, slots=True)
class A1MasterFrameTraderIntentReport:
    """Research evidence that ACTUAL Trader intent selection consumed Master Frame.

    Source denial alters the research intent list, not real broker execution.
    Historical V49 remains unchanged unless this mode is explicitly requested.
    """

    identity: str
    source_opportunity_ids: tuple[str, ...]
    cognitive_packets: tuple[A1TraderCognitionPacket, ...]
    trader_intent_source_ids: tuple[str, ...]
    trade_intents: tuple[V49TradeIntent, ...]
    cognition_pass_ids: tuple[str, ...]
    cognition_wait_ids: tuple[str, ...]
    cognition_abstain_ids: tuple[str, ...]
    held_by_max3_ids: tuple[str, ...]
    all_source_candidates_accounted_for: bool
    selection_policy: str = "FROZEN_V49_CHRONOLOGICAL_MAX3_RESEARCH"
    full_master_frame_used: bool = True
    master_frame_changed_intent_admission: bool = True
    real_orders_placed: bool = False
    risk_authority_granted: bool = False
    certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != "QORE_SCALPER_A1_MASTER_FRAME_TRADER_INTENT_RESEARCH_V1":
            raise ValueError("unrecognized Master Frame Trader intent report")
        if len(set(self.source_opportunity_ids)) != len(self.source_opportunity_ids):
            raise ValueError("duplicate source opportunities")
        sets = [
            set(self.cognition_pass_ids),
            set(self.cognition_wait_ids),
            set(self.cognition_abstain_ids),
        ]
        if (
            not self.all_source_candidates_accounted_for
            or set.union(*sets) != set(self.source_opportunity_ids)
            or any(sets[i] & sets[j] for i in range(3) for j in range(i+1, 3))
            or not set(self.trader_intent_source_ids).issubset(sets[0])
            or set(self.held_by_max3_ids) != sets[0] - set(self.trader_intent_source_ids)
            or len(self.trader_intent_source_ids) != len(self.trade_intents)
        ):
            raise ValueError("Master Frame admission lost an opportunity or policy outcome")
        if (
            self.selection_policy != "FROZEN_V49_CHRONOLOGICAL_MAX3_RESEARCH"
            or not self.full_master_frame_used
            or not self.master_frame_changed_intent_admission
            or self.real_orders_placed
            or self.risk_authority_granted
            or self.certified
        ):
            raise ValueError("Trader Master Frame cannot claim live or certified execution")


def select_master_frame_trade_intents(
    opportunities: tuple[V49Opportunity, ...],
    *,
    barriers: tuple[A1MultiHypothesisBarrier, ...],
    settled_memory: A1CausalSettledMemory,
) -> A1MasterFrameTraderIntentReport:
    """ACTUAL cognitive routing at the frozen V49 Trader selection boundary.

    All externally supplied nine-market barriers are evaluated with the genuine
    Master Frame and as-of chosen settlements. Source IDs match the original
    V49 opportunity hashing contract. No future fills or candidate outcomes
    can influence PASS/WAIT/ABSTAIN. The resulting eligible intents follow
    only the unchanged chronological MAX3 policy; global source-author
    arbitration remains unproven and MUST NOT be called certified.
    """
    if not opportunities or not barriers:
        raise ValueError("Master Frame Trader needs source and observed nine-market barriers")
    known: dict[str, V49Opportunity] = {}
    for opportunity in opportunities:
        id_ = source_opportunity_id(opportunity)
        if id_ in known:
            raise ValueError("duplicated V49 source opportunity identity")
        known[id_] = opportunity
    provided_at = tuple(
        datetime.fromisoformat(row.m1_trigger_confirmed_at)
        for row in opportunities
    )
    if any(at.tzinfo is None or at.utcoffset() is None for at in provided_at):
        raise ValueError("source M1 timestamps must be timezone-aware")
    source_ids = tuple(sorted(known))
    packets: list[A1TraderCognitionPacket] = []
    observed_ids: set[str] = set()
    last_at: datetime | None = None
    for barrier in barriers:
        at = barrier.observed_at
        if last_at is not None and at <= last_at:
            raise ValueError("Master Frame barriers must be strictly chronological")
        last_at = at
        packet = prepare_trader_cognition_packet(
            barrier=barrier, settled_memory=settled_memory
        )
        for candidate in packet.candidates:
            id_ = candidate.source_opportunity_id
            source = known.get(id_)
            if source is None or id_ in observed_ids:
                raise ValueError("unknown/duplicated Master Frame source candidate")
            if (
                candidate.symbol != source.symbol
                or candidate.decision_at != datetime.fromisoformat(
                    source.m1_trigger_confirmed_at
                )
                or candidate.h1_confirmed_at != datetime.fromisoformat(
                    source.h1_state_from
                )
                or candidate.m15_confirmed_at != datetime.fromisoformat(
                    source.m15_setup_confirmed_at
                )
                or candidate.source_rule_id == "TTRADES_REVIEW_PENDING"
            ):
                raise ValueError("unmatched or unresolved H1/M15/M1 source-rule evidence")
            observed_ids.add(id_)
        packets.append(packet)
    if observed_ids != set(known):
        raise ValueError("Master Frame missing original V49 source opportunity IDs")

    pass_ids = {
        x.source_opportunity_id
        for packet in packets
        for x in packet.candidates
        if x.cognitive_gate == "PASS_TO_STRATEGY"
    }
    wait_ids = {
        x.source_opportunity_id
        for packet in packets
        for x in packet.candidates
        if x.cognitive_gate == "WAIT"
    }
    abstain_ids = set(known) - pass_ids - wait_ids
    # Identical chronological frozen source competition; no outcome ranking.
    grouped: dict[tuple[str, str], list[tuple[str, V49Opportunity]]] = defaultdict(list)
    for id_, source in known.items():
        if id_ in pass_ids:
            grouped[(source.session, source.operating_date)].append((id_, source))
    chosen: list[tuple[str, V49TradeIntent]] = []
    for key in sorted(grouped):
        rows = sorted(
            grouped[key],
            key=lambda pair: (
                pair[1].m1_trigger_confirmed_at,
                pair[1].symbol,
                pair[1].m1_trigger_family,
                pair[0],
            ),
        )
        for id_, source in rows[:MAX_EXECUTIONS_PER_SESSION]:
            chosen.append((id_, materialize_trade_intent(source)))
    chosen.sort(key=lambda pair: (pair[1].entry_at, pair[1].symbol, pair[0]))
    chosen_ids = tuple(id_ for id_, _ in chosen)
    return A1MasterFrameTraderIntentReport(
        identity="QORE_SCALPER_A1_MASTER_FRAME_TRADER_INTENT_RESEARCH_V1",
        source_opportunity_ids=source_ids,
        cognitive_packets=tuple(packets),
        trader_intent_source_ids=chosen_ids,
        trade_intents=tuple(intent for _, intent in chosen),
        cognition_pass_ids=tuple(sorted(pass_ids)),
        cognition_wait_ids=tuple(sorted(wait_ids)),
        cognition_abstain_ids=tuple(sorted(abstain_ids)),
        held_by_max3_ids=tuple(sorted(pass_ids - set(chosen_ids))),
        all_source_candidates_accounted_for=True,
    )
