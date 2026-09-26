"""CE2I Capital Opportunity Graph V1.

Represents simultaneous opportunities, capital sources and portfolio interaction
edges before allocation. Research-only: no capital reservation or broker action.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    CapitalSource,
    CiboCapitalManagementError,
    capital_source_dimension,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceAccount
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
)


class OpportunityGraphNodeKind(StrEnum):
    OPPORTUNITY = "OPPORTUNITY"
    CAPITAL_SOURCE = "CAPITAL_SOURCE"
    CONCENTRATION_GROUP = "CONCENTRATION_GROUP"


class OpportunityGraphEdgeKind(StrEnum):
    CAN_FUND = "CAN_FUND"
    COMPETES_FOR_RISK = "COMPETES_FOR_RISK"
    COMPETES_FOR_MARGIN = "COMPETES_FOR_MARGIN"
    SHARES_CONCENTRATION = "SHARES_CONCENTRATION"


@dataclass(frozen=True, slots=True)
class OpportunityGraphNode:
    node_id: str
    kind: OpportunityGraphNodeKind
    trader_id: TraderLineage | None = None
    capital_source: CapitalSource | None = None
    amount_usd: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.node_id:
            raise CiboCapitalManagementError("graph node_id required")
        if type(self.kind) is not OpportunityGraphNodeKind:
            raise CiboCapitalManagementError(
                "graph node kind must be OpportunityGraphNodeKind"
            )
        if self.amount_usd is not None and (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd < 0
        ):
            raise CiboCapitalManagementError(
                "graph node amount must be finite non-negative Decimal/null"
            )


@dataclass(frozen=True, slots=True)
class OpportunityGraphEdge:
    source_node_id: str
    target_node_id: str
    kind: OpportunityGraphEdgeKind
    weight: Decimal

    def __post_init__(self) -> None:
        if not self.source_node_id or not self.target_node_id:
            raise CiboCapitalManagementError("graph edge endpoints required")
        if self.source_node_id == self.target_node_id:
            raise CiboCapitalManagementError("graph self-edge forbidden")
        if type(self.kind) is not OpportunityGraphEdgeKind:
            raise CiboCapitalManagementError(
                "graph edge kind must be OpportunityGraphEdgeKind"
            )
        if (
            not isinstance(self.weight, Decimal)
            or not self.weight.is_finite()
            or self.weight < 0
        ):
            raise CiboCapitalManagementError(
                "graph edge weight must be finite non-negative Decimal"
            )


@dataclass(frozen=True, slots=True)
class CapitalOpportunityGraph:
    nodes: tuple[OpportunityGraphNode, ...]
    edges: tuple[OpportunityGraphEdge, ...]

    def __post_init__(self) -> None:
        node_ids = tuple(item.node_id for item in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise CiboCapitalManagementError("duplicate opportunity graph node")
        valid = set(node_ids)
        for edge in self.edges:
            if (
                edge.source_node_id not in valid
                or edge.target_node_id not in valid
            ):
                raise CiboCapitalManagementError(
                    "graph edge references missing node"
                )

    def edges_of_kind(
        self,
        kind: OpportunityGraphEdgeKind,
    ) -> tuple[OpportunityGraphEdge, ...]:
        return tuple(item for item in self.edges if item.kind is kind)


def build_capital_opportunity_graph(
    *,
    candidates: tuple[CapitalOpportunityCandidate, ...],
    capital_sources: tuple[CapitalSourceAccount, ...],
) -> CapitalOpportunityGraph:
    """Build deterministic portfolio interaction graph from causal inputs."""

    candidate_ids = tuple(item.signal_fingerprint for item in candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise CiboCapitalManagementError(
            "duplicate candidate fingerprint in opportunity graph"
        )
    source_ids = tuple(item.source_id for item in capital_sources)
    if len(source_ids) != len(set(source_ids)):
        raise CiboCapitalManagementError(
            "duplicate capital source in opportunity graph"
        )

    nodes: list[OpportunityGraphNode] = []
    edges: list[OpportunityGraphEdge] = []

    for candidate in candidates:
        nodes.append(
            OpportunityGraphNode(
                node_id=f"opportunity:{candidate.signal_fingerprint}",
                kind=OpportunityGraphNodeKind.OPPORTUNITY,
                trader_id=candidate.trader_id,
                amount_usd=candidate.stop_risk_usd,
            )
        )

    for account in capital_sources:
        nodes.append(
            OpportunityGraphNode(
                node_id=f"capital:{account.source_id}",
                kind=OpportunityGraphNodeKind.CAPITAL_SOURCE,
                capital_source=account.source,
                amount_usd=account.available_usd,
            )
        )

    groups = sorted({item.concentration_group for item in candidates})
    for group in groups:
        nodes.append(
            OpportunityGraphNode(
                node_id=f"group:{group}",
                kind=OpportunityGraphNodeKind.CONCENTRATION_GROUP,
            )
        )

    economic_sources = tuple(
        account
        for account in capital_sources
        if account.available_usd > 0
        and capital_source_dimension(account.source)
        is CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL
    )
    for candidate in candidates:
        opportunity_id = f"opportunity:{candidate.signal_fingerprint}"
        group_id = f"group:{candidate.concentration_group}"
        edges.append(
            OpportunityGraphEdge(
                source_node_id=opportunity_id,
                target_node_id=group_id,
                kind=OpportunityGraphEdgeKind.SHARES_CONCENTRATION,
                weight=candidate.concentration_risk_usd,
            )
        )
        for account in economic_sources:
            edges.append(
                OpportunityGraphEdge(
                    source_node_id=f"capital:{account.source_id}",
                    target_node_id=opportunity_id,
                    kind=OpportunityGraphEdgeKind.CAN_FUND,
                    weight=min(
                        account.available_usd,
                        candidate.stop_risk_usd,
                    ),
                )
            )

    ordered_candidates = sorted(
        candidates,
        key=lambda item: item.signal_fingerprint,
    )
    for index, left in enumerate(ordered_candidates):
        for right in ordered_candidates[index + 1 :]:
            left_id = f"opportunity:{left.signal_fingerprint}"
            right_id = f"opportunity:{right.signal_fingerprint}"
            edges.append(
                OpportunityGraphEdge(
                    source_node_id=left_id,
                    target_node_id=right_id,
                    kind=OpportunityGraphEdgeKind.COMPETES_FOR_RISK,
                    weight=min(left.stop_risk_usd, right.stop_risk_usd),
                )
            )
            edges.append(
                OpportunityGraphEdge(
                    source_node_id=left_id,
                    target_node_id=right_id,
                    kind=OpportunityGraphEdgeKind.COMPETES_FOR_MARGIN,
                    weight=min(left.margin_usd, right.margin_usd),
                )
            )

    return CapitalOpportunityGraph(
        nodes=tuple(nodes),
        edges=tuple(edges),
    )
