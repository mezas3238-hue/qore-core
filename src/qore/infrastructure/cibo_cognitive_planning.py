"""CIBO Cognitive Planning / Goal Graph and Learning substrate (CA-10/11).

Typed, replayable cognitive planning shaped as
``GOAL -> SUBGOAL -> TASK -> DEPENDENCY -> REQUIRED EVIDENCE -> STATUS -> REPLAN``
with exact caller-supplied identities, DAG validation, deterministic dependency
order, and evidence-gated progress. The planner emits governed work/research
requests only; it cannot mutate code, Trader versions, authority state, or
execution.

Governed learning/reflection/counterfactual records separate contemporaneous
evidence from later evidence, attribute error as a hypothesis unless proven,
carry counterfactual alternatives as distinct from the actual outcome, and keep
a lesson supersession lineage. Records are append-only: no hindsight rewriting
and no silent self-modification.

Architecture laws honoured: immutable snapshots (1, 16), DAG/cycle rejection
(19, 22), exact runtime types (15), deterministic ordering (19), secret-bearing
strings fail closed (20), no ambient time/RNG (14), no global mutable state
(21).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveValidationError,
    contains_secret_material,
    require_aware_datetime,
    require_exact_int,
    require_exact_str,
)
from qore.kernel.temporal import canonical_instant


class PlanningError(CiboCognitiveError):
    """Base error for the CIBO cognitive planning/learning substrate."""

    __slots__ = ()


class PlanningValidationError(PlanningError, CiboCognitiveValidationError):
    """Violation of a cognitive planning or learning invariant."""

    __slots__ = ()


class CognitiveGoalStatus(StrEnum):
    """Lifecycle status of a cognitive goal."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class CognitiveTaskStatus(StrEnum):
    """Lifecycle status of a cognitive task."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class PlanRequestKind(StrEnum):
    """Governed request kind emitted by the planner (never execution)."""

    RESEARCH = "research"
    WORK = "work"


@dataclass(frozen=True, slots=True)
class CognitiveGoalId:
    """Explicit identity of a cognitive goal."""

    value: UUID

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.value) is not UUID:
            raise PlanningValidationError("goal id value must be a UUID")

    def logical_values(self) -> tuple[str]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CognitiveTaskId:
    """Explicit identity of a cognitive task."""

    value: UUID

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.value) is not UUID:
            raise PlanningValidationError("task id value must be a UUID")

    def logical_values(self) -> tuple[str]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EvidenceRequirement:
    """Explicit evidence reference required for progress or completion."""

    reference: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.reference, field="evidence requirement reference")
        if not self.reference.strip():
            raise PlanningValidationError("evidence requirement reference must not be blank")
        if contains_secret_material(self.reference):
            raise PlanningValidationError(
                "evidence requirement reference must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[str]:
        return (self.reference,)


@dataclass(frozen=True, slots=True)
class CognitiveTask:
    """One task in the goal graph, with explicit dependencies and evidence."""

    task_id: CognitiveTaskId
    goal_id: CognitiveGoalId
    description: str
    dependencies: tuple[CognitiveTaskId, ...]
    required_evidence: tuple[EvidenceRequirement, ...]
    status: CognitiveTaskStatus

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.task_id) is not CognitiveTaskId:
            raise PlanningValidationError("task id must be a CognitiveTaskId")
        self.task_id.revalidate()
        if type(self.goal_id) is not CognitiveGoalId:
            raise PlanningValidationError("task goal id must be a CognitiveGoalId")
        self.goal_id.revalidate()
        require_exact_str(self.description, field="task description")
        if not self.description.strip():
            raise PlanningValidationError("task description must not be blank")
        if contains_secret_material(self.description):
            raise PlanningValidationError(
                "task description must not carry secret-bearing material"
            )
        if type(self.dependencies) is not tuple:
            raise PlanningValidationError("task dependencies must be a tuple")
        for dep in self.dependencies:
            if type(dep) is not CognitiveTaskId:
                raise PlanningValidationError(
                    "task dependencies must contain only CognitiveTaskId values"
                )
            dep.revalidate()
        if type(self.required_evidence) is not tuple:
            raise PlanningValidationError("required evidence must be a tuple")
        for req in self.required_evidence:
            if type(req) is not EvidenceRequirement:
                raise PlanningValidationError(
                    "required evidence must contain only EvidenceRequirement values"
                )
            req.revalidate()
        if type(self.status) is not CognitiveTaskStatus:
            raise PlanningValidationError("task status must be a CognitiveTaskStatus")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.task_id.value),
            str(self.goal_id.value),
            self.description,
            tuple(str(dep.value) for dep in self.dependencies),
            tuple(req.logical_values() for req in self.required_evidence),
            self.status.value,
        )

    def sort_key(self) -> str:
        return str(self.task_id.value)


@dataclass(frozen=True, slots=True)
class CognitiveGoal:
    """One goal in the goal graph."""

    goal_id: CognitiveGoalId
    description: str
    status: CognitiveGoalStatus

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.goal_id) is not CognitiveGoalId:
            raise PlanningValidationError("goal id must be a CognitiveGoalId")
        self.goal_id.revalidate()
        require_exact_str(self.description, field="goal description")
        if not self.description.strip():
            raise PlanningValidationError("goal description must not be blank")
        if contains_secret_material(self.description):
            raise PlanningValidationError(
                "goal description must not carry secret-bearing material"
            )
        if type(self.status) is not CognitiveGoalStatus:
            raise PlanningValidationError("goal status must be a CognitiveGoalStatus")

    def logical_values(self) -> tuple[object, ...]:
        return (str(self.goal_id.value), self.description, self.status.value)

    def sort_key(self) -> str:
        return str(self.goal_id.value)


@dataclass(frozen=True, slots=True)
class CognitivePlan:
    """Immutable, revisioned snapshot of a validated goal graph."""

    plan_id: UUID
    goals: tuple[CognitiveGoal, ...]
    tasks: tuple[CognitiveTask, ...]
    revision: int
    parent_revision: int | None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.plan_id) is not UUID:
            raise PlanningValidationError("plan id must be a UUID")
        if type(self.goals) is not tuple or not self.goals:
            raise PlanningValidationError("plan goals must be a non-empty tuple")
        goal_ids: set[CognitiveGoalId] = set()
        for goal in self.goals:
            if type(goal) is not CognitiveGoal:
                raise PlanningValidationError("plan goals must contain only CognitiveGoal values")
            goal.revalidate()
            if goal.goal_id in goal_ids:
                raise PlanningValidationError("plan goals must have unique ids")
            goal_ids.add(goal.goal_id)
        if type(self.tasks) is not tuple or not self.tasks:
            raise PlanningValidationError("plan tasks must be a non-empty tuple")
        task_ids: set[CognitiveTaskId] = set()
        for task in self.tasks:
            if type(task) is not CognitiveTask:
                raise PlanningValidationError("plan tasks must contain only CognitiveTask values")
            task.revalidate()
            if task.task_id in task_ids:
                raise PlanningValidationError("plan tasks must have unique ids")
            task_ids.add(task.task_id)
            if task.goal_id not in goal_ids:
                raise PlanningValidationError("task goal id must reference a plan goal")
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise PlanningValidationError("task dependency must reference a plan task")
        require_exact_int(self.revision, field="plan revision")
        if self.revision < 0:
            raise PlanningValidationError("plan revision must be non-negative")
        if self.parent_revision is not None:
            require_exact_int(self.parent_revision, field="plan parent revision")
            if self.parent_revision >= self.revision:
                raise PlanningValidationError("plan parent revision must be below revision")
        if _topological_order(self.tasks) != self.tasks:
            raise PlanningValidationError("plan tasks must be in canonical dependency order")

    def task_by_id(self, task_id: CognitiveTaskId) -> CognitiveTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise PlanningValidationError("task id not present in plan")


@dataclass(frozen=True, slots=True)
class PlanHistory:
    """Append-only lineage of plan revisions."""

    revisions: tuple[CognitivePlan, ...]

    def __post_init__(self) -> None:
        if type(self.revisions) is not tuple or not self.revisions:
            raise PlanningValidationError("plan history must be a non-empty tuple")
        for plan in self.revisions:
            if type(plan) is not CognitivePlan:
                raise PlanningValidationError(
                    "plan history must contain only CognitivePlan values"
                )
            plan.revalidate()
        first = self.revisions[0]
        if first.parent_revision is not None:
            raise PlanningValidationError("first plan revision must have no parent")
        previous = first
        for plan in self.revisions[1:]:
            if plan.parent_revision != previous.revision:
                raise PlanningValidationError("plan revision parent must match prior revision")
            if plan.revision <= previous.revision:
                raise PlanningValidationError("plan revisions must be strictly increasing")
            previous = plan


@dataclass(frozen=True, slots=True)
class PlanRequest:
    """Governed work/research request emitted by the planner (never execution)."""

    goal_id: CognitiveGoalId
    task_id: CognitiveTaskId
    kind: PlanRequestKind
    description: str
    required_evidence: tuple[EvidenceRequirement, ...]

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.goal_id) is not CognitiveGoalId:
            raise PlanningValidationError("request goal id must be a CognitiveGoalId")
        self.goal_id.revalidate()
        if type(self.task_id) is not CognitiveTaskId:
            raise PlanningValidationError("request task id must be a CognitiveTaskId")
        self.task_id.revalidate()
        if type(self.kind) is not PlanRequestKind:
            raise PlanningValidationError("request kind must be a PlanRequestKind")
        require_exact_str(self.description, field="request description")
        if not self.description.strip():
            raise PlanningValidationError("request description must not be blank")
        if contains_secret_material(self.description):
            raise PlanningValidationError(
                "request description must not carry secret-bearing material"
            )
        if type(self.required_evidence) is not tuple:
            raise PlanningValidationError("request required evidence must be a tuple")
        for req in self.required_evidence:
            if type(req) is not EvidenceRequirement:
                raise PlanningValidationError(
                    "request required evidence must contain only EvidenceRequirement values"
                )
            req.revalidate()

    @property
    def request_reference(self) -> str:
        """Deterministic reference for the governed request."""
        return f"{self.goal_id.value}:{self.task_id.value}:{self.kind.value}"


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Evidence reference bound to an explicit, caller-supplied observation time."""

    reference: str
    observed_at: datetime

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.reference, field="evidence bundle reference")
        if not self.reference.strip():
            raise PlanningValidationError("evidence bundle reference must not be blank")
        if contains_secret_material(self.reference):
            raise PlanningValidationError(
                "evidence bundle reference must not carry secret-bearing material"
            )
        require_aware_datetime(self.observed_at, field="evidence bundle observed_at")

    def logical_values(self) -> tuple[str, str]:
        return (self.reference, canonical_instant(self.observed_at))


