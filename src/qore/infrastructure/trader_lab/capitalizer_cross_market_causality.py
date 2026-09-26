"""Decision-time cross-market causal graph for QORE Capitalizer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)


class CapitalizerCrossMarketRelation(StrEnum):
    INDEPENDENT = "INDEPENDENT"
    SHARED_CAUSE = "SHARED_CAUSE"
    LEADER_FOLLOWER = "LEADER_FOLLOWER"
    REINFORCING = "REINFORCING"
    CONTRADICTORY = "CONTRADICTORY"
    REDUNDANT = "REDUNDANT"
    MUTUALLY_INVALIDATING = "MUTUALLY_INVALIDATING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketEdge:
    left_symbol: str
    right_symbol: str
    relation: CapitalizerCrossMarketRelation
    observed_at: datetime
    causal_tokens: tuple[str, ...]
    leader_symbol: str | None = None

    def __post_init__(self) -> None:
        if self.left_symbol not in NINE_MARKET_UNIVERSE:
            raise ValueError("left symbol outside Capitalizer universe")
        if self.right_symbol not in NINE_MARKET_UNIVERSE:
            raise ValueError("right symbol outside Capitalizer universe")
        if self.left_symbol == self.right_symbol:
            raise ValueError("cross-market edge requires two different symbols")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("cross-market edge timestamp must be timezone-aware")
        if self.relation is not CapitalizerCrossMarketRelation.UNKNOWN and not self.causal_tokens:
            raise ValueError("known causal relation requires causal evidence tokens")
        if self.relation is CapitalizerCrossMarketRelation.LEADER_FOLLOWER:
            if self.leader_symbol not in {self.left_symbol, self.right_symbol}:
                raise ValueError("leader/follower relation requires one endpoint as leader")
        elif self.leader_symbol is not None:
            raise ValueError("leader_symbol is valid only for LEADER_FOLLOWER relation")

    @property
    def canonical_pair(self) -> tuple[str, str]:
        if self.left_symbol < self.right_symbol:
            return (self.left_symbol, self.right_symbol)
        return (self.right_symbol, self.left_symbol)


@dataclass(frozen=True, slots=True)
class CapitalizerCrossMarketCausalGraph:
    observed_at: datetime
    edges: tuple[CapitalizerCrossMarketEdge, ...]
    correlation_only_allowed: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("graph timestamp must be timezone-aware")
        if self.correlation_only_allowed:
            raise ValueError("Capitalizer cross-market graph requires causal context")
        if self.grants_capital_authority:
            raise ValueError("cross-market graph cannot grant capital authority")

        seen: set[tuple[str, str]] = set()
        for edge in self.edges:
            if edge.observed_at > self.observed_at:
                raise ValueError("future causal edge cannot enter graph")
            pair = edge.canonical_pair
            if pair in seen:
                raise ValueError("duplicate cross-market pair")
            seen.add(pair)

    def relation_for(
        self,
        left_symbol: str,
        right_symbol: str,
    ) -> CapitalizerCrossMarketEdge | None:
        left = left_symbol.upper()
        right = right_symbol.upper()
        pair = (left, right) if left < right else (right, left)
        matches = tuple(edge for edge in self.edges if edge.canonical_pair == pair)
        return matches[0] if matches else None

    def relations_for_session(
        self,
        session: CapitalizerSession,
    ) -> tuple[CapitalizerCrossMarketEdge, ...]:
        from qore.infrastructure.trader_lab.capitalizer_contract import allowed_markets

        symbols = allowed_markets(session)
        return tuple(
            edge
            for edge in self.edges
            if edge.left_symbol in symbols and edge.right_symbol in symbols
        )
