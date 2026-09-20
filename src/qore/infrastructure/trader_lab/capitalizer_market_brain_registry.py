"""Nine-market brain registry for QORE Capitalizer.

The registry guarantees that the Master Brain owns exactly one governed Market Brain for each
frozen Capitalizer market. It is identity/integrity infrastructure, not a signal selector.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerMarketBrainState,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)


@dataclass(frozen=True, slots=True)
class CapitalizerMarketBrainRegistry:
    brains: tuple[CapitalizerMarketBrainState, ...]
    runtime_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if self.runtime_mutation_allowed:
            raise ValueError("Market Brain registry cannot self-mutate in runtime")
        symbols = tuple(brain.symbol for brain in self.brains)
        if len(symbols) != 9 or frozenset(symbols) != NINE_MARKET_UNIVERSE:
            raise ValueError("Market Brain registry requires exactly the frozen nine markets")
        if len(set(symbols)) != 9:
            raise ValueError("Market Brain registry cannot contain duplicate symbols")

    def get(self, symbol: str) -> CapitalizerMarketBrainState:
        normalized = symbol.upper()
        matches = tuple(brain for brain in self.brains if brain.symbol == normalized)
        if len(matches) != 1:
            raise KeyError(f"unknown Capitalizer Market Brain: {normalized}")
        return matches[0]

    def for_session(
        self,
        session: CapitalizerSession,
    ) -> tuple[CapitalizerMarketBrainState, ...]:
        return tuple(
            sorted(
                (brain for brain in self.brains if brain.session is session),
                key=lambda brain: brain.symbol,
            )
        )

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted(brain.symbol for brain in self.brains))
