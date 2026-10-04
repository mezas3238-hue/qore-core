"""Exact-SHA repository and isolated worktree runtime for QORE Shared Lab."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    repository: str
    repo_root: str
    commit_sha: str
    branch: str


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


class RepositoryRuntime:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path.resolve()
        if not (self.repo_path / ".git").exists():
            top = _git(self.repo_path, "rev-parse", "--show-toplevel")
            self.repo_path = Path(top)

    def resolve(
        self,
        *,
        repository: str,
        commit_sha: str,
        branch: str,
    ) -> RepositorySnapshot:
        resolved = _git(
            self.repo_path,
            "rev-parse",
            "--verify",
            f"{commit_sha}^{{commit}}",
        )
        if len(resolved) != 40:
            raise ValueError("resolved commit SHA must be a full 40-character SHA")
        if not resolved.startswith(commit_sha):
            raise ValueError("resolved commit does not match requested SHA")
        return RepositorySnapshot(
            repository=repository,
            repo_root=str(self.repo_path),
            commit_sha=resolved,
            branch=branch,
        )

    def changed_paths(self, base_sha: str, target_sha: str) -> tuple[str, ...]:
        base = _git(
            self.repo_path,
            "rev-parse",
            "--verify",
            f"{base_sha}^{{commit}}",
        )
        target = _git(
            self.repo_path,
            "rev-parse",
            "--verify",
            f"{target_sha}^{{commit}}",
        )
        raw = _git(self.repo_path, "diff", "--name-only", f"{base}..{target}")
        return tuple(line for line in raw.splitlines() if line.strip())

    @contextmanager
    def worktree(self, commit_sha: str) -> Iterator[Path]:
        temp_root = Path(tempfile.mkdtemp(prefix="qore-shared-lab-"))
        worktree = temp_root / "worktree"
        try:
            subprocess.run(
                (
                    "git",
                    "-C",
                    str(self.repo_path),
                    "worktree",
                    "add",
                    "--detach",
                    str(worktree),
                    commit_sha,
                ),
                check=True,
                capture_output=True,
                text=True,
            )
            actual = _git(worktree, "rev-parse", "HEAD")
            if actual != commit_sha:
                raise RuntimeError("worktree HEAD does not equal requested commit SHA")
            yield worktree
        finally:
            if worktree.exists():
                subprocess.run(
                    (
                        "git",
                        "-C",
                        str(self.repo_path),
                        "worktree",
                        "remove",
                        "--force",
                        str(worktree),
                    ),
                    check=False,
                    capture_output=True,
                    text=True,
                )
            shutil.rmtree(temp_root, ignore_errors=True)
