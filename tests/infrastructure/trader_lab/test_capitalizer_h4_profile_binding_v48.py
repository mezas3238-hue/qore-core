from qore.infrastructure.trader_lab.capitalizer_h4_profile_binding_v48 import (
    EVIDENCE,
    V48_H4_PROFILE_BINDING,
    V48H4BindingState,
)


def test_forex_h4_source_profile_clock_is_resolved() -> None:
    state = V48_H4_PROFILE_BINDING
    assert state.state is V48H4BindingState.RESOLVED_FOREX_SOURCE_PROFILE
    assert state.forex_anchor_hours_ny == (1, 5, 9, 13, 17, 21)
    assert state.provider_native_m1_required is True
    assert state.source_bound_m1_resampling_authorized is True
    assert state.h4_profile_construction_authorized is True


def test_h4_resolution_does_not_assume_native_broker_h4_equivalence() -> None:
    state = V48_H4_PROFILE_BINDING
    assert state.native_broker_h4_equivalence_assumed is False
    assert state.synthetic_price_authorized is False
    assert all(item.proves_native_broker_h4_equivalence is False for item in EVIDENCE)


def test_h4_clock_closure_does_not_authorize_full_route() -> None:
    state = V48_H4_PROFILE_BINDING
    assert state.full_asia_london_route_authorized is False
    assert state.daily_profile_binding_resolved_independently is True
    assert state.generic_scalp_blocked is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False


def test_source_clock_evidence_is_explicit() -> None:
    assert EVIDENCE
    assert all(item.source_clock_fact is True for item in EVIDENCE)
