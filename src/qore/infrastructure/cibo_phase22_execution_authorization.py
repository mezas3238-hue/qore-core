"""Explicit activation barrier for the irreversible Phase22 V2 one-shot.

The activation commit is separate from the durable claim commit. It records
Owner authorization, binds the exact pre-activation scientific HEAD, and grants
only one historical fresh-holdout execution on the sovereign integration branch.
It never grants broker mutation, LIVE, real-capital, merge, or productive authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
)
from qore.infrastructure.cibo_phase22_git_durable_claim import (
    EXACT_CLAIM_PATHS,
)

AUTHORIZATION_ID = "CIBO_PHASE22_V2_ONE_SHOT_OWNER_AUTHORIZATION_V1"
AUTHORIZATION_SCHEMA = "qore.cibo.phase22.execution-authorization.v1"
AUTHORIZATION_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V2-EXECUTION-AUTHORIZATION.json"
)
SOVEREIGN_BRANCH = "agent/cibo-integrator-ab-001"
EXACT_ACTIVATION_PATHS = (AUTHORIZATION_RELATIVE_PATH,)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class Phase22ExecutionAuthorization:
    authorization_id: str
    candidate_id: str
    authorized_parent_head_sha: str
    target_branch: str
    fresh_holdout_execution_authorized: bool
    one_shot_only: bool
    second_execution_authorized: bool
    broker_mutation_authorized: bool
    live_authorized: bool
    real_capital_authorized: bool
    merge_authorized: bool
    productive_authority: bool

    def __post_init__(self) -> None:
        if self.authorization_id != AUTHORIZATION_ID:
            raise CiboCapitalManagementError(
                "Phase22 execution authorization identity drift"
            )
        if self.candidate_id != ACTIVE_USD60_HOLDOUT_CANDIDATE.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 execution authorization candidate drift"
            )
        if _SHA1_RE.fullmatch(self.authorized_parent_head_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 execution authorization parent SHA invalid"
            )
        if self.target_branch != SOVEREIGN_BRANCH:
            raise CiboCapitalManagementError(
                "Phase22 execution authorization branch drift"
            )
        if not self.fresh_holdout_execution_authorized or not self.one_shot_only:
            raise CiboCapitalManagementError(
                "Phase22 execution authorization must be explicit and one-shot"
            )
        if any(
            (
                self.second_execution_authorized,
                self.broker_mutation_authorized,
                self.live_authorized,
                self.real_capital_authorized,
                self.merge_authorized,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 execution authorization governance contamination"
            )

    def payload(self) -> dict[str, object]:
        return {"schema": AUTHORIZATION_SCHEMA, **asdict(self)}

    def fingerprint(self) -> str:
        return _canonical_sha(self.payload())


@dataclass(frozen=True, slots=True)
class Phase22ExecutionActivationEvidence:
    authorized_parent_head_sha: str
    activation_commit_sha: str
    remote_head_sha: str
    target_branch: str
    authorization_sha256: str
    changed_paths: tuple[str, ...]
    parent_authorization_absent: bool
    claim_files_absent: bool
    working_tree_clean: bool
    remote_activation_observed: bool
    ready_to_create_durable_claim: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.authorized_parent_head_sha,
            self.activation_commit_sha,
            self.remote_head_sha,
        ):
            if _SHA1_RE.fullmatch(value) is None:
                raise CiboCapitalManagementError(
                    "Phase22 activation Git SHA invalid"
                )
        if self.activation_commit_sha != self.remote_head_sha:
            raise CiboCapitalManagementError(
                "Phase22 activation is not remote branch HEAD"
            )
        if self.target_branch != SOVEREIGN_BRANCH:
            raise CiboCapitalManagementError(
                "Phase22 activation branch drift"
            )
        if not self.authorization_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "Phase22 activation authorization digest invalid"
            )
        if self.changed_paths != EXACT_ACTIVATION_PATHS:
            raise CiboCapitalManagementError(
                "Phase22 activation commit changed non-authorization files"
            )
        if not all(
            (
                self.parent_authorization_absent,
                self.claim_files_absent,
                self.working_tree_clean,
                self.remote_activation_observed,
                self.ready_to_create_durable_claim,
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 activation proof incomplete"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 activation grants no productive authority"
            )


def build_phase22_execution_authorization(
    *,
    authorized_parent_head_sha: str,
) -> Phase22ExecutionAuthorization:
    return Phase22ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        candidate_id=ACTIVE_USD60_HOLDOUT_CANDIDATE.candidate_id,
        authorized_parent_head_sha=authorized_parent_head_sha,
        target_branch=SOVEREIGN_BRANCH,
        fresh_holdout_execution_authorized=True,
        one_shot_only=True,
        second_execution_authorized=False,
        broker_mutation_authorized=False,
        live_authorized=False,
        real_capital_authorized=False,
        merge_authorized=False,
        productive_authority=False,
    )


def load_phase22_execution_authorization(
    path: Path,
) -> Phase22ExecutionAuthorization:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != AUTHORIZATION_SCHEMA:
        raise CiboCapitalManagementError(
            "Phase22 execution authorization schema drift"
        )
    fields = dict(raw)
    fields.pop("schema", None)
    return Phase22ExecutionAuthorization(**fields)


def verify_phase22_execution_activation(
    *,
    repo_root: Path,
    remote_name: str = "origin",
) -> Phase22ExecutionActivationEvidence:
    repo_root = repo_root.resolve()
    authorization_path = repo_root / AUTHORIZATION_RELATIVE_PATH
    authorization = load_phase22_execution_authorization(authorization_path)

    current_head = _git(repo_root, "rev-parse", "HEAD")
    parent_line = _git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD")
    parts = parent_line.split()
    if len(parts) != 2 or parts[0] != current_head:
        raise CiboCapitalManagementError(
            "Phase22 activation commit must have exactly one parent"
        )
    parent_head = parts[1]
    if parent_head != authorization.authorized_parent_head_sha:
        raise CiboCapitalManagementError(
            "Phase22 activation parent/source lineage drift"
        )

    changed = tuple(
        sorted(
            item
            for item in _git(
                repo_root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ).splitlines()
            if item
        )
    )
    if changed != EXACT_ACTIVATION_PATHS:
        raise CiboCapitalManagementError(
            "Phase22 activation commit changed non-authorization files"
        )

    parent_authorization_absent = not _git_object_exists(
        repo_root,
        f"HEAD^:{AUTHORIZATION_RELATIVE_PATH}",
    )
    if not parent_authorization_absent:
        raise CiboCapitalManagementError(
            "Phase22 activation authorization existed in parent"
        )
    claim_files_absent = all(
        not (repo_root / path).exists() for path in EXACT_CLAIM_PATHS
    )
    if not claim_files_absent:
        raise CiboCapitalManagementError(
            "Phase22 activation found pre-existing claim files"
        )

    status = _git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise CiboCapitalManagementError(
            "Phase22 activation checkout is not clean"
        )

    remote_head = _remote_branch_head(
        repo_root=repo_root,
        remote_name=remote_name,
        branch_name=authorization.target_branch,
    )
    if remote_head != current_head:
        raise CiboCapitalManagementError(
            "Phase22 activation is not remote branch HEAD"
        )

    return Phase22ExecutionActivationEvidence(
        authorized_parent_head_sha=parent_head,
        activation_commit_sha=current_head,
        remote_head_sha=remote_head,
        target_branch=authorization.target_branch,
        authorization_sha256=authorization.fingerprint(),
        changed_paths=changed,
        parent_authorization_absent=parent_authorization_absent,
        claim_files_absent=claim_files_absent,
        working_tree_clean=True,
        remote_activation_observed=True,
        ready_to_create_durable_claim=True,
    )


def _remote_branch_head(
    *,
    repo_root: Path,
    remote_name: str,
    branch_name: str,
) -> str:
    output = _git(
        repo_root,
        "ls-remote",
        remote_name,
        f"refs/heads/{branch_name}",
    )
    rows = [line for line in output.splitlines() if line.strip()]
    if len(rows) != 1:
        raise CiboCapitalManagementError(
            "Phase22 activation remote branch identity unavailable"
        )
    sha, ref = rows[0].split("\t", maxsplit=1)
    if ref != f"refs/heads/{branch_name}" or _SHA1_RE.fullmatch(sha) is None:
        raise CiboCapitalManagementError(
            "Phase22 activation remote branch response invalid"
        )
    return sha


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ("git", "-C", str(repo_root), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_object_exists(repo_root: Path, spec: str) -> bool:
    completed = subprocess.run(
        ("git", "-C", str(repo_root), "cat-file", "-e", spec),
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _canonical_sha(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
