# ruff: noqa: I001
#!/usr/bin/env python3
"""Real multiuser E2E acceptance for the native QORE Shared Lab bank."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_native_completion import (
    MultiuserNativeAcceptance,
)
from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    LabScope,
    ValidationSuite,
)
from qore.infrastructure.core_stack_v2.shared_lab_orchestrator import (
    NativeLabOrchestrator,
)
from qore.infrastructure.core_stack_v2.shared_lab_scheduler import SharedLabScheduler
from qore.infrastructure.core_stack_v2.shared_lab_scheduler_server import (
    SchedulerClient,
    SchedulerServer,
)
from qore.infrastructure.core_stack_v2.shared_lab_suite_registry import (
    NativeSuiteRegistry,
    SuiteDefinition,
)


TERMINAL = {
    "PASS",
    "FAIL",
    "BLOCKED",
    "CANCELLED",
    "TIMEOUT",
    "INVALID_EVIDENCE",
}



def run_cli_json(
    executable: str,
    args: tuple[str, ...],
) -> dict[str, Any]:
    completed = subprocess.run(
        (executable, *args),
        check=True,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    payload: dict[str, Any] = json.loads(completed.stdout)
    return payload


def git(*args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def worker_command() -> tuple[str, ...]:
    code = (
        "import os,time,sys;"
        "owner=os.environ['QORE_SHARED_LAB_SUBMITTED_BY'];"
        "time.sleep(4 if owner in {'Queue-Hold','Cancel-Me'} "
        "else 1 if owner in {'Dedup-A','Lock-A'} else 0.12);"
        "print('owner='+owner);print('1 passed');"
        "sys.exit(1 if owner=='Architect-5' else 0)"
    )
    return (sys.executable, "-c", code)


def acceptance_registry() -> NativeSuiteRegistry:
    registry = NativeSuiteRegistry()
    common = ("pyproject.toml",)
    definitions = (
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
        ("stress", ValidationSuite.STRESS, LabScope.FULL_STACK, ("functional",)),
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
    command = worker_command()
    for task_id, suite, scope, dependencies in definitions:
        registry.register(
            SuiteDefinition(
                task_id=task_id,
                suite=suite,
                scope=scope,
                dependencies=dependencies,
                command=command,
                component_globs=common,
            )
        )
    return registry


def payload(
    *,
    repo_root: Path,
    sha: str,
    branch: str,
    client: str,
    role: str,
    mode: str,
    scope: str,
    dependency_hash: str,
    priority: str = "NORMAL",
    locks: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "repository": "mezas3238-hue/qore-core",
        "repo_path": str(repo_root),
        "commit_sha": sha,
        "branch": branch,
        "dataset_id": "native-acceptance",
        "dataset_version": "1",
        "mode": mode,
        "scope": scope,
        "workers": 1,
        "policy": {
            "timeout_seconds": 20,
            "retries": 0,
            "memory_limit_mb": 2048,
            "cpu_limit_seconds": 20,
        },
        "submitted_by": client,
        "role": role,
        "priority": priority,
        "dependency_hashes": [dependency_hash],
        "exclusive_locks": list(locks),
        "use_cache": True,
    }


def wait_terminal(
    client: SchedulerClient,
    job_id: str,
    *,
    timeout: float = 60,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.status(job_id)
        if status["state"] in TERMINAL:
            return status
        time.sleep(0.03)
    raise TimeoutError(f"job did not finish: {job_id}")


def wait_running(
    client: SchedulerClient,
    job_id: str,
    *,
    timeout: float = 10,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.status(job_id)
        if status["state"] in {"RUNNING", "PASS", "FAIL"}:
            return status
        time.sleep(0.03)
    raise TimeoutError(f"job did not start: {job_id}")


def scrub_github_environment() -> dict[str, str]:
    removed = {
        key: value for key, value in os.environ.items() if key.startswith("GITHUB_")
    }
    for key in removed:
        del os.environ[key]
    return removed


def restore_environment(values: dict[str, str]) -> None:
    os.environ.update(values)


def run_acceptance(state_dir: Path) -> dict[str, Any]:
    repo_root = Path(git("rev-parse", "--show-toplevel")).resolve()
    sha = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current") or "DETACHED"
    removed_github = scrub_github_environment()
    executable = shutil.which("qore-shared-lab")
    if executable is None:
        raise RuntimeError("qore-shared-lab console entry point is not installed")
    direct_state = state_dir / "direct-cli"
    direct_validate = run_cli_json(
        executable,
        (
            "validate",
            "--sha",
            sha,
            "--branch",
            branch,
            "--scope",
            "full-stack",
            "--mode",
            "quick",
            "--workers",
            "2",
            "--timeout",
            "180",
            "--memory-mb",
            "4096",
            "--cpu-seconds",
            "180",
            "--state-dir",
            str(direct_state),
        ),
    )
    if direct_validate["disposition"] != "PASS":
        raise RuntimeError("direct native validate did not PASS")
    direct_reproduce = run_cli_json(
        executable,
        (
            "reproduce",
            str(direct_validate["run_id"]),
            "--state-dir",
            str(direct_state),
        ),
    )
    if direct_reproduce["disposition"] != "PASS":
        raise RuntimeError("direct native reproduce did not PASS")
    direct_replay = run_cli_json(
        executable,
        (
            "replay",
            "--sha",
            sha,
            "--branch",
            branch,
            "--scenario",
            "global-exam",
            "--workers",
            "2",
            "--timeout",
            "180",
            "--memory-mb",
            "4096",
            "--cpu-seconds",
            "180",
            "--state-dir",
            str(direct_state),
        ),
    )
    if direct_replay["disposition"] != "PASS":
        raise RuntimeError("direct native replay did not PASS")

    orchestrator = NativeLabOrchestrator(
        state_dir=state_dir,
        registry=acceptance_registry(),
    )
    orchestrator.dataset_store.put_bytes(
        dataset_id="native-acceptance",
        version="1",
        payload=b"QORE_SHARED_LAB_NATIVE_MULTIUSER_ACCEPTANCE_V1\n",
    )
    scheduler = SharedLabScheduler(
        state_dir=state_dir,
        worker_capacity=4,
        max_worker_capacity=20,
        max_queued_jobs=32,
        orchestrator=orchestrator,
    )
    server = SchedulerServer(scheduler=scheduler, port=0)
    server.start_in_thread()
    client = SchedulerClient(f"http://127.0.0.1:{server.bound_port}")

    try:
        cases = (
            ("Architect-1", "ARCHITECT", "QUICK", "provider", "QUICK"),
            ("Architect-2", "ARCHITECT", "COMPONENT", "sensor", "NORMAL"),
            ("Architect-3", "ARCHITECT", "REPLAY", "full-stack", "NORMAL"),
            ("Architect-4", "ARCHITECT", "INTEGRATION", "provider", "NORMAL"),
            ("Architect-5", "ARCHITECT", "REGRESSION", "cognition", "NORMAL"),
            ("Architect-6", "ARCHITECT", "DEEP", "cognition", "DEEP"),
            ("Integrator-1", "INTEGRATOR", "QUICK", "identity", "QUICK"),
            ("Integrator-2", "INTEGRATOR", "REGRESSION", "full-stack", "NORMAL"),
            ("Integrator-3", "INTEGRATOR", "FULL", "full-stack", "DEEP"),
        )

        def submit_case(
            indexed: tuple[int, tuple[str, str, str, str, str]],
        ) -> dict[str, Any]:
            index, case = indexed
            user, role, mode, scope, priority = case
            return client.submit(
                payload(
                    repo_root=repo_root,
                    sha=sha,
                    branch=branch,
                    client=user,
                    role=role,
                    mode=mode,
                    scope=scope,
                    dependency_hash=f"client-{index}",
                    priority=priority,
                )
            )

        with ThreadPoolExecutor(max_workers=9) as pool:
            submitted = tuple(pool.map(submit_case, enumerate(cases)))
        if len({item["scheduler_job_id"] for item in submitted}) != 9:
            raise RuntimeError("nine-client submission lost or deduplicated unexpectedly")

        observed_parallel = False
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            snapshot = client.status()
            if 2 <= int(snapshot["running_jobs"]) <= 4:
                observed_parallel = True
                break
            time.sleep(0.03)
        if not observed_parallel:
            raise RuntimeError("parallel worker pool was not observed")

        finished = tuple(
            wait_terminal(client, str(item["scheduler_job_id"]))
            for item in submitted
        )
        failures = {
            item["submitted_by"]: item["state"]
            for item in finished
            if item["state"] != "PASS"
        }
        if failures != {"Architect-5": "FAIL"}:
            raise RuntimeError(f"failure isolation mismatch: {failures}")

        evidence_paths = {
            str(item["evidence_path"])
            for item in finished
            if item["evidence_path"] is not None
        }
        run_isolation = len(evidence_paths) == 9
        evidence_ownership = all(
            item["submitted_by"]
            in Path(str(item["evidence_path"])).read_text()
            for item in finished
            if item["evidence_path"] is not None
        )
        exact_sha = all(item["sha"] == sha for item in finished)

        dynamic = client.resize(8)
        dynamic_pool = int(dynamic["worker_capacity"]) == 8
        client.resize(4)

        dedup_a = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Dedup-A",
                role="ARCHITECT",
                mode="QUICK",
                scope="provider",
                dependency_hash="dedup",
                priority="QUICK",
            )
        )
        dedup_b = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Dedup-B",
                role="INTEGRATOR",
                mode="QUICK",
                scope="provider",
                dependency_hash="dedup",
                priority="QUICK",
            )
        )
        dedup_pass = dedup_a["scheduler_job_id"] == dedup_b["scheduler_job_id"]
        dedup_done = wait_terminal(client, str(dedup_a["scheduler_job_id"]))
        if dedup_done["state"] != "PASS":
            raise RuntimeError("deduplicated active run did not PASS")

        cache_job = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Cache-Reader",
                role="INTEGRATOR",
                mode="QUICK",
                scope="provider",
                dependency_hash="dedup",
                priority="QUICK",
            )
        )
        cache_done = wait_terminal(client, str(cache_job["scheduler_job_id"]))
        cache_evidence = json.loads(
            Path(str(cache_done["evidence_path"])).read_text()
        )
        causal_cache = bool(cache_evidence["tasks"]) and all(
            task.get("cache_status") == "CACHE_VALID"
            for task in cache_evidence["tasks"].values()
        )

        lock_a = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Lock-A",
                role="INTEGRATOR",
                mode="QUICK",
                scope="full-stack",
                dependency_hash="lock-a",
                priority="CERTIFICATION",
                locks=("certification-environment",),
            )
        )
        wait_running(client, str(lock_a["scheduler_job_id"]))
        lock_b = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Lock-B",
                role="INTEGRATOR",
                mode="QUICK",
                scope="full-stack",
                dependency_hash="lock-b",
                priority="CERTIFICATION",
                locks=("certification-environment",),
            )
        )
        free = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Free-A",
                role="ARCHITECT",
                mode="QUICK",
                scope="full-stack",
                dependency_hash="free-a",
                priority="QUICK",
            )
        )
        free_started = wait_running(client, str(free["scheduler_job_id"]))
        lock_b_status = client.status(str(lock_b["scheduler_job_id"]))
        granular_lock = (
            free_started["state"] in {"RUNNING", "PASS"}
            and lock_b_status["state"] == "QUEUED"
        )
        wait_terminal(client, str(lock_a["scheduler_job_id"]))
        wait_terminal(client, str(lock_b["scheduler_job_id"]))
        wait_terminal(client, str(free["scheduler_job_id"]))

        cancel_job = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Cancel-Me",
                role="ARCHITECT",
                mode="QUICK",
                scope="full-stack",
                dependency_hash="cancel",
                priority="QUICK",
            )
        )
        wait_running(client, str(cancel_job["scheduler_job_id"]))
        client.cancel(str(cancel_job["scheduler_job_id"]))
        cancelled = wait_terminal(client, str(cancel_job["scheduler_job_id"]))
        cancellation = cancelled["state"] == "CANCELLED"

        client.resize(1)
        queue_hold = client.submit(
            payload(
                repo_root=repo_root,
                sha=sha,
                branch=branch,
                client="Queue-Hold",
                role="ARCHITECT",
                mode="QUICK",
                scope="full-stack",
                dependency_hash="queue-hold",
                priority="QUICK",
            )
        )
        wait_running(client, str(queue_hold["scheduler_job_id"]))
        queued: list[dict[str, Any]] = []
        for index in range(32):
            queued.append(
                client.submit(
                    payload(
                        repo_root=repo_root,
                        sha=sha,
                        branch=branch,
                        client=f"Queue-{index:02d}",
                        role="ARCHITECT",
                        mode="QUICK",
                        scope="full-stack",
                        dependency_hash=f"queue-{index}",
                        priority="NORMAL",
                    )
                )
            )
        queue_32 = int(client.status()["queued_jobs"]) == 32
        overflow_rejected = False
        try:
            client.submit(
                payload(
                    repo_root=repo_root,
                    sha=sha,
                    branch=branch,
                    client="Queue-Overflow",
                    role="ARCHITECT",
                    mode="QUICK",
                    scope="full-stack",
                    dependency_hash="queue-overflow",
                    priority="NORMAL",
                )
            )
        except RuntimeError:
            overflow_rejected = True
        for item in queued:
            client.cancel(str(item["scheduler_job_id"]))
        client.cancel(str(queue_hold["scheduler_job_id"]))
        wait_terminal(client, str(queue_hold["scheduler_job_id"]))
        queue_32 = queue_32 and overflow_rejected
        client.resize(4)

        replay_pass = direct_replay["disposition"] == "PASS"
        status_snapshot = client.status()
        status_observability = (
            "jobs" in status_snapshot
            and "worker_capacity" in status_snapshot
            and "queued_jobs" in status_snapshot
        )
        github_required = any(
            bool(
                json.loads(Path(str(item["evidence_path"])).read_text())[
                    "environment"
                ]["github_actions_required"]
            )
            for item in finished
            if item["evidence_path"] is not None
        )
        dataset_hash = orchestrator.dataset_store.resolve(
            "native-acceptance",
            "1",
        ).content_hash
        persistent_dataset = all(
            json.loads(Path(str(item["evidence_path"])).read_text())[
                "dataset_hash"
            ]
            == dataset_hash
            for item in finished
            if item["evidence_path"] is not None
        )

        receipt = MultiuserNativeAcceptance(
            commit_sha=sha,
            direct_cli_validate_pass=(
                direct_validate["disposition"] == "PASS"
                and direct_validate["commit_sha"] == sha
            ),
            nine_concurrent_clients_pass=len(finished) == 9,
            queue_32_pass=queue_32,
            dynamic_worker_pool_pass=dynamic_pool,
            run_isolation_pass=run_isolation,
            deduplication_pass=dedup_pass,
            causal_cache_pass=causal_cache,
            granular_lock_pass=granular_lock,
            failure_isolation_pass=failures == {"Architect-5": "FAIL"},
            evidence_ownership_pass=evidence_ownership,
            cancellation_pass=cancellation,
            status_observability_pass=status_observability,
            native_replay_pass=replay_pass,
            reproduce_pass=direct_reproduce["disposition"] == "PASS",
            exact_sha_pass=(
                exact_sha
                and direct_validate["commit_sha"] == sha
                and direct_replay["commit_sha"] == sha
            ),
            persistent_dataset_pass=persistent_dataset,
            github_actions_required=github_required,
            github_publication_available=True,
        )
        if not receipt.passed:
            raise RuntimeError(f"native multiuser acceptance failed: {receipt}")
        return {
            "identity": "QORE_SHARED_LAB_MULTIUSER_NATIVE_ACCEPTANCE_001",
            "receipt": asdict(receipt),
            "passed": receipt.passed,
            "scheduler_endpoint": f"http://127.0.0.1:{server.bound_port}",
            "github_environment_removed": bool(removed_github),
        }
    finally:
        server.shutdown()
        restore_environment(removed_github)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-dir",
        default="result/shared-lab-multiuser-native",
    )
    parser.add_argument(
        "--output",
        default="result/shared-lab-multiuser-native/acceptance.json",
    )
    args = parser.parse_args()
    state_dir = Path(str(args.state_dir)).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    result = run_acceptance(state_dir)
    output = Path(str(args.output)).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(output.read_text(), end="")


if __name__ == "__main__":
    main()
