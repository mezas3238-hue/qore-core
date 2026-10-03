"""Permanent universal availability contract for CIBO capabilities.

This module separates two concepts:
- availability: every CIBO function is always callable from Trader Lab;
- approval: each observed execution still needs its own Trader Lab PASS.

Availability must never depend on symbol, asset class, provider, reused holdout,
fresh OOS, replay, stress population, or any future canonical research population.
A missing dependency may make an execution FAIL/ABSTAIN, but it must not disable
or hide the function itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.account_wide_risk import canonical_trader_identity
from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.cibo_functional_receipt import (
    CiboTraderLabFunctionGate,
)

_MARKET_RE = r"[A-Z0-9][A-Z0-9._/-]*"
_POPULATION_RE = r"[a-z][a-z0-9._/-]*"


class CiboFunctionAvailabilityState(StrEnum):
    UNLOCKED = "unlocked"


@dataclass(frozen=True, slots=True)
class CiboUniversalEvaluationScope:
    """Canonical evaluation metadata with no semantic allowlist."""

    market_symbol: str
    population: str
    trader_id: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.market_symbol, str)
            or fullmatch(_MARKET_RE, self.market_symbol) is None
        ):
            raise TraderLabValidationError(
                "market_symbol must use canonical uppercase market syntax"
            )
        if (
            not isinstance(self.population, str)
            or fullmatch(_POPULATION_RE, self.population) is None
        ):
            raise TraderLabValidationError(
                "population must use canonical lowercase research syntax"
            )
        if self.trader_id is not None:
            try:
                canonical_trader_identity(self.trader_id)
            except ValueError as error:
                raise TraderLabValidationError(
                    "trader_id must use canonical universal Trader syntax"
                ) from error

    def logical_values(self) -> tuple[str, str, str | None]:
        return (self.market_symbol, self.population, self.trader_id)


@dataclass(frozen=True, slots=True)
class CiboFunctionAvailability:
    """A capability is permanently available to be exercised by Trader Lab."""

    function: CiboTraderLabFunctionGate
    scope: CiboUniversalEvaluationScope
    state: CiboFunctionAvailabilityState = CiboFunctionAvailabilityState.UNLOCKED

    def __post_init__(self) -> None:
        if type(self.function) is not CiboTraderLabFunctionGate:
            raise TraderLabValidationError(
                "function must be exact CiboTraderLabFunctionGate"
            )
        if type(self.scope) is not CiboUniversalEvaluationScope:
            raise TraderLabValidationError(
                "scope must be exact CiboUniversalEvaluationScope"
            )
        CiboUniversalEvaluationScope.__post_init__(self.scope)
        if self.state is not CiboFunctionAvailabilityState.UNLOCKED:
            raise TraderLabValidationError(
                "CIBO function availability cannot be locked by evaluation scope"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.function.value, self.scope.logical_values(), self.state.value)


def cibo_function_availability(
    function: CiboTraderLabFunctionGate,
    *,
    market_symbol: str,
    population: str,
    trader_id: str | None = None,
) -> CiboFunctionAvailability:
    """Return permanent availability for any canonical symbol/population.

    This grants no PASS, Risk/order/sizing/capital/broker/deployment authority.
    """

    return CiboFunctionAvailability(
        function=function,
        scope=CiboUniversalEvaluationScope(
            market_symbol=market_symbol,
            population=population,
            trader_id=trader_id,
        ),
    )
