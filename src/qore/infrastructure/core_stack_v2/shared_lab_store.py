"""Persistent Dataset, Evidence and causal Cache stores for QORE Shared Lab."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    CacheKey,
    DatasetIdentity,
    RunIdentity,
    TaskResult,
)


def _json_default(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(
        payload,
        sort_keys=True,
        indent=2,
        default=_json_default,
    ) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(raw)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


class DatasetStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_builtin(self) -> DatasetIdentity:
        payload = b"QORE_SHARED_LAB_BUILTIN_ENGINEERING_DATASET_V1\n"
        return self.put_bytes(
            dataset_id="builtin-engineering",
            version="1",
            payload=payload,
        )

    def put_bytes(
        self,
        *,
        dataset_id: str,
        version: str,
        payload: bytes,
    ) -> DatasetIdentity:
        content_hash = sha256_bytes(payload)
        target = self.root / content_hash
        target.mkdir(parents=True, exist_ok=True)
        payload_path = target / "payload.bin"
        if not payload_path.exists():
            payload_path.write_bytes(payload)
        manifest = {
            "dataset_id": dataset_id,
            "version": version,
            "content_hash": content_hash,
            "payload_path": str(payload_path),
        }
        atomic_write_json(target / "manifest.json", manifest)
        index = self.root / "index" / dataset_id / f"{version}.json"
        atomic_write_json(index, manifest)
        return DatasetIdentity(dataset_id, version, content_hash, str(payload_path))

    def put_file(
        self,
        *,
        dataset_id: str,
        version: str,
        source: Path,
    ) -> DatasetIdentity:
        content_hash = sha256_file(source)
        target = self.root / content_hash
        target.mkdir(parents=True, exist_ok=True)
        payload_path = target / source.name
        if not payload_path.exists():
            shutil.copy2(source, payload_path)
        manifest = {
            "dataset_id": dataset_id,
            "version": version,
            "content_hash": content_hash,
            "payload_path": str(payload_path),
        }
        atomic_write_json(target / "manifest.json", manifest)
        atomic_write_json(
            self.root / "index" / dataset_id / f"{version}.json",
            manifest,
        )
        return DatasetIdentity(dataset_id, version, content_hash, str(payload_path))

    def resolve(self, dataset_id: str, version: str) -> DatasetIdentity:
        index = self.root / "index" / dataset_id / f"{version}.json"
        if not index.exists():
            if dataset_id == "builtin-engineering" and version == "1":
                return self.ensure_builtin()
            raise FileNotFoundError(f"dataset not found: {dataset_id}@{version}")
        payload = json.loads(index.read_text())
        return DatasetIdentity(
            dataset_id=str(payload["dataset_id"]),
            version=str(payload["version"]),
            content_hash=str(payload["content_hash"]),
            payload_path=str(payload["payload_path"]),
        )


class CacheStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, key: CacheKey) -> TaskResult | None:
        path = self.root / f"{key.fingerprint()}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        result = TaskResult.from_dict(payload["result"])
        if not result.passed:
            return None
        return result

    def put(self, key: CacheKey, result: TaskResult) -> None:
        if not result.passed:
            return
        atomic_write_json(
            self.root / f"{key.fingerprint()}.json",
            {
                "cache_key": asdict(key),
                "result": result.to_dict(),
            },
        )


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def start_run(
        self,
        *,
        identity: RunIdentity,
        request: dict[str, Any],
        environment: dict[str, Any],
        started_at_ns: int,
    ) -> Path:
        run_dir = self.run_dir(identity.run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        atomic_write_json(
            run_dir / "run.json",
            {
                "identity": asdict(identity),
                "request": request,
                "environment": environment,
                "state": "RUNNING",
                "started_at_ns": started_at_ns,
                "ended_at_ns": None,
                "final_disposition": None,
                "artifact_hash": None,
                "tasks": {},
            },
        )
        return run_dir

    def update_task(
        self,
        run_id: str,
        task_id: str,
        payload: dict[str, Any],
    ) -> None:
        run_file = self.run_dir(run_id) / "run.json"
        run = json.loads(run_file.read_text())
        tasks = dict(run.get("tasks", {}))
        tasks[task_id] = payload
        run["tasks"] = tasks
        atomic_write_json(run_file, run)

    def write_task_result(self, run_id: str, result: TaskResult) -> None:
        task_dir = self.run_dir(run_id) / "tasks" / result.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(task_dir / "result.json", result.to_dict())
        self.update_task(run_id, result.task_id, result.to_dict())

    def finish_run(
        self,
        *,
        run_id: str,
        disposition: str,
        ended_at_ns: int,
        artifact_hash: str,
    ) -> Path:
        run_file = self.run_dir(run_id) / "run.json"
        run = json.loads(run_file.read_text())
        run["state"] = "COMPLETED"
        run["ended_at_ns"] = ended_at_ns
        run["final_disposition"] = disposition
        run["artifact_hash"] = artifact_hash
        atomic_write_json(run_file, run)
        return run_file

    def read_run(self, run_id: str) -> dict[str, Any]:
        path = self.run_dir(run_id) / "run.json"
        if not path.exists():
            raise FileNotFoundError(f"run not found: {run_id}")
        payload: dict[str, Any] = json.loads(path.read_text())
        return payload
