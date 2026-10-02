"""Physical namespace contract for the five Phase22 V2 evidence stores.

The types used by the existing Phase20 durable machinery remain canonical, but
Phase22 must use disjoint physical files and hashes. This module creates no
outcomes and grants no authority.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PHASE22_STORE_ROOT = Path("phase22-v2-stores")


@dataclass(frozen=True, slots=True)
class Phase22StoreIdentity:
    name: str
    relative_path: str
    schema: str
    role: str

    def __post_init__(self) -> None:
        if not self.name or not self.relative_path or not self.schema or not self.role:
            raise CiboCapitalManagementError(
                "Phase22 store identity fields are required"
            )
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise CiboCapitalManagementError(
                "Phase22 store path must remain relative and contained"
            )

    def empty_payload(self) -> dict[str, object]:
        collection_key = {
            "HOLDOUT_FORWARD_EVIDENCE": "decisions_and_outcomes",
            "HOLDOUT_POLICY": "policy_decisions",
            "EXECUTED_RISK": "executed_risk",
            "CMA_SETTLEMENT": "settlements",
            "T20_RELEASE": "release_chain",
        }[self.name]
        return {
            "schema": self.schema,
            "phase": "PHASE22_V2",
            "store_name": self.name,
            "generation": 0,
            collection_key: [],
            "fresh_outcomes_executed": False,
            "productive_authority": False,
        }

    def empty_sha256(self) -> str:
        raw = json.dumps(
            self.empty_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return f"sha256:{sha256(raw).hexdigest()}"


PHASE22_STORE_IDENTITIES = (
    Phase22StoreIdentity(
        name="HOLDOUT_FORWARD_EVIDENCE",
        relative_path="phase22-v2-stores/holdout-forward-evidence.json",
        schema="CIBO_PHASE22_V2_FORWARD_EVIDENCE_BOOK_V1",
        role=(
            "predecision evidence plus counterfactual postdecision outcomes "
            "without historical broker identity"
        ),
    ),
    Phase22StoreIdentity(
        name="HOLDOUT_POLICY",
        relative_path="phase22-v2-stores/holdout-policy.json",
        schema="CIBO_PHASE22_V2_POLICY_BOOK_V1",
        role="frozen policy decisions bound to holdout decisions",
    ),
    Phase22StoreIdentity(
        name="EXECUTED_RISK",
        relative_path="phase22-v2-stores/executed-risk.json",
        schema="CIBO_PHASE22_V2_EXECUTED_RISK_BOOK_V1",
        role=(
            "Risk-authorized counterfactual execution-model initial stop risk "
            "without historical broker identity"
        ),
    ),
    Phase22StoreIdentity(
        name="CMA_SETTLEMENT",
        relative_path="phase22-v2-stores/cma-settlement.json",
        schema="CIBO_PHASE22_V2_CMA_SETTLEMENT_BOOK_V1",
        role=(
            "chronological counterfactual terminal settlement truth without "
            "historical broker deal identity"
        ),
    ),
    Phase22StoreIdentity(
        name="T20_RELEASE",
        relative_path="phase22-v2-stores/t20-release.json",
        schema="CIBO_PHASE22_V2_T20_RELEASE_BOOK_V1",
        role=(
            "chronological returned risk and margin capacity without "
            "historical broker deal identity"
        ),
    ),
)


def phase22_store_contract_payload() -> dict[str, object]:
    paths = tuple(item.relative_path for item in PHASE22_STORE_IDENTITIES)
    hashes = tuple(item.empty_sha256() for item in PHASE22_STORE_IDENTITIES)
    if len(paths) != len(set(paths)) or len(hashes) != len(set(hashes)):
        raise CiboCapitalManagementError(
            "Phase22 stores must have distinct paths and initial hashes"
        )
    return {
        "schema": "qore.cibo.phase22.store-contract.v1",
        "root": str(PHASE22_STORE_ROOT),
        "stores": [
            {
                **asdict(item),
                "empty_sha256": item.empty_sha256(),
            }
            for item in PHASE22_STORE_IDENTITIES
        ],
        "store_reuse_allowed": False,
        "counterfactual_historical_identity_safe": True,
        "broker_identity_fields_prohibited": True,
        "fresh_outcomes_executed": False,
        "productive_authority": False,
    }
