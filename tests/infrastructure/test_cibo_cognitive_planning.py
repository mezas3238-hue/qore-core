"""Tests for the CIBO Cognitive Planning and Learning substrate (CA-10/11)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_common import CiboCognitiveValidationError
from qore.infrastructure.cibo_cognitive_planning import (
    CognitiveGoal,
    CognitiveGoalId,
    CognitiveGoalStatus,
    CognitiveLearningRecord,
    CognitivePlan,
    CognitiveTask,
    CognitiveTaskId,
    CognitiveTaskStatus,
    EvidenceBundle,
    EvidenceRequirement,
    PlanHistory,
    PlanRequestKind,
    append_plan_revision,
    build_cognitive_plan,
    complete_task,
    emit_pending_requests,
    topological_task_order,
)

_GOAL = CognitiveGoalId(UUID("00000000-0000-0000-0000-000000000001"))
_TASK_A = CognitiveTaskId(UUID("00000000-0000-0000-0000-000000000011"))
_TASK_B = CognitiveTaskId(UUID("00000000-0000-0000-0000-000000000012"))
_TASK_C = CognitiveTaskId(UUID("00000000-0000-0000-0000-000000000013"))
_PLAN = UUID("00000000-0000-0000-0000-000000000021")
_DECISION_TIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _goal() -> CognitiveGoal:
    return CognitiveGoal(
        goal_id=_GOAL, description="improve regime detection", status=CognitiveGoalStatus.PENDING
    )


def _task(
    task_id: CognitiveTaskId = _TASK_A,
    dependencies: tuple[CognitiveTaskId, ...] = (),
    required_evidence: tuple[str, ...] = ("ev-1",),
) -> CognitiveTask:
    return CognitiveTask(
        task_id=task_id,
        goal_id=_GOAL,
        description="analyze regime",
        dependencies=dependencies,
        required_evidence=tuple(EvidenceRequirement(reference=r) for r in required_evidence),
        status=CognitiveTaskStatus.PENDING,
    )


def _plan(tasks: tuple[CognitiveTask, ...]) -> CognitivePlan:
    return build_cognitive_plan(plan_id=_PLAN, goals=[_goal()], tasks=tasks)


def test_goal_graph_cycle_rejected() -> None:
    first = _task(_TASK_A, dependencies=(_TASK_B,))
    second = _task(_TASK_B, dependencies=(_TASK_A,))
    with pytest.raises(CiboCognitiveValidationError):
        build_cognitive_plan(plan_id=_PLAN, goals=[_goal()], tasks=[first, second])


def test_dependency_order_is_deterministic() -> None:
    leaf = _task(_TASK_A)
    middle = _task(_TASK_B, dependencies=(_TASK_A,))
    root = _task(_TASK_C, dependencies=(_TASK_B,))
    plan = _plan((root, middle, leaf))
    order = topological_task_order(plan)
    assert order == (_TASK_A, _TASK_B, _TASK_C)


def test_task_completion_without_evidence_rejected() -> None:
    plan = _plan((_task(_TASK_A, required_evidence=("ev-1", "ev-2")),))
    with pytest.raises(CiboCognitiveValidationError):
        complete_task(plan, _TASK_A, completed_evidence=["ev-1"])


def test_task_completion_requires_dependencies_first() -> None:
    first = _task(_TASK_A)
    second = _task(_TASK_B, dependencies=(_TASK_A,))
    plan = _plan((first, second))
    with pytest.raises(CiboCognitiveValidationError):
        complete_task(plan, _TASK_B, completed_evidence=["ev-1"])


def test_task_completion_with_evidence() -> None:
    plan = _plan((_task(_TASK_A, required_evidence=("ev-1",)),))
    updated = complete_task(plan, _TASK_A, completed_evidence=["ev-1"])
    assert updated.task_by_id(_TASK_A).status is CognitiveTaskStatus.COMPLETED
    assert plan.task_by_id(_TASK_A).status is CognitiveTaskStatus.PENDING


def test_replan_cannot_erase_old_history() -> None:
    first = _plan((_task(_TASK_A),))
    history = PlanHistory(revisions=(first,))
    second = build_cognitive_plan(
        plan_id=_PLAN, goals=[_goal()], tasks=[_task(_TASK_A)], revision=1, parent_revision=0
    )
    updated = append_plan_revision(history, second, "refine goal decomposition")
    assert updated.revisions[0] is first
    assert updated.revisions[-1] is second
    assert len(updated.revisions) == 2


def test_replan_revision_must_increment() -> None:
    first = _plan((_task(_TASK_A),))
    history = PlanHistory(revisions=(first,))
    with pytest.raises(CiboCognitiveValidationError):
        append_plan_revision(history, first, "same revision")


def test_learning_separates_contemporaneous_and_later_evidence() -> None:
    contemporaneous = EvidenceBundle(reference="ev-a", observed_at=_DECISION_TIME)
    later = EvidenceBundle(
        reference="ev-b", observed_at=datetime(2024, 6, 2, 12, 0, 0, tzinfo=UTC)
    )
    record = CognitiveLearningRecord(
        record_id=UUID("00000000-0000-0000-0000-000000000031"),
        decision_time=_DECISION_TIME,
        expected_result="regime remains range-bound",
        actual_result_reference=EvidenceBundle(
            reference="ev-a", observed_at=_DECISION_TIME
        ),
        contemporaneous_evidence=(contemporaneous,),
        later_evidence=(later,),
        error_attribution="hypothesis: signal lag",
        proven=False,
        counterfactuals=("had we used more data",),
        reflection_note="revisit sampling window",
        supersedes=None,
    )
    assert record.contemporaneous_view() == (contemporaneous,)
    assert record.later_view() == (later,)


def test_later_evidence_cannot_rewrite_contemporaneous() -> None:
    later = EvidenceBundle(
        reference="ev-b", observed_at=datetime(2024, 6, 2, 12, 0, 0, tzinfo=UTC)
    )
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveLearningRecord(
            record_id=UUID("00000000-0000-0000-0000-000000000031"),
            decision_time=_DECISION_TIME,
            expected_result="x",
            actual_result_reference=None,
            contemporaneous_evidence=(later,),
            later_evidence=(),
            error_attribution="hypothesis",
            proven=False,
            counterfactuals=(),
            reflection_note="r",
            supersedes=None,
        )


def test_counterfactual_cannot_be_asserted_as_actual_outcome() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        CognitiveLearningRecord(
            record_id=UUID("00000000-0000-0000-0000-000000000031"),
            decision_time=_DECISION_TIME,
            expected_result="x",
            actual_result_reference="counterfactual narrative",  # type: ignore[arg-type]
            contemporaneous_evidence=(),
            later_evidence=(),
            error_attribution="hypothesis",
            proven=False,
            counterfactuals=("counterfactual narrative",),
            reflection_note="r",
            supersedes=None,
        )


def test_planner_emits_governed_requests_only() -> None:
    plan = _plan((_task(_TASK_A),))
    requests = emit_pending_requests(plan, kind=PlanRequestKind.RESEARCH)
    assert len(requests) == 1
    assert requests[0].task_id == _TASK_A
    assert requests[0].kind is PlanRequestKind.RESEARCH
    assert requests[0].request_reference == f"{_GOAL.value}:{_TASK_A.value}:research"


def test_plan_revision_rejects_bool_laundering() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        build_cognitive_plan(
            plan_id=_PLAN,
            goals=[_goal()],
            tasks=[_task(_TASK_A)],
            revision=True,
        )


def test_build_plan_rejects_non_sequence_tasks_without_leaking_exception() -> None:
    bad_tasks: Any = None
    with pytest.raises(CiboCognitiveValidationError):
        build_cognitive_plan(plan_id=_PLAN, goals=[_goal()], tasks=bad_tasks)


def test_build_plan_rejects_non_sequence_goals_without_leaking_exception() -> None:
    bad_goals: Any = None
    with pytest.raises(CiboCognitiveValidationError):
        build_cognitive_plan(plan_id=_PLAN, goals=bad_goals, tasks=[_task(_TASK_A)])


def test_build_plan_rejects_non_task_items_without_leaking_exception() -> None:
    bad_items: Any = ["not-a-task"]
    with pytest.raises(CiboCognitiveValidationError):
        build_cognitive_plan(plan_id=_PLAN, goals=[_goal()], tasks=bad_items)
