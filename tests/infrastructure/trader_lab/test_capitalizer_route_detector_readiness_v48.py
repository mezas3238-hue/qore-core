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


def test_london_cisd_and_continuation_have_v48_primitives_but_need_route_binding() -> None:
    assert _status(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_PROTECTED_SWING_CONFIRMED_BY_CISD",
    ) is V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND
    assert _status(
        V48RouteId.TTRADES_LONDON_DAILY_4H_15M,
        "M15_CONTINUATION_AVAILABLE",
    ) is V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND


def test_scalp_continuation_semantics_exist_but_still_need_m1_poi_binding() -> None:
    assert _status(
        V48RouteId.TTRADES_GENERIC_SCALP_H1_M15_M1,
        "M1_CONTINUATION_CONFIRMED",
    ) is V48DetectorReadiness.NEEDS_ROUTE_SCOPED_REBIND


def test_ftm_source_native_primitive_is_now_reusable() -> None:
    assert _status(
        V48RouteId.TTRADES_FAILURE_TO_MANIPULATE,
        "CONTINUATION_STRUCTURE_CONFIRMED",
    ) is V48DetectorReadiness.REUSABLE_CAUSAL_PRIMITIVE


def test_ict_binding_block_does_not_hide_ttrades_detector_work() -> None:
    assert _status(
        V48RouteId.ICT_2022_EXECUTION,
        "ICT_EXACT_PRIMARY_SOURCE_BINDING",
    ) is V48DetectorReadiness.SOURCE_BINDING_BLOCKED
    assert any(
        item.route_id is V48RouteId.TTRADES_ASIA_4H_15M
        and item.readiness is V48DetectorReadiness.DETECTOR_MISSING
        for item in FACTS
    )


def test_readiness_ledger_is_pre_economic_and_fail_closed() -> None:
    state = V48_ROUTE_DETECTOR_READINESS
    assert state.missing_detector_blocks_route_census is True
    assert state.outcome_used is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
