"""Native command-line interface for QORE Shared Lab."""

# ruff: noqa: I001

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunRequest,
    RunSummary,
)
from qore.infrastructure.core_stack_v2.shared_lab_orchestrator import NativeLabOrchestrator
from qore.infrastructure.core_stack_v2.shared_lab_publisher import GitHubResultPublisher
from qore.infrastructure.core_stack_v2.shared_lab_scheduler import SharedLabScheduler
from qore.infrastructure.core_stack_v2.shared_lab_scheduler_server import (
    SchedulerClient,
    SchedulerServer,
)
from qore.infrastructure.core_stack_v2.shared_lab_store import DatasetStore, EvidenceStore


DEFAULT_REPOSITORY = "mezas3238-hue/qore-core"
DEFAULT_SERVER_URL = "http://127.0.0.1:8765"


def _branch(repo_path: Path) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repo_path), "branch", "--show-current"),
        check=True,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    return value or "DETACHED"


def _state_dir(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _summary_payload(summary: RunSummary) -> dict[str, Any]:
    return {
        "run_id": summary.identity.run_id,
        "repository": summary.identity.repository,
        "commit_sha": summary.identity.commit_sha,
        "branch": summary.identity.branch,
        "dataset_id": summary.identity.dataset_id,
        "dataset_version": summary.identity.dataset_version,
        "dataset_hash": summary.identity.dataset_hash,
        "config_hash": summary.identity.configuration_hash,
        "lab_version": summary.identity.lab_version,
        "disposition": summary.disposition.value,
        "duration_ms": summary.duration_ms,
        "evidence_path": summary.evidence_path,
        "artifact_hash": summary.artifact_hash,
        "tasks": [result.to_dict() for result in summary.task_results],
    }


def _request_from_args(
    args: argparse.Namespace,
    *,
    replay: bool = False,
) -> RunRequest:
    repo_path = Path(str(args.repo_path)).resolve()
    branch = str(args.branch) if args.branch else _branch(repo_path)
    return RunRequest(
        repository=str(args.repository),
        repo_path=str(repo_path),
        commit_sha=str(args.sha),
        branch=branch,
        dataset_id=str(args.dataset_id),
        dataset_version=str(args.dataset_version),
        mode=ExecutionMode.REPLAY if replay else ExecutionMode(str(args.mode).upper()),
        scope=LabScope.FULL_STACK if replay else LabScope(str(args.scope)),
        workers=int(args.workers),
        policy=ResourcePolicy(
            timeout_seconds=int(args.timeout),
            retries=int(args.retries),
            memory_limit_mb=int(args.memory_mb),
            cpu_limit_seconds=int(args.cpu_seconds),
        ),
        base_sha=(
            None
            if getattr(args, "base_sha", None) is None
            else str(args.base_sha)
        ),
        scenario=(
            str(args.scenario)
            if replay
            else (
                None
                if getattr(args, "scenario", None) is None
                else str(args.scenario)
            )
        ),
        use_cache=not bool(args.no_cache),
        submitted_by=str(getattr(args, "submitted_by", "local-user")),
        submitted_role=str(getattr(args, "role", "ARCHITECT")).upper(),
        dependency_hashes=tuple(getattr(args, "dependency_hash", ()) or ()),
        exclusive_locks=tuple(getattr(args, "lock", ()) or ()),
    )


def _request_payload(request: RunRequest, priority: str) -> dict[str, Any]:
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
        "scenario": request.scenario,
        "use_cache": request.use_cache,
        "dependency_hashes": request.dependency_hashes,
        "exclusive_locks": request.exclusive_locks,
        "submitted_by": request.submitted_by,
        "role": request.submitted_role,
        "priority": priority,
    }


def _add_execution_args(
    parser: argparse.ArgumentParser,
    *,
    require_identity: bool = False,
) -> None:
    parser.add_argument("--repo-path", default=".")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--branch")
    parser.add_argument("--dataset-id", default="builtin-engineering")
    parser.add_argument("--dataset-version", default="1")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--memory-mb", type=int, default=2048)
    parser.add_argument("--cpu-seconds", type=int, default=300)
    parser.add_argument("--dependency-hash", action="append", default=[])
    parser.add_argument("--lock", action="append", default=[])
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--state-dir", default=".qore-shared-lab")
    parser.add_argument(
        "--submitted-by",
        required=require_identity,
        default=None if require_identity else "local-user",
    )
    parser.add_argument(
        "--role",
        choices=("ARCHITECT", "INTEGRATOR"),
        required=require_identity,
        default=None if require_identity else "ARCHITECT",
    )


