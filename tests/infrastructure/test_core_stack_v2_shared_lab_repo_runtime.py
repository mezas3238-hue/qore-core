import subprocess
from pathlib import Path

from qore.infrastructure.core_stack_v2.shared_lab_repo_runtime import RepositoryRuntime


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


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


def test_exact_sha_worktree_isolated_from_dirty_checkout(tmp_path: Path) -> None:
    repo, sha = make_repo(tmp_path)
    runtime = RepositoryRuntime(repo)
    snapshot = runtime.resolve(
        repository="owner/repo",
        commit_sha=sha[:12],
        branch="main",
    )
    assert snapshot.commit_sha == sha
    (repo / "component.txt").write_text("dirty\n")
    with runtime.worktree(sha) as worktree:
        assert git(worktree, "rev-parse", "HEAD") == sha
        assert (worktree / "component.txt").read_text() == "committed\n"
