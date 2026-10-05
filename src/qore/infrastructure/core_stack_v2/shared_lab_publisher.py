"""Optional GitHub publication for native Shared Lab results.

GitHub receives status after native execution; it is not the execution engine.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    repository: str
    commit_sha: str
    contexts_published: tuple[str, ...]


class GitHubResultPublisher:
    def __init__(self, token: str) -> None:
        if not token.strip():
            raise ValueError("GitHub publication token is required")
        self.token = token

    def publish_evidence(
        self,
        *,
        repository: str,
        evidence: dict[str, Any],
    ) -> PublicationReceipt:
        identity = dict(evidence["identity"])
        sha = str(identity["commit_sha"])
        tasks = dict(evidence.get("tasks", {}))
        contexts: list[str] = []
        for task_id, raw in sorted(tasks.items()):
            task = dict(raw)
            suite = str(task["suite"])
            scope = str(task["scope"])
            state = str(task["state"])
            context = f"Shared Lab / {suite} / {scope}"
            self._post_status(
                repository=repository,
                sha=sha,
                context=context,
                success=state == "PASS",
                description=(
                    "PASS from native QORE Shared Lab"
                    if state == "PASS"
                    else f"{state}: {task.get('failure_reason') or task_id}"
                )[:140],
            )
            contexts.append(context)
        return PublicationReceipt(
            repository=repository,
            commit_sha=sha,
            contexts_published=tuple(contexts),
        )

    def _post_status(
        self,
        *,
        repository: str,
        sha: str,
        context: str,
        success: bool,
        description: str,
    ) -> None:
        url = f"https://api.github.com/repos/{repository}/statuses/{sha}"
        payload = json.dumps(
            {
                "state": "success" if success else "failure",
                "context": context,
                "description": description,
            }
        ).encode()
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                parsed: dict[str, Any] = json.loads(response.read().decode())
                if parsed.get("sha") != sha:
                    raise RuntimeError("GitHub status response SHA mismatch")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub publication failed: {exc}") from exc
