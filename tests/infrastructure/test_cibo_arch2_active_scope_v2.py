from qore.infrastructure.cibo_arch2_active_scope_v2 import (
    ARCHITECT2_ACTIVE_OWNERSHIP,
    ARCHITECT2_ACTIVE_SCOPE,
    ARCHITECT_A1_OWNERSHIP,
    ARCHITECT_A2_OWNERSHIP,
)


def test_architect2_active_scope_has_no_a1_a2_overlap() -> None:
    active = set(ARCHITECT2_ACTIVE_OWNERSHIP)
    assert active.isdisjoint(ARCHITECT_A1_OWNERSHIP)
    assert active.isdisjoint(ARCHITECT_A2_OWNERSHIP)
    assert len(active) == 8


def test_architect2_active_scope_is_external_b_side_only() -> None:
    assert ARCHITECT2_ACTIVE_SCOPE.workstreams == (
        "T02",
        "T03",
        "T11",
        "T16",
        "T20",
        "PROVIDER_ECONOMICS",
        "FORWARD_QUALIFICATION",
        "FRESH_OOS",
    )
    assert ARCHITECT2_ACTIVE_SCOPE.canonical_ledger_mutation_allowed is False
    assert ARCHITECT2_ACTIVE_SCOPE.phase22_consumption_allowed is False
    assert ARCHITECT2_ACTIVE_SCOPE.merge_authority is False
    assert ARCHITECT2_ACTIVE_SCOPE.productive_authority is False