@dataclass(frozen=True, slots=True)
class CognitiveLearningRecord:
    """Governed, append-only learning/reflection/counterfactual record."""

    record_id: UUID
    decision_time: datetime
    expected_result: str
    actual_result_reference: EvidenceBundle | None
    contemporaneous_evidence: tuple[EvidenceBundle, ...]
    later_evidence: tuple[EvidenceBundle, ...]
    error_attribution: str
    proven: bool
    counterfactuals: tuple[str, ...]
    reflection_note: str
    supersedes: UUID | None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.record_id) is not UUID:
            raise PlanningValidationError("learning record id must be a UUID")
        decision_time = require_aware_datetime(self.decision_time, field="decision time")
        require_exact_str(self.expected_result, field="expected result")
        if not self.expected_result.strip():
            raise PlanningValidationError("expected result must not be blank")
        if contains_secret_material(self.expected_result):
            raise PlanningValidationError(
                "expected result must not carry secret-bearing material"
            )
        if self.actual_result_reference is not None:
            if type(self.actual_result_reference) is not EvidenceBundle:
                raise PlanningValidationError(
                    "actual result reference must be an EvidenceBundle"
                )
            self.actual_result_reference.revalidate()
        if type(self.contemporaneous_evidence) is not tuple:
            raise PlanningValidationError("contemporaneous evidence must be a tuple")
        for bundle in self.contemporaneous_evidence:
            if type(bundle) is not EvidenceBundle:
                raise PlanningValidationError(
                    "contemporaneous evidence must contain only EvidenceBundle values"
                )
            bundle.revalidate()
            if bundle.observed_at > decision_time:
                raise PlanningValidationError(
                    "contemporaneous evidence must not postdate the decision time"
                )
        if type(self.later_evidence) is not tuple:
            raise PlanningValidationError("later evidence must be a tuple")
        for bundle in self.later_evidence:
            if type(bundle) is not EvidenceBundle:
                raise PlanningValidationError(
                    "later evidence must contain only EvidenceBundle values"
                )
            bundle.revalidate()
            if bundle.observed_at <= decision_time:
                raise PlanningValidationError(
                    "later evidence must postdate the decision time"
                )
        require_exact_str(self.error_attribution, field="error attribution")
        if not self.error_attribution.strip():
            raise PlanningValidationError("error attribution must not be blank")
        if contains_secret_material(self.error_attribution):
            raise PlanningValidationError(
                "error attribution must not carry secret-bearing material"
            )
        if type(self.proven) is not bool:
            raise PlanningValidationError("learning record proven flag must be an exact bool")
        if type(self.counterfactuals) is not tuple:
            raise PlanningValidationError("counterfactuals must be a tuple")
        for alternative in self.counterfactuals:
            require_exact_str(alternative, field="counterfactual alternative")
            if not alternative.strip():
                raise PlanningValidationError("counterfactual alternative must not be blank")
            if contains_secret_material(alternative):
                raise PlanningValidationError(
                    "counterfactual alternative must not carry secret-bearing material"
                )
        require_exact_str(self.reflection_note, field="reflection note")
        if not self.reflection_note.strip():
            raise PlanningValidationError("reflection note must not be blank")
        if contains_secret_material(self.reflection_note):
            raise PlanningValidationError(
                "reflection note must not carry secret-bearing material"
            )
        if self.supersedes is not None and type(self.supersedes) is not UUID:
            raise PlanningValidationError("supersedes must be a UUID or None")

    def contemporaneous_view(self) -> tuple[EvidenceBundle, ...]:
        """Return only the evidence available at decision time."""
        return self.contemporaneous_evidence

    def later_view(self) -> tuple[EvidenceBundle, ...]:
        """Return only the evidence that arrived after decision time."""
        return self.later_evidence


