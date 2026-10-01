"""Independent Architect-A intake for Phase22 V2 pre-outcome provenance."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
EXECUTION_SCHEMA = "qore.cibo.phase22.execution-manifest.v2"
STORE_SCHEMA = "qore.cibo.phase22.store-contract.v1"
CANONICAL_TRADER_IDS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
CANONICAL_STORE_PATHS = (
    "phase22-v2-stores/holdout-forward-evidence.json",
    "phase22-v2-stores/holdout-policy.json",
    "phase22-v2-stores/executed-risk.json",
    "phase22-v2-stores/cma-settlement.json",
    "phase22-v2-stores/t20-release.json",
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ArchitectAPhase22PreOutcomeReceipt:
    candidate_id: str
    execution_manifest_sha256: str
    source_receipt_sha256: str
    parity_manifest_sha256: str
    trader_ids: tuple[str, ...]
    store_paths: tuple[str, ...]
    one_shot_status: str
    guard_blockers: tuple[str, ...]
    authorized_to_emit_first_fresh_outcome: bool
    fresh_outcomes_already_emitted: bool
    ready_for_fresh_execution: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_id != CANDIDATE_ID:
            raise CiboCapitalManagementError("A pre-outcome candidate drift")
        for name in (
            "execution_manifest_sha256",
            "source_receipt_sha256",
            "parity_manifest_sha256",
        ):
            if _SHA256_RE.fullmatch(getattr(self, name)) is None:
                raise CiboCapitalManagementError(
                    f"A pre-outcome {name} invalid"
                )
        if self.trader_ids != CANONICAL_TRADER_IDS:
            raise CiboCapitalManagementError("A pre-outcome Trader surface drift")
        if self.store_paths != CANONICAL_STORE_PATHS:
            raise CiboCapitalManagementError("A pre-outcome store surface drift")
        if self.one_shot_status not in {"BLOCKED", "READY"}:
            raise CiboCapitalManagementError(
                "A pre-outcome one-shot status must be BLOCKED or READY"
            )
        if self.fresh_outcomes_already_emitted:
            raise CiboCapitalManagementError(
                "A pre-outcome receipt cannot follow emitted outcomes"
            )
        expected_ready = (
            self.one_shot_status == "READY"
            and not self.guard_blockers
            and self.authorized_to_emit_first_fresh_outcome
        )
        if self.ready_for_fresh_execution != expected_ready:
            raise CiboCapitalManagementError("A pre-outcome readiness drift")
        if self.one_shot_status == "BLOCKED":
            if (
                not self.guard_blockers
                or self.authorized_to_emit_first_fresh_outcome
            ):
                raise CiboCapitalManagementError(
                    "A blocked pre-outcome receipt requires blockers/no authorization"
                )
        if self.one_shot_status == "READY" and self.guard_blockers:
            raise CiboCapitalManagementError(
                "A ready pre-outcome receipt cannot retain blockers"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "A pre-outcome receipt grants no productive authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            {
                "candidate_id": self.candidate_id,
                "execution_manifest_sha256": self.execution_manifest_sha256,
                "source_receipt_sha256": self.source_receipt_sha256,
                "parity_manifest_sha256": self.parity_manifest_sha256,
                "trader_ids": list(self.trader_ids),
                "store_paths": list(self.store_paths),
                "one_shot_status": self.one_shot_status,
                "guard_blockers": list(self.guard_blockers),
                "authorized_to_emit_first_fresh_outcome": (
                    self.authorized_to_emit_first_fresh_outcome
                ),
                "fresh_outcomes_already_emitted": False,
                "ready_for_fresh_execution": self.ready_for_fresh_execution,
                "productive_authority": False,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def evaluate_phase22_pre_outcome_provenance(
    *,
    execution_manifest: dict[str, Any],
    store_contract: dict[str, Any],
    one_shot_guard: dict[str, Any],
) -> ArchitectAPhase22PreOutcomeReceipt:
    if execution_manifest.get("schema") != EXECUTION_SCHEMA:
        raise CiboCapitalManagementError("A pre-outcome execution schema drift")
    if execution_manifest.get("candidate_id") != CANDIDATE_ID:
        raise CiboCapitalManagementError("A pre-outcome execution candidate drift")
    if execution_manifest.get("fresh_outcomes_executed") is not False:
        raise CiboCapitalManagementError(
            "A pre-outcome execution manifest already contains outcomes"
        )
    if execution_manifest.get("productive_authority") is not False:
        raise CiboCapitalManagementError(
            "A pre-outcome execution manifest authority drift"
        )
    manifest_sha = execution_manifest.get("manifest_sha256")
    if (
        not isinstance(manifest_sha, str)
        or _SHA256_RE.fullmatch(manifest_sha) is None
    ):
        raise CiboCapitalManagementError("A pre-outcome manifest digest invalid")
    unsigned = dict(execution_manifest)
    unsigned.pop("manifest_sha256", None)
    computed = "sha256:" + hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    if computed != manifest_sha:
        raise CiboCapitalManagementError(
            "A pre-outcome manifest fingerprint drift"
        )

    bindings = execution_manifest.get("trader_bindings")
    if not isinstance(bindings, list) or len(bindings) != 7:
        raise CiboCapitalManagementError("A pre-outcome requires seven Traders")
    trader_ids = tuple(
        str(item.get("trader_id", ""))
        for item in bindings
        if isinstance(item, dict)
    )
    if trader_ids != CANONICAL_TRADER_IDS:
        raise CiboCapitalManagementError("A pre-outcome ordered Trader drift")

    if store_contract.get("schema") != STORE_SCHEMA:
        raise CiboCapitalManagementError("A pre-outcome store schema drift")
    if store_contract.get("store_reuse_allowed") is not False:
        raise CiboCapitalManagementError("A pre-outcome store reuse forbidden")
    if store_contract.get("fresh_outcomes_executed") is not False:
        raise CiboCapitalManagementError("A pre-outcome stores already consumed")
    if store_contract.get("productive_authority") is not False:
        raise CiboCapitalManagementError("A pre-outcome store authority drift")
    stores = store_contract.get("stores")
    if not isinstance(stores, list) or len(stores) != 5:
        raise CiboCapitalManagementError("A pre-outcome requires five stores")
    store_paths = tuple(
        str(item.get("relative_path", ""))
        for item in stores
        if isinstance(item, dict)
    )
    if store_paths != CANONICAL_STORE_PATHS:
        raise CiboCapitalManagementError("A pre-outcome store-path drift")

    if one_shot_guard.get("execution_manifest_sha256") != manifest_sha:
        raise CiboCapitalManagementError("A pre-outcome guard/manifest drift")
    if tuple(one_shot_guard.get("store_paths", ())) != CANONICAL_STORE_PATHS:
        raise CiboCapitalManagementError("A pre-outcome guard/store drift")
    blockers_raw = one_shot_guard.get("blockers")
    if not isinstance(blockers_raw, list):
        raise CiboCapitalManagementError("A pre-outcome blockers must be list")
    blockers = tuple(str(item) for item in blockers_raw)
    status = str(one_shot_guard.get("status", ""))
    already = one_shot_guard.get("fresh_outcomes_already_emitted")
    authorized = one_shot_guard.get("authorized_to_emit_first_fresh_outcome")
    if type(already) is not bool or type(authorized) is not bool:
        raise CiboCapitalManagementError("A pre-outcome guard flags invalid")
    if one_shot_guard.get("productive_authority") is not False:
        raise CiboCapitalManagementError("A pre-outcome guard authority drift")
    if already:
        raise CiboCapitalManagementError("A pre-outcome guard is already consumed")
    ready = status == "READY" and not blockers and authorized

    return ArchitectAPhase22PreOutcomeReceipt(
        candidate_id=CANDIDATE_ID,
        execution_manifest_sha256=manifest_sha,
        source_receipt_sha256=str(
            execution_manifest.get("source_receipt_sha256", "")
        ),
        parity_manifest_sha256=str(
            execution_manifest.get("parity_manifest_sha256", "")
        ),
        trader_ids=trader_ids,
        store_paths=store_paths,
        one_shot_status=status,
        guard_blockers=blockers,
        authorized_to_emit_first_fresh_outcome=authorized,
        fresh_outcomes_already_emitted=False,
        ready_for_fresh_execution=ready,
    )
