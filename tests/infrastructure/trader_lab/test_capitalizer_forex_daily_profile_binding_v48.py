from qore.infrastructure.trader_lab.capitalizer_forex_daily_profile_binding_v48 import (
    V48_FOREX_DAILY_PROFILE_BINDING,
    V48ForexDailyBindingState,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def test_forex_daily_profile_clock_remains_source_binding_blocked() -> None:
    state = V48_FOREX_DAILY_PROFILE_BINDING
    assert state.state is V48ForexDailyBindingState.SOURCE_BINDING_BLOCKED
    assert state.exact_forex_daily_open_hour_ny is None
    assert state.futures_daily_open_may_be_reused_for_forex is False
    assert state.inferred_one_hour_shift_may_be_frozen_as_source_rule is False


def test_daily_clock_blocker_is_local_to_asia_london_routes() -> None:
    state = V48_FOREX_DAILY_PROFILE_BINDING
    assert set(state.affected_routes) == {
        V48RouteId.TTRADES_ASIA_POSITIONAL,
        V48RouteId.TTRADES_ASIA_4H_15M,
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
    }
    assert state.generic_scalp_blocked is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
