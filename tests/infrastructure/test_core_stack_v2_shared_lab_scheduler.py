# ruff: noqa: I001
import resource
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunRequest,
    ValidationSuite,
)
from qore.infrastructure.core_stack_v2.shared_lab_orchestrator import NativeLabOrchestrator
from qore.infrastructure.core_stack_v2.shared_lab_scheduler import (
    ClientRole,
    JobSubmission,
    PriorityLane,
    SchedulerState,
    SharedLabScheduler,
)
from qore.infrastructure.core_stack_v2.shared_lab_suite_registry import (
    NativeSuiteRegistry,
    SuiteDefinition,
)


pytestmark = pytest.mark.skipif(
    not hasattr(resource, "prlimit"),
    reason="native worker acceptance requires Linux prlimit",
)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "lab@example.invalid")
    git(repo, "config", "user.name", "Shared Lab")
    (repo / "component.txt").write_text("committed\n")
    git(repo, "add", "component.txt")
    git(repo, "commit", "-m", "initial")
    return repo, git(repo, "rev-parse", "HEAD")


def command(delay: float = 0.12) -> tuple[str, ...]:
    code = (
        "import os,time,sys;"
        f"time.sleep({delay});"
        "owner=os.environ['QORE_SHARED_LAB_SUBMITTED_BY'];"
        "print('owner='+owner);print('1 passed');"
        "sys.exit(1 if owner=='Architect-5' else 0)"
    )
    return (sys.executable, "-c", code)


def registry(delay: float = 0.12) -> NativeSuiteRegistry:
    result = NativeSuiteRegistry()
    defs = (
        ("unit", ValidationSuite.UNIT, LabScope.FULL_STACK, ()),
        ("contract", ValidationSuite.CONTRACT, LabScope.FULL_STACK, ("unit",)),
        ("data-reality", ValidationSuite.DATA_REALITY, LabScope.DATA, ("contract",)),
        (
            "sensor-reality",
            ValidationSuite.SENSOR_REALITY,
            LabScope.SENSOR,
            ("contract",),
        ),
        (
            "identity-reality",
            ValidationSuite.IDENTITY_REALITY,
            LabScope.IDENTITY,
            ("contract",),
        ),
        (
            "temporal-reality",
            ValidationSuite.TEMPORAL_REALITY,
            LabScope.TEMPORAL,
            ("contract",),
        ),
        (
            "provider-reality",
            ValidationSuite.PROVIDER_REALITY,
            LabScope.PROVIDER,
            ("contract",),
        ),
        (
            "integration",
            ValidationSuite.INTEGRATION,
            LabScope.FULL_STACK,
            (
                "data-reality",
                "sensor-reality",
                "identity-reality",
                "temporal-reality",
                "provider-reality",
            ),
        ),
        (
            "functional",
            ValidationSuite.FUNCTIONAL,
            LabScope.COGNITION,
            ("integration",),
        ),
        (
            "causality",
            ValidationSuite.CAUSALITY,
            LabScope.COGNITION,
            ("functional",),
        ),
        (
            "consumer-validation",
            ValidationSuite.CONSUMER_VALIDATION,
            LabScope.DECISION,
            ("functional",),
        ),
        ("replay", ValidationSuite.REPLAY, LabScope.FULL_STACK, ("contract",)),
        (
            "determinism",
            ValidationSuite.DETERMINISM,
            LabScope.FULL_STACK,
            ("replay",),
        ),
        (
            "regression",
            ValidationSuite.REGRESSION,
            LabScope.FULL_STACK,
            ("functional",),
        ),
        (
            "stress",
            ValidationSuite.STRESS,
            LabScope.FULL_STACK,
            ("functional",),
        ),
        (
            "performance",
            ValidationSuite.PERFORMANCE,
            LabScope.FULL_STACK,
            ("functional",),
        ),
        (
            "full-stack",
            ValidationSuite.FULL_STACK,
            LabScope.FULL_STACK,
            (
                "consumer-validation",
                "causality",
                "determinism",
                "regression",
                "stress",
                "performance",
            ),
        ),
    )
    for task_id, suite, scope, dependencies in defs:
        result.register(
            SuiteDefinition(
                task_id,
                suite,
                scope,
                dependencies,
                command(delay),
                ("component.txt",),
            )
        )
    return result


