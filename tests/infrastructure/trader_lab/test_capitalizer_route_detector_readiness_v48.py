from qore.infrastructure.trader_lab.capitalizer_route_detector_readiness_v48 import (
    FACTS,
    V48_ROUTE_DETECTOR_READINESS,
    V48DetectorReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_source_native_route_registry_v48 import (
    V48RouteId,
)


def _status(route: V48RouteId, fact_id: str) -> V48DetectorReadiness:
    return next(
        item.readiness
        for item in FACTS
        if item.route_id is route and item.fact_id == fact_id
    )


def test_london_cisd_primitive_is_reusable_but_continuation_needs_route_binding() -> None:
    assert _status(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
    ) is V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE
    assert _status(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
    ) is V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND


def test_generic_scalp_core_facts_are_route_bound_pre_economic() -> None:
    for fact_id in (
        "H1_SCALP_BIAS_CONFIRMED",
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
        "M1_CONTINUATION_CONFIRMED",
        "LOGICAL_PROTECTED_SWING_STOP_AVAILABLE",
        "STRUCTURAL_TARGET_AVAILABLE",
    ):
        assert _status(
            V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
            fact_id,
        ) is V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC


def test_ftm_source_native_primitive_is_now_reusable() -> None:
    assert _status(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "CONTINUATION_STRUCTURE_CONFIRMED",
    ) is V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE


def test_h4_and_daily_forex_clocks_are_resolved_while_ict_remains_blocked() -> None:
    assert _status(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "H4_PROFILE_TIME_BINDING",
    ) is V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC
    assert _status(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "H4_PROFILE_TIME_BINDING",
    ) is V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC
    assert _status(
        V48RouteId.TTRADES_ASIA_4H_15M,
        "DAILY_PROFILE_TIME_BINDING",
    ) is V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC
    assert _status(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "DAILY_PROFILE_TIME_BINDING",
    ) is V48DetectorReadiness.ROUTE_BOUND_PRE_ECONOMIC
    assert _status(
        V48RouteId.ICT_2022_EXECUTION,
        "ICT_EXACT_PRIMARY_SOURCE_BINDING",
    ) is V48DetectorReadiness.SOURCE_BINDING_BLOCKED


def test_ny_sweep_and_cisd_exist_but_london_context_resolver_is_missing() -> None:
    assert _status(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_LIQUIDITY_SWEEP_CONFIRMED",
    ) is V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE
    assert _status(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "NY_CISD_CONFIRMED",
    ) is V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE
    assert _status(
        V48RouteId.TTRADES_NEW_YORK_MANIPULATION,
        "LONDON_CONTEXT_RESOLVED",
    ) is V48DetectorReadiness.DETECTOR_MISSING


def test_readiness_ledger_is_pre_economic_and_fail_closed() -> None:
    state = V48_ROUTE_DETECTOR_READINESS
    assert state.missing_detector_blocks_route_census is True
    assert state.outcome_used is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
