"""Native DAG orchestrator for autonomous QORE Shared Lab execution."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_cancel import CancellationToken
from qore.infrastructure.core_stack_v2.shared_lab_manifest import LAB_VERSION
from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    CacheKey,
    DatasetIdentity,
    RunDisposition,
    RunIdentity,
    RunRequest,
    RunSummary,
    TaskResult,
    TaskSpec,
    TaskState,
)
from qore.infrastructure.core_stack_v2.shared_lab_repo_runtime import RepositoryRuntime
from qore.infrastructure.core_stack_v2.shared_lab_store import (
    CacheStore,
    DatasetStore,
    EvidenceStore,
    canonical_json,
    sha256_bytes,
)
from qore.infrastructure.core_stack_v2.shared_lab_suite_registry import (
    NativeSuiteRegistry,
    default_native_suite_registry,
)


def _component_hash(worktree: Path, patterns: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    matched: dict[str, Path] = {}
    for pattern in patterns:
        for path in worktree.glob(pattern):
            if path.is_file():
                matched[str(path.relative_to(worktree))] = path
    if not matched:
        raise ValueError(f"component hash matched no files for {patterns!r}")
    for relative, path in sorted(matched.items()):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _dependency_hash(
    task: TaskSpec,
    completed: dict[str, TaskResult],
) -> str:
    payload = [
        {
            "task_id": dep,
            "artifact_hash": completed[dep].artifact_hash,
            "cache_key": completed[dep].cache_key,
        }
        for dep in sorted(task.dependencies)
    ]
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


def _pytest_counts(stdout: str, returncode: int) -> tuple[int, int, int]:
    passed = sum(int(value) for value in re.findall(r"(\d+) passed", stdout))
    failed = sum(int(value) for value in re.findall(r"(\d+) failed", stdout))
    total = passed + failed
    if total == 0:
        total = 1
        passed = 1 if returncode == 0 else 0
        failed = 0 if returncode == 0 else 1
    return total, passed, failed


def _request_payload(request: RunRequest) -> dict[str, Any]:
    return {
        "repository": request.repository,
        "repo_path": request.repo_path,
        "commit_sha": request.commit_sha,
        "branch": request.branch,
        "dataset_id": request.dataset_id,
        "dataset_version": request.dataset_version,
        "mode": request.mode.value,
        "scope": request.scope.value,
        "workers": request.workers,
        "policy": asdict(request.policy),
        "base_sha": request.base_sha,
        "changed_paths": request.changed_paths,
        "scenario": request.scenario,
        "use_cache": request.use_cache,
        "reproduces_run_id": request.reproduces_run_id,
        "submitted_by": request.submitted_by,
        "submitted_role": request.submitted_role,
        "dependency_hashes": request.dependency_hashes,
        "exclusive_locks": request.exclusive_locks,
    }


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ("git", "-C", str(root), "rev-parse", "HEAD"),
        check=True,
        capture_output=True,
        text=True,
    )
    sha = completed.stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise RuntimeError("Shared Lab harness HEAD is not an exact commit SHA")
    dirty = subprocess.run(
        (
            "git",
            "-C",
            str(root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ),
        check=True,
        capture_output=True,
        text=True,
    )
    if dirty.stdout.strip():
        raise RuntimeError(
            "Shared Lab harness has tracked working-tree mutations; "
            "provenance is ambiguous"
        )
    return sha


def _apply_windows_limits(
    process: subprocess.Popen[str],
    *,
    memory_limit_mb: int,
    cpu_limit_seconds: int,
) -> bool:
    try:
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = (
            wintypes.HANDLE,
            wintypes.HANDLE,
        )
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.PerProcessUserTimeLimit = (
            int(cpu_limit_seconds) * 10_000_000
        )
        info.BasicLimitInformation.LimitFlags = (
            0x00000002  # JOB_OBJECT_LIMIT_PROCESS_TIME
            | 0x00000100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        info.ProcessMemoryLimit = int(memory_limit_mb) * 1024 * 1024
        if not kernel32.SetInformationJobObject(
            job,
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            kernel32.CloseHandle(job)
            return False
        process_handle = wintypes.HANDLE(int(getattr(process, "_handle")))
        if not kernel32.AssignProcessToJobObject(job, process_handle):
            kernel32.CloseHandle(job)
            return False
        setattr(process, "_qore_job_handle", job)
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def _release_limits(process: subprocess.Popen[str]) -> None:
    if os.name != "nt":
        return
    job = getattr(process, "_qore_job_handle", None)
    if not job:
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle(job)
    finally:
        setattr(process, "_qore_job_handle", None)


def _apply_limits(
    process: subprocess.Popen[str],
    *,
    memory_limit_mb: int,
    cpu_limit_seconds: int,
) -> bool:
    if os.name == "nt":
        return _apply_windows_limits(
            process,
            memory_limit_mb=memory_limit_mb,
            cpu_limit_seconds=cpu_limit_seconds,
        )
    if os.name != "posix":
        return False
    try:
        import resource

        if not hasattr(resource, "prlimit"):
            return False
        memory_bytes = memory_limit_mb * 1024 * 1024
        resource.prlimit(process.pid, resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.prlimit(
            process.pid,
            resource.RLIMIT_CPU,
            (cpu_limit_seconds, cpu_limit_seconds),
        )
        return True
    except (OSError, ValueError):
        return False


class NativeLabOrchestrator:
    def __init__(
        self,
        *,
        state_dir: Path,
        registry: NativeSuiteRegistry | None = None,
        harness_root: Path | None = None,
    ) -> None:
        self.state_dir = state_dir.resolve()
        self.harness_root = (
            harness_root.resolve()
            if harness_root is not None
            else Path(__file__).resolve().parents[4]
        )
        self.dataset_store = DatasetStore(self.state_dir / "datasets")
        self.cache_store = CacheStore(self.state_dir / "cache")
        self.evidence_store = EvidenceStore(self.state_dir / "evidence")
        self.registry = registry or default_native_suite_registry()
        self.registry.load_plugins(self.state_dir / "plugins")

    def run(
        self,
        request: RunRequest,
        cancellation_token: CancellationToken | None = None,
        run_id: str | None = None,
    ) -> RunSummary:
        started_at_ns = time.time_ns()
        token = cancellation_token or CancellationToken()
        if token.cancelled:
            raise RuntimeError("native lab run cancelled before preparation")
        harness_sha = _git_head(self.harness_root)
        runtime = RepositoryRuntime(Path(request.repo_path))
        snapshot = runtime.resolve(
            repository=request.repository,
            commit_sha=request.commit_sha,
            branch=request.branch,
        )
        dataset = self.dataset_store.resolve(
            request.dataset_id,
            request.dataset_version,
        )
        changed_paths = request.changed_paths
        if request.base_sha and not changed_paths:
            changed_paths = runtime.changed_paths(
                request.base_sha,
                snapshot.commit_sha,
            )
        plan_request = replace(request, commit_sha=snapshot.commit_sha)
        tasks = self.registry.plan(plan_request, changed_paths)
        resolved_run_id = run_id or self._run_id(snapshot.commit_sha)
        identity = RunIdentity(
            run_id=resolved_run_id,
            repository=snapshot.repository,
            commit_sha=snapshot.commit_sha,
            branch=snapshot.branch,
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            dataset_hash=dataset.content_hash,
            configuration_hash=plan_request.configuration_hash(),
            lab_harness_sha=harness_sha,
        )
        run_dir = self.evidence_store.start_run(
            identity=identity,
            request=_request_payload(plan_request),
            environment=self._environment(plan_request, harness_sha),
            started_at_ns=started_at_ns,
        )

        completed: dict[str, TaskResult] = {}
        pending = {task.task_id: task for task in tasks}
        with runtime.worktree(snapshot.commit_sha) as worktree:
            self._execute_dag(
                request=plan_request,
                identity=identity,
                dataset=dataset,
                worktree=worktree,
                run_dir=run_dir,
                pending=pending,
                completed=completed,
                cancellation_token=token,
            )

        disposition = self._final_disposition(tuple(completed.values()))
        ended_at_ns = time.time_ns()
        artifact_hash = sha256_bytes(
            canonical_json(
                {
                    "identity": asdict(identity),
                    "disposition": disposition.value,
                    "tasks": [
                        result.to_dict()
                        for result in sorted(
                            completed.values(),
                            key=lambda item: item.task_id,
                        )
                    ],
                }
            ).encode()
        )
        evidence_path = self.evidence_store.finish_run(
            run_id=identity.run_id,
            disposition=disposition.value,
            ended_at_ns=ended_at_ns,
            artifact_hash=artifact_hash,
        )
        return RunSummary(
            identity=identity,
            disposition=disposition,
            task_results=tuple(
                sorted(completed.values(), key=lambda item: item.task_id)
            ),
            evidence_path=str(evidence_path),
            artifact_hash=artifact_hash,
            started_at_ns=started_at_ns,
            ended_at_ns=ended_at_ns,
        )

    def _execute_dag(
        self,
        *,
        request: RunRequest,
        identity: RunIdentity,
        dataset: DatasetIdentity,
        worktree: Path,
        run_dir: Path,
        pending: dict[str, TaskSpec],
        completed: dict[str, TaskResult],
        cancellation_token: CancellationToken,
    ) -> None:
        worker_index = 0
        with ThreadPoolExecutor(
            max_workers=request.workers,
            thread_name_prefix="shared-lab-worker",
        ) as executor:
            while pending:
                if cancellation_token.cancelled:
                    now = time.time_ns()
                    for task in tuple(pending.values()):
                        result = self._cancelled_result(task, now)
                        completed[task.task_id] = result
                        self.evidence_store.write_task_result(identity.run_id, result)
                        del pending[task.task_id]
                    break
                progress = False
                blocked = [
                    task
                    for task in pending.values()
                    if all(dep in completed for dep in task.dependencies)
                    and any(not completed[dep].passed for dep in task.dependencies)
                ]
                for task in blocked:
                    worker_index += 1
                    result = self._blocked_result(
                        task,
                        worker_id=f"W{worker_index:02d}",
                        completed=completed,
                    )
                    completed[task.task_id] = result
                    self.evidence_store.write_task_result(identity.run_id, result)
                    del pending[task.task_id]
                    progress = True

                ready = [
                    task
                    for task in pending.values()
                    if all(dep in completed for dep in task.dependencies)
                ]
                futures: dict[Future[TaskResult], tuple[TaskSpec, str]] = {}
                for task in ready:
                    worker_index += 1
                    worker_id = f"W{((worker_index - 1) % request.workers) + 1:02d}"
                    self.evidence_store.update_task(
                        identity.run_id,
                        task.task_id,
                        {
                            "task_id": task.task_id,
                            "suite": task.suite.value,
                            "scope": task.scope.value,
                            "state": TaskState.RUNNING.value,
                            "worker_id": worker_id,
                            "started_at_ns": time.time_ns(),
                        },
                    )
                    future = executor.submit(
                        self._execute_task,
                        request,
                        identity,
                        dataset,
                        worktree,
                        run_dir,
                        task,
                        worker_id,
                        completed.copy(),
                        cancellation_token,
                    )
                    futures[future] = (task, worker_id)
                    del pending[task.task_id]
                    progress = True
                for future in as_completed(futures):
                    task, worker_id = futures[future]
                    task_id = task.task_id
                    try:
                        result = future.result()
                    except Exception as exc:
                        now = time.time_ns()
                        result = TaskResult(
                            task_id=task.task_id,
                            suite=task.suite,
                            scope=task.scope,
                            state=TaskState.INCOMPLETE,
                            worker_id=worker_id,
                            started_at_ns=now,
                            ended_at_ns=now,
                            duration_ms=0.0,
                            attempts=1,
                            cache_hit=False,
                            tests_total=1,
                            tests_passed=0,
                            tests_failed=1,
                            stdout_path="",
                            stderr_path="",
                            artifact_hash=sha256_bytes(str(exc).encode()),
                            failure_reason=f"worker exception: {exc}",
                            resource_limits_applied=False,
                            cache_key="",
                        )
                    completed[task_id] = result
                    self.evidence_store.write_task_result(identity.run_id, result)
                if not progress:
                    unresolved = ", ".join(sorted(pending))
                    raise RuntimeError(f"DAG contains unresolved dependencies: {unresolved}")

    def _execute_task(
        self,
        request: RunRequest,
        identity: RunIdentity,
        dataset: DatasetIdentity,
        worktree: Path,
        run_dir: Path,
        task: TaskSpec,
        worker_id: str,
        completed: dict[str, TaskResult],
        cancellation_token: CancellationToken,
    ) -> TaskResult:
        started = time.time_ns()
        raw_component_hash = _component_hash(
            worktree,
            task.component_globs,
        )
        component_hash = hashlib.sha256(
            canonical_json(
                {
                    "content_hash": raw_component_hash,
                    "task_id": task.task_id,
                    "suite": task.suite.value,
                    "scope": task.scope.value,
                }
            ).encode()
        ).hexdigest()
        dependency_hash = _dependency_hash(task, completed)
        key = CacheKey(
            code_hash=identity.commit_sha,
            component_hash=component_hash,
            dependency_hash=dependency_hash,
            dataset_hash=dataset.content_hash,
            configuration_hash=identity.configuration_hash,
            lab_version=identity.lab_version,
        )
        key_fp = key.fingerprint()
        if request.use_cache:
            cached = self.cache_store.get(key)
            if cached is not None:
                ended = time.time_ns()
                return replace(
                    cached,
                    worker_id=worker_id,
                    started_at_ns=started,
                    ended_at_ns=ended,
                    duration_ms=(ended - started) / 1_000_000,
                    attempts=0,
                    cache_hit=True,
                    cache_key=key_fp,
                )

        task_dir = run_dir / "tasks" / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        command = self._format_command(task.command, request, dataset)
        environment = os.environ.copy()
        existing_pythonpath = environment.get("PYTHONPATH")
        target_pythonpath = str(worktree / "src")
        environment["PYTHONPATH"] = (
            target_pythonpath
            if not existing_pythonpath
            else f"{target_pythonpath}{os.pathsep}{existing_pythonpath}"
        )
        environment.update(
            {
                "QORE_SHARED_LAB_RUN_ID": identity.run_id,
                "QORE_SHARED_LAB_COMMIT_SHA": identity.commit_sha,
                "QORE_SHARED_LAB_DATASET_HASH": dataset.content_hash,
                "QORE_SHARED_LAB_VERSION": LAB_VERSION,
                "QORE_SHARED_LAB_SUBMITTED_BY": request.submitted_by,
                "QORE_SHARED_LAB_SUBMITTED_ROLE": request.submitted_role,
            }
        )

        attempts = 0
        final_stdout = ""
        final_stderr = ""
        state = TaskState.FAIL
        reason: str | None = None
        limits_applied = False
        returncode = 1
        while attempts <= task.retries:
            if cancellation_token.cancelled:
                state = TaskState.CANCELLED
                reason = "cancelled before process start"
                break
            attempts += 1
            process = subprocess.Popen(
                command,
                cwd=worktree,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            limits_applied = _apply_limits(
                process,
                memory_limit_mb=request.policy.memory_limit_mb,
                cpu_limit_seconds=request.policy.cpu_limit_seconds,
            )
            if not limits_applied:
                process.kill()
                process.communicate()
                state = TaskState.INCOMPLETE
                reason = "resource limits could not be applied; fail-closed"
                break
            deadline = time.monotonic() + task.timeout_seconds
            while True:
                if cancellation_token.cancelled:
                    process.kill()
                    out, err = process.communicate()
                    final_stdout += out
                    final_stderr += err
                    returncode = process.returncode
                    state = TaskState.CANCELLED
                    reason = "cancelled by scheduler"
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    process.kill()
                    out, err = process.communicate()
                    final_stdout += out
                    final_stderr += err
                    returncode = process.returncode
                    state = TaskState.TIMEOUT
                    reason = f"timeout after {task.timeout_seconds}s"
                    break
                try:
                    final_stdout, final_stderr = process.communicate(
                        timeout=min(0.1, remaining)
                    )
                    returncode = process.returncode
                    break
                except subprocess.TimeoutExpired:
                    continue
            if state is TaskState.CANCELLED:
                break
            if state is TaskState.TIMEOUT:
                if attempts <= task.retries:
                    state = TaskState.FAIL
                    reason = None
                    continue
                break
            if returncode == 0:
                state = TaskState.PASS
                reason = None
                break
            state = TaskState.FAIL
            reason = f"command exited with code {returncode}"
            if attempts <= task.retries:
                continue

        stdout_path = task_dir / "stdout.txt"
        stderr_path = task_dir / "stderr.txt"
        stdout_path.write_text(final_stdout)
        stderr_path.write_text(final_stderr)
        tests_total, tests_passed, tests_failed = _pytest_counts(
            final_stdout,
            returncode,
        )
        ended = time.time_ns()
        result_payload = {
            "task_id": task.task_id,
            "command": command,
            "stdout_hash": sha256_bytes(final_stdout.encode()),
            "stderr_hash": sha256_bytes(final_stderr.encode()),
            "state": state.value,
            "returncode": returncode,
            "cache_key": key_fp,
        }
        artifact_hash = sha256_bytes(canonical_json(result_payload).encode())
        result = TaskResult(
            task_id=task.task_id,
            suite=task.suite,
            scope=task.scope,
            state=state,
            worker_id=worker_id,
            started_at_ns=started,
            ended_at_ns=ended,
            duration_ms=(ended - started) / 1_000_000,
            attempts=attempts,
            cache_hit=False,
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            artifact_hash=artifact_hash,
            failure_reason=reason,
            resource_limits_applied=limits_applied,
            cache_key=key_fp,
        )
        self.cache_store.put(key, result)
        return result

    @staticmethod
    def _format_command(
        command: tuple[str, ...],
        request: RunRequest,
        dataset: DatasetIdentity,
    ) -> tuple[str, ...]:
        scenario = request.scenario or "global-exam"
        replacements = {
            "{scenario}": scenario,
            "{dataset_path}": dataset.payload_path,
            "{python}": sys.executable,
        }
        return tuple(replacements.get(item, item) for item in command)

    @staticmethod
    def _blocked_result(
        task: TaskSpec,
        *,
        worker_id: str,
        completed: dict[str, TaskResult],
    ) -> TaskResult:
        now = time.time_ns()
        failed_dependencies = [
            dep for dep in task.dependencies if not completed[dep].passed
        ]
        reason = "blocked by dependencies: " + ",".join(sorted(failed_dependencies))
        return TaskResult(
            task_id=task.task_id,
            suite=task.suite,
            scope=task.scope,
            state=TaskState.DEPENDENCY_BLOCKED,
            worker_id=worker_id,
            started_at_ns=now,
            ended_at_ns=now,
            duration_ms=0.0,
            attempts=0,
            cache_hit=False,
            tests_total=0,
            tests_passed=0,
            tests_failed=0,
            stdout_path="",
            stderr_path="",
            artifact_hash=sha256_bytes(reason.encode()),
            failure_reason=reason,
            resource_limits_applied=False,
            cache_key="",
        )

    @staticmethod
    def _cancelled_result(task: TaskSpec, now: int) -> TaskResult:
        reason = "cancelled before task execution"
        return TaskResult(
            task_id=task.task_id,
            suite=task.suite,
            scope=task.scope,
            state=TaskState.CANCELLED,
            worker_id="CANCELLED",
            started_at_ns=now,
            ended_at_ns=now,
            duration_ms=0.0,
            attempts=0,
            cache_hit=False,
            tests_total=0,
            tests_passed=0,
            tests_failed=0,
            stdout_path="",
            stderr_path="",
            artifact_hash=sha256_bytes(reason.encode()),
            failure_reason=reason,
            resource_limits_applied=False,
            cache_key="",
        )

    @staticmethod
    def _final_disposition(
        results: tuple[TaskResult, ...],
    ) -> RunDisposition:
        states = {result.state for result in results}
        if not results:
            return RunDisposition.INVALID_EVIDENCE
        if TaskState.INVALID_EVIDENCE in states:
            return RunDisposition.INVALID_EVIDENCE
        if TaskState.CANCELLED in states:
            return RunDisposition.CANCELLED
        if TaskState.TIMEOUT in states:
            return RunDisposition.TIMEOUT
        if TaskState.FAIL in states:
            return RunDisposition.FAIL
        if TaskState.INCOMPLETE in states:
            return RunDisposition.INCOMPLETE
        if TaskState.DEPENDENCY_BLOCKED in states:
            return RunDisposition.DEPENDENCY_BLOCKED
        return RunDisposition.PASS

    @staticmethod
    def _run_id(commit_sha: str) -> str:
        return f"SL-{time.time_ns()}-{commit_sha[:8]}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _environment(
        request: RunRequest,
        harness_sha: str,
    ) -> dict[str, Any]:
        return {
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "lab_version": LAB_VERSION,
            "lab_harness_sha": harness_sha,
            "target_sha": request.commit_sha,
            "submitted_by": request.submitted_by,
            "submitted_role": request.submitted_role,
            "execution_engine": "QORE_SHARED_LAB_NATIVE",
            "github_actions_detected": os.environ.get("GITHUB_ACTIONS") == "true",
            "github_actions_required": False,
        }
