from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_git_durable_claim import (
    CONSUMPTION_RECEIPT_RELATIVE_PATH,
    EXACT_CLAIM_PATHS,
    ONE_SHOT_CLAIM_RELATIVE_PATH,
    prepare_phase22_git_claim_files,
    verify_phase22_git_durable_claim,
)

BRANCH = "agent/cibo-integrator-ab-001"
NOW = datetime(2026, 10, 2, 3, 45, tzinfo=UTC)


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
    _git(repo, "commit", "-m", "source head")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", BRANCH)
    return repo, _git(repo, "rev-parse", "HEAD")


def _commit_claim(repo: Path, source_head: str) -> str:
    claim, consumption = prepare_phase22_git_claim_files(
        repo_root=repo,
        runner_git_sha=source_head,
        run_id=123456,
        run_attempt=1,
        started_at=NOW,
        store_root=repo / "phase22-v2-stores",
    )
    assert claim.runner_git_sha == source_head
    assert consumption.claim_committed is True
    assert consumption.outcomes_emitted is False
    _git(repo, "add", *EXACT_CLAIM_PATHS)
    _git(repo, "commit", "-m", "claim Phase22 V2 one-shot")
    claim_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "origin", f"HEAD:{BRANCH}")
    return claim_commit


def test_git_claim_is_remote_durable_before_fresh_access(
    tmp_path: Path,
) -> None:
    repo, source_head = _repo(tmp_path)
    claim_commit = _commit_claim(repo, source_head)

    evidence = verify_phase22_git_durable_claim(
        repo_root=repo,
        branch_name=BRANCH,
    )

    assert evidence.source_head_sha == source_head
    assert evidence.claim_commit_sha == claim_commit
    assert evidence.remote_head_sha == claim_commit
    assert evidence.changed_paths == EXACT_CLAIM_PATHS
    assert evidence.parent_claim_files_absent is True
    assert evidence.working_tree_clean is True
    assert evidence.remote_claim_observed is True
    assert evidence.durable_claim_proven is True
    assert evidence.productive_authority is False
    assert evidence.fingerprint().startswith("sha256:")


def test_git_claim_refuses_remote_branch_advance(tmp_path: Path) -> None:
    repo, source_head = _repo(tmp_path)
    claim_commit = _commit_claim(repo, source_head)
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    _git(repo, "add", "later.txt")
    _git(repo, "commit", "-m", "advance branch")
    _git(repo, "push", "origin", f"HEAD:{BRANCH}")
    _git(repo, "checkout", "--detach", claim_commit)

    with pytest.raises(
        CiboCapitalManagementError,
        match="not durably observed at remote branch HEAD",
    ):
        verify_phase22_git_durable_claim(
            repo_root=repo,
            branch_name=BRANCH,
        )


def test_git_claim_refuses_dirty_claim_checkout(tmp_path: Path) -> None:
    repo, source_head = _repo(tmp_path)
    _commit_claim(repo, source_head)
    claim_path = repo / ONE_SHOT_CLAIM_RELATIVE_PATH
    claim_path.write_text(
        claim_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="checkout is not clean",
    ):
        verify_phase22_git_durable_claim(
            repo_root=repo,
            branch_name=BRANCH,
        )


def test_git_claim_files_are_create_once(tmp_path: Path) -> None:
    repo, source_head = _repo(tmp_path)
    _commit_claim(repo, source_head)
    assert (repo / ONE_SHOT_CLAIM_RELATIVE_PATH).is_file()
    assert (repo / CONSUMPTION_RECEIPT_RELATIVE_PATH).is_file()

    with pytest.raises(FileExistsError, match="already exist"):
        prepare_phase22_git_claim_files(
            repo_root=repo,
            runner_git_sha=_git(repo, "rev-parse", "HEAD"),
            run_id=123457,
            run_attempt=1,
            started_at=NOW,
            store_root=repo / "phase22-v2-stores",
        )

def test_git_claim_execution_lease_refuses_rerun_attempt(
    tmp_path: Path,
) -> None:
    repo, source_head = _repo(tmp_path)
    _commit_claim(repo, source_head)

    with pytest.raises(
        CiboCapitalManagementError,
        match="execution lease mismatch",
    ):
        verify_phase22_git_durable_claim(
            repo_root=repo,
            branch_name=BRANCH,
            expected_run_id=123456,
            expected_run_attempt=2,
        )


def test_git_claim_execution_lease_accepts_original_attempt(
    tmp_path: Path,
) -> None:
    repo, source_head = _repo(tmp_path)
    _commit_claim(repo, source_head)

    evidence = verify_phase22_git_durable_claim(
        repo_root=repo,
        branch_name=BRANCH,
        expected_run_id=123456,
        expected_run_attempt=1,
    )

    assert evidence.durable_claim_proven is True

