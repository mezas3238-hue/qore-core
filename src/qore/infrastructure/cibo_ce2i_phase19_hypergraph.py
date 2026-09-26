"""Phase 19H resource/dependence hypergraph research contracts.

Pairwise overlap is insufficient when up to five opportunities coexist. This
module represents multi-opportunity temporal clusters and normalized-capital
collision sets without granting them capital authority.

Two edge families are intentionally distinct:

TEMPORAL_CONCURRENCY
    Pure chronology: opportunities coexist over a positive time interval.

NORMALIZED_CAPITAL_COLLISION
    Scenario-specific resource evidence: a rejected opportunity collided with
    one or more active normalized-capital reservations.

Neither edge family implies harmful dependence, correlation, sizing penalty or
allocation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_capital_collision import (
    Phase19CapitalCollisionEvidence,
)
from qore.infrastructure.cibo_ce2i_phase19_normalized_capital import (
    Phase19NormalizedReplayTrade,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


def _positive(value: Decimal, *, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value <= 0
    ):
        raise CiboCapitalManagementError(
            f"{name} must be finite positive Decimal"
        )


class Phase19HyperedgeKind(StrEnum):
    TEMPORAL_CONCURRENCY = "TEMPORAL_CONCURRENCY"
    NORMALIZED_CAPITAL_COLLISION = "NORMALIZED_CAPITAL_COLLISION"


@dataclass(frozen=True, slots=True)
class Phase19HypergraphMember:
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "hypergraph member signal/symbol identity is required"
            )
        if self.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "hypergraph member Trader outside Phase 19"
            )


@dataclass(frozen=True, slots=True)
class Phase19TemporalConcurrencyHyperedge:
    interval_start: datetime
    interval_end: datetime
    members: tuple[Phase19HypergraphMember, ...]
    kind: Phase19HyperedgeKind = (
        Phase19HyperedgeKind.TEMPORAL_CONCURRENCY
    )

    def __post_init__(self) -> None:
        _aware(self.interval_start, name="interval_start")
        _aware(self.interval_end, name="interval_end")
        if self.interval_end <= self.interval_start:
            raise CiboCapitalManagementError(
                "temporal hyperedge interval must be positive"
            )
        if self.kind is not Phase19HyperedgeKind.TEMPORAL_CONCURRENCY:
            raise CiboCapitalManagementError(
                "temporal hyperedge kind drift"
            )
        if len(self.members) < 2:
            raise CiboCapitalManagementError(
                "temporal hyperedge requires at least two members"
            )
        signals = tuple(item.signal_fingerprint for item in self.members)
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "duplicate temporal hyperedge member"
            )
        if self.distinct_trader_count < 2:
            raise CiboCapitalManagementError(
                "temporal hyperedge must be cross-Trader"
            )

    @property
    def duration_seconds(self) -> Decimal:
        return Decimal(
            str((self.interval_end - self.interval_start).total_seconds())
        )

    @property
    def distinct_trader_count(self) -> int:
        return len({item.trader_id for item in self.members})


@dataclass(frozen=True, slots=True)
class Phase19ResourceCollisionHyperedge:
    observed_at: datetime
    initial_capital_ncu: Decimal
    rejected_member: Phase19HypergraphMember
    blocker_members: tuple[Phase19HypergraphMember, ...]
    capacity_shortfall_ncu: Decimal
    kind: Phase19HyperedgeKind = (
        Phase19HyperedgeKind.NORMALIZED_CAPITAL_COLLISION
    )

    def __post_init__(self) -> None:
        _aware(self.observed_at, name="observed_at")
        _positive(self.initial_capital_ncu, name="initial_capital_ncu")
        _positive(self.capacity_shortfall_ncu, name="capacity_shortfall_ncu")
        if self.kind is not Phase19HyperedgeKind.NORMALIZED_CAPITAL_COLLISION:
            raise CiboCapitalManagementError(
                "resource collision hyperedge kind drift"
            )
        if not self.blocker_members:
            raise CiboCapitalManagementError(
                "resource collision hyperedge requires blockers"
            )
        signals = (
            self.rejected_member.signal_fingerprint,
            *(item.signal_fingerprint for item in self.blocker_members),
        )
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "resource collision hyperedge contains duplicate member"
            )

    @property
    def members(self) -> tuple[Phase19HypergraphMember, ...]:
        return (self.rejected_member, *self.blocker_members)

    @property
    def cardinality(self) -> int:
        return len(self.members)

    @property
    def distinct_trader_count(self) -> int:
        return len({item.trader_id for item in self.members})


@dataclass(frozen=True, slots=True)
class Phase19OpportunityHypergraph:
    temporal_hyperedges: tuple[Phase19TemporalConcurrencyHyperedge, ...]
    collision_hyperedges: tuple[Phase19ResourceCollisionHyperedge, ...]
    max_temporal_cardinality: int
    max_collision_cardinality: int
    temporal_evidence_only: bool = True
    collision_evidence_ex_post_only: bool = True
    harmful_dependence_claimed: bool = False
    sizing_penalty_authorized: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        expected_temporal = max(
            (len(item.members) for item in self.temporal_hyperedges),
            default=0,
        )
        expected_collision = max(
            (item.cardinality for item in self.collision_hyperedges),
            default=0,
        )
        if self.max_temporal_cardinality != expected_temporal:
            raise CiboCapitalManagementError(
                "temporal hypergraph cardinality summary drift"
            )
        if self.max_collision_cardinality != expected_collision:
            raise CiboCapitalManagementError(
                "collision hypergraph cardinality summary drift"
            )
        if not self.temporal_evidence_only or not self.collision_evidence_ex_post_only:
            raise CiboCapitalManagementError(
                "Phase 19 hypergraph evidence semantics drift"
            )
        if (
            self.harmful_dependence_claimed
            or self.sizing_penalty_authorized
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase 19 hypergraph cannot carry trading authority"
            )


def _member_from_opportunity(
    opportunity: Phase19ChronologicalOpportunity,
) -> Phase19HypergraphMember:
    return Phase19HypergraphMember(
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
    )


def build_phase19_temporal_hyperedges(
    opportunities: tuple[Phase19ChronologicalOpportunity, ...],
) -> tuple[Phase19TemporalConcurrencyHyperedge, ...]:
    """Build positive-duration cross-Trader active-set intervals."""

    if not opportunities:
        raise CiboCapitalManagementError(
            "temporal hypergraph requires opportunities"
        )
    signals = tuple(item.signal_fingerprint for item in opportunities)
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "duplicate signal in temporal hypergraph"
        )
    for item in opportunities:
        if item.trader_id not in PHASE19_REQUIRED_TRADERS:
            raise CiboCapitalManagementError(
                "temporal hypergraph opportunity outside Phase 19"
            )

    event_times = sorted(
        {
            at
            for item in opportunities
            for at in (item.entry_at, item.exit_at)
        }
    )
    raw: list[Phase19TemporalConcurrencyHyperedge] = []
    for start, end in zip(event_times, event_times[1:], strict=True):
        if end <= start:
            continue
        active = tuple(
            sorted(
                (
                    item
                    for item in opportunities
                    if item.entry_at <= start < item.exit_at
                ),
                key=lambda item: (
                    item.trader_id.value,
                    item.signal_fingerprint,
                ),
            )
        )
        if len(active) < 2:
            continue
        if len({item.trader_id for item in active}) < 2:
            continue
        raw.append(
            Phase19TemporalConcurrencyHyperedge(
                interval_start=start,
                interval_end=end,
                members=tuple(
                    _member_from_opportunity(item) for item in active
                ),
            )
        )

    if not raw:
        return ()

    merged: list[Phase19TemporalConcurrencyHyperedge] = [raw[0]]
    for edge in raw[1:]:
        previous = merged[-1]
        previous_signals = tuple(
            item.signal_fingerprint for item in previous.members
        )
        edge_signals = tuple(
            item.signal_fingerprint for item in edge.members
        )
        if (
            previous.interval_end == edge.interval_start
            and previous_signals == edge_signals
        ):
            merged[-1] = Phase19TemporalConcurrencyHyperedge(
                interval_start=previous.interval_start,
                interval_end=edge.interval_end,
                members=previous.members,
            )
        else:
            merged.append(edge)
    return tuple(merged)


def build_phase19_collision_hyperedges(
    *,
    evidence: Phase19CapitalCollisionEvidence,
    trades: tuple[Phase19NormalizedReplayTrade, ...],
) -> tuple[Phase19ResourceCollisionHyperedge, ...]:
    """Project normalized-capital collisions into resource hyperedges."""

    if not isinstance(evidence, Phase19CapitalCollisionEvidence):
        raise CiboCapitalManagementError(
            "collision hypergraph evidence type invalid"
        )
    by_signal = {
        item.opportunity.signal_fingerprint: item for item in trades
    }
    if len(by_signal) != len(trades):
        raise CiboCapitalManagementError(
            "duplicate trade signal in collision hypergraph"
        )

    edges: list[Phase19ResourceCollisionHyperedge] = []
    for collision in evidence.collisions:
        rejected_trade = by_signal.get(collision.signal_fingerprint)
        if rejected_trade is None:
            raise CiboCapitalManagementError(
                "collision hypergraph rejected trade missing"
            )
        blockers: list[Phase19HypergraphMember] = []
        for blocker in collision.blockers:
            blocker_trade = by_signal.get(blocker.signal_fingerprint)
            if blocker_trade is None:
                raise CiboCapitalManagementError(
                    "collision hypergraph blocker trade missing"
                )
            blockers.append(
                _member_from_opportunity(blocker_trade.opportunity)
            )
        edges.append(
            Phase19ResourceCollisionHyperedge(
                observed_at=rejected_trade.opportunity.entry_at,
                initial_capital_ncu=evidence.initial_capital_ncu,
                rejected_member=_member_from_opportunity(
                    rejected_trade.opportunity
                ),
                blocker_members=tuple(blockers),
                capacity_shortfall_ncu=collision.capacity_shortfall_ncu,
            )
        )
    return tuple(edges)


def build_phase19_opportunity_hypergraph(
    *,
    opportunities: tuple[Phase19ChronologicalOpportunity, ...],
    collision_evidence: tuple[
        tuple[
            Phase19CapitalCollisionEvidence,
            tuple[Phase19NormalizedReplayTrade, ...],
        ],
        ...,
    ] = (),
) -> Phase19OpportunityHypergraph:
    """Combine chronology hyperedges with optional scenario collision evidence."""

    temporal = build_phase19_temporal_hyperedges(opportunities)
    collision: list[Phase19ResourceCollisionHyperedge] = []
    for evidence, trades in collision_evidence:
        collision.extend(
            build_phase19_collision_hyperedges(
                evidence=evidence,
                trades=trades,
            )
        )
    return Phase19OpportunityHypergraph(
        temporal_hyperedges=temporal,
        collision_hyperedges=tuple(collision),
        max_temporal_cardinality=max(
            (len(item.members) for item in temporal),
            default=0,
        ),
        max_collision_cardinality=max(
            (item.cardinality for item in collision),
            default=0,
        ),
    )
