from qore.infrastructure.cibo_arch2_closure_frontier import (
    ASSIGNED_WORKSTREAMS,
    Arch2ClosureState,
    architect2_closure_frontier,
)


def test_arch2_frontier_explains_exactly_all_43_assigned_workstreams() -> None:
    rows = architect2_closure_frontier()
    assert len(rows) == 43
    assert tuple(item.workstream_id for item in rows) == ASSIGNED_WORKSTREAMS
    assert len(set(item.workstream_id for item in rows)) == 43
    assert all(item.next_dependency for item in rows)
    assert all(item.productive_authority is False for item in rows)


def test_only_evidence_backed_terminal_recommendations_are_ready() -> None:
    rows = {item.workstream_id: item for item in architect2_closure_frontier()}
    ready = {
        name
        for name, row in rows.items()
        if row.state is Arch2ClosureState.TERMINAL_RECOMMENDATION_READY
    }
    assert ready == {"PROVIDER_ECONOMICS", "FORWARD_QUALIFICATION"}
    assert rows["PROVIDER_ECONOMICS"].terminal_recommendation == (
        "SUPERSEDED_WITH_PROVEN_LINEAGE"
    )
    assert rows["FORWARD_QUALIFICATION"].terminal_recommendation == (
        "SUPERSEDED_WITH_PROVEN_LINEAGE"
    )


def test_t16_and_t20_are_not_overclaimed() -> None:
    rows = {item.workstream_id: item for item in architect2_closure_frontier()}
    assert rows["T16"].state is Arch2ClosureState.FROZEN_GATE_WAITING_POPULATION
    assert rows["T20"].state is (
        Arch2ClosureState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE
    )
    assert rows["T16"].terminal_recommendation is None
    assert rows["T20"].terminal_recommendation is None
