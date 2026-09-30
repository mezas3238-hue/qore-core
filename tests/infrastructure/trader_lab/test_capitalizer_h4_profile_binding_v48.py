from qore.infrastructure.trader_lab.capitalizer_h4_profile_binding_v48 import (
    EVIDENCE,
    V48_H4_PROFILE_BINDING,
    V48H4BindingState,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def test_h4_routes_fail_closed_until_profile_boundary_is_source_bound() -> None:
    state = V48_H4_PROFILE_BINDING
    assert state.state is V48H4BindingState.SOURCE_BINDING_BLOCKED
    assert state.provider_native_h4_available is True
    assert state.provider_boundary_equals_ttrades_profile_proven is False
    assert state.synthetic_h4_authorized is False
    assert state.productive_h4_route_census_authorized is False
    assert set(state.blocked_routes) == {
        V48RouteId.TTRADES_ASIA_4H_15M,
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
    }


def test_h4_local_blocker_does_not_block_generic_scalping_route() -> None:
    state = V48_H4_PROFILE_BINDING
    assert state.generic_scalp_blocked is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False


def test_evidence_does_not_claim_provider_boundary_equivalence() -> None:
    assert EVIDENCE
    assert all(item.proves_exact_provider_boundary is False for item in EVIDENCE)
