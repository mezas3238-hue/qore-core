"""Native command-line interface for QORE Shared Lab."""

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
from qore.infrastructure.core_stack_v2.shared_lab_store import DatasetStore, EvidenceStore


DEFAULT_REPOSITORY = "mezas3238-hue/qore-core"


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
        "dataset_hash": summary.identity.dataset_hash,
        "config_hash": summary.identity.configuration_hash,
        "lab_version": summary.identity.lab_version,
        "disposition": summary.disposition.value,
        "duration_ms": summary.duration_ms,
        "evidence_path": summary.evidence_path,
        "artifact_hash": summary.artifact_hash,
        "tasks": [result.to_dict() for result in summary.task_results],
    }


def _request_from_args(args: argparse.Namespace, *, replay: bool = False) -> RunRequest:
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
    )


def _add_execution_args(parser: argparse.ArgumentParser) -> None:
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
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--state-dir", default=".qore-shared-lab")


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


def _run_status(args: argparse.Namespace) -> int:
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
    validate.add_argument("--sha", required=True)
    validate.add_argument(
        "--scope",
        choices=[scope.value for scope in LabScope],
        default=LabScope.FULL_STACK.value,
    )
    validate.add_argument(
        "--mode",
        choices=[mode.value.lower() for mode in ExecutionMode],
        default=ExecutionMode.FULL.value.lower(),
    )
    validate.add_argument("--base-sha")
    validate.add_argument("--scenario")
    _add_execution_args(validate)
    validate.set_defaults(handler=_run_validate)

    replay = sub.add_parser("replay")
    replay.add_argument("--sha", required=True)
    replay.add_argument("--scenario", required=True)
    _add_execution_args(replay)
    replay.set_defaults(handler=_run_replay)

    status = sub.add_parser("status")
    status.add_argument("run_id")
    status.add_argument("--state-dir", default=".qore-shared-lab")
    status.set_defaults(handler=_run_status)

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
