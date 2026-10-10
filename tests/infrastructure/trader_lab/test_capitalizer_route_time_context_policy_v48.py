from qore.infrastructure.trader_lab.capitalizer_route_time_context_policy_v48 import (
    ROUTE_TIME_CONTEXTS,
    V48_ROUTE_TIME_POLICY,
    V48RouteTimeContext,
    V48TimeContextMode,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def _ctx(route_id: V48RouteId) -> V48RouteTimeContext:
    return next(item for item in ROUTE_TIME_CONTEXTS if item.route_id is route_id)


def test_new_york_uses_event_context_not_old_0700_0900_exclusive_window() -> None:
    context = _ctx(V48RouteId.TTRADES_NEW_YORK_MANIPULATION)
    assert context.mode is V48TimeContextMode.EVENT_TIME_CONTEXT_NOT_EXCLUSIVE_WINDOW
    assert context.global_ict_killzone_required is False


def test_london_ttrades_route_has_no_exact_global_killzone_veto() -> None:
    context = _ctx(V48RouteId.TTRADES_LONDON_DAILY_4H_15M)
    assert context.mode is V48TimeContextMode.SESSION_CONTEXT_NO_EXACT_HARD_WINDOW


def test_ict_route_time_binding_stays_blocked_independently() -> None:
    context = _ctx(V48RouteId.ICT_2022_EXECUTION)
    assert context.mode is V48TimeContextMode.SOURCE_WINDOW_BINDING_PENDING


def test_global_session_veto_is_disabled_for_v48() -> None:
    assert V48_ROUTE_TIME_POLICY.global_session_veto_allowed is False
    assert V48_ROUTE_TIME_POLICY.fresh_holdout_authorized is False