def _topological_order(tasks: tuple[CognitiveTask, ...]) -> tuple[CognitiveTask, ...]:
    by_id = {task.task_id: task for task in tasks}
    in_degree = {task.task_id: 0 for task in tasks}
    dependents: dict[CognitiveTaskId, list[CognitiveTaskId]] = {
        task.task_id: [] for task in tasks
    }
    for task in tasks:
        for dep in task.dependencies:
            if dep not in by_id:
                raise PlanningValidationError("task dependency must reference a plan task")
            in_degree[task.task_id] += 1
            dependents[dep].append(task.task_id)
    ready = sorted(
        (tid for tid, degree in in_degree.items() if degree == 0),
        key=lambda tid: str(tid.value),
    )
    ordered: list[CognitiveTask] = []
    while ready:
        current = ready.pop(0)
        ordered.append(by_id[current])
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                ready.append(dependent)
        ready.sort(key=lambda tid: str(tid.value))
    if len(ordered) != len(tasks):
        raise PlanningValidationError("goal graph must be acyclic")
    return tuple(ordered)


def build_cognitive_plan(
    *,
    plan_id: UUID,
    goals: Sequence[CognitiveGoal],
    tasks: Sequence[CognitiveTask],
    revision: int = 0,
    parent_revision: int | None = None,
) -> CognitivePlan:
    """Build a validated, canonically (topologically) ordered plan snapshot."""
    if not isinstance(goals, Sequence):
        raise PlanningValidationError("goals must be a sequence")
    if not isinstance(tasks, Sequence):
        raise PlanningValidationError("tasks must be a sequence")
    goals_tuple = tuple(goals)
    tasks_tuple = tuple(tasks)
    for task in tasks_tuple:
        if type(task) is not CognitiveTask:
            raise PlanningValidationError("tasks must contain only CognitiveTask values")
        task.revalidate()
    ordered = _topological_order(tasks_tuple)
    return CognitivePlan(
        plan_id=plan_id,
        goals=goals_tuple,
        tasks=ordered,
        revision=revision,
        parent_revision=parent_revision,
    )


