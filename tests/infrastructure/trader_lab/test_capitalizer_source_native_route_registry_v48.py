from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    ROUTES,
    V48_SOURCE_NATIVE_ROUTE_REGISTRY,
    V48RouteId,
    V48RouteReadiness,
    V48SourceFamily,
)


def test_ttrades_routes_are_independent_of_ict_binding() -> None:
    ttrades = [route for route in ROUTES if route.source_family is V48SourceFamily.TTRADES]
    assert ttrades
    assert all(route.requires_other_source_family is False for route in ttrades)
    assert all(
        route.readiness is V48RouteReadiness.SOURCE_RESOLVED_PRE_ECONOMIC
        for route in ttrades
    )


def test_ict_route_fails_closed_until_timestamp_binding_is_complete() -> None:
    route = next(route for route in ROUTES if route.route_id is V48RouteId.ICT_2022_EXECUTION)
    assert route.source_family is V48SourceFamily.ICT
    assert route.readiness is V48RouteReadiness.SOURCE_BINDING_BLOCKED
    assert route.productive_replay_authorized is False


def test_global_dual_source_and_is_not_authorized_in_v48() -> None:
    registry = V48_SOURCE_NATIVE_ROUTE_REGISTRY
    assert registry.global_dual_source_acceptance_authorized is False
    assert registry.cross_author_conjunction_requires_explicit_provenance is True


def test_source_routes_can_only_compete_after_independent_admission() -> None:
    registry = V48_SOURCE_NATIVE_ROUTE_REGISTRY
    assert registry.source_native_routes_may_compete_after_independent_admission is True
    assert registry.outcome_may_choose_route_definition is False
    assert registry.fresh_holdout_authorized is False
    assert registry.economics_authorized is False
