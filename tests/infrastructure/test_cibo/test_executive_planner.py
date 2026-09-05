from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo.executive_planner import (
    CiboExecutivePlanner,
    CiboGoal,
    CiboObjective,
    CiboPlan,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_PLANNER = CiboExecutivePlanner()


def _objective(code: str = "direction.growth") -> CiboObjective:
    return CiboObjective(
        objective_code=code,
        description_code=f"{code}.description",
        declared_at=_NOW,
    )


def _goal(
    *,
    code: str,
    parent: str | None = None,
    dependencies: tuple[str, ...] = (),
    work: tuple[str, ...] = (),
    research: tuple[str, ...] = (),
    priority: int = 1,
    rationale: str = "direction.alignment",
) -> CiboGoal:
    return CiboGoal(
        goal_code=code,
        parent_goal_code=parent,
        dependency_codes=dependencies,
        work_request_codes=work,
        research_request_codes=research,
        priority=priority,
        rationale_code=rationale,
    )


def test_plan_builds_acyclic_plan_with_valid_dependencies() -> None:
    objective = _objective()
    goals = (
        _goal(code="goal.ingest", dependencies=(objective.objective_code,)),
        _goal(code="goal.evaluate", dependencies=("goal.ingest",)),
    )
    result = _PLANNER.plan(
        objective,
        goals=goals,
        replan_evidence=(CiboEvidenceRef("evidence:direction"),),
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    plan = result.value
    assert plan.objective == objective
    assert plan.authority is CiboFunctionalAuthority.REQUEST
    assert plan.goals == goals
    assert plan.replan_evidence == (CiboEvidenceRef("evidence:direction"),)


def test_self_dependent_goal_fails() -> None:
    result = _PLANNER.plan(
        _objective(),
        goals=(_goal(code="goal.loop", dependencies=("goal.loop",)),),
        replan_evidence=(),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_unknown_dependency_fails() -> None:
    result = _PLANNER.plan(
        _objective(),
        goals=(_goal(code="goal.a", dependencies=("goal.missing",)),),
        replan_evidence=(),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_cycle_between_goals_fails() -> None:
    result = _PLANNER.plan(
        _objective(),
        goals=(
            _goal(code="goal.a", dependencies=("goal.b",)),
            _goal(code="goal.b", dependencies=("goal.a",)),
        ),
        replan_evidence=(),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalBlockedError)


def test_bool_priority_rejected_on_construction() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        _goal(code="goal.a", priority=True)


def test_bool_priority_at_plan_boundary_returns_failure() -> None:
    corrupted = object.__new__(CiboGoal)
    object.__setattr__(corrupted, "goal_code", "goal.a")
    object.__setattr__(corrupted, "parent_goal_code", None)
    object.__setattr__(corrupted, "dependency_codes", ())
    object.__setattr__(corrupted, "work_request_codes", ())
    object.__setattr__(corrupted, "research_request_codes", ())
    object.__setattr__(corrupted, "priority", True)
    object.__setattr__(corrupted, "rationale_code", "direction.alignment")
    result = _PLANNER.plan(
        _objective(),
        goals=(corrupted,),
        replan_evidence=(),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_malformed_nested_type_returns_failure() -> None:
    result = _PLANNER.plan(
        cast(CiboObjective, object()),
        goals=(),
        replan_evidence=(),
        planned_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboFunctionalValidationError)


def test_repeated_identical_input_equal_logical_values() -> None:
    objective = _objective()
    goals = (_goal(code="goal.a", dependencies=(objective.objective_code,)),)
    left = _PLANNER.plan(objective, goals=goals, replan_evidence=(), planned_at=_NOW)
    right = _PLANNER.plan(objective, goals=goals, replan_evidence=(), planned_at=_NOW)
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value == right.value
    assert left.value.logical_values() == right.value.logical_values()


def test_plan_has_no_mutation_or_execution_fields() -> None:
    objective = _objective()
    result = _PLANNER.plan(
        objective,
        goals=(_goal(code="goal.a", dependencies=(objective.objective_code,)),),
        replan_evidence=(),
        planned_at=_NOW,
    )
    assert isinstance(result, Success)
    plan = result.value
    for name in ("code", "config", "mutation", "order", "execute", "command", "governance"):
        assert not hasattr(plan, name)


def test_plan_constructor_rejects_cycle() -> None:
    # Constructor/deriver parity: a cyclic dependency graph must not be admitted by
    # direct construction, matching the builder ceiling.
    with pytest.raises(CiboFunctionalBlockedError):
        CiboPlan(
            objective=_objective(),
            goals=(
                _goal(code="goal.a", dependencies=("goal.b",)),
                _goal(code="goal.b", dependencies=("goal.a",)),
            ),
            replan_evidence=(),
            planned_at=_NOW,
            authority=CiboFunctionalAuthority.REQUEST,
        )


def test_plan_constructor_rejects_self_dependency() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboPlan(
            objective=_objective(),
            goals=(_goal(code="goal.loop", dependencies=("goal.loop",)),),
            replan_evidence=(),
            planned_at=_NOW,
            authority=CiboFunctionalAuthority.REQUEST,
        )


def test_plan_constructor_rejects_unknown_dependency() -> None:
    with pytest.raises(CiboFunctionalValidationError):
        CiboPlan(
            objective=_objective(),
            goals=(_goal(code="goal.a", dependencies=("goal.missing",)),),
            replan_evidence=(),
            planned_at=_NOW,
            authority=CiboFunctionalAuthority.REQUEST,
        )