def request(
    repo: Path,
    sha: str,
    *,
    client: str,
    mode: ExecutionMode,
    scope: LabScope,
    dependency_hash: str,
) -> RunRequest:
    return RunRequest(
        repository="owner/repo",
        repo_path=str(repo),
        commit_sha=sha,
        branch="main",
        dataset_id="builtin-engineering",
        dataset_version="1",
        mode=mode,
        scope=scope,
        workers=1,
        policy=ResourcePolicy(
            timeout_seconds=20,
            retries=0,
            memory_limit_mb=1024,
            cpu_limit_seconds=20,
        ),
        submitted_by=client,
        submitted_role=(
            "INTEGRATOR" if client.startswith("Integrator") else "ARCHITECT"
        ),
        dependency_hashes=(dependency_hash,),
    )


def scheduler(
    tmp_path: Path,
    *,
    workers: int = 4,
    delay: float = 0.12,
) -> SharedLabScheduler:
    state = tmp_path / "state"
    orchestrator = NativeLabOrchestrator(
        state_dir=state,
        registry=registry(delay),
    )
    return SharedLabScheduler(
        state_dir=state,
        worker_capacity=workers,
        max_worker_capacity=20,
        max_queued_jobs=32,
        orchestrator=orchestrator,
    )


def wait_for_running(scheduler: SharedLabScheduler, minimum: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if scheduler.status()["running_jobs"] >= minimum:
            return
        time.sleep(0.02)
    raise AssertionError("scheduler did not reach expected concurrency")


def test_nine_clients_run_concurrently_without_cross_run_contamination(
    tmp_path: Path,
) -> None:
    repo, sha = make_repo(tmp_path)
    lab = scheduler(tmp_path)
    cases = (
        ("Architect-1", ExecutionMode.QUICK, LabScope.PROVIDER),
        ("Architect-2", ExecutionMode.COMPONENT, LabScope.SENSOR),
        ("Architect-3", ExecutionMode.REPLAY, LabScope.FULL_STACK),
        ("Architect-4", ExecutionMode.INTEGRATION, LabScope.PROVIDER),
        ("Architect-5", ExecutionMode.REGRESSION, LabScope.COGNITION),
        ("Architect-6", ExecutionMode.DEEP, LabScope.COGNITION),
        ("Integrator-1", ExecutionMode.QUICK, LabScope.IDENTITY),
        ("Integrator-2", ExecutionMode.REGRESSION, LabScope.FULL_STACK),
        ("Integrator-3", ExecutionMode.FULL, LabScope.FULL_STACK),
    )

    def submit(index_case: tuple[int, tuple[str, ExecutionMode, LabScope]]):
        index, case = index_case
        client, mode, scope = case
        role = (
            ClientRole.INTEGRATOR
            if client.startswith("Integrator")
            else ClientRole.ARCHITECT
        )
        priority = (
            PriorityLane.QUICK
            if mode is ExecutionMode.QUICK
            else PriorityLane.DEEP
            if mode in {ExecutionMode.DEEP, ExecutionMode.FULL}
            else PriorityLane.NORMAL
        )
        return lab.submit(
            JobSubmission(
                client,
                role,
                request(
                    repo,
                    sha,
                    client=client,
                    mode=mode,
                    scope=scope,
                    dependency_hash=f"client-{index}",
                ),
                priority,
            )
        )

    try:
        with ThreadPoolExecutor(max_workers=9) as pool:
            jobs = tuple(pool.map(submit, enumerate(cases)))
        assert len({job.scheduler_job_id for job in jobs}) == 9
        wait_for_running(lab, 2)
        snapshot = lab.status()
        assert snapshot["running_jobs"] <= 4
        assert snapshot["running_jobs"] >= 2
        finished = tuple(lab.wait(job.scheduler_job_id, timeout=30) for job in jobs)
        assert len(finished) == 9

        expected_failure = next(
            item for item in finished if item.submission.submitted_by == "Architect-5"
        )
        assert expected_failure.state is SchedulerState.FAIL
        others = [item for item in finished if item is not expected_failure]
        assert all(item.state is SchedulerState.PASS for item in others)

        evidence_paths = {
            item.evidence_path for item in finished if item.evidence_path is not None
        }
        assert len(evidence_paths) == 9
        for item in finished:
            if item.evidence_path is None:
                continue
            evidence = Path(item.evidence_path).read_text()
            assert item.submission.submitted_by in evidence
    finally:
        lab.shutdown()


def test_identical_active_jobs_are_deduplicated_across_clients(
    tmp_path: Path,
) -> None:
    repo, sha = make_repo(tmp_path)
    lab = scheduler(tmp_path, workers=1, delay=0.4)
    base = request(
        repo,
        sha,
        client="Architect-1",
        mode=ExecutionMode.QUICK,
        scope=LabScope.PROVIDER,
        dependency_hash="same",
    )
    other = replace(
        base,
        submitted_by="Integrator-1",
        submitted_role="INTEGRATOR",
    )
    try:
        first = lab.submit(
            JobSubmission(
                "Architect-1",
                ClientRole.ARCHITECT,
                base,
                PriorityLane.QUICK,
            )
        )
        second = lab.submit(
            JobSubmission(
                "Integrator-1",
                ClientRole.INTEGRATOR,
                other,
                PriorityLane.QUICK,
            )
        )
        assert first.scheduler_job_id == second.scheduler_job_id
        assert set(second.attached_clients) == {"Architect-1", "Integrator-1"}
        assert lab.wait(first.scheduler_job_id, timeout=20).state is SchedulerState.PASS
    finally:
        lab.shutdown()


def test_queue_accepts_32_waiting_jobs_and_cancel_is_isolated(
    tmp_path: Path,
) -> None:
    repo, sha = make_repo(tmp_path)
    lab = scheduler(tmp_path, workers=1, delay=5)
    jobs = []
    try:
        first = lab.submit(
            JobSubmission(
                "Architect-1",
                ClientRole.ARCHITECT,
                request(
                    repo,
                    sha,
                    client="Architect-1",
                    mode=ExecutionMode.QUICK,
                    scope=LabScope.FULL_STACK,
                    dependency_hash="running",
                ),
                PriorityLane.QUICK,
            )
        )
        wait_for_running(lab, 1)
        jobs.append(first)
        for index in range(32):
            client = f"Queued-{index:02d}"
            jobs.append(
                lab.submit(
                    JobSubmission(
                        client,
                        ClientRole.ARCHITECT,
                        request(
                            repo,
                            sha,
                            client=client,
                            mode=ExecutionMode.QUICK,
                            scope=LabScope.FULL_STACK,
                            dependency_hash=f"queued-{index}",
                        ),
                        PriorityLane.NORMAL,
                    )
                )
            )
        assert lab.status()["queued_jobs"] == 32
        with pytest.raises(RuntimeError, match="queue capacity"):
            lab.submit(
                JobSubmission(
                    "Overflow",
                    ClientRole.ARCHITECT,
                    request(
                        repo,
                        sha,
                        client="Overflow",
                        mode=ExecutionMode.QUICK,
                        scope=LabScope.FULL_STACK,
                        dependency_hash="overflow",
                    ),
                    PriorityLane.NORMAL,
                )
            )
        for job in jobs:
            lab.cancel(job.scheduler_job_id)
        assert lab.wait(first.scheduler_job_id, timeout=10).state is SchedulerState.CANCELLED
    finally:
        lab.shutdown()


def test_granular_lock_does_not_block_unrelated_quick_job(tmp_path: Path) -> None:
    repo, sha = make_repo(tmp_path)
    lab = scheduler(tmp_path, workers=2, delay=0.5)
    try:
        locked_one = lab.submit(
            JobSubmission(
                "Integrator-3",
                ClientRole.INTEGRATOR,
                request(
                    repo,
                    sha,
                    client="Integrator-3",
                    mode=ExecutionMode.QUICK,
                    scope=LabScope.FULL_STACK,
                    dependency_hash="lock-a",
                ),
                PriorityLane.CERTIFICATION,
                ("certification-environment",),
            )
        )
        wait_for_running(lab, 1)
        locked_two = lab.submit(
            JobSubmission(
                "Integrator-2",
                ClientRole.INTEGRATOR,
                request(
                    repo,
                    sha,
                    client="Integrator-2",
                    mode=ExecutionMode.QUICK,
                    scope=LabScope.FULL_STACK,
                    dependency_hash="lock-b",
                ),
                PriorityLane.CERTIFICATION,
                ("certification-environment",),
            )
        )
        unrelated = lab.submit(
            JobSubmission(
                "Architect-1",
                ClientRole.ARCHITECT,
                request(
                    repo,
                    sha,
                    client="Architect-1",
                    mode=ExecutionMode.QUICK,
                    scope=LabScope.FULL_STACK,
                    dependency_hash="no-lock",
                ),
                PriorityLane.QUICK,
            )
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            states = {
                item.scheduler_job_id: item.state
                for item in (locked_one, locked_two, unrelated)
            }
            if states[unrelated.scheduler_job_id] is SchedulerState.RUNNING:
                break
            time.sleep(0.02)
        assert unrelated.state in {SchedulerState.RUNNING, SchedulerState.PASS}
        assert locked_two.state is SchedulerState.QUEUED
        assert lab.wait(unrelated.scheduler_job_id, timeout=10).state is SchedulerState.PASS
        assert lab.wait(locked_one.scheduler_job_id, timeout=10).state is SchedulerState.PASS
        assert lab.wait(locked_two.scheduler_job_id, timeout=10).state is SchedulerState.PASS
    finally:
        lab.shutdown()
