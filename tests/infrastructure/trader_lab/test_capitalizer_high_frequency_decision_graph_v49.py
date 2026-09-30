from qore.infrastructure.trader_lab.capitalizer_high_frequency_decision_graph_v49 import (
    STAGES,
    V49_HIGH_FREQUENCY_DECISION_GRAPH,
    V49GateRelation,
)


def test_decision_graph_contains_only_h1_m15_m1() -> None:
    assert {stage.timeframe for stage in STAGES} == {"H1", "M15", "M1"}


def test_h1_is_persistent_and_m1_is_not_superintersection() -> None:
    state = V49_HIGH_FREQUENCY_DECISION_GRAPH
    assert state.fresh_h1_event_required_per_trade is False
    assert state.m1_superintersection_required is False
    assert state.daily_allowed is False
    assert state.h4_allowed is False


def test_m1_execution_families_are_explicit_alternatives() -> None:
    alternatives = tuple(
        stage for stage in STAGES if stage.relation is V49GateRelation.ALTERNATIVE
    )
    assert len(alternatives) == 1
    assert alternatives[0].timeframe == "M1"
