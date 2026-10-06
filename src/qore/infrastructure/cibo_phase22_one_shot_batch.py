"""Crash-safe one-shot batch contract for the Phase22 V2 holdout.

A durable execution claim is the irreversible boundary. The claim must be
persisted and committed by orchestration before any fresh outcome is read.
A completed 7/7 batch can then finalize the same immutable claim as CONSUMED.
"""

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
    mark_phase22_outcomes_emitted,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_one_shot_guard import (
    Phase22OneShotGuardStatus,
    assess_phase22_one_shot_guard,
)
from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
)
from qore.infrastructure.cibo_phase22_store_bundle import (
    build_phase22_store_bundle,
)
from qore.infrastructure.cibo_phase22_store_contract import (
    PHASE22_STORE_IDENTITIES,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_STORE_ROLES = tuple(item.name for item in PHASE22_STORE_IDENTITIES)


@dataclass(frozen=True, slots=True)
class Phase22OneShotClaimReceipt:
    candidate_id: str
    execution_manifest_sha256: str
    provider_execution_calibration_sha256: str
    runner_git_sha: str
    run_id: int
    run_attempt: int
    started_at: datetime
    trader_ids: tuple[str, ...]
    store_paths: tuple[str, ...]
    durable_claim_required_before_fresh_access: bool = True
    productive_authority: bool = False

    def __post_init__(self) -> None:
        manifest = build_phase22_execution_manifest()
        if self.candidate_id != manifest.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim candidate drift"
            )
        if self.execution_manifest_sha256 != manifest.fingerprint():
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim manifest drift"
            )
        if self.provider_execution_calibration_sha256 != (
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim provider calibration drift"
            )
        if _SHA_RE.fullmatch(self.runner_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim runner Git SHA invalid"
            )
        if (
            not isinstance(self.run_id, int)
            or isinstance(self.run_id, bool)
            or self.run_id <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim run id invalid"
            )
        if (
            not isinstance(self.run_attempt, int)
            or isinstance(self.run_attempt, bool)
            or self.run_attempt <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim run attempt invalid"
            )
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim start time must be timezone-aware"
            )
        if self.trader_ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim requires exact ordered 7/7 Traders"
            )
        expected_paths = tuple(
            item.relative_path for item in PHASE22_STORE_IDENTITIES
        )
        if self.store_paths != expected_paths:
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim store surface drift"
            )
        if not self.durable_claim_required_before_fresh_access:
            raise CiboCapitalManagementError(
                "Phase22 fresh access cannot precede durable claim"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 one-shot claim grants no productive authority"
            )

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


@dataclass(frozen=True, slots=True)
class Phase22OneShotBatchCompletionReceipt:
    claim_receipt_sha256: str
    trader_artifact_sha256s: tuple[tuple[str, str], ...]
    store_sha256s: tuple[tuple[str, str], ...]
    completed_at: datetime
    all_traders_completed: bool
    all_stores_sealed: bool
    fresh_outcomes_emitted: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if _SHA256_RE.fullmatch(self.claim_receipt_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion claim digest invalid"
            )
        if tuple(name for name, _ in self.trader_artifact_sha256s) != (
            CANONICAL_PHASE22_TRADER_IDS
        ):
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion requires exact ordered 7/7 Traders"
            )
        if tuple(name for name, _ in self.store_sha256s) != _STORE_ROLES:
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion store role surface drift"
            )
        for _, digest in (
            self.trader_artifact_sha256s + self.store_sha256s
        ):
            if _SHA256_RE.fullmatch(digest) is None:
                raise CiboCapitalManagementError(
                    "Phase22 one-shot completion digest invalid"
                )
        if self.completed_at.tzinfo is None or self.completed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion time must be timezone-aware"
            )
        if not all(
            (
                self.all_traders_completed,
                self.all_stores_sealed,
                self.fresh_outcomes_emitted,
            )
        ):
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion cannot represent a partial batch"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion grants no productive authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["completed_at"] = self.completed_at.isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def consumed_receipt(
        self,
        *,
        claim: Phase22ExecutionConsumptionReceipt,
    ) -> Phase22ExecutionConsumptionReceipt:
        return mark_phase22_outcomes_emitted(
            claim=claim,
            outcome_bundle_sha256=self.fingerprint(),
        )


def build_phase22_one_shot_claim_receipt(
    *,
    runner_git_sha: str,
    run_id: int,
    run_attempt: int,
    started_at: datetime,
    store_root: Path,
) -> Phase22OneShotClaimReceipt:
    guard = assess_phase22_one_shot_guard()
    if (
        guard.status is not Phase22OneShotGuardStatus.READY
        or not guard.authorized_to_create_durable_claim
        or guard.authorized_to_emit_first_fresh_outcome
        or guard.blockers
    ):
        raise CiboCapitalManagementError(
            "Phase22 one-shot claim requires READY guard"
        )
    bundle = build_phase22_store_bundle(store_root)
    bundle.assert_pristine()
    manifest = build_phase22_execution_manifest()
    return Phase22OneShotClaimReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        provider_execution_calibration_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
        runner_git_sha=runner_git_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        started_at=started_at,
        trader_ids=CANONICAL_PHASE22_TRADER_IDS,
        store_paths=tuple(
            item.relative_path for item in PHASE22_STORE_IDENTITIES
        ),
    )