def topological_task_order(plan: CognitivePlan) -> tuple[CognitiveTaskId, ...]:
    """Return deterministic dependency-ordered task ids."""
    if type(plan) is not CognitivePlan:
        raise PlanningValidationError("plan must be a CognitivePlan")
    return tuple(task.task_id for task in plan.tasks)


def complete_task(
    plan: CognitivePlan,
    task_id: CognitiveTaskId,
    completed_evidence: Sequence[str],
) -> CognitivePlan:
    """Return a new plan with ``task_id`` completed, gated on evidence and deps."""
    if type(plan) is not CognitivePlan:
        raise PlanningValidationError("plan must be a CognitivePlan")
    if type(task_id) is not CognitiveTaskId:
        raise PlanningValidationError("task id must be a CognitiveTaskId")
    if not isinstance(completed_evidence, Sequence):
        raise PlanningValidationError("completed evidence must be a sequence")
    provided = {
        require_exact_str(item, field="completed evidence item")
        for item in completed_evidence
    }
    task = plan.task_by_id(task_id)
    if task.status is CognitiveTaskStatus.COMPLETED:
        raise PlanningValidationError("task is already completed")
    for dep in task.dependencies:
        if plan.task_by_id(dep).status is not CognitiveTaskStatus.COMPLETED:
            raise PlanningValidationError("task dependencies must be completed first")
    required = {req.reference for req in task.required_evidence}
    if not required.issubset(provided):
        missing = sorted(required - provided)
        raise PlanningValidationError(
            f"task completion requires evidence references: {', '.join(missing)}"
        )
    new_tasks = tuple(
        CognitiveTask(
            task_id=item.task_id,
            goal_id=item.goal_id,
            description=item.description,
            dependencies=item.dependencies,
            required_evidence=item.required_evidence,
            status=(
                CognitiveTaskStatus.COMPLETED
                if item.task_id == task_id
                else item.status
            ),
        )
        for item in plan.tasks
    )
    return CognitivePlan(
        plan_id=plan.plan_id,
        goals=plan.goals,
        tasks=new_tasks,
        revision=plan.revision,
        parent_revision=plan.parent_revision,
    )


