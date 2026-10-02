from qore.infrastructure.cibo_arch2_active_frontier_v2 import (
    Architect2ActiveState,
    architect2_active_frontier_v2,
)
from qore.infrastructure.cibo_arch2_active_scope_v2 import (
    ARCHITECT2_ACTIVE_OWNERSHIP,
)


def test_active_frontier_covers_exact_current_scope() -> None:
    rows = architect2_active_frontier_v2()

    assert tuple(item.workstream_id for item in rows) == ARCHITECT2_ACTIVE_OWNERSHIP
    assert len(rows) == 8
    assert all(item.canonical_ledger_modified is False for item in rows)
    assert all(item.productive_authority is False for item in rows)


def test_active_frontier_has_four_terminal_recommendations() -> None:
    rows = {
        item.workstream_id: item
        for item in architect2_active_frontier_v2()
    }

    assert rows["T03"].state is Architect2ActiveState.TERMINAL_RECOMMENDATION_READY
    assert rows["T03"].proposed_terminal_disposition == "FALSIFIED_AND_CLOSED"
    assert (
        rows["PROVIDER_ECONOMICS"].proposed_terminal_disposition
        == "SUPERSEDED_WITH_PROVEN_LINEAGE"
    )
    assert (
        rows["FORWARD_QUALIFICATION"].proposed_terminal_disposition
        == "SUPERSEDED_WITH_PROVEN_LINEAGE"
    )

    assert (
        rows["T11"].state
        is Architect2ActiveState.BLOCKED_ON_PROVIDER_CONTAINMENT
    )
    assert "EXACT_TWO_CANCELLED_V1_DEMO_POSITIONS" in (
        rows["T11"].remaining_requirement
    )
    assert "36946792349_EVIDENCE_INADMISSIBLE" in (
        rows["T11"].remaining_requirement
    )
    assert rows["T16"].state is Architect2ActiveState.TERMINAL_RECOMMENDATION_READY
    assert rows["T16"].proposed_terminal_disposition == "FALSIFIED_AND_CLOSED"
    assert (
        rows["T02"].state
        is Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE
    )
    assert (
        rows["T20"].state
        is Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE
    )
    assert rows["FRESH_OOS"].state is Architect2ActiveState.WAITING_ON_INTEGRATOR_RECEIPT
