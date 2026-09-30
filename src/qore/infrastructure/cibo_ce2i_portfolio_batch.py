"""CE2I portfolio batch planner.

Composes:
Capital Opportunity Graph
-> T09/T18 opportunity competition
-> durable portfolio allocation reservation (CAS)

Research-only. It does not reserve capital-source funding, call QORE Risk, or
mutate broker state.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceAccount
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationDecision,
)
from qore.infrastructure.cibo_ce2i_opportunity_graph import (
    CapitalOpportunityGraph,
    build_capital_opportunity_graph,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_store import (
    DurablePortfolioAllocationStore,
)


@dataclass(frozen=True, slots=True)
class PortfolioBatchDecision:
    graph: CapitalOpportunityGraph
    allocation: OpportunityAllocationDecision
    allocation_generation: int

    def __post_init__(self) -> None:
        if self.allocation_generation < 1:
            raise CiboCapitalManagementError(
                "portfolio batch allocation generation must be positive"
            )

    @property
    def selected_signal_fingerprints(self) -> tuple[str, ...]:
        return self.allocation.selected_signal_fingerprints


def plan_and_reserve_portfolio_batch(
    *,
    candidates: tuple[CapitalOpportunityCandidate, ...],
    capital_sources: tuple[CapitalSourceAccount, ...],
    allocation_store: DurablePortfolioAllocationStore,
) -> PortfolioBatchDecision:
    """Build graph, compete, and persist shared portfolio reservations."""

    if not isinstance(allocation_store, DurablePortfolioAllocationStore):
        raise CiboCapitalManagementError(
            "allocation_store must be DurablePortfolioAllocationStore"
        )

    current = allocation_store.load()
    if current is None:
        raise CiboCapitalManagementError(
            "portfolio allocation store must be initialized before planning"
        )

    graph = build_capital_opportunity_graph(
        candidates=candidates,
        capital_sources=capital_sources,
    )
    next_ledger, allocation = current.ledger.allocate_and_reserve(candidates)
    stored = allocation_store.store(
        next_ledger,
        expected_generation=current.generation,
    )
    return PortfolioBatchDecision(
        graph=graph,
        allocation=allocation,
        allocation_generation=stored.generation,
    )
