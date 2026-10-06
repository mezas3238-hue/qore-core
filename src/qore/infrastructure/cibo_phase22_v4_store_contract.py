"""Dedicated physical store namespace for Phase22 V4.

V4 reuses the canonical replay book data classes, but never reuses the V2
physical namespace, schemas, files, or create-once identities.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_historical_replay_stores import (
    Phase22HistoricalReplayStoreSet,
    _evidence_book_to_json,
    _policy_book_to_json,
    _release_to_json,
    _risk_to_json,
)

PHASE22_V4_STORE_ROOT_NAME = "phase22-v4-stores"


@dataclass(frozen=True, slots=True)
class Phase22V4StoreIdentity:
    name: str
    filename: str
    schema: str

    @property
    def relative_path(self) -> str:
        return f"{PHASE22_V4_STORE_ROOT_NAME}/{self.filename}"


PHASE22_V4_STORE_IDENTITIES = (
    Phase22V4StoreIdentity(
        "HOLDOUT_FORWARD_EVIDENCE",
        "holdout-forward-evidence.json",
        "CIBO_PHASE22_V4_FORWARD_EVIDENCE_BOOK_V1",
    ),
    Phase22V4StoreIdentity(
        "HOLDOUT_POLICY",
        "holdout-policy.json",
        "CIBO_PHASE22_V4_POLICY_BOOK_V1",
    ),
    Phase22V4StoreIdentity(
        "EXECUTED_RISK",
        "executed-risk.json",
        "CIBO_PHASE22_V4_EXECUTED_RISK_BOOK_V1",
    ),
    Phase22V4StoreIdentity(
        "CMA_SETTLEMENT",
        "cma-settlement.json",
        "CIBO_PHASE22_V4_CMA_SETTLEMENT_BOOK_V1",
    ),
    Phase22V4StoreIdentity(
        "T20_RELEASE",
        "t20-release.json",
        "CIBO_PHASE22_V4_T20_RELEASE_BOOK_V1",
    ),
)


def phase22_v4_store_paths(root: Path) -> tuple[Path, ...]:
    _root(root)
    return tuple(root / item.filename for item in PHASE22_V4_STORE_IDENTITIES)


def assert_phase22_v4_store_pristine(root: Path) -> None:
    _root(root)
    if root.name != PHASE22_V4_STORE_ROOT_NAME:
        raise CiboCapitalManagementError(
            f"V4 store root must end with {PHASE22_V4_STORE_ROOT_NAME}"
        )
    paths = phase22_v4_store_paths(root)
    if len(paths) != len(set(paths)):
        raise CiboCapitalManagementError("V4 store paths are not disjoint")
    if any(path.exists() for path in paths):
        raise CiboCapitalManagementError(
            "V4 store surface is not pristine; fresh launch prohibited"
        )


def persist_phase22_v4_historical_store_set(
    *,
    root: Path,
    books: Phase22HistoricalReplayStoreSet,
) -> tuple[str, ...]:
    if not isinstance(books, Phase22HistoricalReplayStoreSet):
        raise CiboCapitalManagementError("V4 store set requires canonical books")
    assert_phase22_v4_store_pristine(root)

    payloads: dict[str, dict[str, object]] = {
        "HOLDOUT_FORWARD_EVIDENCE": _evidence_book_to_json(
            books.holdout_evidence
        ),
        "HOLDOUT_POLICY": _policy_book_to_json(books.holdout_policy),
        "EXECUTED_RISK": {
            "generation": books.executed_risk.generation,
            "executed_risk": [
                _risk_to_json(item) for item in books.executed_risk.executed_risk
            ],
        },
        "CMA_SETTLEMENT": {
            "generation": books.cma_settlement.generation,
            "settlements": [
                item.as_dict() for item in books.cma_settlement.settlements
            ],
        },
        "T20_RELEASE": {
            "generation": books.t20_release.generation,
            "release_chain": [
                _release_to_json(item) for item in books.t20_release.release_chain
            ],
        },
    }

    written: list[Path] = []
    for identity in PHASE22_V4_STORE_IDENTITIES:
        path = root / identity.filename
        _create_once(
            path=path,
            identity=identity,
            payload=payloads[identity.name],
        )
        written.append(path)
    return tuple(_file_sha256(path) for path in written)


def _create_once(
    *,
    path: Path,
    identity: Phase22V4StoreIdentity,
    payload: dict[str, object],
) -> None:
    if path.exists():
        raise CiboCapitalManagementError(
            f"V4 store already exists: {identity.name}"
        )
    full: dict[str, Any] = {
        "schema": identity.schema,
        "phase": "PHASE22_V4",
        "store_name": identity.name,
        **payload,
        "fresh_outcomes_executed": True,
        "counterfactual_historical_replay": True,
        "historical_broker_execution_claimed": False,
        "productive_authority": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(full, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _root(root: Path) -> None:
    if not isinstance(root, Path):
        raise TypeError("V4 store root must be pathlib.Path")
