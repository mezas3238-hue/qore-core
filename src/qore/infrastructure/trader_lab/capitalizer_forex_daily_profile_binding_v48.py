"""V48 source-binding ledger for the TTrades Forex Daily profile/open.

Asia and London source material explicitly uses Daily bias, the Daily wick, and/or the new
Daily/higher-timeframe candle open. Reviewed TTrades timing material documents an 18:00 EST
Daily open in its general/futures examples, while the London Forex example explicitly says
Forex higher-timeframe opens are shifted by one hour.

That evidence is sufficient to reject blindly reusing the futures Daily boundary for Forex,
but it is not sufficient to freeze an exact Forex Daily boundary as an author rule. V48
therefore keeps only this local clock identity blocked. H4 Forex timing is resolved separately.

Generic H1/M15/M1 Scalping is not blocked because its Daily layer is contextual rather than
the mechanical decision timeframe.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_FOREX_DAILY_PROFILE_BINDING"


class V48ForexDailyBindingState(StrEnum):
    SOURCE_BINDING_BLOCKED = "SOURCE_BINDING_BLOCKED"


@dataclass(frozen=True, slots=True)
class V48ForexDailyProfileBinding:
    identity: str = IDENTITY
    state: V48ForexDailyBindingState = V48ForexDailyBindingState.SOURCE_BINDING_BLOCKED
    exact_forex_daily_open_hour_ny: int | None = None
    futures_daily_open_may_be_reused_for_forex: bool = False
    inferred_one_hour_shift_may_be_frozen_as_source_rule: bool = False
    affected_routes: tuple[V48RouteId, ...] = (
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        V48RouteId.TTRADES_ASIA_4H_15M,
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
    )
    generic_scalp_blocked: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("Forex Daily binding identity is frozen")
        if self.exact_forex_daily_open_hour_ny is not None:
            raise ValueError("exact Forex Daily open is not source-bound yet")
        if self.futures_daily_open_may_be_reused_for_forex:
            raise ValueError("futures Daily boundary cannot be silently reused for Forex")
        if self.inferred_one_hour_shift_may_be_frozen_as_source_rule:
            raise ValueError("an inference cannot be promoted to an explicit author clock")
        if self.generic_scalp_blocked:
            raise ValueError("Daily clock cannot block independent H1 decision route")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("Daily binding ledger grants no Fresh/economic authority")


V48_FOREX_DAILY_PROFILE_BINDING = V48ForexDailyProfileBinding()
