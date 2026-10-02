"""Git-backed durability proof for the Phase22 V2 one-shot claim.

The fresh holdout may be consumed only after the execution claim is committed
as an exact two-file Git commit and that commit is observed at the canonical
remote branch. This closes the gap between process-local atomic writes and a
claim that survives runner loss.
"""

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
    Phase22ExecutionConsumptionReceipt,
    load_phase22_execution_consumption_receipt,
    persist_phase22_execution_claim,
)
from qore.infrastructure.cibo_phase22_one_shot_batch import (
    Phase22OneShotClaimReceipt,
    build_phase22_one_shot_claim_receipt,
)

ONE_SHOT_CLAIM_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V2-ONE-SHOT-CLAIM.json"
)
CONSUMPTION_RECEIPT_RELATIVE_PATH = (
    "docs/research/CIBO-PHASE22-V2-CONSUMPTION-RECEIPT.json"
)
EXACT_CLAIM_PATHS = (
    CONSUMPTION_RECEIPT_RELATIVE_PATH,
    ONE_SHOT_CLAIM_RELATIVE_PATH,
)
_CLAIM_SCHEMA = "qore.cibo.phase22.git-durable-one-shot-claim.v1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22GitDurableClaimEvidence:
    source_head_sha: str
    claim_commit_sha: str
    remote_head_sha: str
    branch_name: str
    claim_receipt_sha256: str
    claim_file_sha256: str
    consumption_file_sha256: str
    changed_paths: tuple[str, ...]
    parent_claim_files_absent: bool
    working_tree_clean: bool
    remote_claim_observed: bool
    durable_claim_proven: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("source_head_sha", "claim_commit_sha", "remote_head_sha"):
            if _SHA1_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Phase22 Git durable claim {name} invalid"
                )
        for name in (
            "claim_receipt_sha256",
            "claim_file_sha256",
            "consumption_file_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"Phase22 Git durable claim {name} invalid"
                )
        if not self.branch_name:
            raise CiboCapitalManagementError(
                "Phase22 Git durable claim branch required"
            )
        if self.claim_commit_sha != self.remote_head_sha:
            raise CiboCapitalManagementError(
                "Phase22 Git durable claim is not remote branch HEAD"
            )
        if self.changed_paths != EXACT_CLAIM_PATHS:
            raise CiboCapitalManagementError(
                "Phase22 Git durable claim must change exact two claim files"
            )
        if not all(
            (
                self.parent_claim_files_absent,
                self.working_tree_clean,
                self.remote_claim_observed,
                self.durable_claim_proven,
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 Git durable claim proof is incomplete"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 Git durable claim grants no productive authority"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def phase22_one_shot_claim_payload(
    claim: Phase22OneShotClaimReceipt,
) -> dict[str, Any]:
    if not isinstance(claim, Phase22OneShotClaimReceipt):
        raise TypeError("Phase22 Git claim requires canonical one-shot receipt")
    payload = asdict(claim)
    payload["started_at"] = claim.started_at.isoformat()
    return {"schema": _CLAIM_SCHEMA, **payload}


def load_phase22_one_shot_claim_receipt(
    path: Path,
) -> Phase22OneShotClaimReceipt:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != _CLAIM_SCHEMA:
        raise CiboCapitalManagementError(
            "Phase22 Git one-shot claim schema drift"
        )
    fields = dict(raw)
    fields.pop("schema", None)
    started_at = datetime.fromisoformat(str(fields.pop("started_at")))
    trader_ids = fields.get("trader_ids")
    store_paths = fields.get("store_paths")
    if not isinstance(trader_ids, list) or not isinstance(store_paths, list):
        raise CiboCapitalManagementError(
            "Phase22 Git one-shot claim ordered surfaces invalid"
        )
    fields["trader_ids"] = tuple(str(item) for item in trader_ids)
    fields["store_paths"] = tuple(str(item) for item in store_paths)
    return Phase22OneShotClaimReceipt(started_at=started_at, **fields)


def prepare_phase22_git_claim_files(
    *,
    repo_root: Path,
    runner_git_sha: str,
    run_id: int,
    run_attempt: int,
    started_at: datetime,
    store_root: Path,
) -> tuple[Phase22OneShotClaimReceipt, Phase22ExecutionConsumptionReceipt]:
    """Create the two uncommitted claim files; never access fresh outcomes."""

    repo_root = repo_root.resolve()
    claim_path = repo_root / ONE_SHOT_CLAIM_RELATIVE_PATH
    consumption_path = repo_root / CONSUMPTION_RECEIPT_RELATIVE_PATH
    if claim_path.exists() or consumption_path.exists():
        raise FileExistsError(
            "Phase22 Git claim files already exist; one-shot must fail closed"
        )
    if _git(repo_root, "rev-parse", "HEAD") != runner_git_sha:
        raise CiboCapitalManagementError(
            "Phase22 Git claim runner HEAD drift before claim creation"
        )

    claim = build_phase22_one_shot_claim_receipt(
        runner_git_sha=runner_git_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        started_at=started_at,
        store_root=store_root,
    )
    consumption = claim.consumption_claim()
    persist_phase22_execution_claim(claim=consumption, path=consumption_path)
    _create_once_json(claim_path, phase22_one_shot_claim_payload(claim))
    return claim, consumption


def verify_phase22_git_durable_claim(
    *,
    repo_root: Path,
    branch_name: str,
    remote_name: str = "origin",
) -> Phase22GitDurableClaimEvidence:
    """Prove the claim is an immutable remote Git barrier before fresh access."""

    repo_root = repo_root.resolve()
    claim_path = repo_root / ONE_SHOT_CLAIM_RELATIVE_PATH
    consumption_path = repo_root / CONSUMPTION_RECEIPT_RELATIVE_PATH
    claim = load_phase22_one_shot_claim_receipt(claim_path)
    consumption = load_phase22_execution_consumption_receipt(consumption_path)
    if consumption is None:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim missing consumption receipt"
        )
    if consumption != claim.consumption_claim():
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim/consumption lineage mismatch"
        )
    if consumption.outcomes_emitted:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim verifier requires pre-outcome CLAIMED state"
        )

    current_head = _git(repo_root, "rev-parse", "HEAD")
    parent_line = _git(repo_root, "rev-list", "--parents", "-n", "1", "HEAD")
    parent_parts = parent_line.split()
    if len(parent_parts) != 2 or parent_parts[0] != current_head:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim commit must have exactly one parent"
        )
    source_head = parent_parts[1]
    if (
        source_head != claim.runner_git_sha
        or source_head != consumption.claim_head_sha
    ):
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim parent/source lineage drift"
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
    if changed != EXACT_CLAIM_PATHS:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim commit changed non-claim files"
        )

    parent_absent = all(
        not _git_object_exists(repo_root, f"HEAD^:{path}")
        for path in EXACT_CLAIM_PATHS
    )
    if not parent_absent:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim files existed in parent; create-once violated"
        )

    status = _git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim checkout is not clean"
        )
    for relative_path in EXACT_CLAIM_PATHS:
        committed = _git(repo_root, "show", f"HEAD:{relative_path}") + "\n"
        working = (repo_root / relative_path).read_text(encoding="utf-8")
        if committed != working:
            raise CiboCapitalManagementError(
                "Phase22 Git durable claim worktree/commit content drift"
            )

    remote_head = _remote_branch_head(
        repo_root=repo_root,
        remote_name=remote_name,
        branch_name=branch_name,
    )
    if remote_head != current_head:
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim is not durably observed at remote branch HEAD"
        )

    return Phase22GitDurableClaimEvidence(
        source_head_sha=source_head,
        claim_commit_sha=current_head,
        remote_head_sha=remote_head,
        branch_name=branch_name,
        claim_receipt_sha256=claim.fingerprint(),
        claim_file_sha256=_file_sha256(claim_path),
        consumption_file_sha256=_file_sha256(consumption_path),
        changed_paths=changed,
        parent_claim_files_absent=parent_absent,
        working_tree_clean=True,
        remote_claim_observed=True,
        durable_claim_proven=True,
    )


def durable_claim_evidence_payload(
    evidence: Phase22GitDurableClaimEvidence,
) -> dict[str, Any]:
    if not isinstance(evidence, Phase22GitDurableClaimEvidence):
        raise TypeError("Phase22 Git durability evidence required")
    return {
        "schema": "qore.cibo.phase22.git-durable-claim-evidence.v1",
        **asdict(evidence),
        "fingerprint": evidence.fingerprint(),
    }


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
            "Phase22 Git durable claim remote branch identity unavailable"
        )
    sha, ref = rows[0].split("\t", maxsplit=1)
    if (
        ref != f"refs/heads/{branch_name}"
        or _SHA1_RE.fullmatch(sha) is None
    ):
        raise CiboCapitalManagementError(
            "Phase22 Git durable claim remote branch response invalid"
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


def _create_once_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"Phase22 create-once path exists: {path}")
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
