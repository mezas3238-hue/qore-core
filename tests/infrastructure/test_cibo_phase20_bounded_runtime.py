from __future__ import annotations

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase20_bounded_runtime import (
    Phase20BoundedCycleBudget,
)


def test_unbounded_budget_never_requests_stop() -> None:
    budget = Phase20BoundedCycleBudget(max_cycles=None)

    assert budget.complete_cycle() is False
    assert budget.complete_cycle() is False
    assert budget.completed_cycles == 2


def test_single_cycle_budget_stops_after_first_complete_cycle() -> None:
    budget = Phase20BoundedCycleBudget(max_cycles=1)

    assert budget.complete_cycle() is True
    assert budget.completed_cycles == 1


def test_multi_cycle_budget_stops_only_at_boundary() -> None:
    budget = Phase20BoundedCycleBudget(max_cycles=2)

    assert budget.complete_cycle() is False
    assert budget.complete_cycle() is True


@pytest.mark.parametrize("value", [0, -1, True])
def test_invalid_cycle_budget_fails_closed(value: object) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="max_cycles must be positive int",
    ):
        Phase20BoundedCycleBudget(max_cycles=value)  # type: ignore[arg-type]