def _add_validate_shape(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sha", required=True)
    parser.add_argument(
        "--scope",
        choices=[scope.value for scope in LabScope],
        default=LabScope.FULL_STACK.value,
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value.lower() for mode in ExecutionMode],
        default=ExecutionMode.FULL.value.lower(),
    )
    parser.add_argument("--base-sha")
    parser.add_argument("--scenario")


def _run_validate(args: argparse.Namespace) -> int:
    request = _request_from_args(args)
    orchestrator = NativeLabOrchestrator(state_dir=_state_dir(str(args.state_dir)))
    summary = orchestrator.run(request)
    print(json.dumps(_summary_payload(summary), sort_keys=True, indent=2))
    return 0 if summary.disposition.value == "PASS" else 1


def _run_replay(args: argparse.Namespace) -> int:
    request = _request_from_args(args, replay=True)
    orchestrator = NativeLabOrchestrator(state_dir=_state_dir(str(args.state_dir)))
    summary = orchestrator.run(request)
    print(json.dumps(_summary_payload(summary), sort_keys=True, indent=2))
    return 0 if summary.disposition.value == "PASS" else 1


def _run_serve(args: argparse.Namespace) -> int:
    scheduler = SharedLabScheduler(
        state_dir=_state_dir(str(args.state_dir)),
        worker_capacity=int(args.workers),
        max_worker_capacity=int(args.max_workers),
        max_queued_jobs=int(args.max_queued_jobs),
    )
    SchedulerServer(
        scheduler=scheduler,
        host=str(args.host),
        port=int(args.port),
    ).serve_forever()
    return 0


def _run_submit(args: argparse.Namespace) -> int:
    request = _request_from_args(args)
    client = SchedulerClient(str(args.server_url))
    payload = client.submit(
        _request_payload(request, str(args.priority).upper())
    )
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


def _run_status(args: argparse.Namespace) -> int:
    client = SchedulerClient(str(args.server_url))
    run_id = None if args.run_id is None else str(args.run_id)
    print(json.dumps(client.status(run_id), sort_keys=True, indent=2))
    return 0


