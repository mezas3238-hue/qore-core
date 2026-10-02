"""Fail-closed cross-boundary binding for Architect-2 T02 lifecycle evidence.

T02 must never accept a caller-provided boolean asserting that a QORE client
position lifecycle corresponds to a provider position.  This receipt is the
typed boundary that an authoritative forward-lifecycle producer must emit.

The receipt binds:
- the frozen forward decision and signal;
- the QORE client-position UUID;
- the entry/exit execution receipt UUIDs recorded by the lifecycle;
- the provider position id;
- canonical executed-risk identity/digest;
- canonical CMA settlement digest/deal ids;
- immutable source evidence.

Architect-2 validates and consumes this receipt but does not grant productive
authority and does not manufacture the external binding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from uuid import UUID

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

BINDING_ID = "CIBO_ARCH2_T02_PROVIDER_POSITION_BINDING_V1"
SOURCE_KIND = "CANONICAL_FORWARD_LIFECYCLE_PROVIDER_BINDING"


@dataclass(frozen=True, slots=True)
class T02ProviderPositionBindingReceipt:
    binding_id: str
    source_kind: str
    source_evidence_sha256: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    client_position_id: str
    entry_execution_receipt_id: str
    exit_execution_receipt_id: str
    provider_position_id: int
    execution_risk_evidence_id: str
    executed_risk_sha256: str
    settlement_sha256: str
    settlement_deal_ids: tuple[int, ...]
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.binding_id != BINDING_ID:
            raise CiboCapitalManagementError("T02 provider binding identity drift")
        if self.source_kind != SOURCE_KIND:
            raise CiboCapitalManagementError("T02 provider binding source kind drift")
        for name in (
            "source_evidence_sha256",
            "decision_evidence_sha256",
            "executed_risk_sha256",
            "settlement_sha256",
        ):
            _sha(getattr(self, name), name)
        if not self.signal_fingerprint or not self.execution_risk_evidence_id:
            raise CiboCapitalManagementError(
                "T02 provider binding signal/execution-risk identity required"
            )
        for name in (
            "client_position_id",
            "entry_execution_receipt_id",
            "exit_execution_receipt_id",
        ):
            value = getattr(self, name)
            try:
                UUID(value)
            except (TypeError, ValueError) as error:
                raise CiboCapitalManagementError(
                    f"T02 provider binding {name} must be canonical UUID"
                ) from error
        if self.entry_execution_receipt_id == self.exit_execution_receipt_id:
            raise CiboCapitalManagementError(
                "T02 provider binding entry/exit receipts must be distinct"
            )
        if (
            not isinstance(self.provider_position_id, int)
            or isinstance(self.provider_position_id, bool)
            or self.provider_position_id <= 0
        ):
            raise CiboCapitalManagementError(
                "T02 provider binding provider position id invalid"
            )
        if (
            not self.settlement_deal_ids
            or len(self.settlement_deal_ids) != len(set(self.settlement_deal_ids))
            or any(
                not isinstance(item, int)
                or isinstance(item, bool)
                or item <= 0
                for item in self.settlement_deal_ids
            )
        ):
            raise CiboCapitalManagementError(
                "T02 provider binding settlement deal ids invalid"
            )
        if self.canonical_ledger_modified or self.productive_authority:
            raise CiboCapitalManagementError(
                "T02 provider binding cannot modify ledger or grant authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T02 provider binding {name} must be canonical SHA-256"
        )
