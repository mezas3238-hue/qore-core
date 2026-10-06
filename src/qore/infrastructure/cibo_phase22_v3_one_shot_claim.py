"""Durable pre-outcome claim contract for Phase22 V3."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
    build_phase22_execution_claim,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v3_execution_authorization import (
    Phase22V3ExecutionAuthorization,
)
from qore.infrastructure.cibo_phase22_v3_execution_manifest import (
    build_phase22_v3_execution_manifest,
)
from qore.infrastructure.cibo_phase22_v3_store_contract import (
    PHASE22_V3_STORE_IDENTITIES,
    assert_phase22_v3_store_pristine,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class Phase22V3OneShotClaimReceipt:
    candidate_id: str
    execution_manifest_sha256: str
    execution_authorization_sha256: str
    runner_git_sha: str
    run_id: int
    run_attempt: int
    started_at: datetime
    trader_ids: tuple[str, ...]
    store_paths: tuple[str, ...]
    durable_claim_required_before_fresh_access: bool = True
    productive_authority: bool = False

    def __post_init__(self) -> None:
        manifest = build_phase22_v3_execution_manifest()
        if self.candidate_id != manifest.candidate_id:
            raise CiboCapitalManagementError("V3 claim candidate drift")
        if self.execution_manifest_sha256 != manifest.fingerprint():
            raise CiboCapitalManagementError("V3 claim manifest drift")
        if _SHA256_RE.fullmatch(self.execution_authorization_sha256) is None:
            raise CiboCapitalManagementError("V3 authorization digest invalid")
        if _SHA_RE.fullmatch(self.runner_git_sha) is None:
            raise CiboCapitalManagementError("V3 runner SHA invalid")
        if self.run_id <= 0 or self.run_attempt <= 0:
            raise CiboCapitalManagementError("V3 run lease invalid")
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise CiboCapitalManagementError("V3 claim time must be aware")
        if self.trader_ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError("V3 claim requires 7/7 Traders")
        expected = tuple(item.relative_path for item in PHASE22_V3_STORE_IDENTITIES)
        if self.store_paths != expected:
            raise CiboCapitalManagementError("V3 claim store surface drift")
        if not self.durable_claim_required_before_fresh_access:
            raise CiboCapitalManagementError("V3 durable claim is mandatory")
        if self.productive_authority:
            raise CiboCapitalManagementError("V3 claim grants no authority")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def consumption_claim(self) -> Phase22ExecutionConsumptionReceipt:
        return build_phase22_execution_claim(
            candidate_id=self.candidate_id,
            execution_manifest_sha256=self.execution_manifest_sha256,
            claim_head_sha=self.runner_git_sha,
            claim_run_id=self.run_id,
            claim_run_attempt=self.run_attempt,
        )


def build_phase22_v3_one_shot_claim_receipt(
    *,
    authorization: Phase22V3ExecutionAuthorization,
    runner_git_sha: str,
    run_id: int,
    run_attempt: int,
    started_at: datetime,
    store_root: Path,
) -> Phase22V3OneShotClaimReceipt:
    if not isinstance(authorization, Phase22V3ExecutionAuthorization):
        raise CiboCapitalManagementError("canonical V3 authorization required")
    assert_phase22_v3_store_pristine(store_root)
    manifest = build_phase22_v3_execution_manifest()
    return Phase22V3OneShotClaimReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        execution_authorization_sha256=authorization.fingerprint(),
        runner_git_sha=runner_git_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        started_at=started_at,
        trader_ids=CANONICAL_PHASE22_TRADER_IDS,
        store_paths=tuple(
            item.relative_path for item in PHASE22_V3_STORE_IDENTITIES
        ),
    )