def _run_cancel(args: argparse.Namespace) -> int:
    client = SchedulerClient(str(args.server_url))
    print(
        json.dumps(
            client.cancel(str(args.run_id)),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


def _run_workers(args: argparse.Namespace) -> int:
    client = SchedulerClient(str(args.server_url))
    print(
        json.dumps(
            client.resize(int(args.capacity)),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


def _run_evidence_status(args: argparse.Namespace) -> int:
    store = EvidenceStore(_state_dir(str(args.state_dir)) / "evidence")
    print(json.dumps(store.read_run(str(args.run_id)), sort_keys=True, indent=2))
    return 0


def _run_reproduce(args: argparse.Namespace) -> int:
    state_dir = _state_dir(str(args.state_dir))
    store = EvidenceStore(state_dir / "evidence")
    original = store.read_run(str(args.run_id))
    payload = dict(original["request"])
    policy = dict(payload["policy"])
    request = RunRequest(
        repository=str(payload["repository"]),
        repo_path=str(payload["repo_path"]),
        commit_sha=str(payload["commit_sha"]),
        branch=str(payload["branch"]),
        dataset_id=str(payload["dataset_id"]),
        dataset_version=str(payload["dataset_version"]),
        mode=ExecutionMode(str(payload["mode"])),
        scope=LabScope(str(payload["scope"])),
        workers=int(payload["workers"]),
        policy=ResourcePolicy(
            timeout_seconds=int(policy["timeout_seconds"]),
            retries=int(policy["retries"]),
            memory_limit_mb=int(policy["memory_limit_mb"]),
            cpu_limit_seconds=int(policy["cpu_limit_seconds"]),
        ),
        base_sha=(
            None if payload.get("base_sha") is None else str(payload["base_sha"])
        ),
        changed_paths=tuple(str(x) for x in payload.get("changed_paths", [])),
        scenario=(
            None if payload.get("scenario") is None else str(payload["scenario"])
        ),
        use_cache=bool(payload.get("use_cache", True)),
        reproduces_run_id=str(args.run_id),
        submitted_by=str(payload.get("submitted_by", "reproduce")),
        submitted_role=str(payload.get("submitted_role", "INTEGRATOR")),
        dependency_hashes=tuple(
            str(x) for x in payload.get("dependency_hashes", [])
        ),
        exclusive_locks=tuple(str(x) for x in payload.get("exclusive_locks", [])),
    )
    summary = NativeLabOrchestrator(state_dir=state_dir).run(request)
    print(json.dumps(_summary_payload(summary), sort_keys=True, indent=2))
    return 0 if summary.disposition.value == "PASS" else 1


def _run_dataset_add(args: argparse.Namespace) -> int:
    store = DatasetStore(_state_dir(str(args.state_dir)) / "datasets")
    record = store.put_file(
        dataset_id=str(args.dataset_id),
        version=str(args.dataset_version),
        source=Path(str(args.file)).resolve(),
    )
    print(json.dumps(asdict(record), sort_keys=True, indent=2))
    return 0


def _run_publish(args: argparse.Namespace) -> int:
    state_dir = _state_dir(str(args.state_dir))
    evidence = EvidenceStore(state_dir / "evidence").read_run(str(args.run_id))
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required only for publish")
    repository = str(evidence["identity"]["repository"])
    receipt = GitHubResultPublisher(token).publish_evidence(
        repository=repository,
        evidence=evidence,
    )
    print(json.dumps(asdict(receipt), sort_keys=True, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qore-shared-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    _add_validate_shape(validate)
    _add_execution_args(validate)
    validate.set_defaults(handler=_run_validate)

    replay = sub.add_parser("replay")
    replay.add_argument("--sha", required=True)
    replay.add_argument("--scenario", required=True)
    _add_execution_args(replay)
    replay.set_defaults(handler=_run_replay)

    serve = sub.add_parser("serve")
    serve.add_argument("--state-dir", default=".qore-shared-lab")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--workers", type=int, default=4)
    serve.add_argument("--max-workers", type=int, default=20)
    serve.add_argument("--max-queued-jobs", type=int, default=32)
    serve.set_defaults(handler=_run_serve)

    submit = sub.add_parser("submit")
    _add_validate_shape(submit)
    _add_execution_args(submit, require_identity=True)
    submit.add_argument(
        "--priority",
        choices=("QUICK", "NORMAL", "DEEP", "CERTIFICATION"),
        default="NORMAL",
    )
    submit.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    submit.set_defaults(handler=_run_submit)

    status = sub.add_parser("status")
    status.add_argument("run_id", nargs="?")
    status.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    status.set_defaults(handler=_run_status)

    cancel = sub.add_parser("cancel")
    cancel.add_argument("run_id")
    cancel.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    cancel.set_defaults(handler=_run_cancel)

    workers = sub.add_parser("workers")
    workers.add_argument("--capacity", type=int, required=True)
    workers.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    workers.set_defaults(handler=_run_workers)

    evidence = sub.add_parser("evidence-status")
    evidence.add_argument("run_id")
    evidence.add_argument("--state-dir", default=".qore-shared-lab")
    evidence.set_defaults(handler=_run_evidence_status)

    reproduce = sub.add_parser("reproduce")
    reproduce.add_argument("run_id")
    reproduce.add_argument("--state-dir", default=".qore-shared-lab")
    reproduce.set_defaults(handler=_run_reproduce)

    dataset = sub.add_parser("dataset-add")
    dataset.add_argument("--dataset-id", required=True)
    dataset.add_argument("--dataset-version", required=True)
    dataset.add_argument("--file", required=True)
    dataset.add_argument("--state-dir", default=".qore-shared-lab")
    dataset.set_defaults(handler=_run_dataset_add)

    publish = sub.add_parser("publish")
    publish.add_argument("run_id")
    publish.add_argument("--state-dir", default=".qore-shared-lab")
    publish.set_defaults(handler=_run_publish)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    handler = args.handler
    raise SystemExit(int(handler(args)))


if __name__ == "__main__":
    main()
