"""Local multiuser API for the QORE Shared Lab scheduler."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from qore.infrastructure.core_stack_v2.shared_lab_native_model import (
    ExecutionMode,
    LabScope,
    ResourcePolicy,
    RunRequest,
)
from qore.infrastructure.core_stack_v2.shared_lab_scheduler import (
    ClientRole,
    JobSubmission,
    PriorityLane,
    SharedLabScheduler,
)


def _request_from_payload(payload: dict[str, Any]) -> RunRequest:
    policy_payload = dict(payload.get("policy", {}))
    return RunRequest(
        repository=str(payload["repository"]),
        repo_path=str(payload["repo_path"]),
        commit_sha=str(payload["commit_sha"]),
        branch=str(payload["branch"]),
        dataset_id=str(payload.get("dataset_id", "builtin-engineering")),
        dataset_version=str(payload.get("dataset_version", "1")),
        mode=ExecutionMode(str(payload.get("mode", "QUICK")).upper()),
        scope=LabScope(str(payload.get("scope", "full-stack"))),
        workers=int(payload.get("workers", 1)),
        policy=ResourcePolicy(
            timeout_seconds=int(policy_payload.get("timeout_seconds", 300)),
            retries=int(policy_payload.get("retries", 0)),
            memory_limit_mb=int(policy_payload.get("memory_limit_mb", 2048)),
            cpu_limit_seconds=int(policy_payload.get("cpu_limit_seconds", 300)),
        ),
        base_sha=(
            None if payload.get("base_sha") is None else str(payload["base_sha"])
        ),
        changed_paths=tuple(str(x) for x in payload.get("changed_paths", [])),
        scenario=(
            None if payload.get("scenario") is None else str(payload["scenario"])
        ),
        use_cache=bool(payload.get("use_cache", True)),
        dependency_hashes=tuple(
            str(x) for x in payload.get("dependency_hashes", [])
        ),
        exclusive_locks=tuple(str(x) for x in payload.get("exclusive_locks", [])),
        submitted_by=str(payload["submitted_by"]),
        submitted_role=str(payload["role"]),
    )


class SchedulerRequestHandler(BaseHTTPRequestHandler):
    scheduler: SharedLabScheduler

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload: dict[str, Any] = json.loads(raw or b"{}")
        return payload

    def _send(self, status: int, payload: object) -> None:
        raw = json.dumps(payload, sort_keys=True, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path == "/v1/status":
            self._send(200, self.scheduler.status())
            return
        if self.path.startswith("/v1/status/"):
            job_id = self.path.removeprefix("/v1/status/")
            try:
                self._send(200, self.scheduler.status(job_id))
            except KeyError:
                self._send(404, {"error": "job not found", "job_id": job_id})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            if self.path == "/v1/jobs":
                payload = self._json_body()
                request = _request_from_payload(payload)
                submission = JobSubmission(
                    submitted_by=str(payload["submitted_by"]),
                    role=ClientRole(str(payload["role"]).upper()),
                    request=request,
                    priority=PriorityLane[str(payload.get("priority", "NORMAL")).upper()],
                    exclusive_locks=tuple(
                        str(x) for x in payload.get("exclusive_locks", [])
                    ),
                )
                job = self.scheduler.submit(submission)
                self._send(202, job.to_dict())
                return
            if self.path.startswith("/v1/cancel/"):
                job_id = self.path.removeprefix("/v1/cancel/")
                self._send(200, self.scheduler.cancel(job_id).to_dict())
                return
            if self.path == "/v1/workers/resize":
                payload = self._json_body()
                self.scheduler.resize_workers(int(payload["worker_capacity"]))
                self._send(200, self.scheduler.status())
                return
        except (KeyError, ValueError, RuntimeError) as exc:
            self._send(400, {"error": str(exc)})
            return
        self._send(404, {"error": "not found"})


@dataclass(slots=True)
class SchedulerServer:
    scheduler: SharedLabScheduler
    host: str = "127.0.0.1"
    port: int = 8765

    def serve_forever(self) -> None:
        handler = type(
            "BoundSchedulerHandler",
            (SchedulerRequestHandler,),
            {"scheduler": self.scheduler},
        )
        server = ThreadingHTTPServer((self.host, self.port), handler)
        try:
            server.serve_forever()
        finally:
            server.server_close()
            self.scheduler.shutdown(wait=True)


class SchedulerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/jobs", payload)

    def status(self, job_id: str | None = None) -> dict[str, Any]:
        path = "/v1/status" if job_id is None else f"/v1/status/{job_id}"
        return self._request("GET", path)

    def cancel(self, job_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/cancel/{job_id}", {})

    def resize(self, capacity: int) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/workers/resize",
            {"worker_capacity": capacity},
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                result: dict[str, Any] = json.loads(response.read().decode())
                return result
        except HTTPError as exc:
            message = exc.read().decode()
            raise RuntimeError(
                f"scheduler API failed {exc.code}: {message}"
            ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(prog="qore-shared-lab-scheduler")
    parser.add_argument("--state-dir", default=".qore-shared-lab")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=20)
    parser.add_argument("--max-queued-jobs", type=int, default=32)
    args = parser.parse_args()
    scheduler = SharedLabScheduler(
        state_dir=Path(str(args.state_dir)),
        worker_capacity=int(args.workers),
        max_worker_capacity=int(args.max_workers),
        max_queued_jobs=int(args.max_queued_jobs),
    )
    SchedulerServer(
        scheduler=scheduler,
        host=str(args.host),
        port=int(args.port),
    ).serve_forever()


if __name__ == "__main__":
    main()