def append_plan_revision(
    history: PlanHistory, plan: CognitivePlan, reason: str
) -> PlanHistory:
    """Append a new revision without erasing prior revisions."""
    if type(history) is not PlanHistory:
        raise PlanningValidationError("history must be a PlanHistory")
    if type(plan) is not CognitivePlan:
        raise PlanningValidationError("plan must be a CognitivePlan")
    require_exact_str(reason, field="replan reason")
    if not reason.strip():
        raise PlanningValidationError("replan reason must not be blank")
    if contains_secret_material(reason):
        raise PlanningValidationError("replan reason must not carry secret-bearing material")
    latest = history.revisions[-1]
    if plan.revision != latest.revision + 1:
        raise PlanningValidationError("new plan revision must increment the latest revision")
    if plan.parent_revision != latest.revision:
        raise PlanningValidationError("new plan parent revision must match the latest revision")
    return PlanHistory(revisions=(*history.revisions, plan))


def emit_pending_requests(
    plan: CognitivePlan, *, kind: PlanRequestKind = PlanRequestKind.WORK
) -> tuple[PlanRequest, ...]:
    """Emit deterministic governed work/research requests for pending tasks."""
    if type(plan) is not CognitivePlan:
        raise PlanningValidationError("plan must be a CognitivePlan")
    if type(kind) is not PlanRequestKind:
        raise PlanningValidationError("request kind must be a PlanRequestKind")
    pending = sorted(
        (task for task in plan.tasks if task.status is not CognitiveTaskStatus.COMPLETED),
        key=lambda task: str(task.task_id.value),
    )
    return tuple(
        PlanRequest(
            goal_id=task.goal_id,
            task_id=task.task_id,
            kind=kind,
            description=task.description,
            required_evidence=task.required_evidence,
        )
        for task in pending
    )


__all__ = [
    "CognitiveGoal",
    "CognitiveGoalId",
    "CognitiveGoalStatus",
    "CognitiveLearningRecord",
    "CognitivePlan",
    "CognitiveTask",
    "CognitiveTaskId",
    "CognitiveTaskStatus",
    "EvidenceBundle",
    "EvidenceRequirement",
    "PlanHistory",
    "PlanRequest",
    "PlanRequestKind",
    "PlanningError",
    "PlanningValidationError",
    "append_plan_revision",
    "build_cognitive_plan",
    "complete_task",
    "emit_pending_requests",
    "topological_task_order",
]
