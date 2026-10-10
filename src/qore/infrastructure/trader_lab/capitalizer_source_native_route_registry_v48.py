"""V48 source-native route registry for Capitalizer.

V47 collapsed ICT + TTrades into one global DualSourceEntryAcceptance gate. V48 replaces
that architectural assumption with independently provenance-bound routes.

This registry is pre-economic and does not yet implement market replay/admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_SOURCE_NATIVE_ROUTE_REGISTRY"


class V48SourceFamily(StrEnum):
    TTRADES = "TTRADES"
    ICT = "ICT"


class V48RouteReadiness(StrEnum):
    SOURCE_RESOLVED_PRE_ECONOMIC = "SOURCE_RESOLVED_PRE_ECONOMIC"
    SOURCE_BINDING_BLOCKED = "SOURCE_BINDING_BLOCKED"


class V48RouteId(StrEnum):
    TTRADES_ASIA_POSITIONAL = "TTRADES_ASIA_POSITIONAL"
    TTRADES_ASIA_4H_15M = "TTRADES_ASIA_4H_15M"
    TTRADES_LONDON_DAILY_4H_15M = "TTRADES_LONDON_DAILY_4H_15M"
    TTRADES_NEW_YORK_MANIPULATION = "TTRADES_NEW_YORK_MANIPULATION"
    TTRADES_GENERIC_SCALP_H1_M15_M1 = "TTRADES_GENERIC_SCALP_H1_M15_M1"
    TTRADES_FAILURE_TO_MANIPULATE = "TTRADES_FAILURE_TO_MANIPULATE"
    ICT_2022_EXECUTION = "ICT_2022_EXECUTION"


@dataclass(frozen=True, slots=True)
class V48SourceNativeRoute:
    route_id: V48RouteId
    source_family: V48SourceFamily
    readiness: V48RouteReadiness
    sessions: tuple[str, ...]
    source_urls: tuple[str, ...]
    requires_other_source_family: bool = False
    productive_replay_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.sessions or not self.source_urls:
            raise ValueError("source-native route requires sessions and sources")
        if self.requires_other_source_family:
            raise ValueError("V48 source-native route cannot require another author by default")
        if self.readiness is V48RouteReadiness.SOURCE_BINDING_BLOCKED:
            if self.productive_replay_authorized:
                raise ValueError("blocked source route cannot authorize productive replay")


ROUTES: tuple[V48SourceNativeRoute, ...] = (
    V48SourceNativeRoute(
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        V48SourceFamily.TTRADES,
        V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC,
        ("ASIA",),
        (
            "https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",
            "https://ttrades.com/positional-entries-enter-before-the-expansion/",
        ),
    ),
    V48SourceNativeRoute(
        V48RouteId.TTRADES_ASIA_4H_15M,
        V48SourceFamily.TTRADES,
        V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC,
        ("ASIA",),
        ("https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",),
    ),
    V48SourceNativeRoute(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        V48SourceFamily.TTRADES,
        V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC,
        ("LONDON",),
        ("https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/",),
    ),
    V48SourceNativeRoute(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        V48SourceFamily.TTRADES,
        V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC,
        ("NEW_YORK",),
        ("https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/",),
    ),
    V48SourceNativeRoute(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        V48SourceFamily.TTRADES,
        V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC,
        ("ASIA", "LONDON", "NEW_YORK"),
        ("https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",),
    ),
    V48SourceNativeRoute(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        V48SourceFamily.TTRADES,
        V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC,
        ("ASIA", "LONDON", "NEW_YORK"),
        ("https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",),
    ),
    V48SourceNativeRoute(
        V48RouteId.ICT_2022_EXECUTION,
        V48SourceFamily.ICT,
        V48RouteReadiness.SOURCE_BINDING_BLOCKED,
        ("NEW_YORK",),
        (
            "https://www.youtube.com/watch?v=nQfHZ2DEJ8c",
            "https://www.youtube.com/watch?v=Bkt8B3kLATQ",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V48SourceNativeRouteRegistry:
    identity: str = IDENTITY
    routes: tuple[V48SourceNativeRoute, ...] = ROUTES
    global_dual_source_acceptance_authorized: bool = False
    cross_author_conjunction_requires_explicit_provenance: bool = True
    source_native_routes_may_compete_after_independent_admission: bool = True
    outcome_may_choose_route_definition: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 route registry identity is frozen")
        ids = tuple(route.route_id for route in self.routes)
        if len(ids) != len(set(ids)):
            raise ValueError("V48 route IDs must be unique")
        if self.global_dual_source_acceptance_authorized:
            raise ValueError("V48 rejects the old global dual-source AND architecture")
        if not self.cross_author_conjunction_requires_explicit_provenance:
            raise ValueError("cross-author conjunction needs its own source provenance")
        if self.outcome_may_choose_route_definition:
            raise ValueError("terminal outcomes cannot define source routes")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("route registry is pre-economic")


V48_SOURCE_NATIVE_ROUTE_REGISTRY = V48SourceNativeRouteRegistry()
