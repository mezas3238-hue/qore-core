"""Outcome-blind route competition for Capitalizer V48.

Source-native routes must be admitted independently before this layer. Competition only
applies the Owner MAX3 session ceiling chronologically; it cannot use route economics,
quality scores, terminal outcomes, MAE/MFE, or future information.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.trader_lab.capitalizer_contract import MAX_EXECUTIONS_PER_SESSION
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_SOURCE_NATIVE_ROUTE_COMPETITION"


@dataclass(frozen=True, slots=True)
class V48AdmittedRouteOpportunity:
    opportunity_id: str
    route_id: V48RouteId
    symbol: str
    session: str
    operating_date: str
    admitted_at: datetime
    source_complete: bool = True
    outcome_present: bool = False
    realized_r_present: bool = False
    historical_route_score_present: bool = False

    def __post_init__(self) -> None:
        if not self.opportunity_id:
            raise ValueError("opportunity_id is required")
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be non-empty uppercase")
        if not self.session or not self.operating_date:
            raise ValueError("session and operating_date are required")
        if self.admitted_at.tzinfo is None or self.admitted_at.utcoffset() is None:
            raise ValueError("admitted_at must be timezone-aware")
        if not self.source_complete:
            raise ValueError("competition accepts only independently source-complete routes")
        if (
            self.outcome_present
            or self.realized_r_present
            or self.historical_route_score_present
        ):
            raise ValueError("route competition cannot use outcome/economic information")


@dataclass(frozen=True, slots=True)
class V48RouteCompetitionDecision:
    selected: tuple[V48AdmittedRouteOpportunity, ...]
    displaced_by_max3: tuple[V48AdmittedRouteOpportunity, ...]
    source_population: int
    max_executions_per_session: int = MAX_EXECUTIONS_PER_SESSION
    outcome_used: bool = False
    route_preference_used: bool = False
    numeric_score_used: bool = False

    def __post_init__(self) -> None:
        if self.max_executions_per_session != MAX_EXECUTIONS_PER_SESSION:
            raise ValueError("V48 route competition must preserve Owner MAX3")
        if len(self.selected) > self.max_executions_per_session:
            raise ValueError("selected population exceeds MAX3")
        if len(self.selected) + len(self.displaced_by_max3) != self.source_population:
            raise ValueError("competition population does not reconcile")
        if self.outcome_used or self.route_preference_used or self.numeric_score_used:
            raise ValueError("route competition must remain outcome-blind and score-free")


def compete_session_day(
    opportunities: tuple[V48AdmittedRouteOpportunity, ...],
) -> V48RouteCompetitionDecision:
    """Select first three independently admitted opportunities in causal order."""

    if not opportunities:
        return V48RouteCompetitionDecision(
            selected=(),
            displaced_by_max3=(),
            source_population=0,
        )

    keys = {(item.session, item.operating_date) for item in opportunities}
    if len(keys) != 1:
        raise ValueError("one competition call must contain exactly one session/day bucket")

    ids = tuple(item.opportunity_id for item in opportunities)
    if len(ids) != len(set(ids)):
        raise ValueError("competition opportunity IDs must be unique")

    ordered = tuple(
        sorted(
            opportunities,
            key=lambda item: (
                item.admitted_at,
                item.symbol,
                item.route_id.value,
                item.opportunity_id,
            ),
        )
    )
    selected = ordered[:MAX_EXECUTIONS_PER_SESSION]
    displaced = ordered[MAX_EXECUTIONS_PER_SESSION:]
    return V48RouteCompetitionDecision(
        selected=selected,
        displaced_by_max3=displaced,
        source_population=len(ordered),
    )
