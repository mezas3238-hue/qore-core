# ruff: noqa: I001
import json
import os
import subprocess
import sys

try:
    import resource
except ImportError:  # Windows
    resource = None
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunDisposition,
    RunRequest,
    ValidationSuite,
)
from qore.infrastructure.core_stack_v2.shared_lab_orchestrator import NativeLabOrchestrator
from qore.infrastructure.core_stack_v2.shared_lab_store import EvidenceStore
from qore.infrastructure.core_stack_v2.shared_lab_suite_registry import (
    NativeSuiteRegistry,
    SuiteDefinition,
)


pytestmark = pytest.mark.skipif(
    os.name not in {"posix", "nt"}
    or (
        os.name == "posix"
        and (resource is None or not hasattr(resource, "prlimit"))
    ),
    reason="native resource-limit backend unavailable on this platform",
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


def registry() -> NativeSuiteRegistry:
    result = NativeSuiteRegistry()
    command = (
        sys.executable,
        "-c",
        "print(open('component.txt').read().strip()); print('1 passed')",
    )
    result.register(
        SuiteDefinition(
            "unit",
            ValidationSuite.UNIT,
            LabScope.FULL_STACK,
            (),
            command,
            ("component.txt",),
            execution_origin="TARGET",
        )
    )
    result.register(
        SuiteDefinition(
            "contract",
            ValidationSuite.CONTRACT,
            LabScope.FULL_STACK,
            (),
            command,
            ("component.txt",),
            execution_origin="TARGET",
        )
    )
    result.register(
        SuiteDefinition(
            "sensor-reality",
            ValidationSuite.SENSOR_REALITY,
            LabScope.SENSOR,
            ("unit", "contract"),
            command,
            ("component.txt",),
            execution_origin="TARGET",
        )
    )
    return result


def run_request(repo: Path, sha: str) -> RunRequest:
    return RunRequest(
        repository="owner/repo",
        repo_path=str(repo),
        commit_sha=sha,
        branch="main",
        dataset_id="builtin-engineering",
        dataset_version="1",
        mode=ExecutionMode.FULL,
        scope=LabScope.FULL_STACK,
        workers=2,
        policy=ResourcePolicy(
            timeout_seconds=30,
            retries=0,
            memory_limit_mb=1024,
            cpu_limit_seconds=30,
        ),
    )


def test_native_orchestrator_executes_exact_sha_dag_and_reuses_safe_cache(
    tmp_path: Path,
) -> None:
    repo, sha = make_repo(tmp_path)
    (repo / "component.txt").write_text("dirty\n")
    state = tmp_path / "state"
    orchestrator = NativeLabOrchestrator(state_dir=state, registry=registry())

    first = orchestrator.run(run_request(repo, sha))
    assert first.disposition is RunDisposition.PASS
    assert first.identity.commit_sha == sha
    assert {item.worker_id for item in first.task_results} >= {"W01", "W02"}
    assert not any(item.cache_hit for item in first.task_results)
    for item in first.task_results:
        if item.stdout_path:
            assert "committed" in Path(item.stdout_path).read_text()

    evidence = EvidenceStore(state / "evidence").read_run(first.identity.run_id)
    assert evidence["final_disposition"] == "PASS"
    assert evidence["identity"]["commit_sha"] == sha
    assert len(evidence["identity"]["lab_harness_sha"]) == 40
    assert evidence["environment"]["lab_harness_sha"] == (
        evidence["identity"]["lab_harness_sha"]
    )
    assert evidence["environment"]["github_actions_detected"] in {True, False}
    assert evidence["environment"]["github_actions_required"] is False

    second = orchestrator.run(run_request(repo, sha))
    assert second.disposition is RunDisposition.PASS
    assert all(item.cache_hit for item in second.task_results)
    second_evidence = json.loads(Path(second.evidence_path).read_text())
    assert second_evidence["final_disposition"] == "PASS"


def test_native_cache_invalidates_when_target_plugin_contract_changes(
    tmp_path: Path,
) -> None:
    repo, sha = make_repo(tmp_path)
    state = tmp_path / "state"

    def versioned_registry(label: str) -> NativeSuiteRegistry:
        result = NativeSuiteRegistry()
        result.register(
            SuiteDefinition(
                "unit",
                ValidationSuite.UNIT,
                LabScope.FULL_STACK,
                (),
                (
                    sys.executable,
                    "-c",
                    f"print('{label}'); print('1 passed')",
                ),
                ("component.txt",),
                execution_origin="TARGET",
            )
        )
        return result

    first = NativeLabOrchestrator(
        state_dir=state,
        registry=versioned_registry("plugin-v1"),
    ).run(run_request(repo, sha))
    assert first.disposition is RunDisposition.PASS
    assert not first.task_results[0].cache_hit

    second = NativeLabOrchestrator(
        state_dir=state,
        registry=versioned_registry("plugin-v2"),
    ).run(run_request(repo, sha))
    assert second.disposition is RunDisposition.PASS
    assert not second.task_results[0].cache_hit
    assert "plugin-v2" in Path(second.task_results[0].stdout_path).read_text()
