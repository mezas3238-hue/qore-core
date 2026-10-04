"""Native execution model for the autonomous QORE Shared Lab."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_manifest import LAB_VERSION


class RunDisposition(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class TaskState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"
    DEPENDENCY_BLOCKED = "DEPENDENCY_BLOCKED"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class ExecutionMode(StrEnum):
    QUICK = "QUICK"
    COMPONENT = "COMPONENT"
    INTEGRATION = "INTEGRATION"
    REPLAY = "REPLAY"
    REGRESSION = "REGRESSION"
    DEEP = "DEEP"
    FULL = "FULL"
    CERTIFICATION = "CERTIFICATION"


class LabScope(StrEnum):
    DATA = "data"
    SENSOR = "sensor"
    IDENTITY = "identity"
    TEMPORAL = "temporal"
    PROVIDER = "provider"
    COGNITION = "cognition"
    DECISION = "decision"
    MC18 = "mc18"
    MC23 = "mc23"
    FULL_STACK = "full-stack"


class ValidationSuite(StrEnum):
    UNIT = "UNIT"
    CONTRACT = "CONTRACT"
    INTEGRATION = "INTEGRATION"
    FUNCTIONAL = "FUNCTIONAL"
    END_TO_END = "END_TO_END"
    DATA_REALITY = "DATA_REALITY"
    SENSOR_REALITY = "SENSOR_REALITY"
    IDENTITY_REALITY = "IDENTITY_REALITY"
    TEMPORAL_REALITY = "TEMPORAL_REALITY"
    PROVIDER_REALITY = "PROVIDER_REALITY"
    REPLAY = "REPLAY"
    CAUSALITY = "CAUSALITY"
    CONSUMER_VALIDATION = "CONSUMER_VALIDATION"
    REGRESSION = "REGRESSION"
    STRESS = "STRESS"
    MONTE_CARLO = "MONTE_CARLO"
    PERFORMANCE = "PERFORMANCE"
    DETERMINISM = "DETERMINISM"
    FAILURE_INJECTION = "FAILURE_INJECTION"
    FULL_STACK = "FULL_STACK"
    CERTIFICATION = "CERTIFICATION"


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    timeout_seconds: int = 300
    retries: int = 0
    memory_limit_mb: int = 2048
    cpu_limit_seconds: int = 300

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.retries < 0:
            raise ValueError("retries cannot be negative")
        if self.memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive")
        if self.cpu_limit_seconds <= 0:
            raise ValueError("cpu_limit_seconds must be positive")


@dataclass(frozen=True, slots=True)
class RunRequest:
    repository: str
    repo_path: str
    commit_sha: str
    branch: str
    dataset_id: str
    dataset_version: str
    mode: ExecutionMode
    scope: LabScope
    workers: int = 4
    policy: ResourcePolicy = field(default_factory=ResourcePolicy)
    base_sha: str | None = None
    changed_paths: tuple[str, ...] = ()
    scenario: str | None = None
    use_cache: bool = True
    reproduces_run_id: str | None = None
    submitted_by: str = "local-user"
    submitted_role: str = "ARCHITECT"
    dependency_hashes: tuple[str, ...] = ()
    exclusive_locks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (
            self.repository,
            self.repo_path,
            self.commit_sha,
            self.branch,
            self.dataset_id,
            self.dataset_version,
            self.submitted_by,
            self.submitted_role,
        ):
            if not value.strip():
                raise ValueError("run request identity fields must be non-empty")
        if self.workers <= 0:
            raise ValueError("workers must be positive")

    def configuration_hash(self) -> str:
        payload = {
            "mode": self.mode.value,
            "scope": self.scope.value,
            "workers": self.workers,
            "policy": asdict(self.policy),
            "base_sha": self.base_sha,
            "changed_paths": self.changed_paths,
            "scenario": self.scenario,
            "dependency_hashes": self.dependency_hashes,
            "lab_version": LAB_VERSION,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class DatasetIdentity:
    dataset_id: str
    version: str
    content_hash: str
    payload_path: str

    def __post_init__(self) -> None:
        if len(self.content_hash) != 64:
            raise ValueError("dataset content hash must be sha256")


@dataclass(frozen=True, slots=True)
class RunIdentity:
    run_id: str
    repository: str
    commit_sha: str
    branch: str
    dataset_id: str
    dataset_version: str
    dataset_hash: str
    configuration_hash: str
    lab_version: str = LAB_VERSION


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    suite: ValidationSuite
    scope: LabScope
    dependencies: tuple[str, ...]
    command: tuple[str, ...]
    component_globs: tuple[str, ...]
    timeout_seconds: int
    retries: int

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.command:
            raise ValueError("task spec requires id and command")


@dataclass(frozen=True, slots=True)
class CacheKey:
    code_hash: str
    component_hash: str
    dependency_hash: str
    dataset_hash: str
    configuration_hash: str
    lab_version: str

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class TaskResult:
    task_id: str
    suite: ValidationSuite
    scope: LabScope
    state: TaskState
    worker_id: str
    started_at_ns: int
    ended_at_ns: int
    duration_ms: float
    attempts: int
    cache_hit: bool
    tests_total: int
    tests_passed: int
    tests_failed: int
    stdout_path: str
    stderr_path: str
    artifact_hash: str
    failure_reason: str | None
    resource_limits_applied: bool
    cache_key: str

    @property
    def passed(self) -> bool:
        return self.state is TaskState.PASS

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["suite"] = self.suite.value
        payload["scope"] = self.scope.value
        payload["state"] = self.state.value
        payload["component"] = self.task_id
        payload["cache_status"] = "CACHE_VALID" if self.cache_hit else "EXECUTED"
        payload["outputs"] = tuple(
            path for path in (self.stdout_path, self.stderr_path) if path
        )
        payload["consumer_evidence"] = ()
        payload["causal_evidence"] = ()
        payload["regression_evidence"] = ()
        payload["performance_metrics"] = {}
        payload["replay_metrics"] = {}
        payload["final_disposition"] = self.state.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TaskResult:
        return cls(
            task_id=str(payload["task_id"]),
            suite=ValidationSuite(str(payload["suite"])),
            scope=LabScope(str(payload["scope"])),
            state=TaskState(str(payload["state"])),
            worker_id=str(payload["worker_id"]),
            started_at_ns=int(payload["started_at_ns"]),
            ended_at_ns=int(payload["ended_at_ns"]),
            duration_ms=float(payload["duration_ms"]),
            attempts=int(payload["attempts"]),
            cache_hit=bool(payload["cache_hit"]),
            tests_total=int(payload["tests_total"]),
            tests_passed=int(payload["tests_passed"]),
            tests_failed=int(payload["tests_failed"]),
            stdout_path=str(payload["stdout_path"]),
            stderr_path=str(payload["stderr_path"]),
            artifact_hash=str(payload["artifact_hash"]),
            failure_reason=(
                None
                if payload.get("failure_reason") is None
                else str(payload["failure_reason"])
            ),
            resource_limits_applied=bool(payload["resource_limits_applied"]),
            cache_key=str(payload["cache_key"]),
        )


@dataclass(frozen=True, slots=True)
class RunSummary:
    identity: RunIdentity
    disposition: RunDisposition
    task_results: tuple[TaskResult, ...]
    evidence_path: str
    artifact_hash: str
    started_at_ns: int
    ended_at_ns: int

    @property
    def duration_ms(self) -> float:
        return (self.ended_at_ns - self.started_at_ns) / 1_000_000
