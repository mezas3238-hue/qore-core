from qore.infrastructure.trader_lab.capitalizer_human_decision_graph_v48 import (
    ROUTES,
    V48_HUMAN_DECISION_GRAPH,
    V48HumanDecisionRoute,
    V48Route,
    V48RouteStageRole,
    V48Session,
    shared_required_stage_ids,
)


def _route(route_id: V48Route) -> V48HumanDecisionRoute:
    return next(route for route in ROUTES if route.route is route_id)


def test_asia_has_two_independent_source_routes() -> None:
    asia = [route for route in ROUTES if route.session is V48Session.ASIA]
    assert {route.route for route in asia} == {
        V48Route.ASIA_POSITIONAL,
        V48Route.ASIA_4H_15M_FRACTAL,
    }
    assert all(route.route_is_alternative_not_global_requirement for route in asia)


def test_london_is_not_forced_through_h1_m15_m1() -> None:
    london = _route(V48Route.LONDON_DAILY_4H_15M)
    timeframes = {stage.timeframe for stage in london.stages}
    stage_ids = {stage.stage_id for stage in london.stages}
    assert "DAILY" in timeframes
    assert "4H" in timeframes
    assert "15M" in timeframes
    assert "M1" not in timeframes
    assert "H1" not in timeframes
    assert {
        "LONDON_DAILY_WICK",
        "LONDON_15M_CISD_PROTECTED_SWING",
        "LONDON_15M_CONTINUATION",
    }.issubset(stage_ids)


def test_new_york_entry_models_are_alternatives_not_and_requirements() -> None:
    ny = _route(V48Route.NEW_YORK_MANIPULATION)
    assert len(ny.execution_alternatives) >= 3
    assert {item.alternative_id for item in ny.execution_alternatives} >= {
        "NY_FVG_ENTRY",
        "NY_ORDER_BLOCK_ENTRY",
        "NY_OTHER_VALID_ENTRY_MODEL",
    }


def test_scalp_m1_is_execution_layer_not_primary_narrative() -> None:
    scalp = _route(V48Route.GENERIC_SCALP_H1_M15_M1)
    m1 = [stage for stage in scalp.stages if stage.timeframe == "M1"]
    assert len(m1) == 1
    assert m1[0].role is V48RouteStageRole.EXECUTION
    assert scalp.execution_alternatives == ()


def test_ftm_core_route_does_not_require_m1_fvg_and_ob_stage_ids() -> None:
    ftm = _route(V48Route.FAILURE_TO_MANIPULATE)
    stage_ids = {stage.stage_id for stage in ftm.stages}
    assert "M1_FVG" not in stage_ids
    assert "M1_ORDER_BLOCK" not in stage_ids
    assert {
        "FTM_LEVEL_TAKEN",
        "FTM_EXPECTED_REVERSAL_NOT_CONFIRMED",
        "FTM_CONTINUATION_STRUCTURE",
    }.issubset(stage_ids)


def test_no_literal_stage_is_universal_across_all_source_routes() -> None:
    assert shared_required_stage_ids() == frozenset()


def test_v48_graph_forbids_global_and_and_fresh_holdout() -> None:
    assert V48_HUMAN_DECISION_GRAPH.global_entry_and_gate_allowed is False
    assert V48_HUMAN_DECISION_GRAPH.source_route_may_be_forced_into_other_route is False
    assert V48_HUMAN_DECISION_GRAPH.fresh_holdout_authorized is False
    assert V48_HUMAN_DECISION_GRAPH.economics_authorized is False
