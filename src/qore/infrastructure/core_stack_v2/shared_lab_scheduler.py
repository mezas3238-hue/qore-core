"""Central multiuser scheduler for QORE Shared Lab native execution."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_cancel import CancellationToken
from qore.infrastructure.core_stack_v2.shared_lab_manifest import LAB_VERSION
from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    RunRequest,
    RunSummary,
)
from qore.infrastructure.core_stack_v2.shared_lab_orchestrator import NativeLabOrchestrator
from qore.infrastructure.core_stack_v2.shared_lab_repo_runtime import RepositoryRuntime
from qore.infrastructure.core_stack_v2.shared_lab_store import atomic_write_json


class ClientRole(StrEnum):
    ARCHITECT = "ARCHITECT"
    INTEGRATOR = "INTEGRATOR"


class PriorityLane(IntEnum):
    QUICK = 0
    CERTIFICATION = 1
    NORMAL = 2
    DEEP = 3


class SchedulerState(StrEnum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"


_TERMINAL = {
    SchedulerState.PASS,
    SchedulerState.FAIL,
    SchedulerState.BLOCKED,
    SchedulerState.CANCELLED,
    SchedulerState.TIMEOUT,
    SchedulerState.INVALID_EVIDENCE,
}


@dataclass(frozen=True, slots=True)
class JobSubmission:
    submitted_by: str
    role: ClientRole
    request: RunRequest
    priority: PriorityLane
    exclusive_locks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.submitted_by.strip():
            raise ValueError("submitted_by is required")


@dataclass(slots=True)
class ScheduledJob:
    scheduler_job_id: str
    job_key: str
    submission: JobSubmission
    state: SchedulerState
    sequence: int
    queue_entered_ns: int
    attached_clients: list[str] = field(default_factory=list)
    worker_slot: str | None = None
    run_id: str | None = None
    started_at_ns: int | None = None
    ended_at_ns: int | None = None
    failure_reason: str | None = None
    evidence_path: str | None = None
    artifact_hash: str | None = None
    deduplicated_to: str | None = None

    def to_dict(self, queue_position: int | None = None) -> dict[str, Any]:
        return {
            "scheduler_job_id": self.scheduler_job_id,
            "job_key": self.job_key,
            "submitted_by": self.submission.submitted_by,
            "role": self.submission.role.value,
            "sha": self.submission.request.commit_sha,
            "scope": self.submission.request.scope.value,
            "mode": self.submission.request.mode.value,
            "priority": self.submission.priority.name,
            "state": self.state.value,
            "queue_position": queue_position,
            "worker": self.worker_slot,
            "run_id": self.run_id,
            "start_time_ns": self.started_at_ns,
            "end_time_ns": self.ended_at_ns,
            "attached_clients": tuple(sorted(set(self.attached_clients))),
            "failure_reason": self.failure_reason,
            "evidence_path": self.evidence_path,
            "artifact_hash": self.artifact_hash,
            "exclusive_locks": self.submission.exclusive_locks,
        }


class LockManager:
    def __init__(self) -> None:
        self._owners: dict[str, str] = {}

    def can_acquire(self, job_id: str, locks: tuple[str, ...]) -> bool:
        return all(
            resource not in self._owners or self._owners[resource] == job_id
            for resource in locks
        )

    def acquire(self, job_id: str, locks: tuple[str, ...]) -> bool:
        if not self.can_acquire(job_id, locks):
            return False
        for resource in locks:
            self._owners[resource] = job_id
        return True

    def release(self, job_id: str) -> None:
        for resource, owner in tuple(self._owners.items()):
            if owner == job_id:
                del self._owners[resource]


class SharedLabScheduler:
    def __init__(
        self,
        *,
        state_dir: Path,
        worker_capacity: int = 4,
        max_worker_capacity: int = 20,
        max_queued_jobs: int = 32,
    ) -> None:
        if worker_capacity <= 0 or worker_capacity > max_worker_capacity:
            raise ValueError("invalid worker capacity")
        if max_queued_jobs < 32:
            raise ValueError("scheduler must support at least 32 queued jobs")
        self.state_dir = state_dir.resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.worker_capacity = worker_capacity
        self.max_worker_capacity = max_worker_capacity
        self.max_queued_jobs = max_queued_jobs
        self.orchestrator = NativeLabOrchestrator(state_dir=self.state_dir)
        self._executor = ThreadPoolExecutor(
            max_workers=max_worker_capacity,
            thread_name_prefix="shared-lab-run",
        )
        self._condition = threading.Condition()
        self._jobs: dict[str, ScheduledJob] = {}
        self._active_by_key: dict[str, str] = {}
        self._futures: dict[str, Future[RunSummary]] = {}
        self._tokens: dict[str, CancellationToken] = {}
        self._locks = LockManager()
        self._sequence = 0
        self._last_dispatched_by_client: dict[str, int] = {}
        self._stopping = False
        self._dispatcher = threading.Thread(
            target=self._dispatch_loop,
            name="shared-lab-scheduler",
            daemon=True,
        )
        self._dispatcher.start()

    def submit(self, submission: JobSubmission) -> ScheduledJob:
        normalized, job_key = self._normalize_submission(submission)
        with self._condition:
            existing_id = self._active_by_key.get(job_key)
            if existing_id is not None:
                existing = self._jobs[existing_id]
                if existing.state not in _TERMINAL:
                    existing.attached_clients.append(normalized.submitted_by)
                    self._persist_locked()
                    return existing
            queued_count = sum(
                job.state is SchedulerState.QUEUED for job in self._jobs.values()
            )
            if queued_count >= self.max_queued_jobs:
                raise RuntimeError("scheduler queue capacity exhausted")
            self._sequence += 1
            job_id = f"JOB-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
            locks = normalized.exclusive_locks
            if (
                normalized.request.mode is ExecutionMode.CERTIFICATION
                and "certification-environment" not in locks
            ):
                locks = (*locks, "certification-environment")
                normalized = replace(normalized, exclusive_locks=locks)
            job = ScheduledJob(
                scheduler_job_id=job_id,
                job_key=job_key,
                submission=normalized,
                state=SchedulerState.QUEUED,
                sequence=self._sequence,
                queue_entered_ns=time.time_ns(),
                attached_clients=[normalized.submitted_by],
            )
            self._jobs[job_id] = job
            self._active_by_key[job_key] = job_id
            self._tokens[job_id] = CancellationToken()
            self._persist_locked()
            self._condition.notify_all()
            return job

    def cancel(self, job_id: str) -> ScheduledJob:
        with self._condition:
            job = self._jobs[job_id]
            if job.state in _TERMINAL:
                return job
            token = self._tokens[job_id]
            token.cancel()
            if job.state is SchedulerState.QUEUED:
                job.state = SchedulerState.CANCELLED
                job.ended_at_ns = time.time_ns()
                self._active_by_key.pop(job.job_key, None)
            self._persist_locked()
            self._condition.notify_all()
            return job

    def status(self, job_id: str | None = None) -> dict[str, Any]:
        with self._condition:
            queue = self._queue_order_locked()
            positions = {
                queued_id: index + 1 for index, queued_id in enumerate(queue)
            }
            if job_id is not None:
                job = self._jobs[job_id]
                return job.to_dict(positions.get(job_id))
            return {
                "worker_capacity": self.worker_capacity,
                "max_worker_capacity": self.max_worker_capacity,
                "running_jobs": sum(
                    job.state in {SchedulerState.PREPARING, SchedulerState.RUNNING}
                    for job in self._jobs.values()
                ),
                "queued_jobs": len(queue),
                "jobs": [
                    self._jobs[current_id].to_dict(positions.get(current_id))
                    for current_id in sorted(
                        self._jobs,
                        key=lambda item: self._jobs[item].sequence,
                    )
                ],
            }

    def resize_workers(self, worker_capacity: int) -> None:
        if not 1 <= worker_capacity <= self.max_worker_capacity:
            raise ValueError("worker capacity outside configured bounds")
        with self._condition:
            self.worker_capacity = worker_capacity
            self._persist_locked()
            self._condition.notify_all()

    def wait(self, job_id: str, timeout: float | None = None) -> ScheduledJob:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while self._jobs[job_id].state not in _TERMINAL:
                remaining = (
                    None if deadline is None else deadline - time.monotonic()
                )
                if remaining is not None and remaining <= 0:
                    raise TimeoutError(f"scheduler wait timed out for {job_id}")
                self._condition.wait(timeout=remaining)
            return self._jobs[job_id]

    def shutdown(self, wait: bool = True) -> None:
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        if wait:
            self._dispatcher.join(timeout=10)
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _normalize_submission(
        self,
        submission: JobSubmission,
    ) -> tuple[JobSubmission, str]:
        runtime = RepositoryRuntime(Path(submission.request.repo_path))
        snapshot = runtime.resolve(
            repository=submission.request.repository,
            commit_sha=submission.request.commit_sha,
            branch=submission.request.branch,
        )
        dataset = self.orchestrator.dataset_store.resolve(
            submission.request.dataset_id,
            submission.request.dataset_version,
        )
        request = replace(
            submission.request,
            commit_sha=snapshot.commit_sha,
            submitted_by=submission.submitted_by,
            submitted_role=submission.role.value,
            exclusive_locks=submission.exclusive_locks,
        )
        dependency_hash = hashlib.sha256(
            json.dumps(
                sorted(request.dependency_hashes),
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        payload = {
            "commit_sha": snapshot.commit_sha,
            "scope": request.scope.value,
            "dataset_hash": dataset.content_hash,
            "config_hash": request.configuration_hash(),
            "dependency_hash": dependency_hash,
            "lab_version": LAB_VERSION,
        }
        job_key = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return replace(submission, request=request), job_key

    def _dispatch_loop(self) -> None:
        while True:
            with self._condition:
                if self._stopping:
                    return
                self._collect_finished_locked()
                running = sum(
                    job.state in {SchedulerState.PREPARING, SchedulerState.RUNNING}
                    for job in self._jobs.values()
                )
                available = self.worker_capacity - running
                dispatched = False
                while available > 0:
                    job = self._next_job_locked()
                    if job is None:
                        break
                    if not self._locks.acquire(
                        job.scheduler_job_id,
                        job.submission.exclusive_locks,
                    ):
                        break
                    job.state = SchedulerState.PREPARING
                    job.worker_slot = f"POOL-{running + 1:02d}"
                    job.started_at_ns = time.time_ns()
                    self._last_dispatched_by_client[
                        job.submission.submitted_by
                    ] = job.sequence
                    token = self._tokens[job.scheduler_job_id]
                    future = self._executor.submit(
                        self._run_job,
                        job.scheduler_job_id,
                        job.submission.request,
                        token,
                    )
                    self._futures[job.scheduler_job_id] = future
                    running += 1
                    available -= 1
                    dispatched = True
                if dispatched:
                    self._persist_locked()
                self._condition.wait(timeout=0.05)

    def _next_job_locked(self) -> ScheduledJob | None:
        candidates = [
            job
            for job in self._jobs.values()
            if job.state is SchedulerState.QUEUED
            and self._locks.can_acquire(
                job.scheduler_job_id,
                job.submission.exclusive_locks,
            )
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda job: (
                int(job.submission.priority),
                self._last_dispatched_by_client.get(
                    job.submission.submitted_by,
                    -1,
                ),
                job.sequence,
            ),
        )

    def _queue_order_locked(self) -> list[str]:
        queued = [
            job
            for job in self._jobs.values()
            if job.state is SchedulerState.QUEUED
        ]
        queued.sort(
            key=lambda job: (
                int(job.submission.priority),
                self._last_dispatched_by_client.get(
                    job.submission.submitted_by,
                    -1,
                ),
                job.sequence,
            )
        )
        return [job.scheduler_job_id for job in queued]

    def _run_job(
        self,
        job_id: str,
        request: RunRequest,
        token: CancellationToken,
    ) -> RunSummary:
        with self._condition:
            job = self._jobs[job_id]
            if token.cancelled:
                raise RuntimeError("job cancelled before execution")
            job.state = SchedulerState.RUNNING
            self._persist_locked()
            self._condition.notify_all()
        return self.orchestrator.run(request, cancellation_token=token)

    def _collect_finished_locked(self) -> None:
        for job_id, future in tuple(self._futures.items()):
            if not future.done():
                continue
            job = self._jobs[job_id]
            try:
                summary = future.result()
                job.run_id = summary.identity.run_id
                job.evidence_path = summary.evidence_path
                job.artifact_hash = summary.artifact_hash
                mapping = {
                    "PASS": SchedulerState.PASS,
                    "FAIL": SchedulerState.FAIL,
                    "INCOMPLETE": SchedulerState.BLOCKED,
                    "DEPENDENCY_BLOCKED": SchedulerState.BLOCKED,
                    "INVALID_EVIDENCE": SchedulerState.INVALID_EVIDENCE,
                    "TIMEOUT": SchedulerState.TIMEOUT,
                    "CANCELLED": SchedulerState.CANCELLED,
                }
                job.state = mapping[summary.disposition.value]
            except Exception as exc:
                if self._tokens[job_id].cancelled:
                    job.state = SchedulerState.CANCELLED
                else:
                    job.state = SchedulerState.FAIL
                job.failure_reason = str(exc)
            job.ended_at_ns = time.time_ns()
            self._locks.release(job_id)
            self._active_by_key.pop(job.job_key, None)
            del self._futures[job_id]
            self._persist_locked()
            self._condition.notify_all()

    def _persist_locked(self) -> None:
        atomic_write_json(
            self.state_dir / "scheduler" / "state.json",
            self.status_snapshot_locked(),
        )

    def status_snapshot_locked(self) -> dict[str, Any]:
        queue = self._queue_order_locked()
        positions = {job_id: index + 1 for index, job_id in enumerate(queue)}
        return {
            "worker_capacity": self.worker_capacity,
            "max_worker_capacity": self.max_worker_capacity,
            "max_queued_jobs": self.max_queued_jobs,
            "jobs": {
                job_id: job.to_dict(positions.get(job_id))
                for job_id, job in self._jobs.items()
            },
        }
