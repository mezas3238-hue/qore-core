from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboObjective:
    """A declared direction objective. It carries intent, never execution."""

    objective_code: str
    description_code: str
    declared_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "objective_code",
            _validate_code(self.objective_code, field_name="objective code"),
        )
        object.__setattr__(
            self,
            "description_code",
            _validate_code(self.description_code, field_name="description code"),
        )
        _validate_timestamp(self.declared_at, field_name="objective declared_at")

    def logical_values(self) -> tuple[object, ...]:
        return (self.objective_code, self.description_code, self.declared_at.isoformat())


@dataclass(frozen=True, slots=True)
class CiboGoal:
    """A planning goal referencing the objective or sibling goals only.

    ``dependency_codes`` may reference the objective code or other goal codes;
    work/research request codes ask for work, never command its execution.
    """

    goal_code: str
    parent_goal_code: str | None
    dependency_codes: tuple[str, ...]
    work_request_codes: tuple[str, ...]
    research_request_codes: tuple[str, ...]
    priority: int
    rationale_code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "goal_code",
            _validate_code(self.goal_code, field_name="goal code"),
        )
        if self.parent_goal_code is not None:
            object.__setattr__(
                self,
                "parent_goal_code",
                _validate_code(self.parent_goal_code, field_name="parent goal code"),
            )
        object.__setattr__(
            self,
            "dependency_codes",
            _validate_codes(self.dependency_codes, field_name="dependency codes"),
        )
        object.__setattr__(
            self,
            "work_request_codes",
            _validate_codes(self.work_request_codes, field_name="work request codes"),
        )
        object.__setattr__(
            self,
            "research_request_codes",
            _validate_codes(
                self.research_request_codes,
                field_name="research request codes",
            ),
        )
        if type(self.priority) is not int:
            raise CiboFunctionalValidationError(
                "goal priority must be an exact int (bool is not int)"
            )
        object.__setattr__(
            self,
            "rationale_code",
            _validate_code(self.rationale_code, field_name="rationale code"),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.goal_code,
            self.parent_goal_code,
            self.dependency_codes,
            self.work_request_codes,
            self.research_request_codes,
            self.priority,
            self.rationale_code,
        )


def _has_dependency_cycle(adjacency: dict[str, tuple[str, ...]]) -> bool:
    visited: set[str] = set()
    active: set[str] = set()
    for node in sorted(adjacency):
        if node in visited:
            continue
        if _visit(node, adjacency, visited, active):
            return True
    return False


def _visit(
    node: str,
    adjacency: dict[str, tuple[str, ...]],
    visited: set[str],
    active: set[str],
) -> bool:
    visited.add(node)
    active.add(node)
    for neighbor in adjacency[node]:
        if neighbor in active:
            return True
        if neighbor not in visited:
            if _visit(neighbor, adjacency, visited, active):
                return True
    active.remove(node)
    return False


def _validate_goal_dependencies(
    objective: CiboObjective,
    goals: tuple[CiboGoal, ...],
) -> None:
    """Enforce the plan dependency invariants shared by builder and constructor.

    Dependencies may only reference the objective code or a sibling goal code, a
    goal must not depend on itself, and the goal graph must be acyclic. This is
    the single source of truth so a malformed (cyclic/self/unknown-dependency)
    plan cannot be admitted by direct construction.
    """
    goal_codes = {goal.goal_code for goal in goals}
    allowed = goal_codes | {objective.objective_code}
    for goal in goals:
        if goal.goal_code in goal.dependency_codes:
            raise CiboFunctionalValidationError("goal must not depend on itself")
        for dependency in goal.dependency_codes:
            if dependency not in allowed:
                raise CiboFunctionalValidationError(
                    "goal references an unknown dependency"
                )
    adjacency = {
        goal.goal_code: tuple(
            dependency
            for dependency in goal.dependency_codes
            if dependency in goal_codes
        )
        for goal in goals
    }
    if _has_dependency_cycle(adjacency):
        raise CiboFunctionalBlockedError(
            "goals must form an acyclic dependency structure"
        )


@dataclass(frozen=True, slots=True)
class CiboPlan:
    """A functional plan: requests and direction only, no mutation authority."""

    objective: CiboObjective
    goals: tuple[CiboGoal, ...]
    replan_evidence: tuple[CiboEvidenceRef, ...]
    planned_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.objective, CiboObjective):
            raise CiboFunctionalValidationError("plan requires CiboObjective")
        CiboObjective.__post_init__(self.objective)
        if not isinstance(self.goals, tuple) or any(
            not isinstance(goal, CiboGoal) for goal in self.goals
        ):
            raise CiboFunctionalValidationError(
                "plan goals must be a tuple of CiboGoal"
            )
        for goal in self.goals:
            CiboGoal.__post_init__(goal)
        goal_codes = tuple(goal.goal_code for goal in self.goals)
        if len(set(goal_codes)) != len(goal_codes):
            raise CiboFunctionalValidationError("plan goal codes must be unique")
        # Constructor/deriver parity: a plan must be acyclic with only known,
        # non-self dependencies even when constructed directly.
        _validate_goal_dependencies(self.objective, self.goals)
        object.__setattr__(
            self,
            "replan_evidence",
            _validate_evidence_refs(self.replan_evidence, field_name="replan evidence"),
        )
        _validate_timestamp(self.planned_at, field_name="plan planned_at")
        if self.authority is not CiboFunctionalAuthority.REQUEST:
            raise CiboFunctionalValidationError(
                "functional plan authority must be REQUEST"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.objective.logical_values(),
            tuple(goal.logical_values() for goal in self.goals),
            tuple(item.logical_values() for item in self.replan_evidence),
            self.planned_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboExecutivePlanner:
    """Deterministic, stateless QORE-direction planner.

    Outputs a REQUEST-only plan whose goals must form an acyclic dependency
    structure over the objective code and sibling goal codes. It never mutates
    code/config/governance and never orders execution.
    """

    def plan(
        self,
        objective: CiboObjective,
        *,
        goals: tuple[CiboGoal, ...],
        replan_evidence: tuple[CiboEvidenceRef, ...],
        planned_at: datetime,
    ) -> Result[CiboPlan, CiboFunctionalError]:
        if not isinstance(objective, CiboObjective):
            return Failure(
                CiboFunctionalValidationError("plan requires CiboObjective")
            )
        try:
            CiboObjective.__post_init__(objective)
        except CiboFunctionalError as error:
            return Failure(error)
        if not isinstance(goals, tuple) or any(
            not isinstance(goal, CiboGoal) for goal in goals
        ):
            return Failure(
                CiboFunctionalValidationError("goals must be a tuple of CiboGoal")
            )
        try:
            for goal in goals:
                CiboGoal.__post_init__(goal)
            _validate_timestamp(planned_at, field_name="planned_at")
            normalized_replan = _validate_evidence_refs(
                replan_evidence,
                field_name="replan evidence",
            )
        except CiboFunctionalError as error:
            return Failure(error)

        goal_codes = {goal.goal_code for goal in goals}
        if len(goal_codes) != len(goals):
            return Failure(
                CiboFunctionalValidationError("plan goal codes must be unique")
            )
        try:
            _validate_goal_dependencies(objective, goals)
        except CiboFunctionalError as error:
            return Failure(error)

        try:
            return Success(
                CiboPlan(
                    objective=objective,
                    goals=goals,
                    replan_evidence=normalized_replan,
                    planned_at=planned_at,
                    authority=CiboFunctionalAuthority.REQUEST,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
