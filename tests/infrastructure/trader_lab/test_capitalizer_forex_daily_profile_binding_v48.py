from qore.infrastructure.trader_lab.capitalizer_forex_daily_profile_binding_v48 import (
    V48_FOREX_DAILY_PROFILE_BINDING,
    V48ForexDailyBindingState,
)


def test_forex_daily_profile_clock_is_source_resolved_at_17_new_york() -> None:
    state = V48_FOREX_DAILY_PROFILE_BINDING
    assert state.state is V48ForexDailyBindingState.RESOLVED_FOREX_SOURCE_PROFILE
    assert state.exact_forex_daily_open_hour_ny == 17
    assert state.provider_native_m1_required is True
    assert state.source_bound_m1_resampling_authorized is True
    assert state.daily_profile_construction_authorized is True


def test_daily_resolution_does_not_assume_broker_native_daily_equivalence() -> None:
    state = V48_FOREX_DAILY_PROFILE_BINDING
    assert state.native_broker_daily_equivalence_assumed is False
    assert state.synthetic_price_authorized is False
    assert "H4-PO3-TTrades-PDF.pdf" in state.primary_source_url


def test_daily_profile_binding_grants_no_fresh_or_economic_authority() -> None:
    state = V48_FOREX_DAILY_PROFILE_BINDING
    assert state.generic_scalp_blocked is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
