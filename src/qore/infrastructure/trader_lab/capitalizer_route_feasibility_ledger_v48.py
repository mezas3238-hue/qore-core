"""Pre-economic V48 source-route feasibility ledger.

Consumes only independently source-complete route opportunities. It measures population
by route / market / session / calendar year and never reads terminal outcomes.

No minimum density threshold is frozen here. V48 must first observe the corrected route
population before Owner/UTC density gates are formalized.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_ROUTE_FEASIBILITY_LEDGER"


class V48FeasibilityStatus(StrEnum):
    SOURCE_COMPLETE = "SOURCE_COMPLETE"
    SOURCE_INCOMPLETE = "SOURCE_INCOMPLETE"


@dataclass(frozen=True, slots=True)
class V48RouteOpportunity:
    opportunity_id: str
    route_id: V48RouteId
    symbol: str
    session: str
    observed_at: datetime
    status: V48FeasibilityStatus
    missing_fact_ids: tuple[str, ...] = ()
    outcome_used: bool = False
    realized_r_present: bool = False

    def __post_init__(self) -> None:
        if not self.opportunity_id:
            raise ValueError("opportunity_id is required")
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be non-empty uppercase")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        complete = self.status is V48FeasibilityStatus.SOURCE_COMPLETE
        if complete and self.missing_fact_ids:
            raise ValueError("source-complete opportunity cannot have missing facts")
        if not complete and not self.missing_fact_ids:
            raise ValueError("source-incomplete opportunity requires missing facts")
        if self.outcome_used or self.realized_r_present:
            raise ValueError("V48 feasibility ledger cannot contain outcome data")


@dataclass(frozen=True, slots=True)
class V48RouteFeasibilityReport:
    identity: str
    opportunities_seen: int
    source_complete: int
    source_incomplete: int
    by_route: tuple[tuple[str, int], ...]
    by_market: tuple[tuple[str, int], ...]
    by_session: tuple[tuple[str, int], ...]
    by_year: tuple[tuple[int, int], ...]
    missing_facts: tuple[tuple[str, int], ...]
    outcome_used: bool = False
    fresh_holdout_used: bool = False
    density_gate_applied: bool = False
    economics_calculated: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 feasibility report identity is frozen")
        if self.source_complete + self.source_incomplete != self.opportunities_seen:
            raise ValueError("V48 feasibility counts must reconcile")
        if (
            self.outcome_used
            or self.fresh_holdout_used
            or self.density_gate_applied
            or self.economics_calculated
        ):
            raise ValueError("V48 feasibility report must remain pre-economic")


def build_route_feasibility_report(
    opportunities: tuple[V48RouteOpportunity, ...],
) -> V48RouteFeasibilityReport:
    route_counts: Counter[str] = Counter()
    market_counts: Counter[str] = Counter()
    session_counts: Counter[str] = Counter()
    year_counts: Counter[int] = Counter()
    missing: Counter[str] = Counter()

    complete = 0
    for opportunity in opportunities:
        if opportunity.status is V48FeasibilityStatus.SOURCE_COMPLETE:
            complete += 1
            route_counts[opportunity.route_id.value] += 1
            market_counts[opportunity.symbol] += 1
            session_counts[opportunity.session] += 1
            year_counts[opportunity.observed_at.year] += 1
        else:
            missing.update(opportunity.missing_fact_ids)

    return V48RouteFeasibilityReport(
        identity=IDENTITY,
        opportunities_seen=len(opportunities),
        source_complete=complete,
        source_incomplete=len(opportunities) - complete,
        by_route=tuple(sorted(route_counts.items())),
        by_market=tuple(sorted(market_counts.items())),
        by_session=tuple(sorted(session_counts.items())),
        by_year=tuple(sorted(year_counts.items())),
        missing_facts=tuple(sorted(missing.items(), key=lambda item: (-item[1], item[0]))),
    )
