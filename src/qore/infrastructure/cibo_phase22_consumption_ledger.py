"""Durable fail-closed consumption ledger for the Phase22 V2 one-shot.

The historical holdout is too valuable to protect with process-local state.
A committed claim is therefore treated as a one-way barrier: once a GitHub
execution claims the frozen manifest, no second fresh execution may start,
even if the claiming run crashes before emitting an outcome.

No claim file is created by import or preflight. The execution workflow must
persist the claim to GitHub before reading/emitting fresh outcomes.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_SCHEMA = "qore.cibo.phase22.execution-consumption-receipt.v1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PHASE22_CONSUMPTION_RECEIPT_PATH = (
    _REPO_ROOT / "docs/research/CIBO-PHASE22-V2-CONSUMPTION-RECEIPT.json"
)


@dataclass(frozen=True, slots=True)
class Phase22ExecutionConsumptionReceipt:
    candidate_id: str
    execution_manifest_sha256: str
    outcomes_emitted: bool
    claim_committed: bool = False
    claim_head_sha: str | None = None
    claim_run_id: int | None = None
    claim_run_attempt: int | None = None
    outcome_bundle_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("Phase22 consumption candidate is required")
        if _SHA256_RE.fullmatch(self.execution_manifest_sha256) is None:
            raise ValueError("Phase22 consumption manifest digest invalid")
        if type(self.outcomes_emitted) is not bool:
            raise ValueError("Phase22 outcomes_emitted must be bool")
        if type(self.claim_committed) is not bool:
            raise ValueError("Phase22 claim_committed must be bool")
        if self.outcomes_emitted and not self.claim_committed:
            raise ValueError("Phase22 outcomes require a durable prior claim")
        if self.claim_committed:
            if self.claim_head_sha is None or _SHA1_RE.fullmatch(self.claim_head_sha) is None:
                raise ValueError("Phase22 durable claim HEAD invalid")
            if self.claim_run_id is None or self.claim_run_id <= 0:
                raise ValueError("Phase22 durable claim run id invalid")
            if self.claim_run_attempt is None or self.claim_run_attempt <= 0:
                raise ValueError("Phase22 durable claim run attempt invalid")
        elif any(
            value is not None
            for value in (
                self.claim_head_sha,
                self.claim_run_id,
                self.claim_run_attempt,
                self.outcome_bundle_sha256,
            )
        ):
            raise ValueError("Phase22 unclaimed receipt cannot carry claim metadata")
        if self.outcome_bundle_sha256 is not None:
            if not self.outcomes_emitted:
                raise ValueError("Phase22 outcome bundle requires emitted outcomes")
            if _SHA256_RE.fullmatch(self.outcome_bundle_sha256) is None:
                raise ValueError("Phase22 outcome bundle digest invalid")

    def payload(self) -> dict[str, Any]:
        return {"schema": _SCHEMA, **asdict(self)}


def load_phase22_execution_consumption_receipt(
    path: Path = CANONICAL_PHASE22_CONSUMPTION_RECEIPT_PATH,
) -> Phase22ExecutionConsumptionReceipt | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
        raise ValueError("Phase22 durable consumption receipt schema drift")
    fields = dict(raw)
    fields.pop("schema", None)
    return Phase22ExecutionConsumptionReceipt(**fields)


def build_phase22_execution_claim(
    *,
    candidate_id: str,
    execution_manifest_sha256: str,
    claim_head_sha: str,
    claim_run_id: int,
    claim_run_attempt: int,
) -> Phase22ExecutionConsumptionReceipt:
    return Phase22ExecutionConsumptionReceipt(
        candidate_id=candidate_id,
        execution_manifest_sha256=execution_manifest_sha256,
        outcomes_emitted=False,
        claim_committed=True,
        claim_head_sha=claim_head_sha,
        claim_run_id=claim_run_id,
        claim_run_attempt=claim_run_attempt,
    )


def mark_phase22_outcomes_emitted(
    *,
    claim: Phase22ExecutionConsumptionReceipt,
    outcome_bundle_sha256: str,
) -> Phase22ExecutionConsumptionReceipt:
    if not claim.claim_committed:
        raise ValueError(
            "Phase22 outcomes require durable prior claim; "
            "cannot finalize an uncommitted claim"
        )
    return Phase22ExecutionConsumptionReceipt(
        candidate_id=claim.candidate_id,
        execution_manifest_sha256=claim.execution_manifest_sha256,
        outcomes_emitted=True,
        claim_committed=True,
        claim_head_sha=claim.claim_head_sha,
        claim_run_id=claim.claim_run_id,
        claim_run_attempt=claim.claim_run_attempt,
        outcome_bundle_sha256=outcome_bundle_sha256,
    )


def persist_phase22_execution_claim(
    *,
    claim: Phase22ExecutionConsumptionReceipt,
    path: Path = CANONICAL_PHASE22_CONSUMPTION_RECEIPT_PATH,
) -> None:
    if not claim.claim_committed or claim.outcomes_emitted:
        raise ValueError("Phase22 claim persistence requires CLAIMED state")
    if path.exists():
        raise FileExistsError(
            "Phase22 durable consumption receipt already exists; fail closed"
        )
    _atomic_write(path=path, payload=claim.payload())


def persist_phase22_consumed_receipt(
    *,
    consumed: Phase22ExecutionConsumptionReceipt,
    path: Path = CANONICAL_PHASE22_CONSUMPTION_RECEIPT_PATH,
) -> None:
    if not consumed.claim_committed or not consumed.outcomes_emitted:
        raise ValueError("Phase22 consumed persistence requires CONSUMED state")
    existing = load_phase22_execution_consumption_receipt(path)
    if existing is None:
        raise FileNotFoundError(
            "Phase22 consumed receipt requires durable prior claim"
        )
    immutable_claim = (
        "candidate_id",
        "execution_manifest_sha256",
        "claim_head_sha",
        "claim_run_id",
        "claim_run_attempt",
    )
    for name in immutable_claim:
        if getattr(existing, name) != getattr(consumed, name):
            raise ValueError(f"Phase22 consumption claim drift: {name}")
    if existing.outcomes_emitted:
        raise FileExistsError("Phase22 outcomes were already durably emitted")
    _atomic_write(path=path, payload=consumed.payload())


def _atomic_write(*, path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
