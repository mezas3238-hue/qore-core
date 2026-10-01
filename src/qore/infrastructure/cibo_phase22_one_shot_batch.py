"""Irreversible one-shot batch contract for the Phase22 V2 holdout.

The first fresh-outcome access burns V2 even if a later Trader or downstream
capital stage fails. The burn receipt therefore must be persisted immediately
before the first fresh engine is invoked. It binds the exact execution manifest,
provider calibration, seven-Trader surface and five pristine Phase22 stores.

This module does not itself execute Trader logic or persist the burn receipt.
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
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
)
from qore.infrastructure.cibo_phase22_one_shot_guard import (
    Phase22ExecutionConsumptionReceipt,
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
class Phase22OneShotBurnReceipt:
    candidate_id: str
    execution_manifest_sha256: str
    provider_execution_calibration_sha256: str
    runner_git_sha: str
    started_at: datetime
    trader_ids: tuple[str, ...]
    store_paths: tuple[str, ...]
    fresh_outcome_access_started: bool
    holdout_consumed: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        manifest = build_phase22_execution_manifest()
        if self.candidate_id != manifest.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn candidate drift"
            )
        if self.execution_manifest_sha256 != manifest.fingerprint():
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn manifest drift"
            )
        if self.provider_execution_calibration_sha256 != (
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ):
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn provider calibration drift"
            )
        if _SHA_RE.fullmatch(self.runner_git_sha) is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn runner Git SHA invalid"
            )
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn start time must be timezone-aware"
            )
        if self.trader_ids != CANONICAL_PHASE22_TRADER_IDS:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn requires exact ordered 7/7 Traders"
            )
        expected_paths = tuple(
            item.relative_path for item in PHASE22_STORE_IDENTITIES
        )
        if self.store_paths != expected_paths:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn store surface drift"
            )
        if not self.fresh_outcome_access_started or not self.holdout_consumed:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn must conservatively consume V2 at start"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Phase22 one-shot burn grants no productive authority"
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

    def consumption_receipt(self) -> Phase22ExecutionConsumptionReceipt:
        return Phase22ExecutionConsumptionReceipt(
            candidate_id=self.candidate_id,
            execution_manifest_sha256=self.execution_manifest_sha256,
            outcomes_emitted=True,
        )


@dataclass(frozen=True, slots=True)
class Phase22OneShotBatchCompletionReceipt:
    burn_receipt_sha256: str
    trader_artifact_sha256s: tuple[tuple[str, str], ...]
    store_sha256s: tuple[tuple[str, str], ...]
    completed_at: datetime
    all_traders_completed: bool
    all_stores_sealed: bool
    fresh_outcomes_emitted: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if _SHA256_RE.fullmatch(self.burn_receipt_sha256) is None:
            raise CiboCapitalManagementError(
                "Phase22 one-shot completion burn digest invalid"
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


def build_phase22_one_shot_burn_receipt(
    *,
    runner_git_sha: str,
    started_at: datetime,
    store_root: Path,
) -> Phase22OneShotBurnReceipt:
    guard = assess_phase22_one_shot_guard()
    if (
        guard.status is not Phase22OneShotGuardStatus.READY
        or not guard.authorized_to_emit_first_fresh_outcome
        or guard.blockers
    ):
        raise CiboCapitalManagementError(
            "Phase22 one-shot burn requires READY guard"
        )
    bundle = build_phase22_store_bundle(store_root)
    bundle.assert_pristine()
    manifest = build_phase22_execution_manifest()
    return Phase22OneShotBurnReceipt(
        candidate_id=manifest.candidate_id,
        execution_manifest_sha256=manifest.fingerprint(),
        provider_execution_calibration_sha256=(
            PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT.fingerprint()
        ),
        runner_git_sha=runner_git_sha,
        started_at=started_at,
        trader_ids=CANONICAL_PHASE22_TRADER_IDS,
        store_paths=tuple(
            item.relative_path for item in PHASE22_STORE_IDENTITIES
        ),
        fresh_outcome_access_started=True,
        holdout_consumed=True,
        productive_authority=False,
    )
