"""V48 route-specific time-context policy.

Time is a route-level source fact, not a global veto inherited from one author's
killzone lesson. Exact windows are only hard requirements when the specific route
source proves them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)

IDENTITY = "QORE_CAPITALIZER_V48_ROUTE_TIME_CONTEXT_POLICY"


class V48TimeContextMode(StrEnum):
    SESSION_CONTEXT_NO_EXACT_HARD_WINDOW = "SESSION_CONTEXT_NO_EXACT_HARD_WINDOW"
    EVENT_TIME_CONTEXT_NOT_EXCLUSIVE_WINDOW = "EVENT_TIME_CONTEXT_NOT_EXCLUSIVE_WINDOW"
    SOURCE_WINDOW_BINDING_PENDING = "SOURCE_WINDOW_BINDING_PENDING"


@dataclass(frozen=True, slots=True)
class V48RouteTimeContext:
    route_id: V48RouteId
    mode: V48TimeContextMode
    evidence: str
    global_ict_killzone_required: bool = False

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("route time context requires evidence")
        if self.global_ict_killzone_required:
            raise ValueError("V48 route cannot inherit a global ICT killzone by default")


ROUTE_TIME_CONTEXTS: tuple[V48RouteTimeContext, ...] = (
    V48RouteTimeContext(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        V48TimeContextMode.SESSION_CONTEXT_NO_EXACT_HARD_WINDOW,
        "TTrades Asia defines expansion conditions and positional execution, not an ICT 2h veto.",
    ),
    V48RouteTimeContext(
        V48RouteId.TTRADES_ASIA_4H_15M,
        V48TimeContextMode.SESSION_CONTEXT_NO_EXACT_HARD_WINDOW,
        "TTrades Asia defines the 4H/15M route without proving the ICT 2h window as mandatory.",
    ),
    V48RouteTimeContext(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        V48TimeContextMode.SESSION_CONTEXT_NO_EXACT_HARD_WINDOW,
        "TTrades London states setup/HTF wick structure matters more than exact killzone.",
    ),
    V48RouteTimeContext(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        V48TimeContextMode.EVENT_TIME_CONTEXT_NOT_EXCLUSIVE_WINDOW,
        "TTrades watches 08:30/09:30 sweeps and 09:30/10:00 expansion as event context.",
    ),
    V48RouteTimeContext(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        V48TimeContextMode.SESSION_CONTEXT_NO_EXACT_HARD_WINDOW,
        "The generic scalping lesson defines timeframe alignment, not one universal session clock.",
    ),
    V48RouteTimeContext(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        V48TimeContextMode.SESSION_CONTEXT_NO_EXACT_HARD_WINDOW,
        "FTM is fractal across timeframes and is defined structurally rather than by one killzone.",
    ),
    V48RouteTimeContext(
        V48RouteId.ICT_2022_EXECUTION,
        V48TimeContextMode.SOURCE_WINDOW_BINDING_PENDING,
        (
            "ICT route timing remains blocked until exact primary-source timestamp "
            "binding is complete."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V48RouteTimePolicy:
    identity: str = IDENTITY
    contexts: tuple[V48RouteTimeContext, ...] = ROUTE_TIME_CONTEXTS
    global_session_veto_allowed: bool = False
    fresh_holdout_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 route time policy identity is frozen")
        ids = tuple(item.route_id for item in self.contexts)
        if len(ids) != len(set(ids)):
            raise ValueError("route time contexts must be unique")
        if self.global_session_veto_allowed:
            raise ValueError("V48 forbids one global session hard-veto")
        if self.fresh_holdout_authorized:
            raise ValueError("route time policy grants no Fresh Holdout authority")


V48_ROUTE_TIME_POLICY = V48RouteTimePolicy()
