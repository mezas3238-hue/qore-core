from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_execution_authorization import (
    AUTHORIZATION_RELATIVE_PATH,
    EXACT_ACTIVATION_PATHS,
    SOVEREIGN_BRANCH,
    build_phase22_execution_authorization,
    verify_phase22_execution_activation,
)

BRANCH = SOVEREIGN_BRANCH


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "work"
    subprocess.run(("git", "init", "--bare", str(remote)), check=True)
    subprocess.run(("git", "init", "-b", BRANCH, str(repo)), check=True)
    _git(repo, "config", "user.name", "QORE Test")
    _git(repo, "config", "user.email", "qore@example.invalid")
    (repo / "source.txt").write_text("frozen\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-m", "scientific source")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", BRANCH)
    return repo, _git(repo, "rev-parse", "HEAD")


def _commit_activation(
    repo: Path,
    parent: str,
    *,
    extra_path: bool = False,
) -> str:
    authorization = build_phase22_execution_authorization(
        authorized_parent_head_sha=parent,
    )
    path = repo / AUTHORIZATION_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(authorization.payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", AUTHORIZATION_RELATIVE_PATH)
    if extra_path:
        (repo / "extra.txt").write_text("forbidden\n", encoding="utf-8")
        _git(repo, "add", "extra.txt")
    _git(repo, "commit", "-m", "authorize Phase22 V2 one-shot")
    activation = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "origin", f"HEAD:{BRANCH}")
    return activation


def test_activation_proves_exact_remote_one_file_barrier(
    tmp_path: Path,
) -> None:
    repo, parent = _repo(tmp_path)
    activation = _commit_activation(repo, parent)

    evidence = verify_phase22_execution_activation(repo_root=repo)

    assert evidence.authorized_parent_head_sha == parent
    assert evidence.activation_commit_sha == activation
    assert evidence.remote_head_sha == activation
    assert evidence.changed_paths == EXACT_ACTIVATION_PATHS
    assert evidence.parent_authorization_absent is True
    assert evidence.claim_files_absent is True
    assert evidence.working_tree_clean is True
    assert evidence.remote_activation_observed is True
    assert evidence.ready_to_create_durable_claim is True
    assert evidence.productive_authority is False


def test_activation_rejects_extra_changed_path(tmp_path: Path) -> None:
    repo, parent = _repo(tmp_path)
    _commit_activation(repo, parent, extra_path=True)

    with pytest.raises(
        CiboCapitalManagementError,
        match="changed non-authorization files",
    ):
        verify_phase22_execution_activation(repo_root=repo)


def test_activation_rejects_remote_branch_advance(tmp_path: Path) -> None:
    repo, parent = _repo(tmp_path)
    activation = _commit_activation(repo, parent)
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    _git(repo, "add", "later.txt")
    _git(repo, "commit", "-m", "advance")
    _git(repo, "push", "origin", f"HEAD:{BRANCH}")
    _git(repo, "checkout", "--detach", activation)

    with pytest.raises(
        CiboCapitalManagementError,
        match="not remote branch HEAD",
    ):
        verify_phase22_execution_activation(repo_root=repo)
