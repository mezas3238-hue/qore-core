"""Cross-market cognition and opportunity competition for CRT PURE.

This layer may describe causal relationships between simultaneously active CRT hypotheses.
It cannot infer relationships from correlation alone, rank opportunities by PnL, choose a
capital winner, or override QORE Risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


class CrtPureCrossMarketRelation(StrEnum):
    UNKNOWN = "UNKNOWN"
    INDEPENDENT = "INDEPENDENT"
    SHARED_CAUSE = "SHARED_CAUSE"
    LEADER_FOLLOWER = "LEADER_FOLLOWER"
    REDUNDANT = "REDUNDANT"
    CONTRADICTORY = "CONTRADICTORY"
    MUTUALLY_INVALIDATING = "MUTUALLY_INVALIDATING"


class CrtPureCompetitionState(StrEnum):
    NO_EXECUTABLE = "NO_EXECUTABLE"
    SINGLE_EXECUTABLE = "SINGLE_EXECUTABLE"
    MULTIPLE_REQUIRE_QORE_RISK = "MULTIPLE_REQUIRE_QORE_RISK"
    COGNITIVE_CONFLICT = "COGNITIVE_CONFLICT"


@dataclass(frozen=True, slots=True)
class CrtPureCrossMarketEdge:
    left: CrtPureMarket
    right: CrtPureMarket
    relation: CrtPureCrossMarketRelation
    evidence_id: str | None = None
    causally_validated: bool = False

    def __post_init__(self) -> None:
        if self.left is self.right:
            raise ValueError("cross-market edge requires two distinct markets")
        if self.relation is not CrtPureCrossMarketRelation.UNKNOWN:
            if not self.causally_validated or not self.evidence_id:
                raise ValueError(
                    "non-UNKNOWN cross-market relation requires causal evidence"
                )

    def contains(self, a: CrtPureMarket, b: CrtPureMarket) -> bool:
        return {self.left, self.right} == {a, b}


@dataclass(frozen=True, slots=True)
class CrtPureOpportunityCandidate:
    market: CrtPureMarket
    hypothesis_id: str
    source_event_id: str
    action: CrtPureReasoningAction

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.source_event_id:
            raise ValueError("opportunity identity must be non-empty")


@dataclass(frozen=True, slots=True)
class CrtPureOpportunityCompetition:
    state: CrtPureCompetitionState
    executable_markets: tuple[CrtPureMarket, ...]
    relation_findings: tuple[str, ...]
    selected_market: CrtPureMarket | None = None
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.selected_market is not None:
            raise ValueError("CRT cognition cannot select a capital winner")
        if self.grants_capital_authority:
            raise ValueError("CRT cognition cannot grant capital authority")


def _relation_for(
    a: CrtPureMarket,
    b: CrtPureMarket,
    edges: tuple[CrtPureCrossMarketEdge, ...],
) -> CrtPureCrossMarketRelation:
    matches = tuple(edge for edge in edges if edge.contains(a, b))
    if len(matches) > 1:
        raise ValueError("duplicate cross-market causal relation")
    if not matches:
        return CrtPureCrossMarketRelation.UNKNOWN
    return matches[0].relation


def compete(
    candidates: tuple[CrtPureOpportunityCandidate, ...],
    *,
    causal_edges: tuple[CrtPureCrossMarketEdge, ...] = (),
) -> CrtPureOpportunityCompetition:
    """Describe simultaneous executable CRT opportunities without ranking them."""

    markets = tuple(candidate.market for candidate in candidates)
    if len(set(markets)) != len(markets):
        raise ValueError("only one active competition candidate per market is allowed")

    executable = tuple(
        candidate
        for candidate in candidates
        if candidate.action is CrtPureReasoningAction.EXECUTE
    )
    executable_markets = tuple(candidate.market for candidate in executable)

    if not executable:
        return CrtPureOpportunityCompetition(
            state=CrtPureCompetitionState.NO_EXECUTABLE,
            executable_markets=(),
            relation_findings=(),
        )

    if len(executable) == 1:
        return CrtPureOpportunityCompetition(
            state=CrtPureCompetitionState.SINGLE_EXECUTABLE,
            executable_markets=executable_markets,
            relation_findings=("NO_COMPETITION_REQUIRED",),
        )

    findings: list[str] = []
    hard_conflict = False
    for index, left in enumerate(executable):
        for right in executable[index + 1 :]:
            relation = _relation_for(left.market, right.market, causal_edges)
            findings.append(
                f"{left.market.value}:{right.market.value}:{relation.value}"
            )
            if relation is CrtPureCrossMarketRelation.MUTUALLY_INVALIDATING:
                hard_conflict = True

    return CrtPureOpportunityCompetition(
        state=(
            CrtPureCompetitionState.COGNITIVE_CONFLICT
            if hard_conflict
            else CrtPureCompetitionState.MULTIPLE_REQUIRE_QORE_RISK
        ),
        executable_markets=executable_markets,
        relation_findings=tuple(findings),
    )
