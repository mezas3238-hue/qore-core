"""Git-backed durability barrier for the Phase22 V4 one-shot."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    load_phase22_execution_consumption_receipt,
    persist_phase22_execution_claim,
)
from qore.infrastructure.cibo_phase22_v4_execution_authorization import (
    AUTHORIZATION_RELATIVE_PATH,
    load_phase22_v4_execution_authorization,
)
from qore.infrastructure.cibo_phase22_v4_one_shot_claim import (
    Phase22V4OneShotClaimReceipt,
    build_phase22_v4_one_shot_claim_receipt,
)

ONE_SHOT_CLAIM_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V4-ONE-SHOT-CLAIM.json"
)
CONSUMPTION_RECEIPT_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V4-CONSUMPTION-RECEIPT.json"
)
EXACT_CLAIM_PATHS = (
    CONSUMPTION_RECEIPT_RELATIVE_PATH,
    ONE_SHOT_CLAIM_RELATIVE_PATH,
)
_CLAIM_SCHEMA = "qore.cibo.phase22.v4-git-durable-one-shot-claim.v1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22V4GitDurableClaimEvidence:
    source_head_sha: str
    claim_commit_sha: str
    remote_head_sha: str
    branch_name: str
    claim_receipt_sha256: str
    claim_file_sha256: str
    consumption_file_sha256: str
    changed_paths: tuple[str, ...]
    remote_claim_observed: bool
    durable_claim_proven: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("source_head_sha", "claim_commit_sha", "remote_head_sha"):
            if _SHA1_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V4 durable claim {name} invalid"
                )
        for name in (
            "claim_receipt_sha256",
            "claim_file_sha256",
            "consumption_file_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"V4 durable claim {name} invalid"
                )
        if self.claim_commit_sha != self.remote_head_sha:
            raise CiboCapitalManagementError("V4 claim is not remote branch HEAD")
        if self.changed_paths != EXACT_CLAIM_PATHS:
            raise CiboCapitalManagementError(
                "V4 claim commit must change exact two files"
            )
        if not self.remote_claim_observed or not self.durable_claim_proven:
            raise CiboCapitalManagementError("V4 durable claim proof incomplete")
        if self.productive_authority:
            raise CiboCapitalManagementError("V4 durable claim grants no authority")

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def phase22_v4_claim_payload(
    claim: Phase22V4OneShotClaimReceipt,
) -> dict[str, Any]:
    payload = asdict(claim)
    payload["started_at"] = claim.started_at.isoformat()
    return {"schema": _CLAIM_SCHEMA, **payload}


def load_phase22_v4_one_shot_claim(
    path: Path,
) -> Phase22V4OneShotClaimReceipt:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != _CLAIM_SCHEMA:
        raise CiboCapitalManagementError("V4 claim schema drift")
    fields = dict(raw)
    fields.pop("schema", None)
    fields["started_at"] = datetime.fromisoformat(str(fields["started_at"]))
    fields["trader_ids"] = tuple(str(x) for x in fields["trader_ids"])
    fields["store_paths"] = tuple(str(x) for x in fields["store_paths"])
    return Phase22V4OneShotClaimReceipt(**fields)


def prepare_phase22_v4_git_claim_files(
    *,
    repo_root: Path,
    runner_git_sha: str,
    run_id: int,
    run_attempt: int,
    started_at: datetime,
    store_root: Path,
) -> Phase22V4OneShotClaimReceipt:
    repo_root = repo_root.resolve()
    claim_path = repo_root / ONE_SHOT_CLAIM_RELATIVE_PATH
    consumption_path = repo_root / CONSUMPTION_RECEIPT_RELATIVE_PATH
    if claim_path.exists() or consumption_path.exists():
        raise FileExistsError("V4 claim already exists")
    if _git(repo_root, "rev-parse", "HEAD") != runner_git_sha:
        raise CiboCapitalManagementError("V4 runner HEAD drift")

    authorization = load_phase22_v4_execution_authorization(
        repo_root / AUTHORIZATION_RELATIVE_PATH
    )
    parent = _git(repo_root, "rev-parse", "HEAD^")
    if parent != authorization.authorized_parent_head_sha:
        raise CiboCapitalManagementError("V4 authorization parent HEAD drift")
    changed = tuple(
        sorted(
            x
            for x in _git(
                repo_root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ).splitlines()
            if x
        )
    )
    if changed != (AUTHORIZATION_RELATIVE_PATH,):
        raise CiboCapitalManagementError(
            "V4 authorization commit must change exact authorization file"
        )

    claim = build_phase22_v4_one_shot_claim_receipt(
        authorization=authorization,
        runner_git_sha=runner_git_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        started_at=started_at,
        store_root=store_root,
    )
    persist_phase22_execution_claim(
        claim=claim.consumption_claim(),
        path=consumption_path,
    )
    _create_once_json(claim_path, phase22_v4_claim_payload(claim))
    return claim


def verify_phase22_v4_git_durable_claim(
    *,
    repo_root: Path,
    branch_name: str,
    remote_name: str = "origin",
    expected_run_id: int | None = None,
    expected_run_attempt: int | None = None,
) -> Phase22V4GitDurableClaimEvidence:
    repo_root = repo_root.resolve()
    claim_path = repo_root / ONE_SHOT_CLAIM_RELATIVE_PATH
    consumption_path = repo_root / CONSUMPTION_RECEIPT_RELATIVE_PATH
    claim = load_phase22_v4_one_shot_claim(claim_path)
    consumption = load_phase22_execution_consumption_receipt(consumption_path)
    if consumption is None or consumption != claim.consumption_claim():
        raise CiboCapitalManagementError("V4 claim/consumption lineage mismatch")
    if consumption.outcomes_emitted:
        raise CiboCapitalManagementError(
            "V4 durable verifier requires CLAIMED state"
        )
    if expected_run_id is not None:
        if (
            expected_run_attempt is None
            or claim.run_id != expected_run_id
            or claim.run_attempt != expected_run_attempt
        ):
            raise CiboCapitalManagementError("V4 execution lease mismatch")

    current = _git(repo_root, "rev-parse", "HEAD")
    parent = _git(repo_root, "rev-parse", "HEAD^")
    if parent != claim.runner_git_sha or parent != consumption.claim_head_sha:
        raise CiboCapitalManagementError("V4 claim parent lineage drift")
    changed = tuple(
        sorted(
            x
            for x in _git(
                repo_root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ).splitlines()
            if x
        )
    )
    if changed != EXACT_CLAIM_PATHS:
        raise CiboCapitalManagementError(
            "V4 claim commit changed non-claim files"
        )
    if any(
        _git_object_exists(repo_root, f"HEAD^:{path}")
        for path in EXACT_CLAIM_PATHS
    ):
        raise CiboCapitalManagementError("V4 claim files existed in parent")
    if _git(repo_root, "status", "--porcelain", "--untracked-files=all"):
        raise CiboCapitalManagementError("V4 claim checkout not clean")

    remote = _remote_branch_head(
        repo_root=repo_root,
        remote_name=remote_name,
        branch_name=branch_name,
    )
    if remote != current:
        raise CiboCapitalManagementError(
            "V4 claim not durably observed at remote HEAD"
        )
    return Phase22V4GitDurableClaimEvidence(
        source_head_sha=parent,
        claim_commit_sha=current,
        remote_head_sha=remote,
        branch_name=branch_name,
        claim_receipt_sha256=claim.fingerprint(),
        claim_file_sha256=_file_sha256(claim_path),
        consumption_file_sha256=_file_sha256(consumption_path),
        changed_paths=changed,
        remote_claim_observed=True,
        durable_claim_proven=True,
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
        raise CiboCapitalManagementError("V4 remote branch unavailable")
    sha, ref = rows[0].split("\t", maxsplit=1)
    if ref != f"refs/heads/{branch_name}" or _SHA1_RE.fullmatch(sha) is None:
        raise CiboCapitalManagementError("V4 remote branch response invalid")
    return sha


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repo_root), *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_object_exists(repo_root: Path, spec: str) -> bool:
    result = subprocess.run(
        ("git", "-C", str(repo_root), "cat-file", "-e", spec),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _create_once_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"V4 create-once path exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
